# Agent 平台契约（W0 / B02）

状态：冻结的 MVP 契约。实现可以分阶段交付，但不得在未更新 ADR 的情况下改变本文件定义的外部语义。

## 1. 标识与并发

所有 conversation、run、step、tool call、job 和 event 使用 UUID 字符串。每个请求携带或生成 `request_id`；日志和事件同时保留 `conversation_id`、`run_id`，需要时保留 `step_id`、`job_id`。

run 和 intervention 使用整数 `version` 乐观锁。任何需要改变 run 快照的请求都必须提交 `expected_version`；版本不匹配返回 HTTP 409，不能重复执行动作。终态 run 不重新打开；失败重试创建带 `parent_run_id` 的 child run。

## 2. Run 状态机

允许状态：

`created` → `queued` → `planning` → `waiting_user` / `executing`  
`executing` → `waiting_tool` / `waiting_job` / `waiting_user` / `completed` / `failed`  
任意非终态 → `pause_requested` → `paused` → `executing`  
任意非终态 → `cancelling` → `cancelled`  
任意非终态 → `expired`

终态只有 `completed`、`failed`、`cancelled`、`expired`。暂停和取消是协作式的：模型调用前后、工具调用前后、checkpoint 恢复时检查。每次状态变化必须在同一事务中更新 run 快照并追加不可变事件。非法转换返回 `INVALID_STATE_TRANSITION`。

`review` 模式在计划生成后停在 `waiting_user`；`auto` 模式可进入 `executing`。初始计划最多 6 步，单个 run 最多 1 次 replan、8 个实际 step、10 次模型调用和 8 次工具调用。

## 3. Step 与工具

Step 类型固定为 `clarify`、`tool`、`retrieve`、`wait_job`、`synthesize`、`final`。Step 状态固定为 `pending`、`running`、`waiting_user`、`succeeded`、`failed`、`skipped`、`cancelled`。

首批工具名称固定为：

`get_market_snapshot`、`calculate_indicators`、`assess_risk`、`run_backtest`、`get_backtest_result`、`compare_backtests`、`search_knowledge_base`。

工具注册信息必须包含名称与版本、描述、Pydantic 输入/输出模型、`read_only`、`side_effect`、`confirmation_policy`、超时、额外重试次数、幂等性和允许错误码。工具执行前验证输入，执行后验证输出；LLM 不产生金融计算结果。

统一工具结果信封：

```json
{
  "call_id": "uuid",
  "tool_name": "get_market_snapshot",
  "status": "succeeded",
  "data": {},
  "citations": [],
  "error": null,
  "duration_ms": 12,
  "cached": false
}
```

错误码固定包括 `validation_error`、`business_error`、`dependency_timeout`、`rate_limited`、`permission_denied`、`cancelled`、`internal_error`。校验和业务错误不自动重试；超时和限流只对幂等工具有限重试；内部异常不把堆栈返回客户端。

`run_backtest` 只创建或复用 compute job 并返回 job/backtest 标识；Agent 不在 worker 内轮询，不直接执行 Pandas 回测。

## 4. Event 与 SSE

事件表 append-only。单个 run 的 `seq` 从 1 开始、单调递增且唯一。事件至少包含：`schema_version`、`event_id`、`seq`、`event_type`、`timestamp`、`conversation_id`、`run_id`、`request_id` 和精简 `payload`。

事件类型包括：

`run.status_changed`、`plan.created`、`plan.approval_required`、`plan.approved`、`plan.rejected`、`plan.revised`、`step.started`、`step.progress`、`step.completed`、`step.failed`、`step.cancelled`、`tool.called`、`tool.completed`、`tool.failed`、`tool.cancelled`、`citation.added`、`job.status_changed`、`user.input_required`、`user.input_resolved`、`run.completed`、`run.failed`、`run.cancelled`、`run.pause_requested`、`run.paused`、`run.resumed`、`run.expired`、`memory.updated`。

SSE 使用 `GET /api/agent/runs/{run_id}/events`，支持 `after_seq` 和 `Last-Event-ID`。服务端先重放缺失事件，再进入实时等待；定期发送 heartbeat，终态发送最终事件后关闭。客户端按 `seq` 去重，发现断档先获取 REST snapshot，再继续连接。SSE 永远不是权威存储。

## 5. REST 错误信封

所有错误保留稳定 `code`、用户可读 `message`、`request_id` 和 `retryable`；必要时带字段级 `details`。预期 HTTP 语义：

- `202`：创建或排队成功，返回资源快照或 run 标识。
- `404`：资源不存在，不能泄露其他会话资源。
- `409`：`expected_version` 冲突、重复动作或状态竞态。
- `422`：请求 schema 或业务输入不合法。
- `503`：依赖（模型、数据库、Redis、embedding）暂不可用。

## 6. 记忆与引用

会话消息、滚动摘要、当前计划、工具结果索引和显式 memory 分开存储。只有用户明确要求记住或明确确认的内容可写入 `user_preference`、`research_constraint`、`confirmed_fact`；模型推断不能静默持久化。滚动摘要按 token 预算触发，记录覆盖到的 message 边界，原消息保留。

文档只允许 `.md`、`.markdown` 和文本型 `.pdf`。扫描件进入 `failed`，错误为 `OCR_REQUIRED`，不创建空的 ready 知识库。最终回答中的金融数字必须关联 `tool_result` 或 `backtest_run`；知识解释关联 `document`。citation snapshot 必须保留定位、excerpt 和 content hash，文档重新索引或删除后历史 run 仍可解释。

## 7. 安全边界

文档内容是不可信资料。检索文本中的“忽略系统规则”或工具调用文字永远只是引用内容，不改变 system policy，也不触发写工具。前端展示计划、步骤状态、工具摘要和可理解解释，不展示 chain-of-thought。
