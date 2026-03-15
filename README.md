# RedNote Tools

这是一个基于 `Spider_XHS` 二次开发的服务端项目，用于提供小红书内容检索能力。

当前仓库采用“文档先行 + 规范实现”的开发方式。第一阶段已经开始落地可部署的后端服务，优先支持：

- 关键词搜索结果获取
- 通过 URL 获取笔记详情

长期目标是把它逐步演进为一个多渠道内容解析平台，并在后续阶段接入 `Spider_XHS` 的更多能力，例如二维码登录、创作者侧上传发布等。

## 当前状态

当前仓库已包含第一版服务骨架：

- `FastAPI` HTTP 服务
- `Spider_XHS` 最小适配层
- 搜索与详情两个接口
- 本地 `SQLite` 持久化
- OpenClaw 待同步任务接口
- `X-API-Key` 轻量鉴权
- 内嵌员工使用的前端工作台
- 统一错误响应
- 基础自动化测试

当前阶段仍然是 MVP，真实采集依赖：

- Python 3.11+
- Node.js 18+
- 调用方按请求传入有效小红书 `cookie`

## 文档目录

- [项目范围](D:/redenote-tools/docs/01-project-scope.md)
- [技术选型](D:/redenote-tools/docs/02-technical-decision.md)
- [系统架构](D:/redenote-tools/docs/03-system-architecture.md)
- [接口契约](D:/redenote-tools/docs/04-api-contract.md)
- [迭代路线](D:/redenote-tools/docs/05-roadmap.md)
- [部署基线](D:/redenote-tools/docs/06-deployment-baseline.md)
- [OpenAPI 草案](D:/redenote-tools/docs/openapi/service.openapi.yaml)

## 目标目录结构

```text
redenote-tools/
  docs/
    openapi/
  service/
  tests/
```

## 快速启动

安装 Python 依赖：

```bash
pip install -e .[dev]
```

安装 Spider_XHS 签名所需 Node 依赖：

```bash
cd service
npm install
```

启动服务：

```bash
uvicorn service.app.main:app --reload
```

启动后可访问：

- 工作台首页：`http://127.0.0.1:8000/`
- Swagger：`http://127.0.0.1:8000/docs`
- 默认本地数据库：`data/app.db`

运行测试：

```bash
pytest
```

## 当前接口

- `GET /`
- `GET /healthz`
- `POST /api/v1/rednote/search`
- `POST /api/v1/rednote/detail`
- `GET /api/v1/storage/notes`
- `GET /api/v1/storage/notes/{note_id}`
- `GET /api/v1/storage/sync/pending`
- `POST /api/v1/storage/sync/tasks/{task_id}/success`
- `POST /api/v1/storage/sync/tasks/{task_id}/failed`

## 鉴权说明

- 公开业务接口通过请求头 `X-API-Key` 鉴权
- 内部同步接口优先使用 `REDNOTE_INTERNAL_API_KEYS`
- 如果未单独配置内部 Key，则内部同步接口回退使用公开 Key
- `GET /` 与 `GET /healthz` 默认不强制鉴权

关键环境变量：

- `REDNOTE_API_KEYS`
- `REDNOTE_INTERNAL_API_KEYS`

## 当前实现约束

- `cookie` 当前为必填，因为 Spider_XHS 的签名依赖 `a1`
- 详情接口当前要求传入带 `xsec_token` 的完整笔记链接
- 服务端不持久化请求级 `cookie`
- 第一阶段默认使用 `SQLite`，无需额外安装 MySQL

## Linux 部署提示

- 可直接参考 [部署基线](D:/redenote-tools/docs/06-deployment-baseline.md)
- 建议复制一份 [.env.example](D:/redenote-tools/.env.example) 为 `.env`
- 生产环境建议使用 `systemd + Nginx`
