# 服务目录

这里是当前后端服务的实际实现目录。

## 运行前提

- Python 3.11+
- Node.js 18+
- 在本目录执行过 `npm install`
- 默认使用仓库根目录下的 `data/app.db`

## 启动方式

在仓库根目录安装 Python 依赖：

```bash
pip install -e .[dev]
```

在本目录安装 Node 依赖：

```bash
npm install
```

从仓库根目录启动：

```bash
uvicorn service.app.main:app --reload
```

默认落库行为：

- 搜索结果会写入 `rednote_notes`
- 详情结果会更新同一条笔记记录
- 每条笔记会维护一条 `sync_tasks`，供 OpenClaw 或多维表格同步程序读取

默认同步接口：

- `GET /api/v1/storage/sync/pending`
- `POST /api/v1/storage/sync/tasks/{task_id}/success`
- `POST /api/v1/storage/sync/tasks/{task_id}/failed`

## 当前目录结构

- `app/api`：HTTP 路由与依赖注入
- `app/core`：用例编排、异常与响应封装
- `app/adapters`：Spider_XHS 适配层
- `app/models`：请求与响应模型
- `app/config`：配置管理
- `app/observability`：日志能力
- `app/storage`：SQLite 持久化与同步任务存储
