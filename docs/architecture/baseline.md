# W0 基线记录

记录时间：2026-09-19（Asia/Shanghai）  
基线提交：`be393f5` (`feat: comprehensive platform improvement - 26 tasks completed`)

## 环境

| 项目 | 版本 |
|---|---|
| OS | Windows |
| Python | 3.13.5 |
| Node.js | v22.16.0 |
| npm | 10.9.2 |
| Docker | 28.3.3 |

## 当前启动方式

- 后端：在 `backend` 目录运行 `python -m uvicorn main:app --host 127.0.0.1 --port 8000`，需要把仓库根目录和 `lobster_quant` 加入 `PYTHONPATH`。
- 前端：在 `lobster-quant-web` 目录运行 `npm run dev`。
- 一键开发启动：仓库根目录运行 `./start-dev.ps1`。
- 当前仓库尚未提供升级计划要求的 Docker Compose 全栈启动入口。

## 基线验证

以下结果是在升级开始前、提交 `be393f5` 上取得的：

| 验证 | 命令 | 结果 |
|---|---|---|
| 量化核心 | `cd lobster_quant; python -m pytest -q` | 659 passed，12 failed，1 error |
| Backend | `cd backend; python -m pytest -q` | 100 passed |
| Frontend unit | `cd lobster-quant-web; npm run test:unit` | 120 passed |
| Frontend production build | `cd lobster-quant-web; npm run build` | 失败：`WatchlistAddDialog.tsx:198` 残留代码导致语法错误 |

量化核心失败集中在两类已知问题：`MockProvider` 生成的价格数组与工作日索引长度在当前日期下可能不一致；`SimulationStore` 的固定测试日期会被系统日期过滤。W0 的 B01 修复这两类基线问题，不改变既有 API 语义。

## 复现命令

```powershell
cd lobster_quant
python -m pytest -q

cd ..\backend
python -m pytest -q

cd ..\lobster-quant-web
npm run test:unit
npm run build
```

## 约束

- 旧的股票、扫描、回测、策略和模拟 API 继续保留。
- 本轮不接券商、不执行真实交易，不引入 LangGraph，不迁移全部 JSON 存储。
- 后续波次必须以本文件记录的验证命令为回归入口；新增失败必须单独记录，不得用放宽断言掩盖。
