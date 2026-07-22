# AgentSystem 多 Agent 协作规则模型

## 1. 模型目标

本规则模型把多 Agent 协作从“自由对话”收敛为可恢复、可审计、可验证的工程工作流。确定性工作流拥有任务状态、审批、重试和恢复；Agent 只在自己的职责边界内处理上下文并产生结构化结果。

当前规则版本为 `1.0`，执行模式固定为 `simulated`。规则由 `CollaborationRuleEngine` 在运行时强制执行，缺失输入、缺失输出、非法交接或质量门禁不完整都会失败关闭。

## 2. 核心原则

1. **单一职责**：每个 Agent 只有一个主要目标，不共享模糊所有权。
2. **最小权限**：工具权限按 Agent 白名单分配，Orchestrator 不直接操作代码或 Shell。
3. **契约交接**：每次 handoff 必须满足必需输入、必需输出和允许的下游节点。
4. **版本化上下文**：每个成功 Agent 运行使 `context_version` 加一；审批暂停后恢复同一份上下文快照。
5. **质量共识**：进入 PR Agent 前，`tests_passed`、`security_passed`、`review_passed` 必须同时为真。
6. **失败关闭**：契约缺失、权限越界、Prompt Injection、密钥泄露和真实模型调用均不降级放行。
7. **人工升级**：计划、高风险路径和 PR 创建按照审批策略进入人工门禁。
8. **全链路归因**：任务、Run、Step、Agent、模型配置、工具、审批、产物和 handoff 使用同一 `trace_id`。

## 3. Agent 契约

| Agent | 必需输入 | 必需输出 | 允许交接 |
|---|---|---|---|
| Orchestrator | `prompt` | `workflow` | Repo Context |
| Repo Context | `workflow` | `likely_files`, `base_branch` | Planning |
| Planning | `likely_files`, `base_branch` | `plan`, `expected_paths` | Coding |
| Coding | `plan` | `branch_name`, `changed_paths` | Test |
| Test | `changed_paths` | `tests_passed` | Coding（失败）或 Security（通过） |
| Security | `changed_paths`, `tests_passed` | `security_passed`, `changed_paths` | Review |
| Review | `security_passed`, `tests_passed` | `review_passed`, `review` | PR |
| PR | 三项质量门禁 | `pr_url` | 结束 |

## 4. 决策与冲突处理

- Orchestrator 负责流程级决策，不覆盖专家结论。
- Test 失败时只能回到 Coding，最多自动修复两轮；超出预算使用 `TEST_REPAIR_EXHAUSTED` 终止。
- Security 的越权或密钥发现具有否决权；高风险路径可在策略允许时升级人工审批。
- Review 不能绕过 Test 或 Security 结论；PR Agent 不能自行修改代码。
- 人工拒绝为终态；`changes_requested` 转为 `input_required`，由用户补充上下文后创建新 Run。

## 5. 上下文与可观测性

每个 Workflow Run 持久化：

- `context_version`：成功交接次数。
- `context_snapshot`：当前结构化协作状态。
- `last_agent`：最近成功完成的 Agent。
- `handoff.received`：接收方、来源、可用键和上下文版本。
- `handoff.completed`：产生的键、目标 Agent 和新版本。

API `GET /api/v1/collaboration/rules` 返回当前实际生效的规则，可供 Agent Studio、运营治理和自动化测试读取。

## 6. 演进约束

- 新 Agent 必须先定义职责、工具、输入、输出、失败所有者和交接边。
- 规则版本升级需要迁移测试和至少一条端到端 eval。
- 并行执行只允许用于无写冲突的只读质量门禁，并由确定性汇合节点合并结论。
- 启用真实模型前必须新增 provider 隔离、预算熔断、凭据解析和出网策略测试；本版本明确禁止。
