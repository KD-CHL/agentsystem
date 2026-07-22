# AgentSystem 统一设计系统

版本：0.1  
状态：设计与前端实现的唯一视觉基线  
适用范围：桌面 Web、平板审批视图、移动只读与轻量审批视图

## 1. 设计语言

AgentSystem 是企业研发操作工具，视觉风格应当安静、可信、紧凑、可扫描。界面突出状态、证据和操作，不采用营销式大标题、装饰性渐变、发光背景或大面积玻璃效果。

关键词：`operational`、`high-trust`、`content-dense`、`evidence-first`、`developer-focused`。

### 必须遵守

- 页面只保留一个主要动作。
- 不用颜色单独表达状态。
- 不使用 emoji 作为导航或功能图标。
- 不使用负字间距；字号不随 viewport 宽度缩放。
- 卡片圆角不超过 8 px。
- 页面区块不做成层层嵌套的浮动卡片。
- 不使用装饰性渐变、光球、模糊色块或持续发光动画。
- 原始 JSON、日志和堆栈默认折叠，先展示可读摘要。

## 2. 颜色系统

所有组件只使用语义 token。禁止在业务组件中直接写颜色值。

### 2.1 浅色主题

| Token | 值 | 用途 |
| --- | --- | --- |
| `color-bg-canvas` | `#F5F7FA` | 应用背景 |
| `color-bg-surface` | `#FFFFFF` | 面板、抽屉、表格 |
| `color-bg-subtle` | `#EDF1F6` | 次级区域、hover |
| `color-bg-selected` | `#E7F0FF` | 选中项 |
| `color-border-default` | `#D4DCE7` | 分割线、边框 |
| `color-border-strong` | `#AEB9C8` | 强调边界 |
| `color-text-primary` | `#182230` | 标题、正文 |
| `color-text-secondary` | `#526174` | 说明、元数据 |
| `color-text-tertiary` | `#6C7B8E` | 占位与弱信息 |
| `color-primary` | `#2563EB` | 主要动作、焦点、链接 |
| `color-primary-hover` | `#1D4ED8` | 主要动作 hover |
| `color-on-primary` | `#FFFFFF` | 主要按钮文字 |

### 2.2 深色主题

| Token | 值 | 用途 |
| --- | --- | --- |
| `color-bg-canvas` | `#0B0E14` | 应用背景 |
| `color-bg-surface` | `#111722` | 面板、抽屉、表格 |
| `color-bg-subtle` | `#17202D` | 次级区域、hover |
| `color-bg-selected` | `#172A49` | 选中项 |
| `color-border-default` | `#2A3545` | 分割线、边框 |
| `color-border-strong` | `#46556A` | 强调边界 |
| `color-text-primary` | `#F3F6FA` | 标题、正文 |
| `color-text-secondary` | `#A8B3C2` | 说明、元数据 |
| `color-text-tertiary` | `#8290A3` | 占位与弱信息 |
| `color-primary` | `#6EA8FE` | 主要动作、焦点、链接 |
| `color-primary-hover` | `#8BBAFF` | 主要动作 hover |
| `color-on-primary` | `#08101E` | 主要按钮文字 |

### 2.3 语义颜色

每个状态同时使用图标、文本和颜色。背景使用对应颜色的低饱和透明或 tonal token。

| 语义 | 浅色前景 | 深色前景 | 使用场景 |
| --- | --- | --- | --- |
| Success | `#087A5B` | `#51D6A6` | 完成、健康、通过 |
| Warning | `#9A5B00` | `#F4C15D` | 待审批、预算、降级 |
| Danger | `#C93636` | `#FF8585` | 失败、拒绝、危险操作 |
| Info | `#2563EB` | `#79AEFF` | 运行、信息、链接 |
| Neutral | `#526174` | `#A8B3C2` | 空闲、取消、跳过 |

### 2.4 Agent 辅助色

Agent 色只用于图标、细边、拓扑连线和小型标记，不作为大面积页面背景。

| Agent | 色值 | 语义 |
| --- | --- | --- |
| Orchestrator | `#7567D9` | 调度与控制 |
| Repo Context | `#2F80ED` | 检索与上下文 |
| Planning | `#B7791F` | 规划与决策 |
| Coding | `#15966F` | 代码生成 |
| Test | `#4C79D8` | 验证与测试 |
| Security | `#D14F4F` | 安全与阻断 |
| Review | `#C26735` | 审查与反馈 |
| PR | `#0F8C95` | 交付与集成 |

## 3. 排版

### 3.1 字体栈

- UI：`Inter, "Noto Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif`
- 代码与数据：`"JetBrains Mono", "SFMono-Regular", Consolas, monospace`
- 私有化部署默认使用系统字体，外部字体不是关键依赖。

### 3.2 字号与行高

| Token | 字号 / 行高 | 用途 |
| --- | --- | --- |
| `text-xs` | 12 / 18 px | 时间戳、辅助元数据，不用于主要正文 |
| `text-sm` | 14 / 20 px | 表格、表单、常规正文 |
| `text-md` | 16 / 24 px | 对话、长说明、移动输入 |
| `text-lg` | 18 / 26 px | 面板标题 |
| `text-xl` | 20 / 28 px | 页面标题 |
| `text-2xl` | 24 / 32 px | 工作台关键数字或一级标题 |

字重：正文 400，标签与按钮 500，标题 600，关键数字 600。代码 ID、耗时和成本使用 tabular figures。

## 4. 间距与尺寸

### 4.1 间距刻度

使用 4 px 基础单位：`4, 8, 12, 16, 24, 32, 40, 48`。

- 控件内部：8 或 12 px。
- 同组控件：8 px。
- 表单字段：16 px。
- 面板内容：16 或 24 px。
- 页面区块：24 或 32 px。

### 4.2 稳定尺寸

| 元素 | 尺寸 |
| --- | --- |
| 顶部栏 | 56 px |
| 左导航展开/收起 | 232 / 64 px |
| 右侧 Agent 控制台 | 360-420 px |
| 底部事件控制台 | 默认 240 px，最小 160 px，最大 60vh |
| 常规按钮高度 | 36 px |
| 主要表单控件高度 | 40 px |
| 触控场景最小命中区域 | 44 x 44 px |
| 图标 | 16、18、20、24 px 四档 |
| 紧凑表格行高 | 40 px |
| 默认表格行高 | 48 px |

## 5. 边框、圆角与层级

- 小控件圆角：4 px。
- 按钮、输入、表格容器：6 px。
- 抽屉、对话框、重复卡片：8 px。
- 不使用 12 px 以上胶囊圆角承载普通文本；状态 badge 可使用全圆角。
- 默认依靠背景和 1 px 边框分层，阴影只用于浮层。
- 阴影：`0 8px 24px rgba(0, 0, 0, 0.16)`，深色主题不提高模糊强度。

层级 token：

| Token | z-index | 用途 |
| --- | --- | --- |
| `z-base` | 0 | 页面内容 |
| `z-sticky` | 20 | 粘性表头、任务条 |
| `z-popover` | 40 | 菜单、tooltip、popover |
| `z-drawer` | 80 | 抽屉 |
| `z-modal` | 100 | 对话框 |
| `z-toast` | 120 | Toast |

## 6. 图标

- 统一使用 Lucide 图标，默认 1.75 px stroke。
- 同一层级不混合 filled 与 outline 风格。
- icon-only 按钮必须有 tooltip 与 `aria-label`。
- Agent 身份使用图标容器加名称，不使用单字母作为最终产品图标。
- Provider 品牌标识只使用官方资产；无官方资产时使用通用 Server/Cloud 图标与文字名称。

## 7. 组件规范

### 7.1 按钮

- Primary：每个页面或对话框最多一个，用于当前最重要动作。
- Secondary：普通操作，如重新运行、打开产物。
- Ghost：工具栏低频操作。
- Danger：取消任务、拒绝、删除配置；与主要动作保持空间分隔。
- Icon：仅用于熟悉的工具动作，如刷新、复制、展开、关闭。

所有按钮包含 default、hover、pressed、focus、disabled、loading 状态。异步提交期间禁用重复提交，并保留按钮宽度。

### 7.2 表单

- 标签位于控件上方，不使用 placeholder 替代标签。
- 必填项、帮助文本和验证错误保持固定区域，避免布局跳动。
- 校验默认在 blur 或提交后触发；凭据、URL 连通性使用显式“测试连接”。
- 只读字段使用 `readonly` 语义和不同背景，不伪装成 disabled。
- API key 只接受 credential reference；不提供明文密钥回显。

### 7.3 表格

- 表头粘性，支持排序的列使用 `aria-sort`。
- 主要对象名固定在左侧；操作列固定在右侧。
- 单元格优先换行；ID、路径可截断但提供完整 tooltip 和复制按钮。
- 50 条以上分页，长事件流使用虚拟化和游标加载。
- 行 hover 不改变尺寸；选中行有背景和左侧指示条。

### 7.4 状态 Badge

Badge 结构：状态图标 + 本地化文本。默认高度 24 px，不能只显示彩色圆点。

| 状态 | 图标建议 | 语义色 |
| --- | --- | --- |
| 排队中 | Clock3 | Neutral |
| 运行中 | LoaderCircle | Info |
| 待审批 | CircleAlert | Warning |
| 已完成 | CircleCheck | Success |
| 失败 | CircleX | Danger |
| 已取消 | Ban | Neutral |
| 模拟 | FlaskConical | Warning |

### 7.5 面板与卡片

- 页面分区使用无框容器、分割线或表格。
- 卡片只用于重复对象、审批、产物和可独立操作的实体。
- 卡片内部不再放同风格卡片；需要分组时使用 section、列表或 divider。
- 面板标题使用 14-16 px，不使用 hero 级字号。

### 7.6 Tabs

- 用于同一对象的并列视图，如任务的进度、变更、测试和 Trace。
- 不用于一级导航。
- Tab 数量超过 7 时使用溢出菜单或二级导航。
- 切换后保留每个 Tab 的滚动和筛选状态。

### 7.7 Drawer 与 Modal

- Drawer：新建任务、Agent 检查器、事件详情等可保留背景上下文的操作。
- Modal：短确认、阻断错误和单一决策。
- 复杂配置使用独立页面，不塞入 Modal。
- 浮层有关闭按钮、Escape 支持和焦点陷阱；关闭后焦点返回触发元素。

### 7.8 代码、日志与 Diff

- 使用等宽字体和 tabular figures。
- 默认行高 20 px，字号 13 px；支持用户放大。
- 日志按级别、Agent 和事件类型过滤；不以纯颜色区分级别。
- Diff 提供统一、拆分两种视图；风险文件有图标和文本标签。
- 大文件增量加载，保留行号和可复制链接。

### 7.9 对话

- 消息按发送者和 Agent 分组，不使用社交聊天气泡的夸张样式。
- 显示时间、发送者、目标 Agent、调用模式和上下文版本。
- Agent 输出中的建议、动作和引用产物使用结构化块。
- 输入区支持 Agent 选择、附件、上下文范围和发送状态。

## 8. 工作流与拓扑

- 默认使用 Step 时间线表达顺序、状态、耗时和阻塞。
- 拓扑画布用于展示并行与 handoff，必须提供“自动布局”和时间线替代。
- 连接线类型使用线型加图例：数据流实线、控制流虚线、handoff 点线。
- 节点尺寸固定；状态更新不能改变节点宽高。
- 未知进度显示 indeterminate，不显示推算百分比。
- 画布支持键盘选择、缩放、适配视图和重置；不要求精准拖拽完成关键操作。

## 9. 动效

- 微交互 150-200 ms，抽屉和 Modal 200-300 ms。
- 进入使用 ease-out，退出更短并使用 ease-in。
- 只动画 transform 和 opacity，不动画 width、height、top、left。
- 运行中状态可使用低频旋转图标；不使用持续脉冲发光。
- `prefers-reduced-motion` 下关闭非必要动画，保留即时状态变化。

## 10. 响应式

| 断点 | 规则 |
| --- | --- |
| >= 1440 | 三栏任务工作台，左导航展开，右侧控制台可固定 |
| 1024-1439 | 左导航收起，右侧控制台改为抽屉 |
| 768-1023 | 页面单栏，任务证据与 Agent 使用标签切换 |
| < 768 | 只保留核心查看、对话和审批；隐藏复杂配置能力 |

页面禁止整体横向滚动。代码和表格在明确容器内滚动，并提供移动端替代布局。

## 11. 可访问性

- 正文对比度 >= 4.5:1，UI 图形和大字 >= 3:1。
- 焦点环使用 2 px `color-primary`，外加 2 px 与背景分离的 offset。
- 页面标题层级连续；每页一个 `h1`。
- 动态更新通过 `aria-live`；Toast 不抢焦点。
- 拖拽、画布和鼠标 hover 均提供键盘与点击替代。
- 图表提供文字摘要和数据表。
- 浅色、深色分别测试，不以颜色反转推断可访问性。

## 12. 设计 Token 实现约定

- Token 分为 primitive、semantic、component 三层。
- 主题只重映射 semantic token，组件不判断主题。
- Agent 辅助色由数据映射，不能覆盖成功、警告、危险状态色。
- CSS 自定义属性使用 `--as-` 前缀，例如 `--as-color-bg-surface`。
- 前端组件通过 Storybook 展示主题、语言、密度、状态和可访问性用例。

## 13. 页面级覆盖

页面特例放入 `design-system/pages/<route>.md`。覆盖文件只能描述与本规范不同的部分，不复制整份规则。无覆盖文件时必须完全遵循本规范。

## 14. 交付检查

- 图标来自统一图标库且有可访问名称。
- 所有点击目标在触控场景 >= 44 x 44 px。
- 控件在 hover/pressed/focus/disabled/loading 下不产生布局跳动。
- 表单错误位于字段附近，并包含恢复方法。
- 深浅主题的文字、边框、状态和焦点均可区分。
- 375、768、1024、1440、1920 px 无重叠、截断和页面级横向滚动。
- 200% 缩放、键盘、屏幕阅读器和减少动画检查通过。
