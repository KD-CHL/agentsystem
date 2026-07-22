# MCP and Skill Configuration

AgentSystem keeps capabilities tenant-scoped and binds them to individual Agents. Administrators manage them in **Capability Center** at `/capabilities` or through `/api/v1`.

## MCP servers

Supported transports:

- `streamable_http` for local or approved internal HTTP MCP endpoints;
- `stdio` for allowlisted local commands when process launch is explicitly enabled.

Creating a server stores connection metadata only. `POST /api/v1/mcp-servers/{id}/validate` opens a real MCP session with the official Python SDK, initializes it, and persists the filtered tool catalog. `POST /api/v1/mcp-servers/{id}/tools/{tool}/invoke` invokes a validated, enabled, allowlisted tool and requires `agent:manage`.

Credentials are references to secrets held in macOS Keychain. For HTTP, the secret is sent through the configured header and scheme. For stdio, it is exposed only to the child process through the configured environment variable. Plaintext is not stored in SQLite, API responses, audit details, or Trace.

Default policy:

```dotenv
AGENTSYSTEM_MCP_NETWORK_ENABLED=true
AGENTSYSTEM_MCP_ALLOWED_HOSTS=127.0.0.1,localhost,::1
AGENTSYSTEM_MCP_STDIO_ENABLED=false
AGENTSYSTEM_MCP_STDIO_ALLOWED_COMMANDS=uv,uvx,npx,node,python,python3
```

Host matching is exact unless an administrator adds a `*.example.internal` pattern. Redirects are disabled. stdio commands must be bare allowlisted command names and arguments are passed directly without a shell.

## Skills

Select a directory containing `SKILL.md`. YAML frontmatter may provide `name`, `description`, and `version`; the Markdown body becomes the trusted instruction text. Imports require UTF-8, enforce the configured byte limit, resolve symlinks, and remain within an allowed root.

```dotenv
AGENTSYSTEM_SKILL_ALLOWED_ROOTS=/Users/example/.codex/skills,/Users/example/company-skills
AGENTSYSTEM_SKILL_MAX_BYTES=65536
AGENTSYSTEM_SKILL_PROMPT_BUDGET_CHARS=24000
```

When no Skill root is configured, the current user's home directory is used. Refreshing a Skill reparses the source and records a new SHA-256 hash. Enabled, healthy Skills are added only to the system prompt of Agents to which they are bound. The aggregate prompt budget prevents unbounded instruction growth.

## API summary

- `GET/POST /api/v1/mcp-servers`
- `PATCH/DELETE /api/v1/mcp-servers/{id}`
- `POST /api/v1/mcp-servers/{id}/validate`
- `POST /api/v1/mcp-servers/{id}/tools/{tool}/invoke`
- `GET/POST /api/v1/skills`
- `POST /api/v1/skills/pick`
- `PATCH/DELETE /api/v1/skills/{id}`
- `POST /api/v1/skills/{id}/refresh`
- `GET/PUT /api/v1/agents/{agent}/capabilities`

Read operations require `agent:read`; changes, validation, invocation, and bindings require `agent:manage`. All lookups are restricted to the authenticated Principal's tenant and produce audit events.
