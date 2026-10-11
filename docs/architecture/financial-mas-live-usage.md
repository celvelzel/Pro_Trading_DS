# 真实金融 MAS 接入与组合约束

## 接入方式

页面 `/copilot` 选择 Market、Portfolio 或 Combined，然后选择数据来源：合成演示 / 我的美股持仓与最新行情。真实模式使用单独的金融模型配置；不沿用 General 的 `AI_*` 模型配置。

真实模式的流程为：准备行情与持仓 → 查看并确认快照 → 填写/解析组合约束 → 确认约束 → 创建独立 run → Review 审批或 Auto 执行。快照之后保持不变，审批、重复投递和 worker 重启都不会重新抓取行情或读取变化后的持仓。

支持美股 / USD、只读研究与模拟。Yahoo 提供最新可用分钟估值与已收盘日线，可能延迟；这不是交易所实时流。需要真正的实时授权行情时，应新增明确的数据供应商适配器，并验证时间戳、币种、复权和数据权限，不能将普通行情缓存换个名字当实时数据。

## 第一步：填写独立模型配置

仓库根目录已准备 `financial-mas.json`，密钥为空，已加入 Git 忽略。填写你的 OpenAI-compatible 服务配置：

```json
{
  "base_url": "https://你的模型服务/v1",
  "model": "你的模型名称",
  "api_key": "你的密钥",
  "timeout_seconds": 25
}
```

服务需支持 `/chat/completions` 和 JSON object 返回。每个 Specialist 独立调用、上下文分别构建；同一模型可以承担多个角色。严格校验角色、结构化字段、证据引用和工具权限；格式错误会失败，不会把任意文本当成已验证结果。

也支持单独的 `FINANCIAL_AI_BASE_URL`、`FINANCIAL_AI_MODEL`、`FINANCIAL_AI_API_KEY` 环境变量，优先于文件。`FINANCIAL_CONFIG_PATH` 可指定另一份配置文件。API/worker 必须使用相同配置与数据库；配置文件不要提交或发给他人。页面“测试独立模型连接”只发送连接检查消息，不发送持仓。更换模型/地址后应重新准备快照；轮换同一服务的密钥不影响快照身份。

尚未填写真实密钥时，表单与规则解析、合成演示仍可使用；真实模式和模型解析会明确提示配置缺失。

## 第二步：迁移并启动

PowerShell 终端一：

```powershell
cd C:\Develop\canvas\Pro_Trading_DS
$env:PYTHONPATH="$PWD\backend;$PWD;$PWD\lobster_quant"
# 与已有后端 Agent 数据库一致；不要为了启动另建一个空库覆盖旧会话。
$env:DATABASE_URL="sqlite+aiosqlite:///C:/Develop/canvas/Pro_Trading_DS/backend/data/agent.db"
$env:REDIS_URL=""
New-Item -ItemType Directory -Force backend/data | Out-Null
python -m alembic upgrade head
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

本次新增 migration 为 `0005_financial_datasets`，只增加不可变输入快照表。若你原来配置了其他 `DATABASE_URL`，继续使用原地址，再执行迁移。缺少新增依赖时从仓库根目录执行 `python -m pip install -r backend/requirements.txt`；模型服务凭证不是 Python 依赖。

终端二：

```powershell
cd C:\Develop\canvas\Pro_Trading_DS\lobster-quant-web
$env:NEXT_PUBLIC_API_URL="http://localhost:8001"
npm run dev
```

## 第三步：保存实际持仓与现金

1. 打开 `/portfolio`，用现有添加持仓功能输入美股标的、股数和成本价。
2. 编辑 **Cash Balance**，明确保存实际 USD 现金余额，即使余额为 0 也要保存。
3. 金融 MAS 从同一个 API 工作目录下的 `data/portfolio/positions.json` 和 `cash.json` 只读捕获数据。按上述命令运行时，完整目录是 `backend/data/portfolio/`。
4. 缺失或损坏的现金文件不会被当成默认 100,000；成本价不会用于估值。缺行情、混合币种、重复标的和负数量会被拒绝。

`FINANCIAL_PORTFOLIO_DIR` 可指定另外的本地只读持仓目录；该设置只改变金融快照来源，不改变现有持仓编辑页的存储目录。此入口没有券商账户同步，来源是你在项目中保存的记录。首次检查准备后的股数与现金是否正确。

准备快照不会写回 positions/cash 文件。最终提案与模拟权重只写入金融研究数据库。

## 第四步：确认资产分类

股票的 asset_class 可来自 Yahoo 的 EQUITY 元数据；ETF 不默认全部当成股票。行业分类不能推测。需要 ETF/行业约束时，将 `financial-classifications.example.json` 复制为 `financial-classifications.json`，保留你的持仓标的并核对分类：

```json
{
  "MU": {"asset_class": "equity", "sector": "TECH", "source": "user-confirmed-classification"},
  "SOXX": {"asset_class": "equity", "sector": "TECH", "source": "user-confirmed-classification"},
  "TLT": {"asset_class": "other", "sector": "BOND", "source": "user-confirmed-classification"}
}
```

`asset_class` 当前仅支持 `equity` / `other` / null；行业标识必须与表单/约束里的标识一致。缺失分类的相关硬约束返回 unknown，不能据此生成已通过检查的提案。`FINANCIAL_CLASSIFICATIONS_FILE` 可指定另一份文件。

## 第五步：页面操作

1. 打开 `/copilot?workflow=combined&symbol=MU`；若 MU 不在你的持仓中，改为实际持有的标的。
2. 数据来源选“我的美股持仓 / 最新行情”。测试独立模型连接。
3. 点击“准备真实数据快照”。核对现金、股数、估值价格与价格时间；勾选允许用于独立模型分析。
4. 填写组合约束，或使用下面的自然语言流程；勾选“已核对表单中的组合约束”。
5. 点击“开始 combined 真实分析”。第一次可选择 Auto 观察流程；Review 先批准 Market，等它进入终态后再批准 Portfolio。
6. 查看各 run 的状态、角色/证据轨迹、Market 假说与限制、Portfolio 权重、风险比较及历史模拟。完成后可点击“新建研究任务”；需要新行情时重新准备快照。

开始真实分析后，持仓相关信息、用户约束和分析证据会发送到你配置的模型服务；密钥只在后端使用。Market-only 不读取个人持仓；Portfolio/Combined 读取实际持仓并只创建快照。

## 组合约束表单

| 字段 | 行为 |
| --- | --- |
| 现金最低比例 | 最低现金权重 |
| 现金最高比例 | 以 CASH 的单资产上限执行；可避免全现金提案 |
| 股票总仓位上限 | 基于已确认的 asset_class 检查 |
| 单资产上限 | 为本次快照中的标的逐项添加；可移除 |
| 行业上限 | 依据可信行业分类检查，分类不足不能通过 |

页面填写百分比，API 使用 0–1 比例。现金下限大于上限、比例越界或标的不在快照中会阻止运行。所有条件最后由确定性工具检查，LLM 不能放宽约束。

## 自然语言组合约束

可直接输入：

> MU 不超过 25%，现金 20%–30%，股票总仓位最多 70%

1. 点“解析为约束草稿”。规则解析支持常见明确比例，无需 LLM；勾选“使用独立金融模型解析”可解析其他表达及匹配已提供的行业标识。
2. 检查识别的条件和解释后的百分比。所有原文条件都需要覆盖；遗漏、模糊或不支持条件保留为待澄清项。
3. 没有待澄清项时，点“将草稿填入表单”，可继续手动修改。
4. 核对最终表单并确认，再开始运行。改动描述或数值会使确认失效。

“稳健一点”“股票至少 50%”“目标年收益 15%”“最大回撤 10%”当前不属于可执行的硬约束，不能静默丢弃或自行换算。可以澄清为支持的条件，也可明确点击“清除描述，手动填写”。模型解析不是授权入口，返回草稿后不会直接创建 run 或执行交易。

## 数据与结果限制

- 日线使用交易日历确定的实际收盘时间，排除仍在形成的日线；原始 OHLCV 和复权风险序列分别保存。
- 当前获取的历史数据以实际获取时间作为 available_at，as_of 在捕获完成后确定；不用于声称旧时点已经知道后续修订的历史数据。
- 当前模型生成的权重用于固定权重回顾情景；不代表这些权重在历史当时已生成，不是 walk-forward 策略验收或未来收益预测。
- 最新分钟估值验证时间和完整交易日覆盖；休市沿用最近实际行情并显示价格时间，硬年龄上限为 7 天，开市后较长延迟会拒绝。不是将休市价格标成当下实时价格。
- 新闻只采纳明确发布时间/来源的条目，availability 为实际获取时间。没有新闻就报告缺证据，不生成新闻。
- `completed` 表示执行流程结束；`partial`/`insufficient_evidence` 表示调查证据有限；`feasible` 仅表示当前提案通过确定性约束、风险和模拟检查，不表示收益最优。
- 单个 run 仍受现有 120 秒预算及跨 MAS 有界 TTL 限制；慢模型可能产生失败或证据传递降级。模型配置/数据失败没有演示回退。
- 当前应用没有账户鉴权；以上是本机研究入口，不是已完成生产多用户隔离的交易服务。

## 验证范围

本次实际 Yahoo 数据检查取得 MU、SOXX、SPY 各 251 条日线，并验证其时间不晚于捕获 as_of。没有调用真实 LLM，因为新的模型配置尚待用户填写。

记录的前端全量单测为 217 passed，实际 API Chromium 浏览器为 9/9，TypeScript、变更区 ESLint 和生产 build 通过。后端较大回归为 666 passed、1 个 fresh-process 测试触发原有 30 秒超时；对应四种独立运行矩阵另跑 4/4 通过，后续快照/风险/迁移增量 144 passed。超时原始记录保留，不能把该次大回归写成全量绿灯。最终补充检查见同目录 final 日志。

最终补充：live API/worker、确定性组合工具、迁移及完整 bootstrap 集合 166 passed；加入数据集表的迁移升级/回滚和 PostgreSQL DDL 断言 2 passed；前端 217 passed、自然语言实际 API 浏览器 2/2、变更区 ESLint 和 production build exit 0。SQL/worker 验证仍为 SQLite/注入模型范围。

真实执行配置的 API、worker 重建、独立 run、Combined 审批、配置缺失时安全失败、快照校验与无文件回写采用注入 provider/data 测试，不能称为真实模型端到端验收。浏览器实际 API 检查使用合成演示，额外验证自然语言草稿、确认门和现金上限确实进入计算流程。原始日志位于 `logs/financial-mas/check-20261011/`。

行情接口依据 [yfinance 官方文档](https://ranaroussi.github.io/yfinance/reference/index.html)，交易日历依据 [exchange_calendars 源码与会话 API](https://github.com/gerrymanoim/exchange_calendars/blob/master/exchange_calendars/exchange_calendar.py)。后端重建只读取已保存输入，不复用通用 DataEngine 的未知复权/过期缓存结果。
