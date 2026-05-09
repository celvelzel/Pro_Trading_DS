# Core Logic Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成从老代码（Streamlit）到新代码（Next.js + FastAPI）的彻底迁移，重点是将核心的回测逻辑（Backtest）、全局设置（Settings）API 化，并在前端构建对应的高交互界面。同时统一全栈的数据类型规范。

**Context:** 目前已完成 Scanner 和 Analysis 页面的重构以及基础架构（Next.js + FastAPI）的搭建，且通过了生产构建。剩余的 `lobster_quant` 核心逻辑（主要是策略回测与全局参数）目前尚未与新的前端深度打通。为防止接口漂移，需要首先标准化 Pydantic 与 TypeScript 接口。

## Task 1: 统一全栈类型定义 (TS/Pydantic Alignment)
**Description:** 对齐 FastAPI 后端的 Pydantic Models 和 Next.js 前端的 TypeScript Interfaces，确保数据流动不会因为字段不匹配（如可选字段、拼写错误）而崩溃。

**Acceptance criteria:**
- [ ] 检查并确保 `backend/api/models/` 目录下拥有清晰的回测、配置相关 Pydantic Schemas。
- [ ] 在 `src/types/` 或 `src/services/api/` 中创建对应的 TypeScript interfaces。
- [ ] 确保 Scanner 和 Analysis 现有的 API response 符合上述标准。

## Task 2: 核心回测逻辑 API 化 (Backend Backtest Integration)
**Description:** 将老代码中位于 Streamlit 或 `lobster_quant` 内部的回测引擎暴露为 FastAPI 的 RESTful 接口。

**Acceptance criteria:**
- [ ] 在 `backend/api/routes/backtest.py` 创建处理回测请求的 Endpoint（接受策略参数、时间范围、标的等）。
- [ ] 编写逻辑连接老代码的 `lobster_quant.engine` 或相应的回测类，并捕获执行结果。
- [ ] 将回测的资金曲线、交易记录格式化为 JSON 格式返回。

## Task 3: 构建回测系统前端 (Frontend Backtest UI)
**Description:** 在 `app/backtest/page.tsx` 中实现带有表单和图表的可视化回测界面，风格需保持 Google Finance Style。

**Acceptance criteria:**
- [ ] 创建侧边栏或顶部的参数配置表单（策略选择、资金、滑点、日期范围）。
- [ ] 引入 TanStack Query 发起回测 API 请求，并处理 loading 状态（骨架屏）。
- [ ] 接入 TradingView Lightweight Charts 展示回测结果（资金曲线、回撤图）。
- [ ] 使用统计卡片 (MetricCards) 展示夏普比率、胜率、最大回撤等核心指标。

## Task 4: 设置模块与参数持久化 (Settings Module)
**Description:** 在 `app/settings/page.tsx` 实现系统设置和策略参数设置的配置界面。

**Acceptance criteria:**
- [ ] 在 FastAPI 中创建用于读取/保存用户配置的 API（可写入本地 JSON/YAML 或数据库）。
- [ ] 构建前端 Settings 页面，包含 API Keys 配置、默认策略参数、全局主题设置等区块。
- [ ] 整合前端 Zustand 进行轻量级状态持久化或使用 React Query 缓存设置数据。

## Task 5: 端到端测试与 Streamlit 依赖清理 (E2E Test & Deprecation)
**Description:** 进行全流程的可用性验证，并在确认无误后移除旧版代码入口。

**Acceptance criteria:**
- [ ] 使用 Playwright 测试从 Scanner -> Analysis -> Backtest 的完整业务流。
- [ ] 确保无 500 错误和前端白屏（Error Boundary 正常工作）。
- [ ] 彻底禁用或删除旧的 `streamlit run` 启动入口，宣告迁移 100% 完成。