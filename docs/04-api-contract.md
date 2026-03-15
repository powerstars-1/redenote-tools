# 接口契约

## 接口风格

- 协议：HTTPS
- 内容类型：`application/json`
- 鉴权：后续确定
- Cookie 处理方式：由调用方按请求传入，默认不持久化

## 接口概览

- `POST /api/v1/rednote/search`
- `POST /api/v1/rednote/detail`
- `GET /healthz`

## 搜索请求

```json
{
  "keyword": "护肤",
  "note_type": "image",
  "publish_time": "7d",
  "sort_by": "latest",
  "page_count": 2,
  "cookie": "a1=...; web_session=..."
}
```

### 搜索字段规则

- `keyword`：必填，非空字符串
- `note_type`：可选，默认 `default`
- `publish_time`：可选，默认 `default`
- `sort_by`：可选，默认 `general`
- `page_count`：可选，取值范围 `1-10`，默认 `1`
- `cookie`：可选，但建议传入以提高稳定性

### 搜索响应

```json
{
  "success": true,
  "request_id": "req_123",
  "data": {
    "keyword": "护肤",
    "filters": {
      "note_type": "image",
      "publish_time": "7d",
      "sort_by": "latest"
    },
    "page_count": 2,
    "items": [
      {
        "note_id": "xxxx",
        "title": "示例标题",
        "note_type": "image",
        "author_id": "user_xxx",
        "author_name": "示例作者",
        "url": "https://www.xiaohongshu.com/explore/xxxx?xsec_token=...",
        "cover": "https://...",
        "liked_count": 123,
        "collected_count": 45,
        "comment_count": 6,
        "publish_time": "2026-03-15T08:00:00Z",
        "xsec_token": "..."
      }
    ]
  },
  "error": null
}
```

## 详情请求

```json
{
  "url": "https://www.xiaohongshu.com/explore/xxxx?xsec_token=...",
  "cookie": "a1=...; web_session=..."
}
```

### 详情响应

```json
{
  "success": true,
  "request_id": "req_456",
  "data": {
    "note_id": "xxxx",
    "title": "示例标题",
    "desc": "示例正文",
    "note_type": "image",
    "author_id": "user_xxx",
    "author_name": "示例作者",
    "liked_count": 123,
    "collected_count": 45,
    "comment_count": 6,
    "share_count": 2,
    "publish_time": "2026-03-15T08:00:00Z",
    "last_update_time": "2026-03-15T09:00:00Z",
    "images": [
      "https://..."
    ],
    "video": "",
    "tags": [
      "护肤"
    ],
    "url": "https://www.xiaohongshu.com/explore/xxxx?xsec_token=..."
  },
  "error": null
}
```

## 错误响应

```json
{
  "success": false,
  "request_id": "req_789",
  "data": null,
  "error": {
    "code": "INVALID_COOKIE",
    "message": "The provided cookie is invalid or expired."
  }
}
```

## 错误码

- `INVALID_ARGUMENT`
- `INVALID_URL`
- `INVALID_COOKIE`
- `UPSTREAM_TIMEOUT`
- `UPSTREAM_RATE_LIMITED`
- `UPSTREAM_PARSE_ERROR`
- `INTERNAL_ERROR`

## 契约说明

- 所有时间字段统一返回 ISO 8601 格式。
- 如后续需要排障，可在响应中增加 `raw` 字段承载上游原始数据。
- 后续版本可能增加鉴权头与更多分页元数据。
