# AgentSystem 重构前诊断报告

日期：2026-07-17  
范围：`src/agentsystem`、`frontend/src`、`migrations`、`tests`、启动脚本与现有设计文档。

## 1. 当前产品与核心链路

AgentSystem 当前是一个面向本地代码项目的多 Agent 协作工作台。用户选择项目目录并创建任务后，确定性工作流依次调度 Orchestrator、Repo Context、Planning、Coding、Test、Security、Review 和 PR Agent。计划、推送及创建 PR 可进入人工审批；Agent 可独立配置 provider、model、凭据引用与模拟/实时模式。

主链路已经贯通：

1. React 工作台通过 `/api/v1/tasks` 创建任务。
2. FastAPI 创建 Task/Run/Job，持久化到 SQLite。
3. durable worker 领取任务并驱动 Agent handoff。
4. Agent Runtime 通过 Model Gateway 选择模拟或真实 provider，并调用受限工具。
5. Step、审批、模型调用、工具调用、产物和事件统一绑定 task/trace。
6. 前端通过查询轮询和 SSE 展示任务、Agent 状态、对话、产物与事件。

## 2. 基线验证

| 项目 | 结果 | 备注 |
| --- | --- | --- |
| 后端测试 | 28 passed | 真实 HTTP transport 测试需要本机 loopback 权限；授权环境下全部通过 |
| 前端生产构建 | passed | Vite 产物约 487 KB JS、54 KB CSS（压缩前） |
| 前端测试 | failed | Node 测试环境缺少可用 `localStorage`，i18n/theme 在模块加载时直接访问 |
| 数据库版本 | `0001_local_mvp` | migration 通过 `metadata.create_all/drop_all` 创建或删除全部表 |
| Git 状态 | 不适用 | 当前目录不是 Git 仓库，无法创建重构分支或输出分支差异 |

## 3. 功能矩阵

| 能力 | 当前状态 | 判断 |
| --- | --- | --- |
| 项目目录选择与文件预览 | 可用 | 保留并加强租户、所有者和审计边界 |
| 任务工作流、恢复、取消 | 可用 | 保留；补充并发状态测试和查询层 |
| 多 Agent 状态、Trace、对话 | 可用 | 保留；补充权限与可观测聚合 |
| 模拟/真实模型路由 | 可用 | 保留；凭据不进入数据库明文 |
| 人工审批 | 可用 | 保留；仅 reviewer/operator/admin 可决策 |
| 身份认证 | 缺失 | P0；当前请求头可伪造，默认管理员直通 |
| RBAC 与租户隔离 | 缺失 | P0；`tenant_id` 可由客户端提交，读取无边界校验 |
| 用户管理 | 缺失 | P0/P1；需支持角色、禁用和本地会话 |
| 任务检索与分页 | 不完整 | P1；当前加载全部任务，筛选按钮不生效 |
| 运营聚合与审计查询 | 不完整 | P1；指标在浏览器端由全量任务计算 |
| 通知中心 | 缺失 | P2；审批与失败没有集中待办入口 |
| GitHub 真正推送/PR | 适配边界 | P2；无凭据时为 mock，需产品/基础设施决策 |
| 生产级隔离执行 | 不满足 | P0（生产）；本地 worktree/copy 不是安全沙箱 |

## 4. 问题清单

### P0：必须先修复

| 问题 | 证据 | 风险 | 处理 |
| --- | --- | --- | --- |
| 可伪造身份 | `api_v1.actor()` 信任 `X-AgentSystem-User` | 任意调用者可冒充审批人或管理员 | 引入服务端会话、HttpOnly Cookie、统一 Principal |
| 无权限检查 | `/api/v1` 所有业务端点直接执行 | 凭据、Agent 配置、审批等高权限动作可被越权调用 | 建立 RBAC permission matrix 和 endpoint dependency |
| 租户由客户端控制 | `TaskCreate.tenant_id`、`WorkspaceOpen.tenant_id` | 可跨租户写入与读取 | 服务端覆盖 tenant，所有资源按 Principal 校验 |
| 生产沙箱能力不足 | 工具运行依赖本地副本/进程 | 不可信代码可能读取或消耗宿主资源 | 本地版本明确风险；生产接容器/受管 sandbox |

### P1：本轮核心可用性

| 问题 | 证据 | 影响 | 处理 |
| --- | --- | --- | --- |
| JSON payload 数据模型 | 大多数表仅有 `payload` 和少量索引 | 查询、约束、关联和迁移成本高 | 渐进增加 owner/tenant/status 等查询列，不一次性破坏 payload 兼容性 |
| 内存镜像全量加载 | `SQLiteStore._load_all()` 读取所有记录 | 数据增长后启动和内存不可控 | 本轮为查询增加 SQL 路径；后续拆除 InMemoryStore 继承 |
| 任务列表不可查询 | API 返回全量列表 | 页面增长后慢，筛选不可用 | 增加 status/q/priority/limit/offset 和 total header |
| 无服务端运营指标 | Operations 页面客户端聚合 | 指标不准确且无法授权 | 增加 operations summary 与审计列表 |
| 前端存在空操作 | Task `More`、All/Active | 用户无法判断操作是否生效 | 删除空操作，筛选改为真实状态 |
| 测试环境不稳定 | import 时访问 `localStorage` | 前端 CI 无法可靠执行 | 安全 storage adapter + jsdom setup |

### P2/P3：后续演进

- 将 legacy 无版本 API 设为只读兼容层并在一个版本后删除。
- 将 JSON payload 拆为规范化列和对象存储 artifact；增加真实 FK、唯一约束和保留策略。
- 增加审批/失败通知中心、批量任务操作、已保存筛选和组织级策略模板。
- 接入 OIDC/SCIM、PostgreSQL、企业 Vault、容器或 microVM sandbox、真实 GitHub App。
- 增加 provider 级限流、熔断、预算告警、响应缓存和模型质量 eval 门禁。

## 5. 保留、重构与移除

**保留**：确定性工作流、八 Agent 分工、可插拔 Model Gateway、Keychain 凭据、SSE、Trace、workspace 副本、中文/英文和主题能力。

**重构**：身份上下文、API authorization、task/project ownership、数据库查询列、任务列表、运营与审计页面、前端会话边界。

**移除或降级**：可伪造用户头、用户可提交 tenant、无动作的控件、生产代码中的静默 mock 表述。`/legacy` 仅作为临时兼容入口，不再新增功能。

## 6. 结论

当前项目已不是静态演示，而是具备真实工作流和模型路由的本地 MVP；因此不需要推倒重写。正确路径是保留已验证主链路，先建立身份、权限和数据归属，再将读取与运营能力从内存/UI 聚合迁到服务端，最后替换生产基础设施适配器。
