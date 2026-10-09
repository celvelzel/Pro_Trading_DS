# 双金融 MAS 逐项接手台账

核对日期：2026-10-09；原中断续接基线：`624f4b2`；本轮连续性审计启动 HEAD：`1e7771c`；W7 contract v1 冻结提交：`a635d8a`。共 63 项，逐项对应原计划。独立连续性审计确认 19 个已接受集成检查点及 owned 文件未丢失；README 用户修改保留。W7 contract v1 与实现均已独立 Review PASS，W7 Acceptance Gate 于 `2c83826` 集成后通过。W8 已开放；fixtures 仍只代表输入准备，真实工作流基准尚未执行。原计划定义不变，本表补充执行状态。

DONE 表示该任务已接受的源码或准备成果；不代表整个阶段所有任务完成。CANDIDATE 表示仅在未合并分支实现，不能作为依赖已就绪的依据。FIXTURE_DONE 仅指评测输入准备，未执行工作流。PARTIAL、DEFERRED、IN_PROGRESS、OPEN 均仍需完成。

| 任务 | 状态 | 原计划要求 |
| --- | --- | --- |
| W0-T1 | DONE | 记录 `git rev-parse HEAD`、工作区是否干净、活跃分支；创建 feature branch 和工作树，禁止在 `main` 直接编码。 |
| W0-T2 | DONE | 逐一确认源文件、依赖、SQL migration head、local/Compose 两种启动方式、已有接口及测试命令；维护 `docs/architecture/financial-mas-inventory.md`。 |
| W0-T3 | DONE | 执行并记录（测试不保证先通过）量化核心、Backend、前端单测与 build；区分基线已有失败与新增失败。 |
| W0-T4 | DONE | 新增 `docs/adr/0002-dual-autonomous-financial-mas.md`：两个独立 Run、Runtime 复用、工具权限、联合 router、迁移、事件、预算、回滚和无实盘边界。 |
| W0-T5 | DONE | 定义跨 Agent 与跨 MAS 输入/输出契约、外部 API 兼容策略（优先添加而不是改变旧接口）。 |
| W1-T1 | DONE | `backend/agent/shared/`：`SpecialistRegistry`（角色/模型/工具 allowlist）、`SpecialistInvoker`（独立模型调用、独立 context）、`WorkflowDriver` Protocol、`RunBudget`（calls/tool/time/rounds/depth）。 |
| W1-T2 | DONE | Domain-specific `MarketState` / `PortfolioState` 的统一 snapshot/checkpoint 接口；共享不是共用一个业务 state。 |
| W1-T3 | DONE | `FinancialMASDispatcher` 接入现有 agent worker、run lifecycle；金融 typed API 创建独立 run_id 并保留旧 `GeneralAgent` 行为。W7 API/worker 与三模式真实 API E2E 验证见下方 W7 Gate 记录。 |
| W1-T4 | DONE | 子 Agent 结果先结构化验证，再由 Coordinator 单写入 shared state；记录 who/what/why/evidence id，不能暴露思维链。 |
| W1-T5 | DONE | 完成中间结果持久化、恢复（after worker restart）、暂停/取消、超时、冲突版本、重复投递去重、任务预算耗尽安全停止。 |
| W1-T6 | DONE | MAS/cross_mas 审计事件持久化，Financial SSE 与角色/证据 Timeline 已接线；W7 真实浏览器流程验证游标、完成事件、Combined 双 run 及 General 回归。 |
| W1-T7 | DONE | 给老 Copilot 跑回归；新 fake-provider fixture 可以明确注入角色响应脚本。 |
| W2-T1 | DONE | 基于 `DataEngine` 封装 `get_market_history(symbol, as_of, lookback, adjustment)`；输出经交易日排序的 OHLCV、provider、as_of、data_last_bar_at、币种/交易市场、缺口标识。不假设 provider 默认具备 as_of，必要时本地过滤并做不可用检测。 |
| W2-T2 | DONE | `calculate_market_anomaly`：return、volume/20d、与 SPY/sector benchmark 的同日期 excess return、相对强弱；严格处理停牌、NaN、非交易日、样本不足、复权。无模型数值推算。 |
| W2-T3 | DONE | `get_event_evidence`：先只支持手工整理的历史“新闻/公告” fixture 与现有 `RAG` / Document Retriever；如果无官方历史新闻 provider，明确返回 `unavailable`，不要偷偷让 LLM 编新闻。未来 live adapter 独立 PR。 |
| W2-T4 | DONE | Evidence normalization：published_at、available_at、retrieved_at、source URL、内容 hash、time cutoff。没有发布时间的文本不能用于严格历史归因。 |
| W2-T5 | DONE | 建 8–12 个历史示范事件/合成证据包（带事实真值，不给出虚假唯一因果）；含行业共振、晚于收盘公告、谣传、证据不足。 |
| W2-T6 | DONE | typed tool registration、unit tests、fixture versions；读权限、安全引用校验。 |
| W3-T1 | DONE | 新的 **strict readonly** `get_portfolio_snapshot`，拒绝成本价冒充市价、默认虚拟现金冒充用户真实现金；缺市价/币种/日期不足时输出 `insufficient_data`，可选显式 `demo_portfolio` fixture。 |
| W3-T2 | DONE | `PortfolioRiskAnalyzer` 计算：组合实际权重、单资产集中度、现金比例、基于同日期收益序列的波动率、最大回撤、相关性/集中度预警。明确预期回报、数据缺失处理和统计窗口；不要把旧 OFF Engine 称组合风险。 |
| W3-T3 | DONE | `AllocationSimulator`：基于日期对齐的 total-return/复权数据及现金，按目标权重、rebalance cadence、成本/滑点生成净值；实现 no look-ahead。它不等于现有 `PortfolioBacktest` 的 equity-curve 平均。 |
| W3-T4 | DONE | 设计约束 schema：`max_weight_by_symbol`、`min_cash_weight`、`max_equity_weight`、`max_sector_weight`（只有能可靠获取 sector classification 才强制检查）、`sum(weights)=1` 容差、nonnegative。对含糊/冲突自然语言必须在执行前澄清或显式 infeasible。 |
| W3-T5 | DONE | `validate_allocation`：**确定性** hard constraints 检查，非 Agent 主观判断；指定来源的无法检查条件 => `unknown`, 不得误写为 pass。 |
| W3-T6 | DONE | 轻量 `generate_feasible_candidates`：以简单规则或有界优化产生候选，暂不做复杂收益预测/高阶 MVO；结构化失败原因。 |
| W3-T7 | DONE | 20–30 个可自动评测的组合情景（feasible / infeasible / missing price / conflicting constraints / high concentration / mixed currencies）。 |
| W3-T8 | DONE | typed tools + numerical tests：已知收益路径手算验证、day alignment、费用、空持仓、负权重、总权重超/不足、零波动、缺数据和 snapshot 不变性。 |
| W4-T1 | DONE | `backend/agent/market_mas/` 定义独立 WorkflowDriver、Coordinator、state、prompts、specialists、critic、finalizer。 |
| W4-T2 | DONE | Supervisor 先计算异常，并建立市场/行业/公司/未知因素的竞争假说；每个假说必须标 support / against / unverified。 |
| W4-T3 | DONE | Price-Volume Specialist 使用 only permitted market tools；Macro-Sector Specialist 对比可获得的 sector/macro evidence；Event Specialist 搜索可追溯事件。三者拥有不同上下文和工具权限。 |
| W4-T4 | DONE | Evidence Critic 独立核对消息发布时间、来源真实性与时间顺序，遇冲突给 `REQUEST_CHECK`；不根据新闻标题强行断定因果。 |
| W4-T5 | DONE | Coordinator 基于 `missing_checks` 和预算决定下一次调查；明确区别“新 evidence 改变动作”与固定 waterfall。 |
| W4-T6 | DONE | 汇总强类型 `MarketInvestigationArtifact`：事实、可能解释、反证、缺失证据、拒绝过度归因；所有数字有 tool citations。 |
| W4-T7 | DONE | 最小自足入口独立运行、不依赖 Portfolio MAS。多轮、任务取消/超时、失败降级测试。 |
| W4-T8 | DEFERRED | 固定流水线和单 Agent + 相同工具的 baseline；用 case 测验证率、晚发布信息错误、工具/Token 成本。 |
| W5-T1 | DONE | `backend/agent/portfolio_mas/` 定义独立 WorkflowDriver、Coordinator、state、prompts、specialists、verifier、finalizer。 |
| W5-T2 | DONE | Opportunity Specialist 仅提出候选方向与定性理由，不凭空制造预期收益；Risk Specialist 通过工具审查集中度、相关性、回撤；Constraint Specialist 将用户条件归一化并查矛盾。 |
| W5-T3 | DONE | Coordinator 提交候选配置至 `validate_allocation` 和 `AllocationSimulator`；Verifier 不允许绕过确定性检查。 |
| W5-T4 | DONE | 发现违反硬约束时发 `REVISION_REQUEST`，有界循环重试；如果用户约束不可同时满足则返回 `infeasible`，不擅自放宽限制。 |
| W5-T5 | DONE | 严格以**输入持仓快照 ID**为参考，保存 proposal snapshot 而非修改仓库中实际持仓；支持无 M-MAS 的纯配置需求。 |
| W5-T6 | DONE | `PortfolioProposalArtifact`：before/after、实际计算值、violations、不可测限制、历史模拟假设、风险取舍、人工审阅所需信息。 |
| W5-T7 | DONE | 独立测试：M-MAS API 不可用时 P-MAS 仍完成、价缺失时拒绝无依据提案、用户矛盾条件、重复执行不双写。 |
| W5-T8 | DEFERRED | baseline：单 Agent + 同样工具；不含独立风险 Critic 的 multi-agent；比较 hard-constraint violations、infeasible detection、cost/latency。 |
| W6-T1 | DONE | 统一 `CrossMASRequest/Response` 与 immutable artifact store，M/P 只依赖 shared contracts，不调用对方内部 Python agent classes；已集成 `a0d29f9`。 |
| W6-T2 | DONE | 同时运行时每个 MAS 创建**不同 run_id**；使用 `correlation_id` 链接；保留 parent/cross relation 的持久化图，禁止借用旧的 `parent_run_id` 重新定义旧 retry 语义。 |
| W6-T3 | DONE | MVP 支持 P→M 请求进一步证据和用户组合任务 M→P 传调查 artifact；跨请求声明 `as_of`、scope、授权、预算及 TTL，并要求反向回复关联精确 REQUEST。 |
| W6-T4 | DONE | 严格 cycle guards：`max_hops <= 2`、一次 follow-up、TTL 到期降级、无环等待；覆盖重试幂等、旧 origin 拒绝及无因果回复拒绝。 |
| W6-T5 | DONE | cross-check `as_of`、资产范围、来源存在性与 timepoint；消息不包含任意 prompt 指令，外部证据按不可信文本处理。 |
| W6-T6 | DONE | 对方未部署 / failed / cancelled / budget exhausted 时有限降级，不无限等待；超时、孤儿、过期及重复投递均有测试。 |
| W6-T7 | DONE | Synthetic SQLite router E2E 覆盖 Market-only、Portfolio-only、Combined、独立运行、产物/预算审计与无持仓写入；评测质量基准仍归 W8。 |
| W7-T1 | DONE | 兼容新增 typed Market/Portfolio/Combined API，服务端创建并关联实际 AgentRun ID；legacy `/api/agent` 保持。独立 API、worker 测试及真实 API 浏览器 E2E 通过。 |
| W7-T2 | DONE | typed GET 返回 schema/run/artifact/validation 信息，事件复用 legacy Agent SSE，状态修改经过 versioned lifecycle。独立 API 测试与浏览器 SSE cursor/终态验证通过。 |
| W7-T3 | DONE | Copilot 提供 General/Market/Portfolio/Combined；各 run 独立状态与角色/证据轨迹，展示来源、计算和限制，不展示隐藏思维链。真实 API E2E 通过。 |
| W7-T4 | DONE | Analysis 标的页提供 Market 入口，Portfolio 页提供 Portfolio/Combined 只读入口；两条组合入口完成真实请求和 run，验证没有 portfolio 写请求及本地持仓文件字节未变。 |
| W7-T5 | DONE | Review/Auto 只授权已持久化 run 的研究/模拟阶段；无真实下单/持仓写 API。请求体不携带 holdings/cash/positions，Portfolio 来源为明确标记的不可变 synthetic snapshot。 |
| W7-T6 | DONE | schema/response 校验、SSE replay/reconnect/dedup、加载/错误/partial、可访问性及 General regression 有 unit/browser 覆盖；212 前端单测、TS、lint、build 与 7 条 Chromium 真实 API E2E 通过。 |
| W7 contract v1 | DESIGN_PASS | `docs/architecture/financial-mas-w7-api-ui-contract.md`：独立 Review PASS（2026-10-09），契约冻结。 |
| Gate W7 | PASS | 独立 backend/frontend Review PASS；backend scoped suite 129 passed，router registration 1 passed；frontend 212 unit、TypeScript、owned-file ESLint、production build 通过；真实本地 API + 浏览器 7/7 E2E 通过。Evidence 与范围见下方 W7 Gate 记录。 |
| W8-T1 | FIXTURE_DONE | `eval/market_cases.jsonl`：10–15 个固定事件证据问题；题目分布包括行业共振、错误时序、假新闻、缺证据、未来资料禁止引用。只验可核事实，不将主观“下跌原因”作为唯一真值。 |
| W8-T2 | FIXTURE_DONE | `eval/portfolio_cases.jsonl`：20–30 个约束场景；每例 gold constraint validity、expected failure kind、reference math。 |
| W8-T3 | PARTIAL | 同样数据快照、同样工具与尽可能相同调用预算下：single-agent / fixed pipeline / fully autonomous MAS；可加 verifier ablation。 |
| W8-T4 | OPEN | 指标 M：Evidence citation precision、timing violations、unsupported causal claims、tool/LLM count、latency、partial result correctness。 |
| W8-T5 | PARTIAL | 指标 P：hard constraint violation rate、infeasibility detection、risk-calculation accuracy、data-missing safety、simulated net-value consistency。 |
| W8-T6 | PARTIAL | 安全：prompt injection in event text；工具白名单；异常与失败降级；跨会话引用不可串用；异常输入；价格过期拒绝；无秘密泄露；不能触发 portfolio 写 API。 |
| W8-T7 | PARTIAL | 并发 / 持久化：重复 Celery 投递、cancel/resume/checkpoint restore、乐观锁 409、单调 seq、migration upgrade/downgrade（安全范围内）、缺 Redis inline 执行可用性。 |
| W8-T8 | PARTIAL | 整理 README/ADR/演示脚本/可复现实验，记录真实性：没有实盘、没有验证因果、后验模拟不等于未来收益。 |

W7 实现从 `604cf5d` 开始，后端与前端分别在 `financial-w7-backend`、`financial-w7-frontend` managed worktree 开发；主 Agent 单独集成 `backend/main.py`。已集成提交 `36e72c3`、`79e11e3`、`6ec9b71`、`d782b36`、`5c21269`、`d7b2461`、`2c83826`；精确实现树均经独立 Review。原有 README 15 行用户修改仍未暂存或改写。

## 未完成任务的具体接手边界

- W1-T3/T6：原 W1 阶段保留的金融 lifecycle 与 SSE/UI 缺口已由 W7 typed API、Financial SSE/Timeline 补齐，并在 W7 Gate 完成后关闭。
- W4-T8、W5-T8：已有部分 baseline/ablation hooks，尚无同工具同预算的强单 Agent、Portfolio 固定流水线及实际比较报告；执行债务归 W8，不能以 hook 测试代替。
- W6：路由与来源授权最终提交 `a0d29f9` 已快进集成；独立 Review 对 `dc09ae4..a0d29f9` 完整四文件差异 PASS。Review 揭示并修复两项缺口：router 不得把无授权的 legacy root 推断为 independent；follow-up 回复必须解析确切准入 REQUEST，不可降级成无因果新 READY。确切提交上的 252 项专项（260.85s）和完整 Backend（716 项，438.09s）通过；10 个 fresh-process 实际 worker 入口、legacy-origin 与 reverse-relation 定向矩阵均通过。原始日志及中断/失败候选记录保留在隔离 worktree 的 `logs/financial-mas/w6-repair-*`。W6 Gate 已释放 W7；证据限于 SQLite/合成 provider 和真实 Celery task 函数调用，不代表 Redis/broker/PostgreSQL 或实盘 provider 验收。
- W7：已完成并通过 Gate。真实 API 服务绑定隔离 SQLite `logs/financial-mas/w7-real-api-e2e-agent.db`、关闭 Redis；使用 synthetic snapshot。Chromium E2E 7/7（Market-only、Portfolio-only、Combined 双 run、Portfolio 页两个入口、Analysis 标的入口、General 兼容），无路由 mock。Portfolio 入口 E2E 对 positions/cash 文件存在性与 SHA-256 前后相同作断言，并断言无 portfolio 写请求；实际 `positions.json` SHA-256 为 `4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945`，`cash.json` 测试前后均不存在。真实服务已关闭、3000/8001 端口已释放。此项是 synthetic/local validation，不是 PostgreSQL、Redis/Celery broker、外部 provider 或生产部署验证。
- W8-T1/T2：eval/market_cases.jsonl 12 例、eval/portfolio_cases.jsonl 30 例及独立 Decimal gold 已准备；所有 fixture actual_workflow_executed=false。七个测试函数展开为 46 项用例，不能声称已跑 42 个真实工作流。
- W8-T3/T4/T5：执行实际工作流与同预算基线/消融，保存逐例原始结果、调用计数、工具引用和确定性质量指标；现有工具数值 gold 不是工作流质量。
- W8-T6/T7/T8：已有安全、恢复、迁移片段证据，整合后仍需完整安全/恢复/inline/E2E 与可复现实验。Docker engine 不可用，不能声称已验证真实 PostgreSQL/Redis/Celery。

最新 Gate 和原始测试证据见 [执行台账](financial-dual-mas-execution.md)，暂停时历史快照见 [交接记录](financial-dual-mas-handoff.md)。完整原计划仍是验收依据。

## W4 recovery compatibility repair (closed)

W4-T7 was reopened after a legacy Market macro Specialist result persisted before checkpointing could no longer be resumed after the `f945427` unit-label change. The isolated `financial-market-recovery` worktree reconstructed the issue from the real historical Git blob and retained `logs/financial-mas/reproduce_upgrade.py`, `upgrade-reproduction.log`, `recovery-validation-final-head.log`, and before/after SQLite snapshots. Repair `0e0e327` versions corrected invocation identity while normalizing only restored mutable state; historical invocation rows remain unchanged. Independent review `975cfa9` passed, and the root-owned exact eight-file rerun passed 239 tests in 157.39s (including all 45 Market tests), recorded in `logs/financial-mas/market-upgrade-integrated-root.log`. W4 remains synthetic/offline evidence; no live-provider or causal-accuracy claim is made.

## W7 Acceptance Gate (2026-10-09; PASS)

The frozen W7 API/UI contract remains unchanged. Backend and frontend work stayed in their assigned independent managed worktrees; root owned `backend/main.py` registration and integration. Commits integrated on `codex/financial-dual-mas`: `36e72c3`, `79e11e3`, `6ec9b71`, `d782b36`, `5c21269`, `d7b2461`, `2c83826`. Backend exact implementation tree received independent Review PASS; frontend full implementation and final run-card locator follow-up each received independent Review PASS.

Validation on the integrated source: backend financial API/worker suite **129 passed** (reviewed exact candidate tree; `C:/Users/RickyMa/.codex/worktrees/financial-w7-backend/Pro_Trading_DS/logs/financial-mas/w7-system-unavailable-rerun.log`); main router registration **1 passed**; frontend **212 unit tests passed**, TypeScript check passed, changed-area ESLint passed, and production build passed (`logs/financial-mas/w7-integrated-{unit,tsc,eslint,build}-final.log`). Real local API + Chromium E2E **7/7 passed** (`logs/financial-mas/w7-browser-e2e-final.log`): Market-only, Portfolio-only, Combined (distinct run IDs and both run cards), Portfolio/Combined Portfolio-page entry, Analysis symbol entry, and General Copilot regression. No API route mocks were used.

The E2E API used disposable SQLite `logs/financial-mas/w7-real-api-e2e-agent.db`, `REDIS_URL` unset, and the immutable synthetic `synthetic-mu-soxx-v1` snapshot. Portfolio entry tests asserted no non-read portfolio API requests and identical `positions.json`/`cash.json` existence and SHA-256 before and after; `cash.json` stayed absent. No real order or holding mutation occurred. This gate does not establish PostgreSQL, Redis/broker delivery, external-provider correctness, deployment, or real trading behavior. Initial missing-browser and selector assertion failures are retained in `logs/financial-mas/w7-browser-e2e-missing-browser.log` and `w7-browser-e2e-selector-failure.log`; the first exposed a missing pinned browser install, the second a duplicate text locator in the test. Both were corrected without weakening flow assertions; the full suite then passed.

## W8 continuation scope

Independent read-only W8 audits confirm W8-T1/T2 are fixture preparation only (12 Market + 30 Portfolio cases; every `actual_workflow_executed` remains false). W4-T8/W5-T8 and W8-T3/T4/T5 remain incomplete: baseline hooks are not a quality comparison, there is no actual per-case workflow runner, and no aggregated MAS metrics or raw W8 results exist. W8-T6/T7 have useful unit/integration slices but no joined W8 adversarial/recovery run; secret-leak aggregation is absent. SQLite migration and direct worker-task tests do not prove PostgreSQL, broker, or Redis operation; Docker is still unavailable. Continue with real fixture-backed MAS runs, comparable baselines/ablations, metric calculations, per-case raw evidence, security/recovery matrix, and reproducible scripts/results before declaring W8 PASS.
