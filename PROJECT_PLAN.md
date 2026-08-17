# Cinematic Scene Case Library 制作计划

最后更新：2026-08-17

## 1. 项目目标

基于 Higgsfield 公开项目 `Hell Grind` 中的全部可读取生成资产 Prompt，建立一个名为 `cinematic-scene-case-library` 的轻量文本案例库 Skill。

案例库用于在影视视频提示词制作过程中检索、复刻、参考和优化优秀场景案例。它提供模型无关的场景范式以及面向不同视频模型的适配提示，但不负责生成图片、角色素材或视频资产。

项目地址：

`https://higgsfield.ai/generate?projectId=3caa2f3a-52b5-4293-9237-0c8f76c7158a`

目标安装目录：

`C:\Users\Admin\.agents\skills\cinematic-scene-case-library`

安装前所有制作和审核工作仅在当前工作区完成。

## 2. 已确认决策

1. 数据范围改为项目公开展示的全部生成资产 Prompt，不再尝试识别所谓“最终成片版本”。
2. 作者没有提供可靠的版本管理或最终采用标记。场景文件夹中的资产应视为制作过程语料，而不是天然的最终镜头清单。
3. 原始 Prompt 全集、抓取日志和分析中间结果只保留在工作目录，不进入最终 Skill。
4. 最终 Skill 只收录精华案例、模型无关范式、检索索引和轻量来源元数据。
5. 最终 Skill 不包含图片、视频、音频、缩略图、Base64 内容或其他重资产。
6. 素材生成继续由 `lira-image-prompts` 负责；案例库只处理场景提示词参考。
7. `cinema-studio-production` 仍作为 Seedance 工作流的统一入口，并在后续接受最小路由补丁以调用案例库。
8. 案例库必须验证对 Seedance 和 MiniMax H3 的可迁移性。模型专有语法不得污染模型无关范式。
9. 若需要安装任何 Python 依赖，必须先说明依赖名称、用途、版本范围、替代方案和安装影响，得到用户批准后才能安装。
10. 最终审核通过前不得写入本地 Skill 安装目录。
11. 案例库是低权限的检索与建议层，不是最终 Prompt 组装器。案例的 Prompt Content Score 只证明源 Prompt 的结构证据，不证明生成视频质量，也不能凌驾于用户锁定事实、目标模型规则或下游 Skill 的职责。
12. 禁止把完整源 Prompt、历史 `@tag`、源资产 ID、历史时长或模型专有语法直接注入下游 Prompt。源文只能作为可追溯证据；跨 Skill 交接必须先抽象、过滤并按下游职责裁剪。
13. Seedance 路径的所有权保持不变：`cinema-studio-production` 负责路由和集成，`acting-for-ai-video` 只负责表演层，`cinedance-seedance-director` 负责最终 Seedance Prompt 的结构组装与质量检查。
14. H3 路径保持独立：`minimax-h3-director` 自行编排并拥有最终 H3 Prompt；不得由 `cinema-studio-production` 包装或调用。官方 H3 语法、真实资产绑定规则和模型限制始终优先于案例建议。
15. 集成采用两条互不包装的路径：`cinema-studio-production -> 案例检索 -> ACTING/CINEDANCE -> Seedance 最终稿`；`minimax-h3-director -> 案例检索 -> 可选专家 -> H3 最终稿`。
16. 初始集成不直接修改 ACTING 或 CINEDANCE 使其强制检索案例。案例检索保持可选，只在需求抽象、缺少场景结构、请求修复或用户明确要求查找案例时触发；信息已具体且可拍时应跳过检索。
17. 案例库只返回经过筛选的指导包，并只向每个下游 Skill 传递其职责所需片段，避免 Prompt 膨胀、重复指令和所有权冲突。

## 3. 当前已知事实

通过公开页面只读检查已确认：

- 项目名称：`Hell Grind`
- 页面显示资产总数：`115451`
- 页面包含大量场景文件夹，例如 `Scene 69 - Fight`、`Scene 72: Roko vs Dagon`
- 单个场景文件夹包含大量候选生成，而不是一个最终版本
- `Scene 69 - Fight` 页面显示 146 个资产，首屏延迟加载 48 个视频资产
- 资产详情可读取完整 Prompt、模型、分辨率、创建时间和资产 ID
- 已验证样本资产：`bf48d11b-4b06-4429-84fa-3822399d5418`
- 样本类型：视频
- 样本模型：Seedance 2
- 样本分辨率：2016x864
- 样本时长：15 秒
- 样本 Prompt 长度：15674 字符
- 公共界面没有可依赖的 Final、Used in final cut、收藏或最终剪辑顺序标记

## 4. 非目标

- 不下载或封装原项目的图片、视频、音频和缩略图。
- 不把 115451 个资产逐条原样安装进最终 Skill。
- 不根据“最新”“第一条”或“最后一条”等未经证实的规则判断最佳版本。
- 不评价原作者的创作成败；只分析 Prompt 的可控性、可拍性和可迁移价值。
- 不让案例库取代 LIRA、ACTING、CINEDANCE 或 MiniMax H3 Director 的最终输出所有权。
- 不在当前阶段修改或安装任何现有本地 Skill。

## 5. 成功标准

### 5.1 抓取成功标准

- 找到公开、可重复、无需登录的 Prompt 数据获取路径。
- 仅下载文本和必要元数据，不下载媒体正文。
- 支持分页、断点续传、失败重试、限速和重复运行。
- 每条记录至少保留项目 ID、文件夹 ID/名称、资产 ID、资产类型、Prompt 原文和可用模型元数据。
- 对请求失败、空 Prompt、字段缺失、重复资产和解析异常逐条记录，禁止静默跳过。
- 先以 5 条样本验证，再进行单文件夹验证，最后才考虑全量抓取。

### 5.2 语料处理成功标准

- 原始语料保持不可变，清洗结果另存。
- 完全相同 Prompt 进行精确去重；近似 Prompt 只标记聚类，不删除原始记录。
- 素材引用描述与真正的场景动作正文可以区分。
- 所有排除、合并和入选决策可追溯到资产 ID。

### 5.3 案例库成功标准

- 每个精华案例包含来源、适用条件、Prompt-only 证据与置信度、限制说明、模型无关骨架、可迁移约束、变量槽位、下游交接、适配说明、禁止复制字段和质量检查。
- 检索结果必须是过滤后的指导包，至少包含案例 ID、适用条件、证据/置信度及注意事项、模型无关场景范式、可迁移约束、ACTING 交接、CINEDANCE/导演交接、Seedance/H3 适配说明和禁止复制字段。
- 原始 Prompt 或必要片段只用于来源审计并显式标记为不可直接注入；指导包不得携带可被误用的历史 `@tag`、源资产 ID、历史时长或未隔离的模型专有语法。
- Seedance 专有 `@tag`、章节结构和局部锁定规则只进入 Seedance 适配层。
- H3 的 Context-IR、T2VA/I2VA/FL2VA/L2VA/Ref2VA 关系、真实媒体标签和 4 至 15 秒限制只进入 H3 适配层。
- 案例检索是可选增强：抽象需求、场景结构缺失、Prompt 修复或显式案例查询能够命中；已经具体、可拍且无需修复的请求不会被强制扩写。
- 集成后职责所有权不变：案例库不输出最终 Prompt，ACTING 不接管镜头结构，CINEDANCE 仍最后组装 Seedance，`minimax-h3-director` 仍最后组装 H3。
- 只传递下游需要的片段；代表性测试中不得出现整段案例复制、同义指令重复或因案例注入导致的不必要 Prompt 增长。
- 最终 Skill 能按场景类型进行渐进式检索，不需要一次加载全部案例。
- 最终安装包不存在媒体文件。

## 6. 工作目录规划

```text
cinematic-scene-case-library-work/
├── PROJECT_PLAN.md
├── scripts/
│   ├── probe_higgsfield.py
│   └── fetch_prompts.py
├── data/
│   ├── raw/
│   ├── normalized/
│   └── reports/
├── logs/
└── skill/
    └── cinematic-scene-case-library/
```

说明：只有 `skill/cinematic-scene-case-library/` 是候选安装包。其余内容都是制作档案。

## 7. 执行阶段

### 阶段 0：范围和架构锁定

状态：已完成

已完成事项：

- 确认 Skill 名称、工作区路径和最终安装目录
- 确认不包含重资产
- 确认案例库是参考增强层
- 确认需要 Seedance 与 H3 的跨模型验证
- 确认 Python 依赖安装必须先审批

### 阶段 1：Python 数据获取可行性验证

状态：已完成并通过用户审核

步骤：

1. 使用 Python 标准库获取公开项目 HTML。
2. 提取页面引用的 JavaScript 资源 URL、嵌入数据和公开 API 线索。
3. 搜索项目、文件夹、资产分页和详情请求的端点结构。
4. 验证能否通过公开端点获取一个已知资产 ID 的 Prompt。
5. 验证能否列出一个已知文件夹的资产分页。
6. 实现只抓取 5 条 Prompt 的概念验证。
7. 输出字段样本、请求数量、响应状态和失败说明。

依赖策略：

- 首选 Python 标准库：`urllib.request`、`json`、`re`、`html.parser`、`sqlite3`
- 可以检测当前环境是否已经存在第三方包，但不能自行安装
- 若必须使用 `requests`、`httpx`、`playwright`、`beautifulsoup4` 等未安装包，先暂停并申请批准

阶段验收：

- 公开端点或可重复抓取方法得到验证
- 提交 5 条 Prompt 样本及其来源元数据
- 用户确认后才扩大到单文件夹

阶段 1 实际结果：

1. Python 标准库直接请求项目页面成功，HTTP 200，页面正文 188317 字节。
2. 从公开 JavaScript 中确认 API 基址为 `https://fnf-api-gw.higgsfield.ai/fnf`。
3. 在不安装 Selenium、Playwright 或 WebDriver 的前提下，使用 Python 标准库与本机已有 headless Chrome 的 DevTools Protocol 捕获页面真实 `XHR/fetch`。
4. 动态探测捕获 235 个非分析类请求和 186 个文本响应，0 个未处理错误；据此锁定以下公开端点：
   - 文件夹详情：`GET /fnf/folders/{folder_id}`
   - 子文件夹分页：`GET /fnf/folders/{folder_id}/children?size=100&sort_by=name`
   - 资产 Prompt 分页：`GET /fnf/folders/{folder_id}/items/v2?include_subfolders=true&size={size}&cursor={cursor}`
5. Prompt 响应 Schema 已验证为 `items[].job.params.prompt`；页游标位于顶层 `cursor`。
6. `fetch_prompts.py` 使用纯 `urllib` 成功抓取 5 条完整 Prompt，0 错误，总计 48425 字符：
   - `f1d9012c-fe27-4a69-9a95-a7869f680581`：video，Seedance 2.0，26648 字符
   - `58d7f18f-f547-43bd-ada8-3542afe10990`：image，Soul Cinema Studio，4598 字符
   - `8c1eabf6-edec-4c50-a23f-c77918885a52`：video，Seedance 2.0，4020 字符
   - `58ead793-6aa7-48b7-92fc-24f30e735165`：video，Seedance 2.0，11556 字符
   - `f156feb6-af85-44e8-b398-1700cac94f33`：image，Soul Cinematic，1603 字符
7. 5 条清洗后 Prompt 与原始响应逐字一致；资产 ID 和 Prompt SHA-256 均唯一；清洗报告不包含 CloudFront、CDN、缩略图、MP4 或 WebP URL。
8. 使用首屏返回的 cursor 请求下一页 1 条记录成功，新资产 ID 为 `4739fefc-cc5a-456e-9dc0-5a2342f82030`，与第一页不重复，Prompt 长度 12193 字符，下一 cursor 继续前进。
9. 未安装任何 Python 或 Node.js 依赖。最终 5 条 Prompt 与 cursor 验证均由纯 `urllib` JSON 请求完成，没有主动请求或保存媒体正文。
10. 早期 CDP 发现阶段加载了完整网页；虽然探测器没有捕获或保存媒体响应正文，浏览器仍可能在临时配置目录中请求过页面缩略图。该临时目录已清理，后续 CDP 运行也已改为显式阻断常见媒体后缀。

阶段 1 产物：

- 页面与脚本探测器：`scripts/probe_higgsfield.py`
- 无第三方 Python 依赖的 CDP 网络探测器：`scripts/capture_higgsfield_network.py`
- Prompt 分页抓取器：`scripts/fetch_prompts.py`
- 5 条完整 Prompt：`data/reports/five-prompt-samples.json`
- cursor 验证记录：`data/reports/pagination-probe.json`
- 公开请求捕获报告：`data/reports/network-capture-extended.json`
- 每次请求的原始 JSON：`data/raw/pages/`

阶段 1 已显式处理的问题：

- 默认沙箱最初阻止 `higgsfield.ai` 网络访问；在用户批准的公开页面访问范围内重试成功。
- `/share/{asset_id}` 在缺少 `folder_id` 时返回 `asset:null`，因此不采用资产 ID 单页枚举方案。
- 首轮 25 秒 CDP 捕获因国际化资源延迟没有看到项目 API，并暴露 Windows 临时目录清理时序错误；修正为 Chrome 退出后清理，并将观察窗口延长到 55 秒后成功。
- 两条离线 PowerShell 核验命令曾因管道语法和正则引号失败；已修正并重新执行，最终核验通过。

当前检查点：用户已审核阶段 1，并明确批准阶段 2。

### 阶段 2：稳健抓取器与单文件夹试运行

状态：已完成并通过用户审核

已批准试运行范围：

- 文件夹名称：`Scene 69 - Fight`
- 文件夹 ID：`52eefbe6-4d49-405a-a244-24ead11f2887`
- 页面预期资产数：`146`
- 子文件夹：无；API 请求固定使用 `include_subfolders=false`

步骤：

1. 实现显式分页，不猜测总页数。
2. 实现每页落盘和检查点，程序中断后从最后成功页继续。
3. 实现请求间隔、指数退避和最大重试次数。
4. 将 HTTP 错误、解析错误、空 Prompt 和缺失字段分别写入日志。
5. 禁止请求媒体正文；规范化记录不得包含媒体 URL，Prompt 内若出现 URL 必须显式记录并替换为占位符，原文仅保留在原始响应中。
6. 选择一个规模适中的场景文件夹做完整试运行。
7. 对页面显示数量、API 返回数量、唯一资产数量和非空 Prompt 数量进行对账。

阶段验收：

- 单文件夹抓取可恢复、可重复且数量对账通过
- 用户批准后才执行全项目抓取

阶段 2 实际结果：

1. 新增纯 Python 标准库抓取器 `scripts/crawl_folder_prompts.py`，固定 `include_subfolders=false`，支持显式 cursor 分页、逐页原始/规范化原子写入、稳定检查点、完成态短路、请求间隔、有限指数退避和重复 cursor 停止。
2. 新增 `tests/test_crawl_folder_prompts.py`，覆盖 Prompt URL 显式替换、重复 cursor 停止和完成态重跑零网络请求；3 项测试全部通过，并完成不写 `__pycache__` 的内存语法编译。
3. `Scene 69 - Fight` 共抓取 3 页，分页条目数为 50、50、46；API 条目数 146、唯一资产 ID 数 146、非空 Prompt 数 146，全部与页面预期数量 146 一致。
4. 146 条 Prompt 总计 2459060 字符，最短 11089 字符，中位数 17475 字符，最长 20388 字符；资产类型、任务类型和模型均为 `video` / `seedance_2_0` / `seedance_2_0`。
5. 146 个资产只对应 23 个唯一 Prompt 哈希；23 个 Prompt 均存在重复生成，共有 123 条超出每个唯一 Prompt 首条代表的精确重复资产。这些重复是语料事实，不作为抓取错误删除。
6. 三页原始 Prompt 与规范化 Prompt 逐字一致，资产 ID 顺序一致；0 条解析错误、0 条空 Prompt、0 个重复资产 ID、0 条 URL 替换警告，规范化记录中不存在 Prompt URL 或媒体元数据字段。
7. 全部请求仅访问 `fnf-api-gw.higgsfield.ai/fnf/folders/52eefbe6-4d49-405a-a244-24ead11f2887/items/v2`；事件日志累计记录 3 次 HTTP 请求。第一页单页验证 1 次，检查点续跑剩余两页 2 次。
8. 完成态重跑结果为 3 页、146 条、全部检查通过，且 `network_requests_this_invocation=0`；证明完整运行可重复且不会重新请求已完成文件夹。
9. 对账报告内置每页原始/规范化文件的字节数和 SHA-256 清单；合并语料位于 `data/runs/scene-69-fight/corpus.json`，最终对账位于 `data/runs/scene-69-fight/reconciliation.json`。
10. 未安装任何 Python 或其他依赖，未下载或保存图片、视频、音频和缩略图正文。

阶段 2 已显式处理的问题：

- 默认受限进程最初无法创建 `data/runs`；在用户已批准的当前工作区写入与公共 API 只读访问范围内重试后成功，没有改写阶段 1 文件。
- 实际文件夹 API 的 cursor 是浮点时间戳，而非仅字符串。初次规范化因此显式失败并保留原始第一页；修正为支持字符串、整数或浮点标量后，从已保存原始页恢复，恢复过程网络请求数为 0。
- 一次 `py_compile` 因既有 `scripts/__pycache__` 目录权限失败；没有删除或修改该目录，改用内存 `compile()` 复核成功，且完整单元测试可正常导入和执行脚本。

阶段 2 产物：

- 稳健单文件夹抓取器：`scripts/crawl_folder_prompts.py`
- 标准库行为测试：`tests/test_crawl_folder_prompts.py`
- 运行配置与检查点：`data/runs/scene-69-fight/config.json`、`checkpoint.json`
- 逐页原始与规范化数据：`data/runs/scene-69-fight/pages/`
- 合并 Prompt 语料：`data/runs/scene-69-fight/corpus.json`
- 对账与分布报告：`data/runs/scene-69-fight/reconciliation.json`
- 显式事件与错误日志：`data/runs/scene-69-fight/events.jsonl`

当前检查点：阶段 2 已完成且用户已批准阶段 3；阶段 3 的全量抓取与审计现已完成，等待用户审核。

### 阶段 3：全量抓取与原始语料审计

状态：已完成并通过用户审核

步骤：

1. 从项目根目录以 `include_subfolders=true` 单游标抓取全部公开资产元数据与 Prompt，并用文件夹清单补充场景归属。
2. 原始响应按页保存，避免单一超大文件损坏后无法恢复。
3. 同时建立 SQLite 索引，支持断点、去重和快速统计。
4. 输出文件夹数、资产数、Prompt 非空率、资产类型、模型分布和时间分布。
5. 输出完全重复 Prompt、近似重复候选、异常超短或超长 Prompt 列表。
6. 所有跳过项必须有明确原因。

阶段验收：

- 页面资产统计与抓取统计差异得到解释
- 用户审核完整性报告后进入规范化

阶段 3 规模预检与架构结果：

1. 新增 `scripts/inventory_project_folders.py`，通过公开根目录详情和 `/children` 分页完成文件夹树枚举；新增 4 项目录清单测试。
2. 文件夹清单得到 162 个目录（根目录 + 161 个后代），最大深度 3，根详情声明的 `folders_count=161` 与公开树总数闭合；所有派生直接资产数非负，合计 115451。
3. 根目录的 `subfolders_count=109` 与公开直属分页返回的 108 条存在一条显式 `public_child_count_mismatch` 警告。该差异不再静默忽略，也不用于决定 Prompt 是否抓取；完整公开树仍以总后代数和资产总数对账。
4. 逐文件夹直接抓取预计需要 1234 页，根目录 `include_subfolders=true` 单游标预计需要 1155 页。为避免父子目录计数口径造成漏抓，Prompt 主抓取路径锁定根级单游标；文件夹清单只用于资产的场景名称映射和审计。
5. 按 `Scene 69 - Fight` 的 146 条原始页估算，原始 JSON 约 2.35 GB；不生成等量规范化 JSON，改为 SQLite 保存全部资产行、唯一 Prompt 文本表、Prompt 到资产 ID 映射、分页元数据和问题记录。
6. 新增 `scripts/crawl_project_prompts.py`，新增 4 项项目抓取测试；SQLite 使用事务提交、WAL、原始页 SHA-256、浮点/字符串 cursor、断点恢复和完成态短路。
7. 项目根级单页真实验证已完成：2 页、200 个 API 条目、200 个唯一资产、200 条非空 Prompt、189 个唯一 Prompt，0 错误、0 警告；SQLite 字段不包含媒体 URL，Prompt 表中 URL 计数为 0。
8. 当前全量运行目录为 `data/runs/project-corpus/`，检查点位于第 3 页 cursor；已提交 2 页，后续不得删除或覆盖前两页原始 JSON。
9. 10 页稳定性窗口已完成：1000 个 API 条目、1000 个唯一资产、999 条非空 Prompt、861 个唯一 Prompt，10 个原始页与 10 个 SQLite 页记录一致，cursor 请求无重复。
10. 稳定性窗口发现 1 条空 Prompt（第 8 页第 25 项，资产 `d2eab1c6-59f7-4f4e-8874-841cefbaf711`），已作为 `empty_prompt` 错误保留资产行和审计记录；没有静默跳过。
11. 稳定性窗口模型分布为 `seedance_2_0=874`、`videotape-alpha=23`、模型缺失=103；全量统计必须保留这些差异，不得假定项目只使用单一模型。

阶段 3 已执行规则：

- 全量 Prompt 请求固定使用根目录 `include_subfolders=true`、`size=100`，串行低速请求，失败有限重试。
- 每页先原子保存原始 JSON，再在 SQLite 事务中写入资产、唯一 Prompt 和审计记录，最后原子推进检查点。
- 空 Prompt、字段缺失、重复资产 ID、未知文件夹、Prompt URL 和解析异常都必须进入 `issues`，不得静默跳过。
- 运行可在任意页安全中断；恢复优先读取已存在的原始页或已提交 SQLite 页，不重复请求。
- 阶段 3 完成条件是根资产总数、item occurrence 数、唯一资产数与 115451 对账，并提交重复 Prompt、模型/类型/时间分布和异常报告；完成后停止等待用户审核。

阶段 3 最终结果：

1. 根级 `include_subfolders=true` 抓取完成 1155 页，共收到 115451 条 API item occurrence；最后一页 51 条且下一 cursor 为 `null`。
2. 115451 条 occurrence 完整闭合为：115446 个唯一资产 + 4 次已审计的重复资产出现 + 1 条不支持的 `video_input` occurrence。4 个重复资产的 Prompt 与内容哈希一致，只是同时归属根目录和另一个文件夹；已通过 `asset_folder_memberships` 保留全部 115450 条资产-文件夹归属。
3. 115446 个唯一资产中，115309 个带非空 Prompt，137 个为空；非空语料按原始 SHA-256 折叠为 7517 个精确 Prompt 簇，其中 212 个单例、7305 个重复簇、107792 条超出各簇首条代表的精确重复记录。所有 115309 个 Prompt 资产均保留在簇映射中。
4. 来源问题共 142 条：137 条 `empty_prompt`、4 条 `duplicate_asset_id`、1 条 `unsupported_item_type`。这些问题均保留页码、页内索引和可用资产 ID，没有静默跳过；未知文件夹资产为 0。
5. 资产类型分布为 image 12970、video 102476；模型分布为 `seedance_2_0=101856`、`videotape-alpha=2640`、模型缺失 10950。语料确实包含多个生成管线，后续不得按 Seedance 单模型假设处理。
6. 1155 个原始页共 1838878093 字节（约 1.713 GiB）；逐页文件 SHA-256 全部匹配，页码连续、请求 cursor 无重复、事件日志可解析，SQLite `PRAGMA integrity_check=ok`，全部 12 项最终检查通过。
7. 长度审计基于 7517 个唯一 Prompt：最短 6 字符、P01 29、P05 151、中位数 6370、P95 28426、P99 35563、最长 39801；输出 79 个短文本候选和 76 个长文本候选，仅供后续人工审查，不自动排除。
8. 近似重复审计仅形成候选：75 个大小写/空白规范化组（150 个唯一 Prompt 成员）和 81 个独立数字规范化组（163 个唯一 Prompt 成员）。不自动合并、不删除、不按出现频率评分，后续仍须依据内容和可审计理由决定。
9. 完成态续跑执行了数据库结构迁移和多文件夹归属回填，网络请求数为 0；证明已完成语料不会被重复抓取。
10. `python -B -m unittest discover -s tests -v` 共 15 项测试全部通过；scripts 与 tests 共 11 个 Python 文件完成内存语法编译。未安装任何依赖，未下载媒体正文。

阶段 3 最终产物：

- 全量语料数据库：`data/runs/project-corpus/corpus.sqlite3`
- 原始分页响应：`data/runs/project-corpus/pages/raw/`
- 完成态与检查点：`data/runs/project-corpus/status.json`、`data/runs/project-corpus/checkpoint.json`
- 全局对账：`data/runs/project-corpus/audit/reconciliation.json`
- 原始页清单：`data/runs/project-corpus/audit/raw-page-manifest.json`
- 精确 Prompt 簇：`data/runs/project-corpus/audit/exact-prompt-clusters.json`
- 近似重复候选：`data/runs/project-corpus/audit/near-duplicate-candidates.json`
- 长度异常候选：`data/runs/project-corpus/audit/prompt-length-outliers.json`
- Prompt 与文件夹统计：`data/runs/project-corpus/audit/prompt-statistics.json`、`data/runs/project-corpus/audit/folder-statistics.json`

阶段 3 审核结论：审计状态为 `passed_with_audited_source_issues`。这表示抓取覆盖与存储完整性全部通过，同时 142 条来源数据问题被显式保留；不是“零问题”状态。用户已审核并明确批准进入阶段 4。

### 阶段 4：语料规范化与跨模型验证

状态：阶段 4B-5 全量规范化检查点已完成并通过自动封存，等待用户审核；未进入阶段 5

规范化层分为：

1. 来源层：资产、文件夹、模型和原始 Prompt
2. 素材引用层：角色、地点、道具、参考标签和资产描述
3. 模型无关场景层：目标、主体、空间、动作、表演、摄影、物理、光线、声音、连续性和约束
4. Seedance 适配层：`@tag`、第一帧、空间阻挡、镜头结构和本地失败锁
5. H3 适配层：Prompt Mode、Context-IR、真实媒体角色、时长限制和设置分离

验证方法：

- 从动作打斗、对白表演、环境建立等不同类型各选样本
- 分别转换为 Seedance 与 H3 合法结构
- 记录不可直接迁移的模型专有信息
- 判断哪些字段属于真正通用范式，哪些只能保留为模型适配规则

阶段 4 执行顺序：

1. 先定义五层规范化 Schema、字段来源、未知值策略和审计映射，不直接批量处理 7517 个唯一 Prompt。
2. 使用可复现的文本与文件夹条件，从动作打斗、对白表演、环境建立三类中分别抽取候选；候选筛选不使用 Prompt 重复生成次数作为质量权重。
3. 人工精读候选并各选一个代表样本，保留原始 Prompt SHA-256、全部来源资产 ID、文件夹归属、原模型和选样理由。
4. 将每个样本拆成来源层、素材引用层、模型无关场景层、Seedance 适配层和 H3 适配层；未知或无法从文本证明的字段保持 `null`，不得补写成来源事实。
5. 分别生成合法 Seedance 与 H3 验证稿，记录保留、重编码、删除、阻塞和不可直接迁移的字段；H3 参考标签只能绑定真实可访问媒体，文本中的 Seedance `@tag` 不得伪装成 H3 资产。
6. 提交 Schema、三个规范化样本、双模型验证结果和差异报告，停止等待用户审核；用户批准前不批量规范化全部语料。

阶段 4 当前已确认的模型边界：

- 通用层可以保存可见目标、主体、空间、动作因果、表演、摄影结果、物理、光线、声音、连续性和约束意图。
- Seedance 的 `@tag`、分节结构、第一帧占位锁、对角视场角表达和局部失败锁属于 Seedance 适配层。
- H3 的 T2VA/I2VA/FL2VA/L2VA/Ref2VA 模式、Context-IR 字段、`<Picture N>`/`<Subject N>`/`<Video N>`/`<Audio N>`、`(Sx)`、`<d>` 和 4 至 15 秒限制属于 H3 适配层。
- 同一模型无关场景可以派生不同模型的合法最终 Prompt，但不存在一种可原样提交给所有模型的“通用最终语法”。

阶段 4 小样本来源核验：

- 对白表演样本：Prompt SHA-256 `086a04b7f0f8e168bfcbf3183684e1cf275d57e59a3c639dbdabc0713867d658`，来源文件夹 `Scene 22`；Prompt 正文与 12 个资产元数据均为 4 秒，无时长冲突。
- 动作打斗样本：Prompt SHA-256 `166a0440f6f01e02419b42f47d088e1919dedd1800b62b4b632e0047cb446ba0`，来源文件夹 `Roko Fight`；Prompt 正文声明 10 秒，但 11 个资产元数据均为 15 秒。该冲突必须由人工决定适配稿使用哪个时长，Schema 必须同时保留两项来源及冲突状态。
- 最初的环境建立候选：Prompt SHA-256 `4cc914cfc71002094477dc6d2af542ae71fcede9fb57aacf5ad8a5a97e8698ab`，来源文件夹 `Scene Pizza Aerial`；Prompt 正文未声明时长，5 个资产元数据均为 6 秒。该候选后来因 6 秒、约 150 米下降距离和 `slow steady drift` 互相冲突而被替换，继续保留在候选审计文件中。
- 最终三条样本的完整 Prompt 与全部资产映射已重建到 `data/runs/stage-4-normalization/selected-source-records.json`，共覆盖 40 个资产。
- 动作样本原文在 10 秒叙事目标内安排约 14 个切分段。若生成模型适配稿减少切分或合并为较少的因果动作节拍，必须记录为适配决策，不得表述为原文结构。
- 用户已决定动作适配稿采用 15 秒资产元数据，并批准把原约 14 个切分段压缩为 5 个因果动作节拍；两项均作为用户批准的适配决策记录，原文 10 秒声明和原切分结构保持不变。
- 环境动态下降样本存在新的可拍性风险：6 秒内从约 150 米降至街面要求约 25 米/秒平均垂直速度，与原文的 `slow steady drift` 不相容。该问题不得通过暗改高度或速度静默修复。
- 已核验替代环境候选 Prompt SHA-256 `00e4c15e723379bb862770bb9c4a46093978048a29e2426de31e3c39fb512c89`：来源文件夹同为 `Scene Pizza Aerial`，17 个资产元数据均为 10 秒；约 600 米固定高空鸟瞰，镜头不移动，以暴雨、稀疏交通和高架列车形成画面内运动，不存在同类位移物理冲突。替换与否等待用户决定。
- 用户已批准使用 `00e4c15e723379bb862770bb9c4a46093978048a29e2426de31e3c39fb512c89` 替换原动态下降环境样本；原样本继续保留在候选审计文件中并记录未选原因，不进入本轮三个规范化样本。

阶段 4 小样本验证结果：

1. 建立 `normalization-schema.json`，将记录严格拆分为来源层、素材引用层、模型无关场景层、Seedance 适配层和 H3 适配层；人工或模型适配改写单独进入 `adaptation_decisions`。
2. 完成对白表演、动作打斗、环境建立三个规范化样本；源 Prompt 不复制到规范化记录，而是通过 SHA-256 指针解析到 `selected-source-records.json` 中的完整原文和全部资产映射。
3. 对白样本保留 4 秒单镜头、三段微表演、精确英文台词、侧向机位、实景光源和声音；Seedance 与 H3 T2VA 验证均通过。
4. 动作样本按用户决定采用 15 秒，并把原约 14 个切分段压缩为五个因果节拍；左右关系、体型差、受力链、慢动作范围、环境完整性和精确日语台词均在两个适配器中保留。
5. 环境样本采用用户批准的 10 秒静态高空候选；时长明确标记为 `asset_metadata_only`，不冒充 Prompt 正文声明；以暴雨、稀疏交通和一列高架列车提供画面内运动。
6. 三个 H3 稿均因当前没有真实媒体而使用 T2VA；没有伪造 `<Picture N>`、`<Subject N>`、`<Video N>` 或 `<Audio N>`。实际工作提供媒体后必须按真实角色重新选择 I2VA、L2VA、FL2VA 或 Ref2VA。
7. 三个 Seedance 稿均为无媒体文本验证稿；没有把源 `<<<...>>>` 或 UUID 伪装成当前可用 `@tag`。实际工作只有在用户提供真实当前资产后才能激活标签。
8. 纯标准库验证器检查 JSON Schema、源 Prompt 哈希和长度、40 个来源资产映射、元数据观察值、节拍连续性、语法隔离、H3 字段顺序、时长范围和逐字对白；正式报告为 `pass`、0 问题。
9. 当前全部 27 项单元测试通过；未安装依赖、未访问网络、未下载媒体。

阶段 4 产物：

- 五层 Schema：`data/runs/stage-4-normalization/normalization-schema.json`
- 三条完整源记录与 40 个资产映射：`data/runs/stage-4-normalization/selected-source-records.json`
- 三个规范化样本和双模型验证稿：`data/runs/stage-4-normalization/normalized-samples.json`
- 跨模型差异报告：`data/runs/stage-4-normalization/cross-model-validation-report.md`
- 结构与审计验证报告：`data/runs/stage-4-normalization/normalization-validation.json`
- 验证器：`scripts/validate_stage4_normalization.py`
- 验证测试：`tests/test_validate_stage4_normalization.py`

阶段 4 小样本审核结论：用户已明确批准 Schema、三个规范化样本、双模型验证稿和跨模型差异报告。该批准只关闭小样本检查点，不等于授权直接执行全量语义处理或进入阶段 5。

#### 阶段 4B：全量语料规范化执行方案（已获用户确认，按检查点执行）

语料边界复核：

- 全部精确唯一 Prompt：7517
- 至少用于视频资产的唯一 Prompt：6555
- 至少用于图片资产的唯一 Prompt：965
- 同时用于图片和视频的唯一 Prompt：3
- 纯图片 Prompt：962

推荐处理范围：

1. 对 6555 个“至少用于视频”的唯一 Prompt 执行全量结构化提取和模型无关语义归纳；同时用于图片和视频的 3 条仍按视频语料处理并保留双重资产来源。
2. 962 个纯图片 Prompt 保留在阶段 3 的完整来源审计和 Prompt 簇映射中，但不进入视频场景分类、案例评分或视频适配稿生成；静态资产 Prompt 继续属于 `lira-image-prompts` 的职责。
3. 不为 6555 条语料逐条生成完整 Seedance 与 H3 最终稿。阶段 4 已通过三个样本证明通用场景层可以迁移；逐条生成双模型长稿会放大存储、审校和幻觉风险，却不会帮助阶段 5 判断案例质量。
4. 对全部 6555 条建立轻量规范化记录；只有阶段 5 最终入选的精华案例才扩展为完整五层案例和双模型适配示例。

全量执行分为五个检查点：

##### 4B-1：确定性结构预处理

目标：不做审美或质量判断，只从源文和资产元数据提取可证明事实。

提取字段：

- Prompt SHA-256、原文长度和完整源记录指针
- 全部资产 ID、文件夹归属、模型、时长和分辨率观察值
- Prompt 内声明的时长、画幅、生成模式和模型名
- 引用标签、引用说明块、章节标题和镜头标记
- 显式对白、语言标签、说话人线索和音乐/静默声明
- CUT/SHOT 数量、可解析时间点、单镜头/多镜头声明
- 角色、环境、道具引用的文本跨度，不在此步改写其含义
- URL、空字段、来源冲突、解析失败和不支持结构

存储：继续使用 SQLite 作为主索引，长文本只保存一次；JSON 只输出清单、统计和审核样本，不生成数千个松散大文件。

验收：6555 个 Prompt 哈希全部闭合；所有解析失败显式记录；完成态重跑不重复处理；先用现有三条样本和不同长度分层样本验证后再全量运行。

##### 4B-2：风险和复杂度分层

目标：为后续语义处理分批，不进行质量评分。

分层维度：

- 单镜头、多镜头、未声明结构
- 有对白、无对白、对白疑似误判
- 动作密度、镜头密度、时长密度
- 明确环境建立、角色表演、动作交互或混合场景信号
- 引用密集、描述密集、模型专有语法密集
- 时长一致、时长缺失、Prompt 与资产时长冲突
- 超短、常规、超长 Prompt
- 结构完整、部分可解析、需要人工复核

约束：这些字段只决定处理队列和审核抽样，不能成为优秀案例分数。

验收：每条语料进入且只进入一个复杂度队列；多标签场景信号可以并存；频率仍不参与分层。

##### 4B-3：全量轻量语义规范化

目标：对 6555 条视频语料建立可检索、可比较、可进入阶段 5 评分的模型无关记录。

每条记录包含：

- 可见场景目标
- 主体和当前状态
- 空间关系和方向
- 核心动作及因果链摘要
- 表演、对白和反应摘要
- 摄影结果、光线、声音和物理规则
- 连续性与关键约束
- 素材引用角色及其是否具备真实媒体
- 缺失字段、来源冲突和不确定性
- Seedance/H3 可迁移性状态，不生成完整最终 Prompt

语义规则：

- 只总结源文可证明内容；不补写身份、动作、时长或参考关系。
- 删除模型语法时必须保留其可见或可听意图。
- 任何合并、压缩、冲突选择或推断都记录操作类型、理由和证据跨度。
- 无法可靠归纳的记录标记 `needs_manual_review`，不得输出貌似完整的假结果。
- 每个精确 Prompt 簇只处理一次，结果仍映射回全部来源资产。

验收：6555 条均有状态：`normalized`、`needs_manual_review` 或 `excluded_with_reason`；禁止静默跳过。

阶段 4B-3 样本实测结果：

- 新增 `scripts/normalize_video_prompt_semantics.py`，独立输出 `prompt_normalizations`、`normalization_assets`、`normalization_evidence` 和 `normalization_decisions`；目标库不复制完整 Prompt。
- 10 条回归样本使用 v6 首次运行 `processed=10`、`failed=0`，二次同参数运行 `processed=0`、`skipped=10`；逻辑摘要保持 `7d228a71814506437e12f6b69927a97c8a56748102c1136e8f8ed161c129b951`。
- 状态闭合为 `normalized=8`、`needs_manual_review=2`、`excluded_with_reason=0`。人工复核仅包含 24 字的 `connect these two clips` 欠定指令和 Unicode 损坏文本，不把可显式保留的时长、结构、引用或对白问题误判为处理失败。
- 10 条记录映射回全部 206 个来源资产；14 个素材引用均标记为 `described_only`，因为语料库只有来源元数据而没有可访问媒体字节，没有伪造 Seedance 或 H3 媒体绑定。
- 5 个来源冲突全部保持未解决：4 个时长冲突或多值观察、1 个单镜头/多镜头结构冲突；未擅自选择时长或镜头结构。
- 三个已批准样本的关键回归事实保持：对白样本为 4 秒且逐字保留 `Are you kidding me?`；动作样本保留 Prompt 10 秒/资产 15 秒冲突和逐字日语对白；环境样本保留 `asset_metadata_only` 的 10 秒来源和无对白状态。
- SQLite 含 848 条证据和 848 条变换决策；`integrity_check=ok`、外键错误 0、验证错误 0，源库、4B-1 库和 4B-2 库的内容身份均未改变。
- v6 在 v4 的跨行引用残片清理和伪对白拒绝基础上，修正超限字段只保留前 N 条造成的长 Prompt 尾部覆盖风险；候选按首/中/尾确定性保留，超长尾部无证据的记录转人工复核。专项测试 9/9、全部测试 51/51、Python 内存编译 25/25 通过。审核产物为 `data/runs/stage-4b-semantic-normalization-sample/manifest.json`、`report.json`、`review-sample.json`、`non-normalized-manifest.json` 和 `semantic_normalization.sqlite3`。

阶段 4B-3 全量实测结果：

- 使用 `stage4b-light-semantic-normalization-v6` 和固定配置处理全部 6555 条视频相关唯一 Prompt；首跑 `processed=6555`、`failed=0`，二次同参数运行 `processed=0`、`skipped=6555`。
- 三种终态完整闭合：`normalized=6494`、`needs_manual_review=61`、`excluded_with_reason=0`；人工复核包括原有 37 条语义欠定或过短来源文本、3 条 Unicode replacement 损坏文本，以及 21 条长 Prompt 尾部无确定性证据跨度的记录。没有静默跳过或把来源问题伪装成成功摘要。
- 复杂度队列与 4B-2 闭合：`complex=6069`、`standard=407`、`simple=76`、`manual_review=3`。
- 目标 SQLite 含 6555 条规范化记录、102530 条来源资产映射、582306 条证据和 582306 条变换决策；`integrity_check=ok`、外键错误 0、验证错误 0，无 `prompt_text` 列。
- 源库、4B-1 预处理库和 4B-2 分层库的内容身份均未改变；报告逻辑摘要为 `7e5cdc959b5102576494bd7c0cee4b032e7a2b92747bc7a5918a75c352740d16`。
- 全量审核 JSON 只保留确定性分层样本 58 条；`non-normalized-manifest.json` 保留全部 61 条人工复核哈希与原因。约 595 MB 的 `semantic_normalization.sqlite3` 按 GitHub 单文件限制仅本地保留并可由脚本重建，不纳入版本库。
- 全量产物为 `data/runs/stage-4b-semantic-normalization-full/manifest.json`、`report.json`、`review-sample.json` 和 `non-normalized-manifest.json`；已进入 4B-4 分层质量审计。

##### 4B-4：分层质量审计

审计方式：

- 对三个已批准样本做回归验证
- 按场景信号、长度、镜头结构、时长冲突和规范化状态进行分层抽样
- 逐项核对摘要是否有源文证据、对白是否逐字、时长是否保留来源、引用是否被伪造
- 检查模型专有语法没有进入中性字段
- 检查长 Prompt 没有因截断丢失结尾动作、对白或约束
- 对审计失败的规则只修复相应层并重新运行受影响记录

建议至少审核每个主要分层 20 条，并对全部 `needs_manual_review` 中的高价值场景候选人工复核。抽样数量可在 4B-2 得到真实队列规模后再提交用户确认，不在当前阶段猜定总量。

阶段 4B-4 实测结果：

- 新增 `scripts/audit_stage4b_semantic_normalization.py` 和 `tests/test_audit_stage4b_semantic_normalization.py`；审计不复制源 Prompt 或全量中间库，只输出确定性哈希清单、抽样元数据和失败清单。
- 全量闭合为 `6555` 条；分层抽样 `460` 条。复杂度队列、规范化状态、场景标签、文本长度、镜头结构和时长状态的每个主要值均至少抽取 20 条；仅有 3 条的 `manual_review` 队列全部纳入。
- 全部 `61` 条 `needs_manual_review` 进入 `manual-review.json`，其中 `27` 条含动作、表演或环境高价值场景信号并进入主审核样本。
- 逐条检查 `source_hash_and_length`、`asset_mapping_closure`、证据范围与 SHA-256、变换决策证据链接、字段来源、对白逐字保留、时长与结构冲突保留、引用 `described_only`、模型语法隔离、Seedance/H3 迁移状态和长 Prompt 尾部覆盖；6555 条全部通过，审计失败数为 `0`。
- 三条已批准回归样本全部通过：4 秒英文对白、10/15 秒动作时长冲突与日语对白、10 秒环境元数据时长与无对白状态均保持。
- 审计摘要为 `f2a029ed927193db4d6105a716c5ee511edcfd6c511879097d126684f78d8dd7`；产物为 `data/runs/stage-4b-quality-audit-full/manifest.json`、`report.json`、`audit-sample.json`、`manual-review.json` 和 `failures.json`。

##### 4B-5：全量规范化检查点

提交内容：

- 6555 条状态对账
- 结构、场景信号和风险分布
- 解析失败、人工复核和排除清单
- 分层抽样审计结果
- 规范化数据库与不可变源记录之间的哈希映射
- 未解决问题和进入阶段 5 的建议

停止条件：用户审核并批准全量规范化结果前，不进入阶段 5 的分类体系和质量评分。

阶段 4B-5 实测结果：

- 新增只读检查器 `scripts/checkpoint_stage4b_normalization.py` 和 `tests/test_checkpoint_stage4b_normalization.py`；检查器不修改源数据库、4B-1/4B-2 数据库或 4B-3 规范化数据库。
- 全量闭合为 `6555` 条；源 Prompt SHA-256 与长度校验 `6555/6555`，预处理结构、4B-2 分层、4B-3 规范化集合和资产映射全部闭合。
- 规范化状态为 `normalized=6494`、`needs_manual_review=61`、`excluded_with_reason=0`；规范化数据库含 `102530` 条资产映射、`582306` 条证据和 `582306` 条变换决策。
- 封存了 `6555` 条逐 Prompt 哈希映射；完整性检查 `integrity_check=ok`、外键错误 `0`、4B-4 审计 `pass` 且失败 `0`，所有输入库内容指纹前后不变。
- 解析状态为 `completed=1625`、`completed_with_issues=4930`；来源解析问题全部保留为显式计数。人工复核 `61` 条，其中高价值场景 `27` 条；排除清单为 `0` 条。
- 检查点摘要为 `e0f1011ebd3e8981cafa78412bcd84db44be9b578954e2a1c7dc322ded290d4c`；产物为 `data/runs/stage-4b-5-normalization-checkpoint/manifest.json`、`report.json`、`hash-mapping.json` 和 `issue-register.json`。
- 已生成进入阶段 5 前的建议：自动分类只使用 `normalized` 记录；人工复核、时长/镜头结构冲突和 `described_only` 引用状态必须继续显式保留；不以重复生成次数评分，也不为全量提前生成 Seedance/H3 长 Prompt。

全量阶段资源规则：

- 不安装新依赖；如标准库不能满足需求，先提交依赖审批。
- 不重新抓取网页，不下载媒体，不修改阶段 3 原始页和源数据库。
- 不把生产过程 Prompt 的重复次数当质量。
- 不在候选 Skill 中装入全量语料数据库或中间审计文件。
- 若使用并行子代理进行语义批处理或独立抽样审计，必须先取得用户明确授权，并固定批次清单、输出 Schema 和合并校验；子代理不得自行修改规划、Schema 或来源事实。

阶段 4B 授权结论：

- 用户同意深度处理 6555 个视频相关唯一 Prompt，962 个纯图片 Prompt 只保留来源审计。
- 用户同意全量只建立轻量模型无关规范化记录，完整五层案例和双模型长稿只为阶段 5 入选案例生成。
- 用户授权最多 3 个并行子代理处理固定批次和独立抽样审计；仍必须遵守只读来源、固定 Schema、显式问题和主代理合并校验。
- 4B-1 全量确定性结构预处理已完成；审核前不进入 4B-2 或阶段 5。

阶段 4B-1 小批次实测结果：

- 固定样本覆盖 10 个唯一 Prompt、206 个资产、207 条来源 occurrence 和 207 条文件夹 membership；视频相关唯一 Prompt 总量复核为 6555，另有 2 个空 Prompt 视频资产被排除。
- 初次真实解析完成 `processed=10`、`failed=0`，其中 `completed=4`、`completed_with_issues=6`。目标 SQLite 的 `integrity_check=ok`、外键错误为 0、证据跨度与 SHA-256 错误为 0。
- 初次运行发现只读 WAL 连接会更新 `corpus.sqlite3-shm` 的 mtime，但主 DB、WAL、SHM 的存在性、大小和 SHA-256 均未改变。判定已最小修正为以路径、存在性、大小和 SHA-256 识别来源内容，仍完整记录 mtime 供审计；大小或哈希变化仍会失败。
- 修正后连续两次增量运行均为 `status=pass`、`processed=0`、`skipped=10`、`failed=0`、`source_state_unchanged=true`，逻辑摘要均为 `6ab517c8a1a87d57499438b276ae0dcea7a6780fa4de440b97d2dc1d3616f18e`，且与初次解析结果一致。
- 事实数量 / Prompt 覆盖数：`audio=22/8`、`cut_marker=32/4`、`declared_aspect_ratio=6/5`、`declared_duration=4/4`、`dialogue=11/3`、`entity_reference_span=10/5`、`generation_mode=2/1`、`heading=18/4`、`language=7/3`、`reference_block=13/5`、`reference_tag=302/7`、`shot_marker=29/4`、`take_declaration=18/5`、`timestamp=18/3`。
- 显式问题分布：`audio_dialogue_scope_ambiguity=3`、`duration_metadata_conflict=3`、`take_structure_conflict=1`、`unicode_replacement_character=1`、`unresolved_reference_occurrence=3`；没有静默丢弃解析失败记录。
- 专项测试 6/6、全部测试 33/33、Python 内存编译 19/19 通过。全套测试仍显示 2 条来自既有 `test_export_prompt_sources.py` 未关闭夹具连接的 `ResourceWarning`，不属于本次脚本连接泄漏。
- 审核产物：`data/runs/stage-4b-preprocessing-sample/manifest.json`、`report.json`、`preprocessed.sqlite3`；脚本与测试分别为 `scripts/preprocess_video_prompt_sample.py` 和 `tests/test_preprocess_video_prompt_sample.py`。

阶段 4B-1 全量实测结果：

- 新增显式 `--all-video-prompts` 选择开关，默认回归样本行为保持不变；专项测试覆盖完整视频选择、确定性排序和与显式哈希参数互斥。
- 首次全量运行：`selected=6555`、`processed=6555`、`skipped=0`、`failed=0`、`status=pass`；视频 Prompt universe 为 6555，排除 2 个空 Prompt 视频资产。
- 第二次同参数增量运行：`processed=0`、`skipped=6555`、`failed=0`、`status=pass`；两次逻辑目标摘要一致：`79bb256126f7e87c4e06f2e1192ee59523750f814541a82488c9e5e9b7fbde9c`。
- 来源内容身份审计：主 DB、WAL、SHM 的存在性、大小和 SHA-256 均一致；仅 SHM mtime 发生 SQLite WAL 协调性漂移，`source_state_unchanged=true`。
- 选中来源映射：102530 个资产、102532 条 occurrence、102532 条 membership、149 个文件夹；目标表含 6555 个 `source_prompts`、6555 个 `prompt_structure`、256850 个 `extracted_facts` 和 7430 个 `processing_issues`。
- 处理状态：`completed=1625`、`completed_with_issues=4930`，无静默失败或未处理 Prompt。目标 `integrity_check=ok`、外键错误为 0、证据跨度/哈希错误为 0。
- 事实数量：`audio=23839`、`cut_marker=14286`、`declared_aspect_ratio=3638`、`declared_duration=3230`、`declared_model=7`、`dialogue=6708`、`entity_reference_span=6432`、`generation_mode=534`、`heading=9840`、`language=1090`、`reference_block=13639`、`reference_tag=127364`、`shot_marker=12464`、`take_declaration=12615`、`timestamp=21164`。
- 问题分布：`audio_dialogue_scope_ambiguity=1162`、`duration_metadata_conflict=1202`、`multiple_declared_duration_values=188`、`multiple_output_aspect_values=40`、`take_structure_conflict=1951`、`unicode_replacement_character=3`、`unresolved_reference_occurrence=2884`。
- 全量审计产物为 `data/runs/stage-4b-preprocessing-full/manifest.json` 和 `report.json`；约 201.36MB 的 `preprocessed.sqlite3` 可由脚本再生成，因超过 GitHub 100MB 单文件限制而不纳入版本库。

阶段 4B-2 小批次实测结果：

- 新增 `scripts/stratify_video_prompt_complexity.py`，从 4B-1 结构事实和源 Prompt 证据生成四个互斥队列：`simple`、`standard`、`complex`、`manual_review`；不读取资产数量、occurrence 数量、membership 数量或生成次数。
- 10 条已批准样本首次分层 `processed=10`、`failed=0`，队列分布为 `complex=6`、`standard=2`、`simple=1`、`manual_review=1`；二次运行 `processed=0`、`skipped=10`，逻辑摘要保持一致。
- 场景信号使用可并存标签；结构、对白、时长、文本长度、镜头密度、引用密度和问题码均保存规则 ID 与证据跨度。部分资产时长为 `null` 时不参与数值比较，但显式记录 `missing_asset_duration` 风险。
- 分层输出不复制完整 Prompt；全量输出使用独立 SQLite、manifest 和 report，并保留源库与 4B-1 库内容指纹。

阶段 4B-2 全量实测结果：

- 首次全量运行：`selected=6555`、`processed=6555`、`skipped=0`、`failed=0`、`status=pass`；第二次同参数运行：`processed=0`、`skipped=6555`、`failed=0`、`status=pass`。
- 四个互斥队列：`complex=6069`、`standard=407`、`simple=76`、`manual_review=3`。人工队列仅包含 3 条 `unicode_replacement_character` 损坏文本；时长冲突、镜头结构冲突、引用未解析和对白范围歧义保留在 complex 队列的风险标签中。
- 结构状态：`single_take=2074`、`multi_take=1084`、`not_declared=1446`、`conflicted=1951`；对白状态：`detected=817`、`none=4576`、`ambiguous=1162`。
- 时长状态：`asset_metadata_only=3828`、`conflict=1381`、`consistent=1070`、`multiple_metadata=276`；文本长度：`short=150`、`standard=2546`、`long=1716`、`very_long=2143`。
- 密度分布：镜头标记 `low=2396 / medium=2175 / high=1984`；引用 `none=1065 / light=577 / dense=4913`。
- 场景标签可并存：`action_interaction=5635`、`character_performance=5349`、`environment_establishing=6119`、`mixed_scene=5891`、`unspecified_scene=236`。
- 风险标签：`audio_dialogue_scope_ambiguity=1162`、`dense_references=4913`、`duration_conflict=1381`、`duration_metadata_conflict=1202`、`high_marker_density=1984`、`missing_asset_duration=3`、`multiple_declared_duration_values=188`、`multiple_output_aspect_values=40`、`structure_conflict=1951`、`take_structure_conflict=1951`、`unicode_replacement_character=3`、`unresolved_reference_occurrence=2884`、`very_long_prompt=2143`。
- 目标 SQLite 含 6555 个 `prompt_strata` 和 138424 条证据记录；`integrity_check=ok`、外键错误为 0、验证错误为 0；源库和 4B-1 库内容指纹均未改变。逻辑摘要为 `19c67470a9c4dc0800559fc511f6f611d27340494861b8a29636827c7e3ed011`。
- 交付产物：`data/runs/stage-4b-stratification-final/manifest.json`、`report.json`、`stratification.sqlite3`（约 55.32MB，低于 GitHub 单文件限制）。

阶段验收：

- 用户审核 4B-1 小批次的来源审计、字段覆盖、显式问题、幂等性和误报修正

### 阶段 5：场景分类与精华案例筛选

状态：5-1 场景分类与 Prompt-only 评分已完成，等待用户审核；尚未进入 5-2 精华案例最终筛选

步骤：

1. 根据实际语料自底向上建立多标签分类。
2. 原始审计层永久保留全部资产记录和资产 ID；Prompt 分析层按原文 SHA-256 折叠完全重复文本，并保留“唯一 Prompt → 全部来源资产 ID”的完整映射。
3. 对近似变体建立簇但不自动删除；只有在人工可审计的合并理由成立后，才能选择代表文本，其余变体继续保留来源映射。
4. 不把同一 Prompt 的重复生成次数作为质量分数、最终采用标记或优秀案例证据。重复频率只能描述生成行为，可能来自批量生成、随机重试或反复试错。
5. Prompt 完全相同不代表生成视频相同；在未检查媒体结果时，不得根据 Prompt 哈希推断输出画面或质量相同。
6. 对每个精确 Prompt 簇只精读一次代表文本，但评分结论必须落在 Prompt 内容本身，不能落在资产数量上。
7. 按可拍性、空间明确度、动作因果、表演细度、摄影控制、物理合理性、连续性和复用价值评分。
8. 将案例分为核心范式、有效变体和特殊场景。
9. 为每条未入选或合并记录保留原因和来源映射。

Stage 5-1 检查点已完成：

- 6555 个精确 Prompt 簇进入分类；6494 条 `normalized` 自动分类，61 条 `needs_manual_review` 保持未评分，0 条排除。
- 主场景标签和派生模式均为多标签；近似变体保留为 `candidate_only_not_merged`，未删除、未合并。
- Prompt Content Score v2 仍为 8 个维度、每项 0–4 分；动作、物理、摄影、连续性维度要求各自证据；跨字段完全重复证据最多扣 4 分并阻止 `core_pattern`。
- 案例层级分布：`core_pattern=1351`、`effective_variant=4560`、`special_scene=583`；人工复核 61 条不进入自动评分。
- 候选清单按主要派生家族每类最多 20 条（未指定场景 15 条），共 175 条家族记录和 175 个不同 Prompt；排序先使用 Prompt Content Score 和最低维度分数，只在完全并列时优先尚未进入其他家族候选的 Prompt，最后按 SHA-256 稳定排序；资产数量只保留 `asset_count_audit_only`。
- 全量首跑与相同参数幂等重跑均为 `pass`，摘要 `d829fb2fdca139be35a2329b463a0e95d747c1520a069cbca540c89222b06546`；源库、4B-2 分层库和 4B-3 规范化库内容身份均未改变。
- 产物：`data/runs/stage-5-1-prompt-classification/taxonomy-and-scoring.json`、`classified-records.json`、`selection-candidates.json`、`manifest.json`、`report.json`。

阶段验收：

- 用户审核 Stage 5-1 分类体系、评分规则和候选清单后，才进入 5-2 精华案例最终筛选
- 任一入选案例均可追溯到唯一 Prompt 哈希和全部来源资产 ID
- 完全重复文本只分析一次，但原始资产记录无删除、无丢失
- 评分中不存在以重复生成次数替代内容质量判断的字段或隐性权重
- 近似变体的合并、保留和排除均有可审计理由

### 阶段 6：范式抽象与唯一案例库 Skill 制作

状态：未开始

最终 Skill 预计包含：

```text
cinematic-scene-case-library/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    ├── index.md
    └── <按最终分类生成的案例文件>.md
```

每个案例包含：

- 案例 ID 与来源资产 ID
- 场景类型和适用条件
- Prompt-only 证据、置信度和限制说明，不将分数表述为成片质量
- 仅供审计的精选原始 Prompt 或必要片段，显式标记为不可直接注入
- 有效结构分析
- 模型无关范式
- 可迁移约束与可替换变量
- ACTING 表演层交接
- CINEDANCE/导演层交接
- 相互隔离的 Seedance 适配提示与 H3 适配提示
- 禁止复制字段：源 `@tag`、源资产 ID、历史时长、完整源 Prompt 和不属于目标模型的语法
- 复刻、变体与优化策略
- 常见失败和质量检查

阶段验收：

- 审核完整 Skill、案例覆盖率和资源大小
- 审核指导包 Schema、模型适配隔离、禁止复制字段和 Prompt-only 证据声明
- 确认案例库只给出建议与交接片段，不生成或声称拥有 Seedance/H3 最终稿

### 阶段 7：总编排集成与验证

状态：未开始

步骤：

1. 为 `cinema-studio-production` 和 `minimax-h3-director` 分别准备最小、可选的案例检索路由补丁；不把检索要求写入 ACTING 或 CINEDANCE。
2. Seedance 路径固定为 `cinema-studio-production -> 案例检索 -> 按需 ACTING/CINEDANCE -> CINEDANCE 最终组装与 QA`，并验证案例库不会取代 LIRA、ACTING 或 CINEDANCE 的职责。
3. H3 路径固定为 `minimax-h3-director -> 案例检索 -> 按需专家 -> minimax-h3-director 最终组装与 QA`；不得经由 `cinema-studio-production` 包装，官方 H3 语法和真实资产规则覆盖案例建议。
4. 检索后只向专家传递职责相关片段：表演事实交给 ACTING，空间、镜头、物理与连续性提示交给 CINEDANCE，模型适配说明留给各自最终组装器。
5. 使用代表性正向与负向任务验证触发条件、职责所有权、Prompt 密度和语法隔离：抽象/缺结构/修复/显式查询应检索；完整可拍请求应跳过；历史标签、资产 ID、时长和异模型语法不得泄漏。
6. 验证冲突优先级：用户锁定事实和目标模型官方规则高于案例建议；案例建议与专家规则冲突时，由拥有该事实或最终格式的 Skill 裁决。
7. 运行 Skill 结构校验、索引链接校验、案例 ID 校验、指导包 Schema 校验和无重资产检查。

注意：`minimax-h3-director` 明确禁止作为 `cinema-studio-production` 的下游包装器。两条路径必须保持独立；任何改变该所有权关系的方案都属于后续独立架构决策，不能在本阶段擅自实施。

### 阶段 8：最终审核与安装

状态：未开始

步骤：

1. 提交候选安装包、现有 Skill 补丁、验证报告和目录树。
2. 得到用户明确批准。
3. 检查目标安装目录是否已存在同名 Skill。
4. 安装案例库并应用已审核补丁。
5. 对安装后的文件再次验证。
6. 保留工作目录，除非用户明确要求清理。

## 8. 抓取器技术约束

- 默认 User-Agent 必须明确，不伪装登录用户。
- 不使用 Cookie、登录会话、访问令牌或其他私密凭据。
- 不绕过 CAPTCHA、访问控制或速率限制。
- 仅访问项目页面实际引用的公开端点，不枚举其他项目 ID。
- 默认串行或低并发抓取；并发数和请求间隔在单文件夹试运行后决定。
- 每个响应先验证 HTTP 状态、Content-Type 和 JSON 结构，再解析字段。
- 原始响应不可覆盖；重复运行使用新的运行 ID 或可验证检查点。
- 写入使用临时文件完成后原子重命名，避免中断产生半截 JSON。
- 日志不得包含 Cookie、Authorization、会话标识或完整媒体下载 URL 查询串。

## 9. 数据记录建议

原始资产记录最低字段：

```json
{
  "project_id": "...",
  "folder_id": "...",
  "folder_name": "...",
  "asset_id": "...",
  "asset_type": "video",
  "status": "completed",
  "model": "Seedance 2",
  "created_at": "...",
  "duration_seconds": 15,
  "width": 2016,
  "height": 864,
  "prompt": "...",
  "source_endpoint": "...",
  "fetched_at": "..."
}
```

字段只在来源明确提供时写入。未知值使用 `null`，不得推测。

## 10. 进度日志

### 2026-08-16

- 完成需求理解和总体架构讨论。
- 确认 Skill 名称为 `cinematic-scene-case-library`。
- 确认工作区制作、审核后安装。
- 通过公开页面验证项目和资产详情可读取。
- 发现项目包含全部制作过程资产，没有可靠最终版本标记。
- 用户决定将范围改为全部 Prompt，并通过 Python 抓取。
- 创建本计划文档。
- 使用 Python 标准库完成公开 HTML、脚本和 API 数据路径探测。
- 锁定文件夹、子文件夹和资产 Prompt 的公开分页端点。
- 新增并验证 `probe_higgsfield.py`、`capture_higgsfield_network.py` 和 `fetch_prompts.py`。
- 完成 5 条完整 Prompt 概念验证与下一页 cursor 验证。
- 阶段 1 已完成；下一步必须等待用户批准后才能进行阶段 2 单文件夹试运行。
- 用户明确批准阶段 2；锁定 `Scene 69 - Fight`（146 个资产）作为单文件夹试运行范围。
- 阶段 2 已开始；正在实现逐页原始/规范化落盘、断点续传、限速、重试、错误日志和数量对账。
- 完成 `Scene 69 - Fight` 三页抓取与对账：146 个 API 条目、146 个唯一资产、146 条非空 Prompt，0 错误、0 警告。
- 确认 146 个资产只对应 23 个唯一 Prompt，精确重复生成资产为后续聚类和代表案例筛选的主要压缩来源。
- 完成断点恢复和完成态重跑验证；最终重跑网络请求数为 0。
- 阶段 2 已完成；停止在用户审核点，尚未执行阶段 3。
- 用户确认阶段 2 的重复处理准则，并要求将其固化到阶段 5；已记录“保留全部资产、精确 Prompt 折叠、近似变体只聚类、重复频率不参与质量评分、相同 Prompt 不等于相同视频”等约束。
- 用户明确批准阶段 3；阶段 3 已开始，先进行全项目规模预检与抓取架构核验。
- 完成全项目 1155 页抓取：115451 条 API occurrence，115446 个唯一资产，115309 个非空 Prompt 资产，7517 个精确唯一 Prompt。
- 将 4 次重复资产出现确认为多文件夹归属，并回填完整的资产-文件夹映射；另有 1 条 `video_input` occurrence，最终 occurrence 对账完全闭合。
- 完成 1.713 GiB 原始页、SQLite、cursor、事件日志、精确簇映射、近似候选和长度候选审计；全部最终检查通过，审计状态为 `passed_with_audited_source_issues`。
- 完成态续跑网络请求数为 0；15 项测试和 11 个 Python 文件内存语法编译通过；未安装依赖、未下载媒体。
- 阶段 3 已完成并停止在用户审核点；尚未开始阶段 4。
- 用户审核阶段 3 并明确批准进入阶段 4。
- 阶段 4 已开始；先完成五层规范化 Schema、三类小样本和 Seedance/H3 跨模型验证，用户审核前不批量处理全部 7517 个唯一 Prompt。
- 完成阶段 4 三条代表样本的可审计源文导出；发现动作样本存在 Prompt 10 秒与资产元数据 15 秒的来源冲突，已暂停适配稿生成并等待用户决定时长优先级。
- 用户批准动作适配稿采用 15 秒，并批准将约 14 个原文切分段压缩为 5 个因果节拍。
- 发现原环境样本的 6 秒运行时长与约 150 米慢速下降互相冲突；已完成静态高空环境候选的源文与 17 个资产元数据核验，等待用户决定是否替换。
- 用户批准将环境样本替换为 10 秒静态高空鸟瞰候选；阶段 4 三个样本选择现已锁定。
- 完成五层规范化 Schema、三个规范化样本、Seedance/H3 双适配验证稿和跨模型差异报告。
- 阶段 4 正式验证报告为 `pass`：3 条规范化记录、3 条完整源记录、40 个来源资产、0 个问题；全部 27 项测试通过。
- 阶段 4 停止在用户审核点；尚未批量规范化 7517 个唯一 Prompt，也未进入阶段 5。
- 用户批准阶段 4 小样本检查点；新增阶段 4B 全量规范化方案，等待用户确认处理范围、规范化深度和是否允许并行子代理。
- 用户批准阶段 4B 三项方案：处理 6555 个视频相关 Prompt、全量轻量规范化、最多 3 个并行子代理；开始 4B-1 小批次确定性结构预处理。
- 完成阶段 4B-1：10 个 Prompt、206 个资产和 207 条 occurrence/membership 已写入独立 SQLite；证据、完整性、外键和来源内容身份检查全部通过，连续增量运行摘要一致；停止等待用户审核。
- 用户于 2026-08-17 审核通过 4B-1 小批次，批准执行 6555 个视频相关 Prompt 的全量确定性结构预处理；全量结果仍须单独提交审核。
- 完成阶段 4B-1 全量：6555 个 Prompt 全部处理并通过审计，二次运行全部幂等跳过；已停止在 4B-2 前等待用户审核。
- 完成阶段 4B-2 小批次：10 条样本完成互斥队列分层、场景多标签和证据校验；全量分层已获批准并开始执行。
- 完成阶段 4B-2 全量：6555 条全部进入且只进入一个复杂度队列，证据和幂等性通过；已停止在 4B-3 前等待用户审核。
- 用户审核通过阶段 4B-2 全量队列、场景标签、风险分布和人工复核入口；批准继续 4B-3。
- 完成阶段 4B-3 10 条样本：8 条规范化、2 条人工复核、0 条排除；资产映射、证据、变换决策、模型语法隔离和幂等性全部通过；已停止在全量运行前等待用户审核。
- 用户审核通过阶段 4B-3 样本的字段结构、状态判定、冲突保留、媒体状态和语义摘要；批准按同一版本与配置执行 6555 条全量语义规范化。
- 完成阶段 4B-3 全量：6555 条首跑通过，二次运行全部幂等跳过；三态、资产映射、证据、变换决策、模型语法隔离和三套来源身份校验全部通过；已停止在 4B-4 前等待用户审核。
- 用户审核通过 4B-3 全量并批准进入 4B-4；完成 460 条分层抽样和 61 条人工复核清单，6555 条逐条审计全部通过，已停止等待用户审核。
- 用户审核通过 4B-4 并批准进入 4B-5；完成全量规范化检查点封存、6555 条哈希映射和进入阶段 5 的建议，当前停止等待用户审核。
- 完成 Stage 5-1 首轮分类与 Prompt-only 评分后，发现字段存在性会放大高分；将评分升级为 v2，加入维度证据门槛、跨字段重复证据扣分和可复用性单次计分。
- Stage 5-1 v2 全量运行与幂等重跑均通过：6555 个精确 Prompt 簇、6494 条自动评分、61 条人工复核、0 条排除；修正满分并列导致的跨家族候选塌缩后，175 条家族候选对应 175 个不同 Prompt；全套 60 项测试和 Python 内存编译通过，已停止等待用户审核分类体系、评分规则和候选清单。

### 2026-08-17

- 用户确认案例库应作为低权限、可选的检索增强层；已锁定 Seedance/H3 双路径、最终组装所有权、指导包字段、禁止复制项、Prompt-only 证据边界和代表性集成验收条件。此次只更新计划，不进入 Stage 5-2。

## 11. 中断恢复说明

恢复工作时按以下顺序执行：

1. 完整阅读本文件。
2. 检查“进度日志”和各阶段状态。
3. 检查 `scripts/`、`data/reports/` 和 `logs/` 中最近产物。
4. 不重复已经完成的全量请求。
5. 运行抓取器时优先使用其检查点或 `--resume` 功能。
6. 若计划和用户最新指示冲突，以用户最新指示为准，并先更新本文件再继续。

## 12. 当前下一步

1. 等待用户审核 Stage 5-1 的多标签分类、Prompt Content Score v2、175 条互异候选家族记录和 61 条人工复核入口。
2. 用户批准后进入 Stage 5-2 精华案例最终筛选，为入选、保留和不入选记录补充可审计理由；不根据未检查媒体推断成片质量。
3. 在 Stage 5-2 审核完成前不生成全量 Seedance/H3 最终稿，也不制作最终 Skill 安装包。
