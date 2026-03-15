# 接口契约

## 接口风格

- 协议：HTTPS
- 内容类型：`application/json`
- 鉴权：后续确定
- Cookie 处理方式：由调用方按请求传入，默认不持久化

## 接口概览

- `POST /api/v1/rednote/search`
- `POST /api/v1/rednote/detail`
- `GET /api/v1/storage/notes`
- `GET /api/v1/storage/notes/{note_id}`
- `GET /api/v1/storage/sync/pending`
- `POST /api/v1/storage/sync/tasks/{task_id}/success`
- `POST /api/v1/storage/sync/tasks/{task_id}/failed`
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
- `cookie`：必填，当前至少需要包含 `a1`，建议传入完整登录态 Cookie
- 互动数字字段按文本返回，以保留 `1.5w`、`2.3万` 这类原始展示样式

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
        "author_profile_url": "https://www.xiaohongshu.com/user/profile/user_xxx",
        "url": "https://www.xiaohongshu.com/explore/xxxx?xsec_token=...",
        "cover": "https://...",
        "liked_count": "123",
        "collected_count": "45",
        "comment_count": "6",
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

### 详情字段规则

- `url`：必填，当前阶段建议传入带 `xsec_token` 的完整笔记链接
- `cookie`：必填，当前至少需要包含 `a1`
- 互动数字字段按文本返回，以保留 `1.5w`、`2.3万` 这类原始展示样式

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
    "author_profile_url": "https://www.xiaohongshu.com/user/profile/user_xxx",
    "liked_count": "1.5w",
    "collected_count": "45",
    "comment_count": "6",
    "share_count": "2",
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
- `NOT_FOUND`
- `UPSTREAM_TIMEOUT`
- `UPSTREAM_RATE_LIMITED`
- `UPSTREAM_PARSE_ERROR`
- `INTERNAL_ERROR`

## 契约说明

- 所有时间字段统一返回 ISO 8601 格式。
- 如后续需要排障，可在响应中增加 `raw` 字段承载上游原始数据。
- 后续版本可能增加鉴权头与更多分页元数据。

## SQLite 持久化说明

- 第一阶段默认使用 `SQLite`
- 默认数据库文件路径：`data/app.db`
- 搜索与详情请求成功后，服务会自动写入 `rednote_notes`
- 每条笔记还会自动维护一条 `sync_tasks`，供 OpenClaw 或其他同步程序读取

## 已落库笔记列表

```http
GET /api/v1/storage/notes?limit=20
```

响应示例：

```json
{
  "success": true,
  "request_id": "req_notes_001",
  "data": {
    "limit": 20,
    "items": [
      {
        "platform": "rednote",
        "note_id": "xxxx",
        "title": "示例标题",
        "desc": "示例正文",
        "note_type": "image",
        "author_id": "user_xxx",
        "author_name": "示例作者",
        "author_profile_url": "https://www.xiaohongshu.com/user/profile/user_xxx",
        "url": "https://www.xiaohongshu.com/explore/xxxx?xsec_token=...",
        "cover": "https://...",
        "video": "",
        "publish_time": "2026-03-15T08:00:00Z",
        "last_update_time": "2026-03-15T09:00:00Z",
        "liked_count_text": "1.5w",
        "collected_count_text": "45",
        "comment_count_text": "6",
        "share_count_text": "2",
        "images": ["https://..."],
        "tags": ["护肤"],
        "xsec_token": "...",
        "source_type": "detail",
        "raw_json": {},
        "created_at": "2026-03-15T08:00:00Z",
        "updated_at": "2026-03-15T09:00:00Z"
      }
    ]
  },
  "error": null
}
```

## 待同步任务列表

```http
GET /api/v1/storage/sync/pending?target=openclaw_bitable&limit=20
```

响应示例：

```json
{
  "success": true,
  "request_id": "req_sync_001",
  "data": {
    "target": "openclaw_bitable",
    "limit": 20,
    "items": [
      {
        "id": 1,
        "platform": "rednote",
        "biz_key": "rednote:xxxx",
        "note_id": "xxxx",
        "task_type": "note_detail",
        "target": "openclaw_bitable",
        "status": "pending",
        "payload": {
          "source": "detail",
          "note": {
            "note_id": "xxxx",
            "title": "示例标题"
          }
        },
        "bitable_record_id": null,
        "error_message": null,
        "retry_count": 0,
        "created_at": "2026-03-15T08:00:00Z",
        "updated_at": "2026-03-15T08:00:00Z",
        "synced_at": null
      }
    ]
  },
  "error": null
}
```

## 同步任务状态回写

成功：

```http
POST /api/v1/storage/sync/tasks/{task_id}/success
```

```json
{
  "bitable_record_id": "rec_xxx"
}
```

失败：

```http
POST /api/v1/storage/sync/tasks/{task_id}/failed
```

```json
{
  "error_message": "多维表格写入失败"
}
```
