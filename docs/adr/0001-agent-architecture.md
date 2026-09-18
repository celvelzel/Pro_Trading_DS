# ADR-0001：采用受控 Plan-and-Execute Agent

- 状态：Accepted
- 日期：2026-09-19

## 决策

Agent 使用结构化 Planner 生成有限计划，由 Orchestrator 按状态机执行注册工具；不引入 LangGraph。Agent run 使用独立 Celery `agent` 队列，回测和文档入库使用独立 `compute` 队列。PostgreSQL 保存权威状态、消息、事件、任务和引用；Redis 只作为 Celery broker/result backend 与短期协调。

## 原因

该方案能把计划、人工批准、checkpoint、异步 job 恢复和审计事件表达为可测试的持久化状态，同时不重写现有量化核心。独立队列避免 Agent 在等待回测时占满 compute 资源，REST 快照加可重放 SSE 也能让前端刷新后恢复。

## 约束

首轮不做真实交易、模型训练、隐式长期画像或任意历史 step 分叉。任何增加替代编排框架、改变队列职责或把 Redis 当权威存储的提议必须新增 ADR。
