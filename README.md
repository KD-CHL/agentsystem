# AgentSystem

AgentSystem is a local-first MVP for a private, enterprise multi-agent code collaboration platform. It includes a React operations workbench, SQLite persistence, a durable local worker, isolated task workspaces, approvals, trace replay, and an executable collaboration rule engine.

1. create a code task from an API or GitHub Enterprise webhook;
2. build repository context;
3. generate an implementation plan;
4. wait for human approval when policy requires it;
5. produce a minimal patch artifact;
6. run deterministic test/security/review gates;
7. create a draft PR through a GitHub Enterprise adapter, or a mock URL when no adapter credentials are configured;
8. expose the full trace for audit and replay.

The runtime supports deterministic simulation and explicit live API calls per Agent. Fresh profiles remain simulated; a network request is made only after an operator selects a live provider profile and supplies a Keychain credential or approved environment-variable reference.

## Product and Development Baseline

The next production iteration is defined in the project documentation:

- [Documentation index](docs/README.md)
- [Product requirements](docs/product-requirements.md)
- [UI/UX design specification](docs/ux-ui-design.md)
- [Target system architecture](docs/architecture.md)
- [Development and migration plan](docs/development-plan.md)
- [Refactor diagnostic](docs/refactor-diagnostic.md)
- [Target product and architecture](docs/refactor-target-design.md)
- [Refactor implementation report](docs/refactor-implementation-report.md)
- [Design system](design-system/MASTER.md)
- [Multi-Agent collaboration rules](docs/collaboration-rules.md)
- [Model provider configuration](docs/model-provider-configuration.md)
- [MCP and Skill configuration](docs/capability-configuration.md)

These documents distinguish the local MVP from the target production platform and provide requirement IDs, acceptance criteria, interface boundaries, security controls, and implementation milestones.

## Multi-Agent Model Routing

Each Agent has its own versioned model profile:

- provider, for example `openai`, `openai-compatible`, `qwen`, `deepseek`, or `local-vllm`;
- model name;
- API format (`responses` or `chat_completions`);
- a macOS Keychain credential reference or API key environment variable name;
- optional model base URL.

Provider presets supply safe defaults while model IDs and endpoints stay editable. Agent Studio can store a key once in macOS Keychain, discover models through `/models`, validate connectivity, and switch each Agent independently between live and simulated execution. Secret values are never stored in traces, task records, API responses, or the UI.

## MCP and Skills

The Capability Center registers Streamable HTTP or stdio MCP servers, imports local `SKILL.md` packages, and binds either capability to individual Agents. MCP validation uses the official Python SDK to initialize a session and discover the server's tool catalog. A protected invocation endpoint is available for validated, enabled, allowlisted tools.

Skill instructions are hash-tracked and injected only into the system prompt of bound Agents. Agent traces record capability IDs, names, status, and tool counts without copying Skill instructions or secrets. MCP authentication reuses macOS Keychain credential references.

The local defaults allow HTTP MCP only on `127.0.0.1`, `localhost`, and `::1`; stdio process launch is disabled. Expand `AGENTSYSTEM_MCP_ALLOWED_HOSTS` for approved internal servers, or explicitly enable stdio together with a narrow command allowlist. See [the capability configuration guide](docs/capability-configuration.md).

## Executable Collaboration Rules

`CollaborationRuleEngine` validates every Agent entry, exit, and handoff. Each contract defines required inputs, required outputs, allowed downstream Agents, least-privilege tools, and failure ownership. Workflow context is persisted with a monotonically increasing version so an approval resumes the exact same collaboration state.

Before PR packaging, Test, Security, and Review must all report a passing result. Missing contract data, an illegal handoff, or an incomplete quality consensus fails closed with a stable error code. The active model is available at `GET /api/v1/collaboration/rules` and in Operations & Governance.

See `.env.example` for the per-Agent variables such as `AGENTSYSTEM_CODING_MODEL`, `AGENTSYSTEM_CODING_API_KEY_ENV`, and `CODING_AGENT_API_KEY`.

The console layout is inspired by ChatPilot's persistent sidebar workbench: the left sidebar shows the selected task and every Agent's live workflow status, while the main area keeps task creation, model routing, task lists, approvals, artifacts, and trace replay.

## ChatPilot Integration

This project now folds ChatPilot-style interaction into the AgentSystem control plane without importing a second frontend stack:

- local project opening through `POST /workspaces/open`;
- project file listing and safe text preview through `/workspaces/{id}/files` and `/workspaces/{id}/file`;
- task creation with `workspace_path`, so the Repo Context Agent can summarize a real local codebase;
- an AI collaboration chat panel on each task;
- per-message routing to a selected Agent, using that Agent's provider/model/API-key environment-variable profile;
- full trace attachment for chat messages and both live and simulated model calls.

ChatPilot is Apache-2.0 licensed: https://github.com/shibing624/ChatPilot. The current integration reuses its product pattern (chat workbench, model routing, chat history shape) while keeping AgentSystem's private code-collaboration workflow and security boundaries.

Chat uses the selected Agent profile: simulated profiles return deterministic replies, while live profiles call the selected provider and record redacted request metadata, latency, usage, and provider request ID.

## Local Run

```bash
scripts/bootstrap.sh
scripts/dev.sh
```

Open the console at:

```text
http://127.0.0.1:8000/
```

The new React workbench is served at `/`; the previous embedded console remains at `/legacy`.

### Authentication modes

The default `AGENTSYSTEM_AUTH_MODE=dev` keeps local development zero-config while the identity is injected by the server, not by a caller-controlled request header. Set `AGENTSYSTEM_AUTH_MODE=local` to enable password login, durable sessions, and user management:

```bash
export AGENTSYSTEM_AUTH_MODE=local
export AGENTSYSTEM_BOOTSTRAP_ADMIN_USERNAME=admin
export AGENTSYSTEM_BOOTSTRAP_ADMIN_PASSWORD='replace-with-a-long-random-password'
scripts/start.sh
```

The bootstrap password is used only when the user table is empty. Passwords are stored as salted scrypt hashes. Session tokens are random, stored only as SHA-256 hashes in SQLite, and delivered to the browser through an HttpOnly, SameSite=Lax cookie. Remove the bootstrap password from the process environment after the first administrator has been created.

Roles are `admin`, `operator`, `reviewer`, and `viewer`. The server enforces permission and tenant checks for tasks, approvals, projects, traces, Agent configuration, credentials, operations, audit, and user management. UI visibility is only a convenience; it is not the security boundary. Legacy API routes are administrator-only.

For a headless local-auth API session:

```bash
curl -sS -c /tmp/agentsystem-cookie \
  -H 'content-type: application/json' \
  -d '{"username":"admin","password":"replace-with-a-long-random-password"}' \
  http://127.0.0.1:8000/api/v1/auth/login

curl -sS -b /tmp/agentsystem-cookie http://127.0.0.1:8000/api/v1/tasks
```

Create a simulated task:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/tasks \
  -H 'content-type: application/json' \
  -d '{
    "repo_id": "github.example.com/acme/payments",
    "base_branch": "main",
    "prompt": "Fix the checkout retry bug and add tests",
    "workspace_path": "/Users/chl/Codespace/agentsystem",
    "approval_policy": "manual_all",
    "priority": "normal"
  }'
```

Open a local project and send a task-scoped Agent message:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/projects \
  -H 'content-type: application/json' \
  -d '{"path": "/Users/chl/Codespace/agentsystem"}'

curl -sS -X POST http://127.0.0.1:8000/api/v1/tasks/<task_id>/messages \
  -H 'content-type: application/json' \
  -d '{"agent_name": "coding", "content": "请定位最可能需要修改的文件"}'
```

Approve the pending plan:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/approvals/<approval_id>/decisions \
  -H 'content-type: application/json' \
  -d '{"action": "approve", "comment": "Plan approved"}'
```

Run tests:

```bash
.venv/bin/python -m pytest -q
npm --prefix frontend test
npm --prefix frontend run build
.venv/bin/python evals/run_local.py
```

Or run the complete local quality gate:

```bash
scripts/check.sh
```

`scripts/bootstrap.sh`, `scripts/dev.sh`, and `scripts/start.sh` apply Alembic migrations before serving the application. Before upgrading an important local database, stop the worker and back up `data/agentsystem.db` together with any active `-wal` file.

## Architecture Notes

- `WorkflowService` owns deterministic state, approvals, retries, context snapshots, and recovery.
- `DurableWorkflowWorker` leases SQLite jobs and reclaims expired work after a restart.
- `CollaborationRuleEngine` enforces Agent contracts and the final quality consensus.
- `AgentRuntime` executes bounded specialists and records handoff events for every run.
- `ToolExecutor` enforces per-agent tool permissions before any side effect.
- Git projects use a temporary worktree when possible; other projects are copied under `data/workspaces`.
- `GitHubEnterpriseAdapter` is the boundary for real GitHub Enterprise integration.
- `SecurityPolicy` centralizes prompt-injection, secret, high-risk-file, and command checks.
- `AuthService` owns local authentication, hashed sessions, role permissions, and the server-side Principal.
- `CapabilityRegistry` owns MCP policy enforcement, tool discovery/invocation, Skill parsing, and per-Agent capability bindings.
- API resource guards derive tenant and owner from the Principal; client-supplied identity and tenant values are ignored.
- Task search, operations metrics, and audit pagination execute on server-side query paths rather than downloading all records to the browser.
