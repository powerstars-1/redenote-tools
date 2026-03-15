# RedNote Tools

这是一个基于 `Spider_XHS` 二次开发的服务端项目，用于提供小红书内容检索能力。

当前仓库采用“文档先行”的开发方式。第一阶段的交付目标是一个可部署到自有服务器的后端服务，优先支持：

- 关键词搜索结果获取
- 通过 URL 获取笔记详情

长期目标是把它逐步演进为一个多渠道内容解析平台，并在后续阶段接入 `Spider_XHS` 的更多能力，例如二维码登录、创作者侧上传发布等。

## 当前状态

当前阶段聚焦于需求梳理、技术选型、系统架构、接口契约和迭代规划，尚未开始提交正式业务实现代码。

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

其中 `service/` 和 `tests/` 目前为实现阶段预留的占位目录。
