# AgentSystem 重构实施报告

日期：2026-07-18  
对应设计：[重构前诊断](refactor-diagnostic.md) 与 [目标产品和架构](refactor-target-design.md)。

## 1. 已交付

### 身份与安全

- 新增 `AuthService`、本地用户、scrypt 密码、哈希会话、HttpOnly Cookie 和会话撤销。
- 建立 Admin、Operator、Reviewer、Viewer 四角色权限矩阵。
- `/api/v1` 默认认证，所有业务资源验证权限与 tenant；task/project 的 tenant 和 owner 由服务端 Principal 写入。
- 旧版 API 在认证模式下仅允许 Admin，移除通过 `X-AgentSystem-User` 冒充审批人的路径。
- 用户管理支持创建、角色调整、禁用、密码更新和“最后一个活动管理员”保护。
- 响应增加 request ID、`nosniff`、same-origin referrer 和 deny-frame 安全头。

### 数据与查询

- 将动态 `0001` 固化为稳定初始迁移，新增可逆 `0002_identity_rbac`。
- 新增 users/auth_sessions；为 task/project/audit 增加 tenant、owner 和查询索引，并回填历史 JSON payload。
- SQLite 启用 WAL、busy timeout 和 foreign keys。
- 任务列表支持多状态、优先级、关键字、limit/offset；总数通过 `X-Total-Count` 返回。
- 新增服务端运营摘要和审计查询，避免浏览器下载全部任务后计算。

### 产品界面

- 增加登录页、真实账户菜单、退出、用户与权限页面。
- 导航、创建任务、项目选择、审批、取消/重跑、Agent 对话和 Agent Studio 按角色显示。
- 任务队列 All/Active 和搜索改为真实服务端过滤，搜索请求有短延迟。
- Operations 改用服务端 summary 与 audit；删除任务页无行为的 More 控件。
- 修复测试环境 `localStorage`，保留中文/英文、深色/浅色/跟随系统。
- 页面采用路由级懒加载，首屏主 JS 从约 502 KB 降至 445 KB，构建不再触发 500 KB chunk 警告。

### 工程化

- `bootstrap/dev/start` 统一应用 Alembic；新增 `scripts/check.sh`。
- 增加认证、角色、旧 API 绕过、租户隔离、会话撤销、SQLite 重启、查询、运营和审计测试。
- 新增诊断、目标架构、认证运行和数据库升级文档。

## 2. 数据迁移与回滚

- 升级：`.venv/bin/alembic upgrade head`。
- 回滚身份层：`.venv/bin/alembic downgrade 0001_local_mvp`。
- 回滚会删除 users/auth_sessions 和新增查询列，但保留原 task/project/audit payload。
- 重要数据库升级前应停止 worker，并同时备份 SQLite 主文件与 WAL 文件。
- 本轮升级前的本地备份为 `data/agentsystem.db.before-0002-20260717.bak`。

## 3. 验证范围

- 后端：认证/RBAC、租户边界、审批竞争、worker 持久化、模型网关、工具策略和 API 回归。
- 前端：主题、语言、Agent 配置、登录行为、TypeScript 和生产构建。
- 迁移：现有数据库升级，以及全新临时库的 upgrade/downgrade/upgrade 往返。
- 浏览器：工作台、任务队列、用户页、运营审计、主题切换、控制台错误和页面横向溢出。

最终命令与结果在完成验收后以本报告最后一节为准。

## 4. 明确保留的后续工作

- OIDC/SCIM、组织与团队映射、个人访问令牌和登录限流需要产品/身份基础设施决策。
- PostgreSQL repository 应移除 `SQLiteStore -> InMemoryStore` 全量镜像继承，并规范化其余 payload/FK。
- 生产执行仍需容器或 microVM sandbox；本地 worktree/copy 不构成不可信代码的强隔离。
- GitHub App 的真实 push/PR、webhook 签名和分支保护策略需要企业 GitHub 权限方案。
- 通知中心、批量任务、保存筛选、对象存储、备份保留和 HA 属于下一生产里程碑。

## 5. 最终验收结果

执行 `scripts/check.sh` 的结果：

- Python 编译检查通过；后端 `pytest` 共 35 项全部通过。
- 前端 Vitest 共 4 个测试文件、5 项测试全部通过。
- TypeScript 检查与 Vite 生产构建通过，主入口产物为 445.44 KB（gzip 141.30 KB）。
- Alembic 当前版本为 `0002_identity_rbac (head)`。
- 现有数据库升级通过；全新临时库的 upgrade/downgrade/upgrade 往返通过。
- 唯一非阻断提示为 FastAPI TestClient 依赖的 Starlette `httpx` 弃用警告，后续随上游迁移到 `httpx2`。

浏览器运行态验收结果：

- 工作台、All/Active 服务端筛选、关键字搜索、用户页深链刷新、运营审计和主题切换可用。
- 375、768、1024、1280、1440 px 视口均有有效内容、无页面级横向溢出、无错误遮罩或控制台错误。
- 375 px 验收发现并修复移动端 Grid 最小内容宽度撑开顶栏的问题；修复后顶栏和主内容均严格落在视口内，新建任务按钮完整可操作。
- 独立临时数据库以 `AGENTSYSTEM_AUTH_MODE=local` 启动成功；管理员登录、HttpOnly Cookie 会话和用户权限页通过浏览器验证。
- 临时登录验收服务与数据库已和主运行数据隔离，验收后服务已停止。

最终全量门禁在响应式修复后再次执行，结果仍为后端 35 项、前端 5 项全部通过，生产构建和迁移版本检查通过。
