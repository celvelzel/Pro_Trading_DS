# 双金融 MAS 逐项接手台账

核对日期：2026-10-09；接手基线：624f4b2。共 63 项，逐项对应原计划。独立连续性审计确认 19 个已接受集成检查点及 owned 文件未丢失；README 用户修改保留。原计划定义不变，本表补充执行状态。

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
| W1-T3 | PARTIAL | `FinancialMASDispatcher` 接入现有 agent worker、run lifecycle，确保 M-MAS/P-MAS 是单独 run id；保留旧 `GeneralAgent`。建议将 domain run 元数据与子调用轨迹通过 additive migration 保存；依现有实现选择引用表结构。 |
| W1-T4 | DONE | 子 Agent 结果先结构化验证，再由 Coordinator 单写入 shared state；记录 who/what/why/evidence id，不能暴露思维链。 |
| W1-T5 | DONE | 完成中间结果持久化、恢复（after worker restart）、暂停/取消、超时、冲突版本、重复投递去重、任务预算耗尽安全停止。 |
| W1-T6 | PARTIAL | Audit Events：Agent invoked/returned、artifact created、challenge、replan、handoff、failure；扩展事件 schema 与 SSE 显示，不能破坏已有 event consumer。 |
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
| W4-T7 | REOPENED | 最小自足入口独立运行、不依赖 Portfolio MAS。多轮、任务取消/超时、失败降级测试。 |
| W4-T8 | DEFERRED | 固定流水线和单 Agent + 相同工具的 baseline；用 case 测验证率、晚发布信息错误、工具/Token 成本。 |
| W5-T1 | DONE | `backend/agent/portfolio_mas/` 定义独立 WorkflowDriver、Coordinator、state、prompts、specialists、verifier、finalizer。 |
| W5-T2 | DONE | Opportunity Specialist 仅提出候选方向与定性理由，不凭空制造预期收益；Risk Specialist 通过工具审查集中度、相关性、回撤；Constraint Specialist 将用户条件归一化并查矛盾。 |
| W5-T3 | DONE | Coordinator 提交候选配置至 `validate_allocation` 和 `AllocationSimulator`；Verifier 不允许绕过确定性检查。 |
| W5-T4 | DONE | 发现违反硬约束时发 `REVISION_REQUEST`，有界循环重试；如果用户约束不可同时满足则返回 `infeasible`，不擅自放宽限制。 |
| W5-T5 | DONE | 严格以**输入持仓快照 ID**为参考，保存 proposal snapshot 而非修改仓库中实际持仓；支持无 M-MAS 的纯配置需求。 |
| W5-T6 | DONE | `PortfolioProposalArtifact`：before/after、实际计算值、violations、不可测限制、历史模拟假设、风险取舍、人工审阅所需信息。 |
| W5-T7 | DONE | 独立测试：M-MAS API 不可用时 P-MAS 仍完成、价缺失时拒绝无依据提案、用户矛盾条件、重复执行不双写。 |
| W5-T8 | DEFERRED | baseline：单 Agent + 同样工具；不含独立风险 Critic 的 multi-agent；比较 hard-constraint violations、infeasible detection、cost/latency。 |
| W6-T1 | CANDIDATE | 统一 `CrossMASRequest/Response` 与 immutable artifact store，M/P 只依赖 shared contracts，不调用对方内部 Python agent classes。 |
| W6-T2 | PARTIAL | 同时运行时每个 MAS 创建**不同 run_id**；使用 `correlation_id` 链接；保留 parent/cross relation 的持久化图，禁止借用旧的 `parent_run_id` 重新定义旧 retry 语义。 |
| W6-T3 | PARTIAL | MVP 支持 P→M 请求进一步证据和用户组合任务 M→P 传调查 artifact；跨请求必须声明 `as_of`、scope、数据授权、预算、timeout。 |
| W6-T4 | PARTIAL | 启用严格 cycle guards：`max_hops <= 2`、最多一次重复问询、TTL 到期降级、无环等待；明确重试幂等。 |
| W6-T5 | CANDIDATE | cross-check `as_of`、资产代码映射、来源存在性、timepoint；消息不包含任意 prompt 指令，所有外部证据按不可信文本处理。 |
| W6-T6 | CANDIDATE | 边界情况：对方未部署 / failed / cancelled / budget exhausted => 本 MAS 产出 partial，不无限等待。 |
| W6-T7 | CANDIDATE | E2E 场景：调查 MU -> 评估含 MU/SOXX 的 demo 组合 -> 生成已验证模拟方案；可在未启用跨 MAS 情况下独立运行双方。 |
| W7-T1 | OPEN | 在现有 `/api/agent` 基础上增加**兼容的 typed 入口**，推荐 `POST /api/financial/market-investigations`、`POST /api/financial/portfolio-reviews`、`POST /api/financial/combined-reviews`；服务端统一创建/关联实际 AgentRun ID。若最终选择向原 `/runs` 加可选 `workflow_type`，必须保留旧请求行为。 |
| W7-T2 | OPEN | 结果 GET 接口带 `schema_version`、run status、artifact ref、validation outcome；继续复用 `/api/agent/runs/{id}/events`、versioned approve/pause/resume/cancel。 |
| W7-T3 | PARTIAL | `lobster-quant-web/src/app/copilot` 新增模式选择：General / Market / Portfolio / Combined，展示角色轨迹、evidence board、风险 before/after 和引用；禁止展示隐藏思维链。 |
| W7-T4 | OPEN | 在 `analysis/[symbol]` 提供“调查异动”，在 `portfolio` 提供“模拟调仓风险复核”链接；默认不会静默持久化用户投资偏好。 |
| W7-T5 | PARTIAL | “Review” 只批准分析/模拟阶段，**不是**授权真实持仓变更或实盘操作；保留两层权限界限。 |
| W7-T6 | PARTIAL | 前端测试：响应 schema、SSE replay/reconnect、重复事件、加载态、错误/partial 状态、可访问性、原页面 regression。 |
| W8-T1 | FIXTURE_DONE | `eval/market_cases.jsonl`：10–15 个固定事件证据问题；题目分布包括行业共振、错误时序、假新闻、缺证据、未来资料禁止引用。只验可核事实，不将主观“下跌原因”作为唯一真值。 |
| W8-T2 | FIXTURE_DONE | `eval/portfolio_cases.jsonl`：20–30 个约束场景；每例 gold constraint validity、expected failure kind、reference math。 |
| W8-T3 | PARTIAL | 同样数据快照、同样工具与尽可能相同调用预算下：single-agent / fixed pipeline / fully autonomous MAS；可加 verifier ablation。 |
| W8-T4 | OPEN | 指标 M：Evidence citation precision、timing violations、unsupported causal claims、tool/LLM count、latency、partial result correctness。 |
| W8-T5 | PARTIAL | 指标 P：hard constraint violation rate、infeasibility detection、risk-calculation accuracy、data-missing safety、simulated net-value consistency。 |
| W8-T6 | PARTIAL | 安全：prompt injection in event text；工具白名单；异常与失败降级；跨会话引用不可串用；异常输入；价格过期拒绝；无秘密泄露；不能触发 portfolio 写 API。 |
| W8-T7 | PARTIAL | 并发 / 持久化：重复 Celery 投递、cancel/resume/checkpoint restore、乐观锁 409、单调 seq、migration upgrade/downgrade（安全范围内）、缺 Redis inline 执行可用性。 |
| W8-T8 | PARTIAL | 整理 README/ADR/演示脚本/可复现实验，记录真实性：没有实盘、没有验证因果、后验模拟不等于未来收益。 |

## 未完成任务的具体接手边界

- W1-T3：金融 worker 分派已完成，旧 /api/agent 创建与 approve/resume/pause/cancel 仍走 General；金融生命周期 API 接线必须在 W7 完成。
- W1-T6：后台 mas/cross_mas 事件已持久化，前端 useAgentEvents 的 EVENT_TYPES 尚未订阅，Timeline 尚未展示角色和 invocation；必须在 W7 补齐。
- W4-T8、W5-T8：已有部分 baseline/ablation hooks，尚无同工具同预算的强单 Agent、Portfolio 固定流水线及实际比较报告；执行债务归 W8，不能以 hook 测试代替。
- W6：候选 866f7df 未合并，独立 Review 为 NEEDS_WORK；拒绝准入后遗留 run 可绕过路由执行，以及 TTL preflight/claim 间隙被复现。ADR-0005 修订设计 8676c26 与共享运行时实现 60999dc 均独立 PASS。主分支已集成运行时及两个 worker 入口 cbee118，138 项 fresh worker/worker-bootstrap/授权测试 PASS。剩余 W6 独立路由候选 866f7df 尚未修复 origin 接线 P1、未 Review、未合并；三个实际模式/重试/并发/TTL Gate 未释放。
- W7-T3/T5/T6：只读结果组件及数值展示已集成 e53bc28/7172360/9248ec5；150 前端单测、production build、TypeScript 检查 PASS。组件不是页面集成；Copilot 模式、真实 API、SSE、两个 run ID 的操作、入口链接及浏览器 E2E 尚未完成。
- W8-T1/T2：eval/market_cases.jsonl 12 例、eval/portfolio_cases.jsonl 30 例及独立 Decimal gold 已准备；所有 fixture actual_workflow_executed=false。七个测试函数展开为 46 项用例，不能声称已跑 42 个真实工作流。
- W8-T3/T4/T5：执行实际工作流与同预算基线/消融，保存逐例原始结果、调用计数、工具引用和确定性质量指标；现有工具数值 gold 不是工作流质量。
- W8-T6/T7/T8：已有安全、恢复、迁移片段证据，整合后仍需完整安全/恢复/inline/E2E 与可复现实验。Docker engine 不可用，不能声称已验证真实 PostgreSQL/Redis/Celery。

最新 Gate 和原始测试证据见 [执行台账](financial-dual-mas-execution.md)，暂停时历史快照见 [交接记录](financial-dual-mas-handoff.md)。完整原计划仍是验收依据。

## 新发现的恢复兼容性缺口

W4-T7 重新打开：原只读 scout 输出表明，旧版 Market 的宏观 Specialist 结果先持久化、checkpoint 尚未写入时，f945427 单位标签修复导致恢复任务的 invocation hash 不匹配，run 保持 executing。原 scout 的临时 harness 未留存，完整 stdout 在 ignored logs/financial-mas/market-upgrade-scout-reproduction.md。独立 financial-market-recovery worktree 已基于真实旧 Git blob 重建并保留 `logs/financial-mas/reproduce_upgrade.py`、`upgrade-reproduction.log`、`recovery-validation.log` 和隔离 SQLite 前后快照；实现候选 975cfa9 为恢复调用加单位版本并把正确单位只应用到恢复中的可变 state，旧 invocation rows 保持不变。实施者报告 239 个 Market/金融运行时测试 PASS；Review 已通过其独立恶意恢复探针，正核对最终 HEAD 的完整测试命令/计数是否包含最后新增的预算耗尽用例。候选未合入，W4-T7/W6 仍不开 Gate。
