# AgentSystem 统一设计系统

版本：0.2（Graphite Signal）
状态：设计与前端实现的唯一视觉基线
适用范围：桌面 Web、平板审批视图、移动只读与轻量审批视图

## 1. 设计语言

AgentSystem 是企业研发操作工具，视觉风格应当安静、可信、紧凑、可扫描。界面突出状态、证据和操作，不采用营销式大标题、装饰性渐变、发光背景或大面积玻璃效果。

v0.2 方向「Graphite Signal」：深石墨中性底色 + 钴蓝信号主色。相比 v0.1 的紫色调，更克制、更工程化，与语义色（绿/黄/红/橙/青）保持最大区分度。

关键词：`operational`、`high-trust`、`content-dense`、`evidence-first`、`developer-focused`。

### 必须遵守

- 页面只保留一个主要动作。
- 不用颜色单独表达状态（状态 = 图标 + 文字 + 色彩）。
- 不使用 emoji 作为导航或功能图标。
- 不使用负字间距；字号不随 viewport 宽度缩放。
- 卡片圆角不超过 10 px。
- 页面区块不做成层层嵌套的浮动卡片。
- 不使用装饰性渐变、光球、模糊色块或持续发光动画。
- 原始 JSON、日志和堆栈默认折叠，先展示可读摘要。
- 图表必须提供数据表格替代视图（无障碍）。

## 2. 颜色系统

所有组件只使用语义 token（`frontend/src/styles/tokens.css`）。禁止在业务组件中直接写颜色值。

### 2.1 深色主题（主角主题）

| Token | 值 | 用途 |
| --- | --- | --- |
| `--bg` | `#0a0c10` | 应用画布 |
| `--bg-elevated` | `#0f1218` | 顶栏、导航栏 |
| `--bg-subtle` | `#141821` | 次级区域、表头 |
| `--bg-hover` | `#1a1f2a` | hover 行 |
| `--panel` | `#0e1117` | 卡片、面板 |
| `--panel-strong` | `#131722` | 强调面板 |
| `--border` | `#232936` | 分割线、边框 |
| `--border-strong` | `#343c4d` | 强调边界 |
| `--text` | `#edf1f7` | 标题、正文 |
| `--text-muted` | `#9aa3b2` | 说明、元数据 |
| `--text-faint` | `#6d7686` | 占位与弱信息 |
| `--accent` | `#5b8cff` | 钴蓝信号色 |
| `--accent-strong` | `#82a9ff` | 强调文本/图标 |
| `--accent-soft` | `#16233d` | tonal 填充 |
| `--accent-action` | `#3d6ef5` | 主要按钮 |
| `--accent-action-hover` | `#3360d8` | 主要按钮 hover |

### 2.2 浅色主题

| Token | 值 |
| --- | --- |
| `--bg` | `#f5f6f8` |
| `--bg-elevated` | `#ffffff` |
| `--bg-subtle` | `#eceef2` |
| `--bg-hover` | `#e4e7ec` |
| `--panel` | `#ffffff` |
| `--panel-strong` | `#f8f9fb` |
| `--border` | `#d9dde4` |
| `--border-strong` | `#b6bec9` |
| `--text` | `#161a21` |
| `--text-muted` | `#55606e` |
| `--text-faint` | `#7a8494` |
| `--accent` | `#2f5fe8` |
| `--accent-strong` | `#2450c9` |
| `--accent-soft` | `#e8eefc` |
| `--accent-action` | `#2f5fe8` |
| `--accent-action-hover` | `#2650c9` |

### 2.3 语义颜色

| 语义 | 深色前景 | 浅色前景 | 使用场景 |
| --- | --- | --- | --- |
| Success `--green` | `#3ecf8e` | `#0e8a5f` | 完成、健康、通过 |
| Warning `--yellow` | `#e8b84d` | `#9a6a08` | 待审批、预算、降级 |
| Danger `--red` | `#f26d6f` | `#c53d47` | 失败、拒绝、危险操作 |
| Info `--cyan` | `#4cc9e8` | `#0e7fa8` | 运行中、实时、链接 |
| Risk-high `--orange` | `#e88a4a` | `#b25e21` | 高风险标记 |

每个语义色附带 `*-soft` tonal 背景 token（如 `--green-soft`）。

### 2.4 图表色板

`--chart-1` ~ `--chart-6`，按主题取值。系列 1 固定使用 `--chart-1`（钴蓝），其余按序分配。图表坐标轴使用 `--text-faint`，网格线使用 `--border`。

### 2.5 功能 token

| Token | 用途 |
| --- | --- |
| `--focus-ring` | 焦点环（双层 box-shadow） |
| `--backdrop` | 模态/命令面板遮罩 |
| `--shadow` | 浮层阴影（双层） |
| `--grid-dot` | 点阵背景 |

## 3. 排版

- UI：`Inter, "Inter Variable", ui-sans-serif, -apple-system, ..., "PingFang SC", "Noto Sans SC", sans-serif`
- 代码与数据：`"JetBrains Mono", ui-monospace, "SFMono-Regular", Consolas, monospace`
- 数字密集区域启用 `font-variant-numeric: tabular-nums`（code/pre/time/.tabular 自动应用）。
- 正文 14px / 行高 1.5；元数据 12px；徽章 11px；最小可读 11px。
- 字重：标题 700+，正文 400，元数据 500-650。

## 4. 形状与间距

- 圆角：`--radius-sm: 6px`（按钮、输入框、徽章）、`--radius-md: 10px`（卡片、面板、模态）。
- 结构尺寸：header 56px、导航栏 64px、侧边栏 286px、检查器 356px、事件控制台 210px。
- 间距基数 4px，常用 8/12/16/20/24。
- 触控目标最小 44×44px（移动端）。

## 5. 动效

- 基础过渡 `--transition: 160ms ease`，仅用于 hover/展开等微交互。
- 无装饰性动画；必须响应 `prefers-reduced-motion`。

## 6. 组件规范

### StatusBadge（共享组件）

`src/components/StatusBadge.tsx`。所有状态展示统一使用：图标 + 本地化文字 + tonal 色彩。禁止裸色点表达状态。

### CommandPalette（命令面板）

Cmd/Ctrl+K 唤起；遮罩使用 `--backdrop` + 4px 模糊；搜索源：页面/任务/项目/Agent；键盘全操作；空查询显示最近访问。

### ApprovalCard（审批证据卡片）

固定结构：类型图标+标签、风险徽章、状态徽章、触发策略（mono chip）、原因、影响范围、证据摘要（原始 JSON 折叠于 `<details>`）、元信息行、操作区（批准=唯一 primary / 要求修改 / 拒绝=danger）。

### ChartCard（图表卡片）

标题 + 副标题 + 「图表/表格」切换；图表区固定高度 220-260px；表格模式渲染底层数据。

## 7. 无障碍

- 焦点环 ≥2px，对比度：正文 ≥4.5:1，图形 ≥3:1。
- 图标按钮必须 aria-label；模态必须 aria-modal + 焦点管理。
- 事件流 aria-live polite；错误 role=alert。
- 图表提供表格替代；时间线提供文字替代。
