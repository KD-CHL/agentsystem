from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from datetime import timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from agentsystem.config import Settings
from agentsystem.credentials import CredentialBackendError, CredentialService
from agentsystem.domain import (
    AgentCapabilitiesUpdate,
    AgentCapabilityBindingRecord,
    AgentCapabilitySet,
    AgentName,
    CapabilityKind,
    CapabilityStatus,
    McpServerCreate,
    McpServerRecord,
    McpServerUpdate,
    McpToolDescriptor,
    McpToolInvokeResult,
    McpTransport,
    McpValidationResult,
    SkillImport,
    SkillRecord,
    SkillUpdate,
    utcnow,
)
from agentsystem.store import AlreadyExistsError, InMemoryStore, NotFoundError


class CapabilityError(RuntimeError):
    def __init__(self, code: str, message: str, *, network_attempted: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.network_attempted = network_attempted


class CapabilityRegistry:
    """Tenant-scoped registry for trusted Skill instructions and MCP servers."""

    _HEADER_NAME = re.compile(r"^[A-Za-z0-9-]+$")
    _ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    _TOOL_NAME = re.compile(r"^[A-Za-z0-9_.:/-]+$")

    def __init__(
        self,
        store: InMemoryStore,
        credentials: CredentialService,
        settings: Settings,
    ) -> None:
        self.store = store
        self.credentials = credentials
        self.settings = settings

    def create_mcp_server(self, tenant_id: str, payload: McpServerCreate) -> McpServerRecord:
        normalized = self._normalize_mcp_payload(payload)
        if normalized.credential_ref:
            self.store.get_credential(normalized.credential_ref)
        return self.store.add_mcp_server(
            McpServerRecord(tenant_id=tenant_id, **normalized.model_dump())
        )

    def update_mcp_server(
        self,
        tenant_id: str,
        server_id: str,
        payload: McpServerUpdate,
    ) -> McpServerRecord:
        current = self._mcp_for_tenant(server_id, tenant_id)
        changes = payload.model_dump(exclude_unset=True)
        candidate_data = current.model_dump(
            exclude={
                "id",
                "tenant_id",
                "status",
                "tools",
                "last_error",
                "last_validated_at",
                "version",
                "created_at",
                "updated_at",
            }
        )
        candidate_data.update(changes)
        normalized = self._normalize_mcp_payload(McpServerCreate.model_validate(candidate_data))
        if normalized.credential_ref:
            self.store.get_credential(normalized.credential_ref)
        updated = current.model_copy(
            update={
                **normalized.model_dump(),
                "status": CapabilityStatus.UNTESTED,
                "tools": [],
                "last_error": None,
                "last_validated_at": None,
                "version": current.version + 1,
            }
        )
        return self.store.update_mcp_server(updated)

    def list_mcp_servers(self, tenant_id: str) -> list[McpServerRecord]:
        return self.store.list_mcp_servers(tenant_id)

    def delete_mcp_server(self, tenant_id: str, server_id: str) -> McpServerRecord:
        self._mcp_for_tenant(server_id, tenant_id)
        return self.store.delete_mcp_server(server_id)

    def validate_mcp_server(self, tenant_id: str, server_id: str) -> McpValidationResult:
        server = self._mcp_for_tenant(server_id, tenant_id)
        try:
            tools, network_attempted = asyncio.run(self._discover_tools(server))
        except CapabilityError as exc:
            status = CapabilityStatus.BLOCKED if exc.code.endswith("_DISABLED") or exc.code == "MCP_HOST_BLOCKED" else CapabilityStatus.ERROR
            self.store.update_mcp_server(
                server.model_copy(
                    update={
                        "status": status,
                        "tools": [],
                        "last_error": self._safe_error(str(exc)),
                        "last_validated_at": utcnow(),
                    }
                )
            )
            return McpValidationResult(
                valid=False,
                status=status,
                message=self._safe_error(str(exc)),
                network_attempted=exc.network_attempted,
            )
        except Exception as exc:
            message = self._safe_error(str(exc))
            self.store.update_mcp_server(
                server.model_copy(
                    update={
                        "status": CapabilityStatus.ERROR,
                        "tools": [],
                        "last_error": message,
                        "last_validated_at": utcnow(),
                    }
                )
            )
            return McpValidationResult(
                valid=False,
                status=CapabilityStatus.ERROR,
                message=message,
                network_attempted=server.transport == McpTransport.STREAMABLE_HTTP,
            )
        updated = self.store.update_mcp_server(
            server.model_copy(
                update={
                    "status": CapabilityStatus.READY,
                    "tools": tools,
                    "last_error": None,
                    "last_validated_at": utcnow(),
                }
            )
        )
        return McpValidationResult(
            valid=True,
            status=updated.status,
            message=f"Connected and discovered {len(tools)} MCP tool(s).",
            tools=tools,
            network_attempted=network_attempted,
        )

    def invoke_mcp_tool(
        self,
        tenant_id: str,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> McpToolInvokeResult:
        server = self._mcp_for_tenant(server_id, tenant_id)
        if not server.enabled:
            raise CapabilityError("MCP_SERVER_DISABLED", "Enable the MCP server before invoking a tool.")
        if server.status != CapabilityStatus.READY:
            raise CapabilityError("MCP_SERVER_NOT_READY", "Validate the MCP server before invoking a tool.")
        available = {tool.name for tool in server.tools}
        if tool_name not in available:
            raise CapabilityError("MCP_TOOL_NOT_FOUND", "The requested MCP tool is not in the validated tool catalog.")
        if server.tool_allowlist and tool_name not in server.tool_allowlist:
            raise CapabilityError("MCP_TOOL_BLOCKED", "The requested MCP tool is not in this server's allowlist.")
        return asyncio.run(self._invoke_tool(server, tool_name, arguments))

    def import_skill(self, tenant_id: str, payload: SkillImport) -> SkillRecord:
        parsed = self._parse_skill(payload.path)
        return self.store.add_skill(
            SkillRecord(tenant_id=tenant_id, enabled=payload.enabled, **parsed)
        )

    def list_skills(self, tenant_id: str) -> list[SkillRecord]:
        return self.store.list_skills(tenant_id)

    def update_skill(self, tenant_id: str, skill_id: str, payload: SkillUpdate) -> SkillRecord:
        skill = self._skill_for_tenant(skill_id, tenant_id)
        changes = payload.model_dump(exclude_unset=True)
        return self.store.update_skill(skill.model_copy(update=changes))

    def refresh_skill(self, tenant_id: str, skill_id: str) -> SkillRecord:
        skill = self._skill_for_tenant(skill_id, tenant_id)
        try:
            parsed = self._parse_skill(skill.source_path)
        except CapabilityError as exc:
            self.store.update_skill(
                skill.model_copy(
                    update={
                        "status": CapabilityStatus.ERROR,
                        "last_error": self._safe_error(str(exc)),
                        "last_loaded_at": utcnow(),
                    }
                )
            )
            raise
        return self.store.update_skill(
            skill.model_copy(
                update={
                    **parsed,
                    "status": CapabilityStatus.READY,
                    "last_error": None,
                    "last_loaded_at": utcnow(),
                }
            )
        )

    def delete_skill(self, tenant_id: str, skill_id: str) -> SkillRecord:
        self._skill_for_tenant(skill_id, tenant_id)
        return self.store.delete_skill(skill_id)

    def capabilities_for_agent(self, tenant_id: str, agent_name: AgentName) -> AgentCapabilitySet:
        bindings = self.store.list_agent_capability_bindings(tenant_id, agent_name)
        mcp_servers: list[McpServerRecord] = []
        skills: list[SkillRecord] = []
        for binding in bindings:
            try:
                if binding.capability_kind == CapabilityKind.MCP_SERVER:
                    mcp_servers.append(self._mcp_for_tenant(binding.capability_id, tenant_id))
                else:
                    skills.append(self._skill_for_tenant(binding.capability_id, tenant_id))
            except NotFoundError:
                continue
        return AgentCapabilitySet(agent_name=agent_name, mcp_servers=mcp_servers, skills=skills)

    def replace_agent_capabilities(
        self,
        tenant_id: str,
        agent_name: AgentName,
        payload: AgentCapabilitiesUpdate,
    ) -> AgentCapabilitySet:
        mcp_ids = list(dict.fromkeys(payload.mcp_server_ids))
        skill_ids = list(dict.fromkeys(payload.skill_ids))
        for server_id in mcp_ids:
            self._mcp_for_tenant(server_id, tenant_id)
        for skill_id in skill_ids:
            self._skill_for_tenant(skill_id, tenant_id)
        now = utcnow()
        bindings = [
            AgentCapabilityBindingRecord(
                tenant_id=tenant_id,
                agent_name=agent_name,
                capability_kind=CapabilityKind.MCP_SERVER,
                capability_id=server_id,
                created_at=now,
                updated_at=now,
            )
            for server_id in mcp_ids
        ] + [
            AgentCapabilityBindingRecord(
                tenant_id=tenant_id,
                agent_name=agent_name,
                capability_kind=CapabilityKind.SKILL,
                capability_id=skill_id,
                created_at=now,
                updated_at=now,
            )
            for skill_id in skill_ids
        ]
        self.store.replace_agent_capability_bindings(tenant_id, agent_name, bindings)
        return self.capabilities_for_agent(tenant_id, agent_name)

    def prompt_context(self, tenant_id: str, agent_name: AgentName) -> str:
        capabilities = self.capabilities_for_agent(tenant_id, agent_name)
        sections: list[str] = []
        remaining = self.settings.skill_prompt_budget_chars
        for skill in capabilities.skills:
            if not skill.enabled or skill.status != CapabilityStatus.READY or remaining <= 0:
                continue
            content = skill.instructions[:remaining]
            remaining -= len(content)
            sections.append(
                f"\n[Trusted configured skill: {skill.name}]\n{content}\n[End configured skill]"
            )
        ready_servers = [
            server
            for server in capabilities.mcp_servers
            if server.enabled and server.status == CapabilityStatus.READY
        ]
        if ready_servers:
            catalog = [
                {
                    "server": server.name,
                    "tools": [
                        {"name": tool.name, "description": tool.description}
                        for tool in server.tools
                        if not server.tool_allowlist or tool.name in server.tool_allowlist
                    ],
                }
                for server in ready_servers
            ]
            sections.append(
                "\nConfigured MCP catalog (availability metadata only; never claim a tool was called "
                f"unless a tool result is supplied):\n{json.dumps(catalog, ensure_ascii=True)}"
            )
        return "".join(sections)

    def trace_manifest(self, tenant_id: str, agent_name: AgentName) -> dict[str, Any]:
        capabilities = self.capabilities_for_agent(tenant_id, agent_name)
        return {
            "skills": [
                {"id": item.id, "name": item.name, "enabled": item.enabled, "status": item.status}
                for item in capabilities.skills
            ],
            "mcp_servers": [
                {
                    "id": item.id,
                    "name": item.name,
                    "enabled": item.enabled,
                    "status": item.status,
                    "tool_count": len(item.tools),
                }
                for item in capabilities.mcp_servers
            ],
        }

    def policy_summary(self) -> dict[str, Any]:
        return {
            "network_enabled": self.settings.mcp_network_enabled,
            "allowed_hosts": self._split_setting(self.settings.mcp_allowed_hosts),
            "stdio_enabled": self.settings.mcp_stdio_enabled,
            "stdio_allowed_commands": self._split_setting(self.settings.mcp_stdio_allowed_commands),
            "skill_allowed_roots": [str(path) for path in self._skill_roots()],
            "skill_max_bytes": self.settings.skill_max_bytes,
        }

    def _normalize_mcp_payload(self, payload: McpServerCreate) -> McpServerCreate:
        data = payload.model_dump()
        data["name"] = payload.name.strip()
        data["description"] = payload.description.strip()
        data["args"] = [item.strip() for item in payload.args]
        data["tool_allowlist"] = list(dict.fromkeys(item.strip() for item in payload.tool_allowlist if item.strip()))
        if any(not self._TOOL_NAME.fullmatch(item) for item in data["tool_allowlist"]):
            raise CapabilityError("MCP_TOOL_NAME_INVALID", "Tool allowlist entries contain unsupported characters.")
        if not self._HEADER_NAME.fullmatch(payload.credential_header):
            raise CapabilityError("MCP_HEADER_INVALID", "Credential header must be a valid HTTP header name.")
        if payload.credential_env and not self._ENV_NAME.fullmatch(payload.credential_env):
            raise CapabilityError("MCP_ENV_INVALID", "Credential environment variable name is invalid.")
        if any("\x00" in item or "\n" in item or "\r" in item for item in data["args"]):
            raise CapabilityError("MCP_ARGUMENT_INVALID", "MCP command arguments cannot contain control characters.")
        if payload.transport == McpTransport.STREAMABLE_HTTP:
            if not payload.url:
                raise CapabilityError("MCP_URL_REQUIRED", "A Streamable HTTP MCP server requires a URL.")
            self._validate_url_shape(payload.url)
            data["url"] = payload.url.strip()
            data["command"] = None
            data["args"] = []
            data["credential_env"] = None
        else:
            command = (payload.command or "").strip()
            if not command:
                raise CapabilityError("MCP_COMMAND_REQUIRED", "A stdio MCP server requires a command.")
            if Path(command).name != command:
                raise CapabilityError("MCP_COMMAND_INVALID", "Use an allowlisted command name without a path.")
            data["command"] = command
            data["url"] = None
        return McpServerCreate.model_validate(data)

    async def _discover_tools(self, server: McpServerRecord) -> tuple[list[McpToolDescriptor], bool]:
        async with self._session(server) as session:
            result = await session.list_tools()
            tools = [self._tool_descriptor(item) for item in result.tools]
        if server.tool_allowlist:
            tools = [tool for tool in tools if tool.name in server.tool_allowlist]
        return tools, server.transport == McpTransport.STREAMABLE_HTTP

    async def _invoke_tool(
        self,
        server: McpServerRecord,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> McpToolInvokeResult:
        try:
            async with self._session(server) as session:
                result = await session.call_tool(tool_name, arguments=arguments)
        except CapabilityError:
            raise
        except Exception as exc:
            raise CapabilityError("MCP_TOOL_CALL_FAILED", self._safe_error(str(exc)), network_attempted=True) from exc
        output = result.model_dump(mode="json", by_alias=True, exclude_none=True)
        return McpToolInvokeResult(
            server_id=server.id,
            tool_name=tool_name,
            output=output,
            is_error=bool(getattr(result, "isError", False)),
        )

    def _session(self, server: McpServerRecord):
        if server.transport == McpTransport.STREAMABLE_HTTP:
            self._enforce_http_policy(server)
            return _HttpMcpSession(server, self.credentials)
        self._enforce_stdio_policy(server)
        return _StdioMcpSession(server, self.credentials)

    def _enforce_http_policy(self, server: McpServerRecord) -> None:
        if not self.settings.mcp_network_enabled:
            raise CapabilityError("MCP_NETWORK_DISABLED", "MCP network connections are disabled by server policy.")
        parsed = self._validate_url_shape(server.url or "")
        host = (parsed.hostname or "").casefold()
        allowed = self._split_setting(self.settings.mcp_allowed_hosts)
        if not any(self._host_matches(host, pattern.casefold()) for pattern in allowed):
            raise CapabilityError("MCP_HOST_BLOCKED", f"MCP host '{host}' is not in AGENTSYSTEM_MCP_ALLOWED_HOSTS.")

    def _enforce_stdio_policy(self, server: McpServerRecord) -> None:
        if not self.settings.mcp_stdio_enabled:
            raise CapabilityError("MCP_STDIO_DISABLED", "MCP stdio process launch is disabled by server policy.")
        allowed = set(self._split_setting(self.settings.mcp_stdio_allowed_commands))
        if (server.command or "") not in allowed:
            raise CapabilityError("MCP_COMMAND_BLOCKED", "The MCP stdio command is not in the server allowlist.")

    def _parse_skill(self, raw_path: str) -> dict[str, Any]:
        requested = Path(raw_path).expanduser()
        skill_file = requested / "SKILL.md" if requested.is_dir() else requested
        try:
            resolved = skill_file.resolve(strict=True)
        except OSError as exc:
            raise CapabilityError("SKILL_NOT_FOUND", "The selected directory does not contain a readable SKILL.md.") from exc
        if resolved.name != "SKILL.md" or not resolved.is_file():
            raise CapabilityError("SKILL_FILE_INVALID", "Select a Skill directory containing SKILL.md.")
        if not any(self._is_within(resolved, root) for root in self._skill_roots()):
            raise CapabilityError("SKILL_PATH_BLOCKED", "The Skill path is outside the configured allowed roots.")
        size = resolved.stat().st_size
        if size > self.settings.skill_max_bytes:
            raise CapabilityError("SKILL_TOO_LARGE", f"SKILL.md exceeds the {self.settings.skill_max_bytes}-byte limit.")
        try:
            raw = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise CapabilityError("SKILL_READ_FAILED", "SKILL.md must be readable UTF-8 text.") from exc
        metadata, instructions = self._parse_frontmatter(raw)
        name = str(metadata.get("name") or resolved.parent.name).strip()
        description = str(metadata.get("description") or "").strip()
        version_value = metadata.get("version")
        version = str(version_value).strip() if version_value is not None else None
        if not name or len(name) > 120:
            raise CapabilityError("SKILL_NAME_INVALID", "Skill metadata must contain a name of at most 120 characters.")
        if len(description) > 1000:
            raise CapabilityError("SKILL_DESCRIPTION_INVALID", "Skill description exceeds 1000 characters.")
        if not instructions:
            raise CapabilityError("SKILL_EMPTY", "SKILL.md has no instruction body.")
        return {
            "name": name,
            "description": description,
            "version": version,
            "source_path": str(resolved.parent),
            "instructions": instructions,
            "content_hash": sha256(raw.encode("utf-8")).hexdigest(),
            "last_loaded_at": utcnow(),
        }

    @staticmethod
    def _parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
        if not raw.startswith("---"):
            return {}, raw.strip()
        match = re.match(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n?(.*)$", raw, re.DOTALL)
        if not match:
            raise CapabilityError("SKILL_FRONTMATTER_INVALID", "SKILL.md frontmatter is not closed correctly.")
        try:
            metadata = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as exc:
            raise CapabilityError("SKILL_FRONTMATTER_INVALID", "SKILL.md frontmatter is invalid YAML.") from exc
        if not isinstance(metadata, dict):
            raise CapabilityError("SKILL_FRONTMATTER_INVALID", "SKILL.md frontmatter must be a YAML object.")
        return metadata, match.group(2).strip()

    def _mcp_for_tenant(self, server_id: str, tenant_id: str) -> McpServerRecord:
        server = self.store.get_mcp_server(server_id)
        if server.tenant_id != tenant_id:
            raise NotFoundError(server_id)
        return server

    def _skill_for_tenant(self, skill_id: str, tenant_id: str) -> SkillRecord:
        skill = self.store.get_skill(skill_id)
        if skill.tenant_id != tenant_id:
            raise NotFoundError(skill_id)
        return skill

    def _skill_roots(self) -> list[Path]:
        configured = self._split_setting(self.settings.skill_allowed_roots)
        roots = configured or [str(Path.home())]
        return [Path(item).expanduser().resolve() for item in roots]

    @staticmethod
    def _validate_url_shape(value: str):
        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise CapabilityError("MCP_URL_INVALID", "MCP URL must be an absolute HTTP(S) URL.")
        if parsed.username or parsed.password:
            raise CapabilityError("MCP_URL_INVALID", "MCP URL cannot contain embedded credentials.")
        return parsed

    @staticmethod
    def _tool_descriptor(tool: Any) -> McpToolDescriptor:
        schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None) or {}
        return McpToolDescriptor(
            name=str(getattr(tool, "name", "")),
            description=str(getattr(tool, "description", "") or "")[:1000],
            input_schema=schema if isinstance(schema, dict) else {},
        )

    @staticmethod
    def _host_matches(host: str, pattern: str) -> bool:
        if pattern.startswith("*."):
            suffix = pattern[1:]
            return host.endswith(suffix) and host != suffix[1:]
        return host == pattern

    @staticmethod
    def _split_setting(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    @staticmethod
    def _safe_error(message: str) -> str:
        redacted = re.sub(r"(?i)(authorization|api[-_ ]?key|token)(\s*[:=]\s*)\S+", r"\1\2[redacted]", message)
        return (redacted.strip() or "Capability operation failed.")[:800]


class _HttpMcpSession:
    def __init__(self, server: McpServerRecord, credentials: CredentialService) -> None:
        self.server = server
        self.credentials = credentials
        self._stack = AsyncExitStack()

    async def __aenter__(self) -> ClientSession:
        headers: dict[str, str] = {}
        if self.server.credential_ref:
            secret = self.credentials.resolve(self.server.credential_ref)
            value = f"{self.server.credential_scheme} {secret}".strip()
            headers[self.server.credential_header] = value
        try:
            client = await self._stack.enter_async_context(
                httpx.AsyncClient(
                    headers=headers,
                    timeout=float(self.server.timeout_seconds),
                    follow_redirects=False,
                )
            )
            read, write, _ = await self._stack.enter_async_context(
                streamable_http_client(self.server.url or "", http_client=client)
            )
            session = await self._stack.enter_async_context(
                ClientSession(
                    read,
                    write,
                    read_timeout_seconds=timedelta(seconds=self.server.timeout_seconds),
                )
            )
            await session.initialize()
            return session
        except Exception as exc:
            await self._stack.aclose()
            raise CapabilityError(
                "MCP_CONNECTION_FAILED",
                CapabilityRegistry._safe_error(str(exc)),
                network_attempted=True,
            ) from exc

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self._stack.__aexit__(exc_type, exc, traceback)


class _StdioMcpSession:
    def __init__(self, server: McpServerRecord, credentials: CredentialService) -> None:
        self.server = server
        self.credentials = credentials
        self._stack = AsyncExitStack()

    async def __aenter__(self) -> ClientSession:
        env = {
            key: value
            for key in ("PATH", "HOME", "TMPDIR", "LANG")
            if (value := os.getenv(key)) is not None
        }
        if self.server.credential_ref:
            if not self.server.credential_env:
                raise CapabilityError("MCP_ENV_REQUIRED", "Set a credential environment variable for this stdio server.")
            try:
                env[self.server.credential_env] = self.credentials.resolve(self.server.credential_ref)
            except CredentialBackendError as exc:
                raise CapabilityError("MCP_CREDENTIAL_UNAVAILABLE", str(exc)) from exc
        params = StdioServerParameters(
            command=self.server.command or "",
            args=self.server.args,
            env=env,
        )
        try:
            errlog = self._stack.enter_context(open(os.devnull, "w", encoding="utf-8"))
            read, write = await self._stack.enter_async_context(stdio_client(params, errlog=errlog))
            session = await self._stack.enter_async_context(
                ClientSession(
                    read,
                    write,
                    read_timeout_seconds=timedelta(seconds=self.server.timeout_seconds),
                )
            )
            await session.initialize()
            return session
        except Exception as exc:
            await self._stack.aclose()
            raise CapabilityError("MCP_CONNECTION_FAILED", CapabilityRegistry._safe_error(str(exc))) from exc

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self._stack.__aexit__(exc_type, exc, traceback)
