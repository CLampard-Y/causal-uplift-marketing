# 问题记录文档

## 问题记录规范
- 适用范围：本规范用于本文件内所有后续新增、更新、续写的问题记录；后续任何 AI 或人工维护者都应严格遵循，不得随意改动主结构。
- 记录目标：每个问题应在不额外翻阅大量上下文的情况下提供约 8/10 的理解度；剩余 2/10 通过“相关线索”中的文件、代码、文档位置继续回查补全。
- 记录原则：
  - 一个问题只记录一个主矛盾，不把多个无关问题混写在同一条目中；
  - 已解决问题不删除，统一通过更新“当前状态”“采用的方案”“核查记录”来闭环；
  - 信息不足时必须保留字段并写明“待补充”，不能省略关键结构；
  - 所有关键判断尽量给出可回查线索，优先写到文件路径、文档位置、代码位置或产物位置；
  - 若问题与过去讨论、审查结论或设计决策有关，应在“问题详情与背景”或“补充说明”中写清该历史上下文。
- 新增问题时的编号规则：
  - 按顺序追加 `## 问题 N：[问题标题]`；
  - 不对既有问题重新编号；
  - 如需拆分一个旧问题，新增新编号，并在“补充说明”中写清与旧问题的关系。
- 每个问题必须严格包含以下主结构，不得缺项：
  - `### 第一部分：问题情况与介绍`
  - `### 第二部分：解决与跟进记录`
  - `#### 采用的方案（后续重点详细补充）`
  - `#### 核查记录`
- 第一部分的必填字段：
  - `问题简况`
  - `问题详情与背景`
  - `影响范围`
  - `相关线索`
  - `补充说明`
- 第二部分的必填字段：
  - `当前状态`
  - `当前进度说明`
  - `建议方案一`
  - `方案一涉及范围`
  - `建议方案二`
  - `方案二涉及范围`
  - `建议方案对比`
  - `当前建议方向`
- “采用的方案”部分的填写要求：
  - 这是后续真正开始修改、验证、落地后需要重点详细补全的核心区域；
  - 在问题尚未真正进入实施前，至少保留：`是否已确定采用方案`、`采用方案说明`、`实施记录`、`变更影响`、`注意事项`；
  - 一旦进入真实修复，必须尽可能详细记录最终采用的方法、修改范围、关键权衡、实施顺序和对上下游的影响。
- “核查记录”部分的填写要求：
  - 用于记录检查、验证、回归、复盘情况；
  - 至少填写：`核查状态`、`核查方式`、`核查结果`、`遗留问题或后续动作`；
  - 若问题已解决，但核查未完成，不得直接写成完全闭环。
- 状态填写规范：
  - `未解决`：尚未开始处理，`当前进度说明` 固定写“无”；
  - `着手解决`：必须明确写出“已完成内容 / 正在处理的部分 / 尚未完成内容 / 当前卡点或待确认事项”；
  - `已解决`：必须在“采用的方案”和“核查记录”中写出足够证据，避免只有结论没有过程。
- 线索记录规范：
  - 尽量使用可直接回查的文件路径与行号，如 `README.md:55`、`src/business.py:578`；
  - 若是 notebook，可同时记录“源码位置/已保存输出位置”；
  - 若是 JSON / CSV / 图表产物，应写清文件路径与关键字段/关键值所在位置；
  - 若涉及设计决策或口径边界，应同时写明相关文档或报告位置。
- 维护更新规范：
  - 每次问题状态变化时，优先更新对应问题条目，而不是在文档其他地方零散补记；
  - 若某个问题被明确决定“暂不处理”，应保留问题本身，并在“当前建议方向”或“补充说明”中写明延期原因；
  - 若后续新增修复动作，应先补“采用的方案”，再补“核查记录”，最后更新“当前状态”。
- 推荐写法：
  - 先写事实，再写判断；
  - 先写当前现象，再写为什么重要；
  - 先写主线问题，再写补充边界；
  - 避免只有抽象结论，尽量补充可验证的文件/代码/产物线索。
- 新增问题时建议直接复制以下骨架：

```md
## 问题 N：[问题标题]

### 第一部分：问题情况与介绍
- 问题简况：[一句话概括问题]
- 问题详情与背景：[详细说明问题的具体情况、出现背景、已知现象]
- 影响范围：[涉及的模块、功能、页面、接口、数据、业务流程、协作方等]
- 相关线索：[相关文件、代码路径、文档、日志、配置、上下游信息等]
- 补充说明：[待补充信息、已知限制、假设条件等]

### 第二部分：解决与跟进记录
- 当前状态：[未解决 / 着手解决 / 已解决]
- 当前进度说明：[若为“着手解决”，说明已完成什么、还剩什么、当前卡点；否则写“无”]
- 建议方案一：[方案思路]
- 方案一涉及范围：[简要说明]
- 建议方案二：[方案思路]
- 方案二涉及范围：[简要说明]
- 建议方案对比：[简要比较两种思路的适用性、风险、影响范围]
- 当前建议方向：[填写推荐方向；如暂未确定则写“待确认”]

#### 采用的方案（后续重点详细补充）
- 是否已确定采用方案：[是 / 否]
- 采用方案说明：[预留；后续实际实施时尽可能详细填写]
- 实施记录：[预留]
- 变更影响：[预留]
- 注意事项：[预留]

#### 核查记录
- 核查状态：[未核查 / 核查中 / 已核查]
- 核查方式：[填写]
- 核查结果：[填写]
- 遗留问题或后续动作：[填写]
```

## 文档说明
- 文档用途：归档当前仓库在主线问题基本收口后，仍未解决或仍值得后续跟进的剩余问题/改进点，帮助任何 AI 或协作者快速理解问题背景、影响、处理边界与回查线索。
- 维护原则：
  - 只记录当前仍未闭环的问题，不重复记录已确认解决的问题；
  - 每个问题尽量提供 8/10 的上下文理解，剩余部分通过“相关线索”中的文件和代码位置补全；
  - 后续一旦开始真实修复，应优先补全“采用的方案（后续重点详细补充）”与“核查记录”；
  - 若问题被明确决定暂不处理，也保留记录，避免后续重复讨论或遗忘边界条件。
- 状态标记说明：
  - `未解决`：尚未开始处理
  - `着手解决`：已开始处理，需说明当前进度
  - `已解决`：问题已处理完成

---

## 问题 1：Notebook 05 / 06 仍存在陈旧输出与绝对路径残留

### 第一部分：问题情况与介绍
- 问题简况：部分 notebook 的已保存输出仍残留旧路径或不够干净的本机路径提示，说明 notebook 尚未做最终 clean rerun。
- 问题详情与背景：
  - `notebooks/05_segmentation_and_roi.ipynb:1192` 的已保存输出仍显示旧仓库绝对路径 `e:\Work\MyCode\Data-Analysis-Projects\Project3_Causal-Uplift-Marketing\data\processed\roi_simulation.json`，但当前代码实际写盘逻辑已经改成当前仓库路径，见 `notebooks/05_segmentation_and_roi.ipynb:1234`、`notebooks/05_segmentation_and_roi.ipynb:1238`。
  - `notebooks/06_robustness_checks.ipynb:817` 的已保存输出仍显示绝对路径 `.json saved: E:\Work\MyCode\causal-uplift-marketing\data\processed\placebo_results.json`。这不是错误，但和仓库其他相对路径/更审阅友好的风格不完全一致。
  - 该问题本质上不是逻辑错误，而是 notebook 保存输出没有在当前最终状态下做一次彻底刷新，导致 reviewer 能看出“代码与渲染输出并非完全同一轮”。
- 影响范围：
  - `notebooks/05_segmentation_and_roi.ipynb`
  - `notebooks/06_robustness_checks.ipynb`
  - 审阅体验、项目自洽感、GitHub 浏览时的可信度
- 相关线索：
  - `notebooks/05_segmentation_and_roi.ipynb:1192`
  - `notebooks/05_segmentation_and_roi.ipynb:1234`
  - `notebooks/05_segmentation_and_roi.ipynb:1238`
  - `notebooks/06_robustness_checks.ipynb:817`
- 补充说明：
  - 当前问题不影响仓库主线方法与面试叙事；
  - 若后续环境无法直接 rerun notebook，可先做最小手工清理；
  - 待补充：是否需要同时统一 `.png saved` / `.json saved` 的展示风格。

### 第二部分：解决与跟进记录
- 当前状态：未解决
- 当前进度说明：无
- 建议方案一：在真实 Python / Jupyter 环境下重新执行 `notebooks/05_segmentation_and_roi.ipynb` 与 `notebooks/06_robustness_checks.ipynb`，用新的执行结果覆盖旧输出。
- 方案一涉及范围：两个 notebook 的输出区、可能同步刷新本地图表/JSON 落盘时间戳。
- 建议方案二：只做最小人工清理，手动替换或清除明显陈旧的输出行，避免 reviewer 看到旧路径残留。
- 方案二涉及范围：仅 notebook JSON 输出区，不改业务逻辑。
- 建议方案对比：
  - 方案一更完整，能同时解决路径残留、执行证据陈旧、输出一致性问题；
  - 方案二更省时间，但仍会保留“未重新全量执行”的风险。
- 当前建议方向：若后续有可用执行环境，优先采用方案一；若项目当前重心是面试而非工程收尾，可暂缓。

#### 采用的方案（后续重点详细补充）
- 是否已确定采用方案：否
- 采用方案说明：待补充
- 实施记录：待补充
- 变更影响：待补充
- 注意事项：待补充

#### 核查记录
- 核查状态：已核查
- 核查方式：静态文件审阅 + notebook 源码/输出交叉回查
- 核查结果：已确认 Notebook 05 存在旧仓库路径残留，Notebook 06 存在绝对路径保存提示；代码与保存输出并非完全同轮。
- 遗留问题或后续动作：待可执行环境可用后，决定是否进行 notebook clean rerun。

---

## 问题 2：Notebook 03 内部 OVL 口径不一致

### 第一部分：问题情况与介绍
- 问题简况：同一份 notebook 内，`OVL` 的两个展示位置数值不一致，容易被视为 summary stale / copy drift。
- 问题详情与背景：
  - `notebooks/03_propensity_score_matching.ipynb:346` 的 stdout 打印 `Overlap Coefficient (OVL): 0.9880`；
  - 但 `notebooks/03_propensity_score_matching.ipynb:491` 的 Section Summary 又写成 `OVL 为 0.9889`。
  - 当前主线文档与报告多数采用 `0.9880`，因此 `0.9889` 更像是旧 summary 未同步刷新，而不是新计算结果。
  - 该问题不会改变 Phase 2 的结论，但会降低 notebook 自身的精细度和审阅可信度。
- 影响范围：
  - `notebooks/03_propensity_score_matching.ipynb`
  - `docs/Phase2_Execution_PRD.md` 的数字可信度感知
  - reviewer 对 notebook 输出一致性的判断
- 相关线索：
  - `notebooks/03_propensity_score_matching.ipynb:346`
  - `notebooks/03_propensity_score_matching.ipynb:491`
  - `docs/Phase2_Execution_PRD.md:10`
  - `docs/Phase2_Execution_PRD.md:169`
- 补充说明：
  - 当前更可信的主口径是 `0.9880`；
  - 待补充：是否存在当次运行前后因显示精度/分箱差异造成的真实变化，还是纯 summary stale。

### 第二部分：解决与跟进记录
- 当前状态：未解决
- 当前进度说明：无
- 建议方案一：以 notebook 实际 stdout 为准，将 summary 文本中的 `0.9889` 修为 `0.9880`。
- 方案一涉及范围：`notebooks/03_propensity_score_matching.ipynb` 的 markdown / text output 区域。
- 建议方案二：重新执行 Notebook 03，让 summary 与输出一并刷新，并确认最终 OVL 的唯一来源。
- 方案二涉及范围：Notebook 03 全量执行、相关输出区、必要时同步检查 `docs/Phase2_Execution_PRD.md`。
- 建议方案对比：
  - 方案一最快，适合把问题压缩为纯文案修复；
  - 方案二更彻底，但成本更高，需要可用执行环境。
- 当前建议方向：若只是清 reviewer-visible 毛边，优先方案一；若后续准备统一清所有 notebook stale outputs，则直接走方案二。

#### 采用的方案（后续重点详细补充）
- 是否已确定采用方案：否
- 采用方案说明：待补充
- 实施记录：待补充
- 变更影响：待补充
- 注意事项：待补充

#### 核查记录
- 核查状态：已核查
- 核查方式：静态 notebook 输出与 summary 交叉比对
- 核查结果：已确认同一 notebook 内至少有一处 `OVL` summary 与 stdout 不一致。
- 遗留问题或后续动作：确定最终以 stdout 还是 rerun 结果为准，然后统一单一口径。

---

## 问题 3：Phase 4 的 shadow baseline ATE 与 Phase 2 canonical PSM 估计仍有轻微差异

### 第一部分：问题情况与介绍
- 问题简况：Phase 4 的 robustness notebook 中，shadow matcher 计算出的 baseline ATE 为 `0.521%`，而 Phase 2 主实验 canonical PSM 口径为 `0.502%`，两者存在轻微差异。
- 问题详情与背景：
  - Phase 2 主实验口径见 `docs/Phase2_Execution_PRD.md:10`，对应 `PSM ATE = 0.502%`；
  - Phase 4 当前已明确改写为：`0.521%` 是 `Notebook 06` 的 **shadow baseline**，而不是 `Notebook 03` 的逐步重放结果，见 `docs/Phase4_Execution_PRD.md:10`、`docs/Phase4_Execution_PRD.md:12`、`docs/Phase4_Execution_PRD.md:113`；
  - `Notebook 06` 当前采用 notebook-local in-memory shadow matcher，而不是 `src.causal.match_ps()`，见 `notebooks/06_robustness_checks.ipynb:59`、`notebooks/06_robustness_checks.ipynb:60`、`notebooks/06_robustness_checks.ipynb:231`；
  - 当前项目已经选择保留 shadow implementation，以保留 independent audit / falsification 的价值，因此这个数值差异不再被定义为“文档口径错误”，而是被定义为“设计上允许的实现漂移边界”。
  - 但是，数值差异本身仍然存在，因此在技术审阅或面试问答中，仍需能解释为什么这是 **independent audit trade-off** 而非 bug。
- 影响范围：
  - `notebooks/06_robustness_checks.ipynb`
  - `docs/Phase4_Execution_PRD.md`
  - 与 Phase 2 / Phase 4 跨文档数字对照时的可解释性
  - 面试中的 method / robustness 防守
- 相关线索：
  - `docs/Phase2_Execution_PRD.md:10`
  - `docs/Phase4_Execution_PRD.md:10`
  - `docs/Phase4_Execution_PRD.md:12`
  - `docs/Phase4_Execution_PRD.md:113`
  - `notebooks/06_robustness_checks.ipynb:59`
  - `notebooks/06_robustness_checks.ipynb:231`
  - `notebooks/06_robustness_checks.ipynb:546`
  - `notebooks/06_robustness_checks.ipynb:950`
- 补充说明：
  - 当前已经完成的是“口径澄清”，不是“数值统一”；
  - 待补充：是否要长期接受该差异，还是未来增加更细粒度的 comparative note / metadata；
  - 该问题更偏“可解释性边界管理”，而不是强制要修掉的工程 bug。

### 第二部分：解决与跟进记录
- 当前状态：着手解决
- 当前进度说明：
  - 已完成内容：README、Phase 4 文档、Notebook 06 已统一改写为 `shadow matcher / shadow baseline` 叙事，不再假装是 Notebook 03 的 exact replay；
  - 正在处理的部分：当前主要是决定是否需要在 artifact / doc 中进一步补充“为什么允许 0.521% vs 0.502%”的长期说明；
  - 尚未完成内容：若未来转向更工程化的 portfolio 叙事，仍可补充一份更正式的 cross-implementation note 或 run comparison；
  - 当前卡点或待确认事项：项目当前定位更偏 interview repo，因此该问题暂以“边界已澄清但差异仍保留”的方式记录，而未继续深挖。
- 建议方案一：保持 shadow matcher 设计不变，仅在文档、artifact、面试话术中继续明确“design-aligned shadow chain ≠ canonical replay”。
- 方案一涉及范围：`README.md`、`docs/Phase4_Execution_PRD.md`、`notebooks/06_robustness_checks.ipynb`、面试话术。
- 建议方案二：未来若希望减少 reviewer 追问，可在 Phase 4 中额外加入“为何不同 matcher 会导致轻微数值漂移”的专门说明，或补一份 comparison note。
- 方案二涉及范围：`docs/Phase4_Execution_PRD.md`、`problem/problem_record.md`、可能新增 comparison artifact。
- 建议方案对比：
  - 方案一最符合当前 interview-first 目标，成本低且不破坏 shadow audit 价值；
  - 方案二更工程化，但收益主要面向严苛 reviewer，而非春招面试。
- 当前建议方向：维持方案一，接受该差异为 shadow audit 的正常代价；若后续转向 portfolio 再考虑方案二。

#### 采用的方案（后续重点详细补充）
- 是否已确定采用方案：是
- 采用方案说明：已采用“保留 Notebook 06 shadow matcher + 全面修正文档口径”的方向；后续如需进一步工程化，再补 comparison note，而不直接改成复用 `src.causal.match_ps()`。
- 实施记录：已完成 README、Phase 4 报告、Notebook 06 的 wording 修订，明确 shadow baseline / notebook-local matcher 边界。
- 变更影响：口径层面已不再将 `0.521%` 错当作 Phase 2 persisted main estimate；但数值差异本身仍保留。
- 注意事项：后续新增任何 Phase 4 相关文档时，都应避免重新写回“same matcher / same chain replay”这类表述。

#### 核查记录
- 核查状态：已核查
- 核查方式：多轮静态代码/文档审阅 + agent 交叉 review
- 核查结果：已确认 narrative boundary 已收口，但 `0.521%` vs `0.502%` 的数值差异仍然存在，且当前被项目有意接受。
- 遗留问题或后续动作：若未来需要更工程化的闭环，可新增一段 explicit comparison note，记录 shadow matcher 与 canonical matcher 的差异来源。

---

## 问题 4：Phase 3 核心 business logic 仍缺少直接测试覆盖

### 第一部分：问题情况与介绍
- 问题简况：目前单元测试主要覆盖 Phase 3 导出合同 helper，但未直接覆盖 `segment_users(...)` / `simulate_roi(...)` 等决定核心结论的业务逻辑。
- 问题详情与背景：
  - `tests/README.md:56`-`tests/README.md:61` 目前明确列出的 Phase 3 测试重点是 `prepare_user_segments_export(...)`；
  - 但真正决定 Phase 3 headline 数字的逻辑仍在 `src/business.py`，如 `src/business.py:578` 的 `Precision Targeting (Persuadables only)`、`src/business.py:610` 的 `budget_sweep` 等。
  - 这意味着当前 `25% Persuadables`、`51.9% retention`、`2.08x ROI proxy` 等主结果更偏 **notebook-backed claim**，而不是 **unit-test-backed claim**。
  - 对 interview repo 来说，这不一定致命；但对长线维护或严格代码审阅来说，这属于尚未补齐的工程门禁。
- 影响范围：
  - `src/business.py`
  - `tests/test_business.py`
  - `tests/README.md`
  - Phase 3 业务结论的可回归性
- 相关线索：
  - `tests/README.md:56`
  - `tests/README.md:61`
  - `src/business.py:578`
  - `src/business.py:610`
  - `docs/Phase3_Execution_PRD.md:137`
  - `notebooks/05_segmentation_and_roi.ipynb:1261`
- 补充说明：
  - 当前项目已具备一部分 contract test 思路；
  - 待补充：是否需要把 headline 数字保护到 deterministic snapshot / fixture 层。

### 第二部分：解决与跟进记录
- 当前状态：未解决
- 当前进度说明：无
- 建议方案一：补充 lightweight data-free tests，覆盖 `segment_users(...)` 的分群边界、`simulate_roi(...)` 的 ROI / budget / retention 不变量。
- 方案一涉及范围：`src/business.py`、`tests/test_business.py`、`tests/README.md`。
- 建议方案二：不追求完整单测，只增加 1~2 个最小 regression test，保护 `Persuadables only` 主策略和 `budget_sweep` 的关键输出结构。
- 方案二涉及范围：测试文件少量新增，低成本保护核心 narrative。
- 建议方案对比：
  - 方案一更像工程闭环，适合 portfolio 化；
  - 方案二更适合 interview-first 场景，成本低但覆盖有限。
- 当前建议方向：如果后续目标转向 portfolio，优先方案一；若仍以面试为主，方案二即可，甚至可以继续暂缓。

#### 采用的方案（后续重点详细补充）
- 是否已确定采用方案：否
- 采用方案说明：待补充
- 实施记录：待补充
- 变更影响：待补充
- 注意事项：待补充

#### 核查记录
- 核查状态：已核查
- 核查方式：测试文档、测试文件与业务代码静态交叉审阅
- 核查结果：已确认目前测试更偏 export contract，尚未直接保护 Phase 3 主业务逻辑。
- 遗留问题或后续动作：若新增测试，应先决定是走“最小 narrative guardrail”还是“完整 business regression gate”。

---

## 问题 5：审计产物 metadata 仍不完整，artifact chain 尚未达到“审计级完整”

### 第一部分：问题情况与介绍
- 问题简况：当前部分本地 JSON / panel 产物仍缺少关键诊断值或关键假设参数，导致单看 artifact 还不能完整自证分析口径。
- 问题详情与背景：
  - `data/processed/psm_match_panel.json:14`-`data/processed/psm_match_panel.json:19` 当前只记录 `match_rate_max`、`treated_utilization` 等指标，没有把 `OVL`、`overlap_ratio` 等关键 overlap 诊断一起落盘；
  - `data/processed/roi_simulation.json:130`-`data/processed/roi_simulation.json:135` 的 `_meta` 只记录 `ate_observed` / `ate_from_cate` 等结果型信息，没有写入 `cost_per_contact`、`baseline_threshold`、`cate_threshold_pct` 等关键假设；
  - 因此这些 artifact 更像“结果快照”，还不是“可独立审计的完整口径说明”。
  - 当前项目通过 docs 可以解释这些口径，但 artifact 自身仍然不够自描述。
- 影响范围：
  - `data/processed/psm_match_panel.json`
  - `data/processed/roi_simulation.json`
  - 审计链完整性、离线结果复核便利性
- 相关线索：
  - `data/processed/psm_match_panel.json:14`
  - `data/processed/roi_simulation.json:130`
  - `docs/Phase2_Execution_PRD.md:101`
  - `docs/Phase3_Execution_PRD.md:167`
  - `src/business.py:598`
- 补充说明：
  - 这不是当前面试叙事的主 blocker；
  - 若后续强调“audit trail”或“artifact reproducibility”，这个问题会被放大。

### 第二部分：解决与跟进记录
- 当前状态：未解决
- 当前进度说明：无
- 建议方案一：在现有 JSON / panel 里直接补字段，把关键阈值、诊断值和 run-level metadata 写进去。
- 方案一涉及范围：`src/causal.py`、`src/business.py`、相关 notebook 落盘逻辑、`data/README.md`。
- 建议方案二：新增统一 manifest / run metadata 产物，集中记录当前 run 的参数、路径、关键口径，再由各 JSON 轻量引用。
- 方案二涉及范围：新增 manifest 文件、多个 notebook / script 的联动修改、文档同步。
- 建议方案对比：
  - 方案一实现简单，最适合当前仓库；
  - 方案二更规范，但超出当前 repo 的必要复杂度。
- 当前建议方向：如后续处理，先走方案一，逐步补齐现有 artifact 的 `_meta`。

#### 采用的方案（后续重点详细补充）
- 是否已确定采用方案：否
- 采用方案说明：待补充
- 实施记录：待补充
- 变更影响：待补充
- 注意事项：待补充

#### 核查记录
- 核查状态：已核查
- 核查方式：processed artifact 文件内容与上游代码/文档静态对比
- 核查结果：已确认 artifact 结果值基本可对上，但 metadata 尚不足以独立自证口径。
- 遗留问题或后续动作：若后续开始补 metadata，应先梳理“每个 artifact 最小必备字段清单”。

---

## 问题 6：`configs/config.yml` 仍不是严格意义上的单一真源

### 第一部分：问题情况与介绍
- 问题简况：虽然仓库现在已经明显更依赖配置，但部分关键参数与输出路径仍在代码中硬编码，`config.yml` 仍不是严格的 single source of truth。
- 问题详情与背景：
  - `configs/config.yml:48` 已定义 `psm.caliper_factor: 0.2`，但 `src/causal.py:216` 仍直接写 `0.2 * std(ps)`；
  - `configs/config.yml:13` 已定义 `matched_data` 路径，但 `src/causal.py:380` 仍直接写 `data/processed/hillstrom_matched.csv`；
  - 这说明当前配置文件更像“主要配置入口”，不是严格意义上完全无漂移的唯一真源；
  - 该问题本身不会立刻引发结果错误，但当路径或参数需要变更时，容易造成“改了 config 但代码没完全跟上”的隐患。
- 影响范围：
  - `configs/config.yml`
  - `src/causal.py`
  - 仓库配置治理、路径维护、一致性承诺
- 相关线索：
  - `configs/config.yml:13`
  - `configs/config.yml:48`
  - `src/causal.py:216`
  - `src/causal.py:380`
  - `README.md:76`（历史单一真源表述背景）
- 补充说明：
  - 当前 README 的相关表述已做过一定降级，但如果未来重新强化“single source of truth”叙事，这个问题会重新暴露。

### 第二部分：解决与跟进记录
- 当前状态：未解决
- 当前进度说明：无
- 建议方案一：把 `caliper_factor`、`matched_data` 等剩余硬编码项全部改成显式从 config 读取。
- 方案一涉及范围：`src/causal.py`、相关 notebook 调用、必要时补参数透传。
- 建议方案二：保留当前实现不动，但在 README / 文档中继续坚持“主要配置入口”而不是“严格唯一真源”的表述。
- 方案二涉及范围：文档口径，不改实现。
- 建议方案对比：
  - 方案一能真正收口工程一致性；
  - 方案二成本低，但只是表述降级，没解决根因。
- 当前建议方向：若项目后续继续工程化，优先方案一；若以面试为主，可接受继续使用方案二的口径边界。

#### 采用的方案（后续重点详细补充）
- 是否已确定采用方案：否
- 采用方案说明：待补充
- 实施记录：待补充
- 变更影响：待补充
- 注意事项：待补充

#### 核查记录
- 核查状态：已核查
- 核查方式：config 与代码实现静态比对
- 核查结果：已确认存在“config 已定义，但代码仍硬编码”的残余点。
- 遗留问题或后续动作：若未来开始修复，需先列出所有仍未 config 化的参数/路径清单，避免只修一半。

---

## 问题 7：SQL validator 的 row-order fallback 仍存在语义假通过风险

### 第一部分：问题情况与介绍
- 问题简况：当前 SQL validator 虽已支持 canonical contract，但在缺少稳定 `customer_id` 时仍会回退到 `row_number() OVER ()` 生成代理键；这会带来“查询能跑通，但 score-feature join 语义可能已经错位”的假通过风险。
- 问题详情与背景：
  - `scripts/validate_sql_slice_duckdb.py:88`-`scripts/validate_sql_slice_duckdb.py:92` 当前会在 `user_segments.csv` / `hillstrom_features.csv` 缺少稳定 `customer_id` 时，分别退回到 `row_number() OVER ()` 生成代理键；
  - `scripts/validate_sql_slice_duckdb.py:97`-`scripts/validate_sql_slice_duckdb.py:101` 已明确说明这是为了 backward-compatible local demos；
  - 风险在于：如果两个 CSV 的行顺序不完全一致，Q0/Q7/Q8/Q9 仍可能形式上跑通，但 `analytics.uplift_scores.customer_id` 与 `analytics.hillstrom_features.customer_id` 的 join 语义已经偏离真实用户对应关系；
  - 当前 `docs/sql_slice.md:21` 已将其降级表述为“本地复现链路中的 repo-local surrogate `customer_id` / fallback demo contract”，但脚本层面的语义风险本身并未消失；
  - 这意味着该 validator 更接近 **local smoke test**，而不是 **SQL 语义正确性的充分证明**。
- 影响范围：
  - `scripts/validate_sql_slice_duckdb.py`
  - `docs/sql_slice.md`
  - `data/processed/user_segments.csv` 与 `data/processed/hillstrom_features.csv` 的本地 join 可信度
  - SQL appendix / local demo 的可解释边界
- 相关线索：
  - `scripts/validate_sql_slice_duckdb.py:88`
  - `scripts/validate_sql_slice_duckdb.py:89`
  - `scripts/validate_sql_slice_duckdb.py:90`
  - `scripts/validate_sql_slice_duckdb.py:91`
  - `scripts/validate_sql_slice_duckdb.py:97`
  - `scripts/validate_sql_slice_duckdb.py:101`
  - `docs/sql_slice.md:21`
  - `docs/sql_slice.md:28`
- 补充说明：
  - 这是一个被明确延期处理的问题；
  - 当前如果继续把 SQL slice 讲成 local demo / appendix，这个问题影响可控；
  - 但若未来想把这条 SQL 链路进一步包装成更严格的 contract handoff，这会成为核心阻碍之一。

### 第二部分：解决与跟进记录
- 当前状态：未解决
- 当前进度说明：无
- 建议方案一：继续保留 fallback，但在脚本和文档中更明确标注“local smoke test / row-order demo contract”，并避免把校验结果表述成语义正确性证明。
- 方案一涉及范围：`scripts/validate_sql_slice_duckdb.py` 注释、`docs/sql_slice.md`、必要时 `README.md` 的 SQL appendix 边界说明。
- 建议方案二：移除 `row_number()` fallback，要求 `user_segments.csv` 与 `hillstrom_features.csv` 都必须显式提供稳定 `customer_id`，validator 默认只接受 canonical local contract。
- 方案二涉及范围：validator 实现、`user_segments.csv` 导出逻辑、历史 demo 兼容性、SQL appendix 文档。
- 建议方案三：保留 fallback，但额外增加“行序一致性 / join 合理性”显式校验，尽量把假通过风险降到最低。
- 方案三涉及范围：validator 实现、CSV 预检查逻辑、可能新增 run metadata 或 row hash 对照。
- 建议方案对比：
  - 方案一最符合当前 interview repo / local appendix 定位，成本最低；
  - 方案二最干净，能真正消除语义假通过，但会破坏一部分历史 demo 兼容性；
  - 方案三介于两者之间，能部分补强风险，但实现复杂度高于当前 repo 的必要水平。
- 当前建议方向：若仓库仍以 interview-first 为主，维持方案一即可；若未来要强化 SQL appendix 的 contract 严格性，再优先考虑方案二。

#### 采用的方案（后续重点详细补充）
- 是否已确定采用方案：否
- 采用方案说明：待补充
- 实施记录：待补充
- 变更影响：待补充
- 注意事项：待补充

#### 核查记录
- 核查状态：已核查
- 核查方式：validator 脚本静态审阅 + contract 逻辑回查
- 核查结果：已确认 validator 会优先使用 canonical 字段，但仍保留 `row_number()` fallback；在缺少稳定 `customer_id` 时，存在“本地 SQL 跑通但 join 语义可能已错位”的假通过风险。
- 遗留问题或后续动作：若未来强化 contract enforcement，应先决定是否保留 legacy-demo 输入兼容，或直接要求稳定 `customer_id` 成为硬门槛。

---

## 问题 8：`Phase1_DoD.ipynb` 的定位仍偏旧，未完全适配当前仓库整体回归门禁叙事

### 第一部分：问题情况与介绍
- 问题简况：`Phase1_DoD.ipynb` 仍主要体现“Phase 1 自己的 DoD 文档”，与当前仓库把它当作项目级最小 regression gate 的叙事并不完全一致。
- 问题详情与背景：
  - `notebooks/Phase1_DoD.ipynb:8`、`notebooks/Phase1_DoD.ipynb:18` 仍将自己定义为“Phase 1 — Data Pipeline & Feature Engineering”；
  - `notebooks/Phase1_DoD.ipynb:137` 只列 `01`、`02`、`Phase1_DoD` 为已测试 notebooks；
  - `notebooks/Phase1_DoD.ipynb:181` 还在用 “Next: Phase 2” 的过时推进方式；
  - 同时当前仓库叙事里它又被当作一个最小端到端回归门禁来引用，因此角色存在轻微错位；
  - 此外 `notebooks/Phase1_DoD.ipynb:101`-`notebooks/Phase1_DoD.ipynb:103` 仍带有 `os.chdir(project_root)` + 直接打开 config 的早期实现风格，也让它更像历史文档而不是现代 regression gate。
- 影响范围：
  - `notebooks/Phase1_DoD.ipynb`
  - `README.md` 的快速阅读路径与回归门禁叙事
  - 项目“最小可复现入口”的清晰度
- 相关线索：
  - `notebooks/Phase1_DoD.ipynb:8`
  - `notebooks/Phase1_DoD.ipynb:18`
  - `notebooks/Phase1_DoD.ipynb:101`
  - `notebooks/Phase1_DoD.ipynb:137`
  - `notebooks/Phase1_DoD.ipynb:181`
  - `README.md:31`
  - `README.md:137`
- 补充说明：
  - 这是典型的“老文档角色漂移”问题；
  - 当前对春招 ROI 很低，因此长期处于可接受的 deferred 状态。

### 第二部分：解决与跟进记录
- 当前状态：未解决
- 当前进度说明：无
- 建议方案一：重写或刷新 `Phase1_DoD.ipynb`，把它明确成当前仓库的最小 regression gate，并更新测试范围、文案与执行边界。
- 方案一涉及范围：`notebooks/Phase1_DoD.ipynb`、`README.md`、可能联动 `docs/Phase1_Execution_PRD.md`。
- 建议方案二：不改 notebook，只在 README / docs 里降低它的“项目级 gate”权重，明确它只是 Phase 1 验收产物。
- 方案二涉及范围：文档口径调整，不改 notebook 实现。
- 建议方案对比：
  - 方案一更干净，但收益主要面向工程整洁度；
  - 方案二足够应对当前 interview-first 目标。
- 当前建议方向：若不打算继续工程化，可采用方案二；若未来要提升仓库整体完成度，再考虑方案一。

#### 采用的方案（后续重点详细补充）
- 是否已确定采用方案：否
- 采用方案说明：待补充
- 实施记录：待补充
- 变更影响：待补充
- 注意事项：待补充

#### 核查记录
- 核查状态：已核查
- 核查方式：DoD notebook 与 README/项目定位静态比对
- 核查结果：已确认该 notebook 当前更像 Phase 1 历史验收文档，而不是完全贴合现阶段仓库叙事的 regression gate。
- 遗留问题或后续动作：如果后续要统一入口，应先决定是“升级 DoD”还是“降级其在 README 中的角色”。

---

## 问题 9：Q8 SQL 文件名仍保留 legacy 命名，和实际行为存在轻微偏差

### 第一部分：问题情况与介绍
- 问题简况：`sql/sql_slice/08_cutoff_solver_budget_argmax_expected_roi.sql` 的文件名仍带有“argmax expected roi”含义，但当前 SQL 实际行为更接近“预算上限下的 `uplift_score > 0` top-K helper”。
- 问题详情与背景：
  - 当前 SQL 文件头部已经明确说明：该文件名是 legacy，查询并不是严格意义上的 ROI-ratio argmax solver，而是预算约束下的 top-K / cutoff 辅助器，见 `sql/sql_slice/08_cutoff_solver_budget_argmax_expected_roi.sql:6`-`sql/sql_slice/08_cutoff_solver_budget_argmax_expected_roi.sql:8`；
  - `docs/sql_slice.md` 当前也已同步采用更准确的表述：把 Q8 定义为 `Budget allocation helper`，并说明“当前 SQL 未实现 ROI 过滤”，见 `docs/sql_slice.md:103`、`docs/sql_slice.md:122`、`docs/sql_slice.md:243`；
  - 但文件路径本身仍然保留旧命名，这会给 reviewer 带来轻微认知噪音：文件名像“严格优化器”，实际行为是“预算内 top-K demo helper”；
  - 当前项目已经通过文档与注释收口叙事，因此这不是逻辑 bug，而是一个残余的命名一致性问题。
- 影响范围：
  - `sql/sql_slice/08_cutoff_solver_budget_argmax_expected_roi.sql`
  - `docs/sql_slice.md`
  - `README.md` 中对 SQL appendix / local demo 的专业感与命名一致性
- 相关线索：
  - `sql/sql_slice/08_cutoff_solver_budget_argmax_expected_roi.sql:2`
  - `sql/sql_slice/08_cutoff_solver_budget_argmax_expected_roi.sql:6`
  - `sql/sql_slice/08_cutoff_solver_budget_argmax_expected_roi.sql:8`
  - `docs/sql_slice.md:103`
  - `docs/sql_slice.md:122`
- 补充说明：
  - 当前文档层已经有充分解释，因此这不是高优先级 blocker；
  - 该问题主要影响的是 reviewer 的第一印象与命名整洁度，而不是结果正确性。

### 第二部分：解决与跟进记录
- 当前状态：着手解决
- 当前进度说明：
  - 已完成内容：已在 SQL 文件头注释和 `docs/sql_slice.md` 中明确说明当前 Q8 的真实行为与 legacy 文件名之间的差异；
  - 正在处理的部分：评估是否值得为这个命名问题承担一次 repo-wide rename 的维护成本；
  - 尚未完成内容：文件路径本身尚未调整，README / docs / legend 仍沿用当前 legacy 文件名；
  - 当前卡点或待确认事项：该问题主要影响 polish 而非核心面试信号，因此是否继续处理取决于仓库后续是否转向 portfolio 化。
- 建议方案一：保持现有文件名不动，继续依赖 SQL 头注释与 `docs/sql_slice.md` 解释 legacy naming。
- 方案一涉及范围：不改文件路径，仅维持现有文档/注释口径。
- 建议方案二：做一次 repo-wide rename，把文件名改成更准确的 helper 命名，并同步更新 README / docs / SQL legend 引用。
- 方案二涉及范围：SQL 文件路径、`docs/sql_slice.md`、README、任何引用该路径的文档与脚本。
- 建议方案对比：
  - 方案一成本最低，适合当前 interview-first 阶段；
  - 方案二命名最干净，但收益主要体现在 polish，而不是核心面试信号。
- 当前建议方向：若仓库当前重心仍是面试，维持方案一即可；若未来要进一步 portfolio 化，再考虑方案二。

#### 采用的方案（后续重点详细补充）
- 是否已确定采用方案：否
- 采用方案说明：待补充
- 实施记录：待补充
- 变更影响：待补充
- 注意事项：待补充

#### 核查记录
- 核查状态：已核查
- 核查方式：SQL 文件头注释、README / docs 命名口径交叉审阅
- 核查结果：已确认当前“行为定义”已收口，但文件名仍保留 legacy 误导性语义。
- 遗留问题或后续动作：若后续决定统一命名，应先清点所有路径引用，避免 rename 后遗漏 README / docs / validator 中的链接。
