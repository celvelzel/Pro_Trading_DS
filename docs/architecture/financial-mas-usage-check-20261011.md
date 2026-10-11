# 双金融 MAS 完成度检查与使用指南

检查日期：2026-10-11。源码基线：`3cfa38a`。本次不修改业务代码。

本页保留上述基线检查的历史结论。后续真实数据、独立 LLM 和自定义/自然语言约束实现的当前操作方式见 [真实接入与约束使用指南](financial-mas-live-usage.md)。

## 结论与完成边界

当前是可运行的双金融 MAS 研究/模拟 MVP：Market 与 Portfolio 有独立角色调用、状态、预算、产物和 run_id，Combined 通过持久化关系传递证据。并非只有设计文档或两个聊天提示词。

W0–W8 台账已关闭，但验收范围是本地 SQLite、合成数据和无网络模拟模型。真实市场/新闻、用户真实持仓、远程 LLM 角色映射与 PostgreSQL/Redis broker 尚未完成相应验收。API 和 worker 当前只接通 `synthetic-demo-v1`。给 General 配置模型密钥不会把金融 MAS 自动切换为真实模型。

| 能力 | 当前检查结果 |
| --- | --- |
| Market 独立调查 | 已实现：确定性行情异常计算、竞争假说、分角色调查、Critic、按 missing_checks 追加调查 |
| Portfolio 独立评审 | 已实现：只读快照、风险计算、候选配置、硬约束检查、历史模拟、独立 Verifier 与有界修订 |
| Combined | 已实现：两个独立 run、共同 correlation、证据准入和传递、跨系统预算/TTL/循环保护 |
| 执行生命周期 | 已实现：Review/Auto、独立审批、版本冲突、暂停/恢复/取消、checkpoint 与重复交付保护 |
| API 与 UI | 三类 typed API、Copilot 模式选择、SSE 轨迹、证据/风险报告、Analysis 与 Portfolio 页面入口已接通 |
| 真实数据与真实模型 | 依赖注入接口存在；公开 API/worker 未接通可信非演示配置 |
| 产品交互 | 演示可用；页面没有组合约束编辑、真实快照导入、历史 run 选择/刷新恢复入口 |
| 交易 | 只研究与模拟；金融工作流不下单、不修改真实持仓/现金 |

Market finalizer 当前只有 `partial` 或 `insufficient_evidence`，不会产出 `verified`；流程 completed 不代表确认因果。Portfolio feasible 只表示提案通过当前约束和计算门，不表示最优收益或适合真实投资。

## 本次验证

- 前端完整单测：13 个文件、212 项通过。
- TypeScript：`npx tsc --noEmit`，exit 0。
- 新隔离 SQLite：Alembic 从空库迁移至 `0004_financial_mas` 成功。
- Chromium + 实际 FastAPI：`financial-mas.spec.ts` 7/7，通过三个工作流、两个 Portfolio 入口、Analysis 链接、General 创建兼容；无 API 路由 mock，持仓/现金文件存在性及字节校验不变。
- 额外 Combined Review HTTP smoke：等待 Market waiting_user，批准后 completed/partial；再批准 Portfolio 后 completed/feasible。示例提案为 CASH=100%，其余为 0%。这说明约束可满足，不代表收益优化。
- 后端专项回归：`python -m pytest backend/tests -q -k 'financial or market_mas or portfolio_mas or cross_mas' --tb=short`，634 passed、176 deselected，486.14 秒，exit 0。

本次没有重跑完整量化核心、生产 build、完整 W8 benchmark 或真实基础设施/外部 provider 验收。W8 canonical v2 保留 187 条记录、188 个运行；其模型为合成 provider，不能据此声称真实 LLM 推理优势。Token usage 保持 null，因果指标不适用，不能当成零错误。

本次静态核对已有 canonical summary：Market autonomous 数值事实 72/72、引用位置 7/7、被引用事件时序违规 0/7；Portfolio full 的硬约束不安全 feasible 声明 0/30，缺数据安全 8/8，风险计算 88/88。分母较小且均为合成输入，不能推广为真实世界准确率。

原始浏览器、API 与额外 Review smoke 记录：`logs/financial-mas/check-20261011/`。后端/前端单测为本次命令实际返回的上述结果，未单独保存完整 stdout 日志。

## 启动：两个 PowerShell 终端

先检查 3000、8001 是否空闲；如果已被占用，确认进程归属。当前 `start-dev.ps1` 会强制终止占用端口的进程且没有执行数据库迁移，首次使用建议按以下步骤分别启动。

终端一，从仓库根目录启动后端。使用专用演示库，迁移与服务必须使用同一个 DATABASE_URL：

```powershell
cd C:\Develop\canvas\Pro_Trading_DS
$env:PYTHONPATH="$PWD\backend;$PWD;$PWD\lobster_quant"
$env:DATABASE_URL="sqlite+aiosqlite:///C:/Develop/canvas/Pro_Trading_DS/backend/data/financial-demo.db"
$env:REDIS_URL=""
New-Item -ItemType Directory -Force backend/data | Out-Null
python -m alembic upgrade head
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

终端二启动前端：

```powershell
cd C:\Develop\canvas\Pro_Trading_DS\lobster-quant-web
$env:NEXT_PUBLIC_API_URL="http://localhost:8001"
npm run dev
```

当前机器 Python/Node/前端依赖已能运行本次检查。新环境需要先安装项目的 Python 与 npm 依赖。关闭各终端内的服务用 Ctrl+C。

## 第一次使用

1. 打开 `http://localhost:3000/copilot?workflow=combined&symbol=MU`。
2. Workflow 选择 Combined；执行模式第一次选择 Auto。
3. Market symbol 保留 MU；点击“开始 combined 合成演示”。
4. 页面出现 Market、Portfolio 两张 run 卡片，ID 不同、Correlation 相同。
5. 等待各自 completed；查看角色与证据轨迹、Market 假说/反证/限制、Portfolio 调整前后权重、约束核验、风险对比和历史模拟。
6. 换 Review 再体验审批：重新进入新工作流/刷新后创建新任务；先批准 Market，等它进入终态后，再批准 Portfolio。审批只授权对应 run 的研究与模拟。

Auto 自动执行有界分析；Review 在 waiting_user 等待审批。修改模式选择不会改变已经创建的任务。页面刷新会丢失当前组件保存的 run 卡片；数据库中记录仍在，因此先记下 run_id，再用结果 API 查找。

| 入口 | 用途 |
| --- | --- |
| `/copilot?workflow=market&symbol=MU` | 独立行情调查演示 |
| `/copilot?workflow=portfolio` | 独立组合评审演示 |
| `/copilot?workflow=combined&symbol=MU` | 调查 + 组合联动 |
| `/analysis/MU` | “此标的 Market 合成只读演示”链接 |
| `/portfolio` | Portfolio/Combined 合成只读演示链接；不读取此页真实持仓 |
| `http://localhost:8001/docs` | OpenAPI 输入结构与接口试用 |

## 演示输入与输出怎么理解

- 合成数据截止时间：`2026-09-29T20:05:00Z`，北京时间 2026-09-30 04:05。
- 只提供 MU、SOXX、SPY、TLT 的合成行情。Combined 的 Market 标的必须属于合成快照；初次推荐 MU 或 SOXX。
- 合成持仓：MU 400 股、SOXX 200 股、SPY 100 股、TLT 100 股，现金 20,000 USD；不是你的持仓。
- 页面默认限制：MU 权重不超过 25%，现金至少 20%。当前网页没有编辑这些约束的输入框。
- 全现金提案符合这些限制；当前系统没有最低股票仓位或最大现金权重条件，也不做预期收益预测。
- Market 的数值事实来自计算工具；假说与支持证据不能解释为已经证明的原因。
- `feasible`=提案通过当前确定性门；`infeasible`=已有证据证明输入约束不可同时满足；`insufficient_data`=数据/独立检查不足。
- `partial`/`insufficient_evidence` 是报告质量状态，可以与流程 `completed` 同时出现。
- 流程 `failed` 看 error_code；不要把无产物时的 pending 看成正在成功分析。

## 使用 API 修改约束

页面只演示固定约束。需要测试自定义限制，可先创建 conversation，再向 Portfolio API 发送结构化输入；持仓快照与 as_of 仍必须是受支持的合成值。

```powershell
$base="http://localhost:8001"
$conversation=Invoke-RestMethod "$base/api/agent/conversations" -Method Post -ContentType "application/json" -Body (@{title="组合约束测试"} | ConvertTo-Json)
$request=@{
  conversation_id=$conversation.id
  idempotency_key=[guid]::NewGuid().ToString()
  mode="auto"
  portfolio=@{
    portfolio_snapshot_id="synthetic-mu-soxx-v1"
    as_of="2026-09-29T20:05:00Z"
    user_constraints=@{
      max_weight_by_symbol=@{MU=0.15; SOXX=0.20}
      min_cash_weight=0.30
      max_equity_weight=0.60
    }
  }
}
$created=Invoke-RestMethod "$base/api/financial/portfolio-reviews" -Method Post -ContentType "application/json" -Body ($request | ConvertTo-Json -Depth 8)
$runId=$created.portfolio_run_id
Invoke-RestMethod "$base/api/financial/runs/$runId" | ConvertTo-Json -Depth 20
```

202 是已创建，不是已完成；间隔查询直到 completed/failed/cancelled/expired。权重采用 0–1 比例。重放同一请求用同一 idempotency_key；更改条件创建新任务用新 key。

Review 需要先查询最新 version，并仅在 waiting_user 时提交：

```powershell
$run=Invoke-RestMethod "$base/api/financial/runs/$runId"
Invoke-RestMethod "$base/api/financial/runs/$runId/approve" -Method Post -ContentType "application/json" -Body (@{expected_version=$run.version} | ConvertTo-Json)
```

409 通常是版本已变化、审批时机不对或 Combined 的 Market 还没有结束；重新读取状态再操作。422 通常是快照/timepoint/资产范围或结构化请求不符合契约。没有真实持仓导入接口；连接真实模型和数据还需实现可信 deployment profile 与 worker 重建映射。

## 待完善项

1. 真实模型角色配置与结构化返回验证、可信行情/事件 provider、不可变真实持仓导入。
2. 自定义约束表单、历史 run 导航与刷新恢复；明确限制全现金等业务偏好的产品契约。
3. PostgreSQL、Redis/Celery broker、真实 provider 的集成与恢复验收。
4. 同步旧 README/runtime 文档中的端口及 migration head；当前前端默认 8001，migration head 为 0004。
