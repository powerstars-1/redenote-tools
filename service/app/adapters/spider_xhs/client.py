from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

import requests

from service.app.adapters.spider_xhs.normalizers import normalize_detail_item, normalize_search_item
from service.app.adapters.spider_xhs.signing import SpiderXHSSigner, generate_trace_id
from service.app.config.settings import Settings
from service.app.core.exceptions import ServiceError
from service.app.models.rednote import NoteDetailData, SearchResultItem
from service.app.observability.logging import get_logger


SORT_MAPPING = {
    "general": "general",
    "latest": "time_descending",
    "most_liked": "popularity_descending",
    "most_commented": "comment_descending",
    "most_collected": "collect_descending",
}

NOTE_TYPE_MAPPING = {
    "default": "不限",
    "video": "视频笔记",
    "image": "普通笔记",
}

PUBLISH_TIME_MAPPING = {
    "default": "不限",
    "1d": "一天内",
    "7d": "一周内",
    "180d": "半年内",
}


class SpiderXHSClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._timeout = settings.upstream_timeout_seconds
        self._base_url = settings.spider_base_url.rstrip("/")
        self._signer = SpiderXHSSigner(node_modules_dir=settings.resolved_node_modules_dir)
        self._session = requests.Session()
        self._session.headers.update({"user-agent": settings.default_user_agent})
        self._logger = get_logger(__name__)

    def search_notes(
        self,
        *,
        keyword: str,
        note_type: str,
        publish_time: str,
        sort_by: str,
        page_count: int,
        cookie: str,
    ) -> list[SearchResultItem]:
        items: list[SearchResultItem] = []

        for page in range(1, page_count + 1):
            response = self._post(
                api="/api/sns/web/v1/search/notes",
                cookie=cookie,
                payload={
                    "keyword": keyword,
                    "page": page,
                    "page_size": 20,
                    "search_id": generate_trace_id(21),
                    "sort": "general",
                    "note_type": 0,
                    "ext_flags": [],
                    "filters": [
                        {"tags": [SORT_MAPPING[sort_by]], "type": "sort_type"},
                        {"tags": [NOTE_TYPE_MAPPING[note_type]], "type": "filter_note_type"},
                        {"tags": [PUBLISH_TIME_MAPPING[publish_time]], "type": "filter_note_time"},
                        {"tags": ["不限"], "type": "filter_note_range"},
                        {"tags": ["不限"], "type": "filter_pos_distance"},
                    ],
                    "geo": "",
                    "image_formats": ["jpg", "webp", "avif"],
                },
            )
            data = self._as_dict(response.get("data"))
            raw_items = data.get("items") or []
            if not isinstance(raw_items, list):
                raise ServiceError(
                    code="UPSTREAM_PARSE_ERROR",
                    message="上游搜索结果结构异常，无法解析 items 字段。",
                    status_code=502,
                )

            for entry in raw_items:
                if isinstance(entry, dict) and entry.get("model_type") == "note":
                    items.append(normalize_search_item(entry))

            if not data.get("has_more", False):
                break

        return items

    def get_note_detail(self, *, url: str, cookie: str) -> NoteDetailData:
        resolved_url = self._resolve_note_url(url)
        note_id, xsec_token, xsec_source = self._parse_note_url(resolved_url)
        response = self._post(
            api="/api/sns/web/v1/feed",
            cookie=cookie,
            payload={
                "source_note_id": note_id,
                "image_formats": ["jpg", "webp", "avif"],
                "extra": {"need_body_topic": "1"},
                "xsec_source": xsec_source,
                "xsec_token": xsec_token,
            },
        )
        items = self._as_dict(response.get("data")).get("items") or []
        if not isinstance(items, list) or not items:
            raise ServiceError(
                code="UPSTREAM_PARSE_ERROR",
                message="上游详情结果为空，无法获取笔记详情。",
                status_code=502,
            )
        if not isinstance(items[0], dict):
            raise ServiceError(
                code="UPSTREAM_PARSE_ERROR",
                message="上游详情结构异常，无法解析笔记详情。",
                status_code=502,
            )
        return normalize_detail_item(items[0], resolved_url)

    def _post(self, *, api: str, cookie: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers, cookies, serialized = self._signer.build_request_params(
            cookie=cookie,
            api=api,
            data=payload,
            method="POST",
        )

        try:
            response = self._session.post(
                f"{self._base_url}{api}",
                headers=headers,
                cookies=cookies,
                data=serialized.encode("utf-8"),
                timeout=self._timeout,
            )
        except requests.Timeout as exc:
            raise ServiceError(
                code="UPSTREAM_TIMEOUT",
                message="上游请求超时，请稍后重试。",
                status_code=504,
            ) from exc
        except requests.RequestException as exc:
            raise ServiceError(
                code="UPSTREAM_PARSE_ERROR",
                message=f"上游请求失败：{exc}",
                status_code=502,
            ) from exc

        if response.status_code == 429:
            raise ServiceError(
                code="UPSTREAM_RATE_LIMITED",
                message="上游触发限流或风控，请稍后重试。",
                status_code=429,
            )
        if response.status_code >= 500:
            raise ServiceError(
                code="UPSTREAM_PARSE_ERROR",
                message=f"上游服务异常，HTTP {response.status_code}。",
                status_code=502,
            )
        if response.status_code >= 400:
            raise ServiceError(
                code="UPSTREAM_PARSE_ERROR",
                message=f"上游请求失败，HTTP {response.status_code}。",
                status_code=502,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ServiceError(
                code="UPSTREAM_PARSE_ERROR",
                message="上游响应不是合法 JSON，无法完成解析。",
                status_code=502,
            ) from exc

        if not data.get("success", False):
            self._raise_upstream_error(str(data.get("msg") or "未知上游错误"))

        return self._as_dict(data)

    def _resolve_note_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.netloc.endswith("xhslink.com"):
            try:
                response = self._session.get(
                    url,
                    allow_redirects=True,
                    timeout=self._timeout,
                )
            except requests.RequestException as exc:
                raise ServiceError(
                    code="INVALID_URL",
                    message=f"短链解析失败：{exc}",
                    status_code=400,
                ) from exc
            return response.url
        return url

    def _parse_note_url(self, url: str) -> tuple[str, str, str]:
        parsed = urlparse(url)
        if "xiaohongshu.com" not in parsed.netloc:
            raise ServiceError(
                code="INVALID_URL",
                message="当前仅支持小红书笔记链接。",
                status_code=400,
            )

        segments = [segment for segment in parsed.path.split("/") if segment]
        note_id = ""
        if len(segments) >= 2 and segments[-2] == "explore":
            note_id = segments[-1]
        elif len(segments) >= 3 and segments[-3] == "discovery" and segments[-2] == "item":
            note_id = segments[-1]

        if not note_id:
            raise ServiceError(
                code="INVALID_URL",
                message="无法从 URL 中提取笔记 ID。",
                status_code=400,
            )

        query = parse_qs(parsed.query)
        xsec_token = (query.get("xsec_token") or [None])[0]
        xsec_source = (query.get("xsec_source") or ["pc_search"])[0]
        if not xsec_token:
            raise ServiceError(
                code="INVALID_URL",
                message="当前阶段请传入包含 xsec_token 的完整笔记 URL。",
                status_code=400,
            )

        return note_id, xsec_token, xsec_source

    def _raise_upstream_error(self, message: str) -> None:
        lowered = message.lower()
        if any(keyword in lowered for keyword in ("cookie", "a1", "login")) or any(
            keyword in message for keyword in ("登录", "登陆", "请先登录")
        ):
            raise ServiceError(
                code="INVALID_COOKIE",
                message="cookie 无效、缺失或已过期，请重新获取后再试。",
                status_code=400,
            )
        if any(keyword in lowered for keyword in ("rate", "limit")) or any(
            keyword in message for keyword in ("频繁", "频次", "风控", "限制", "稍后再试")
        ):
            raise ServiceError(
                code="UPSTREAM_RATE_LIMITED",
                message="上游触发限流或风控，请稍后重试。",
                status_code=429,
            )
        raise ServiceError(
            code="UPSTREAM_PARSE_ERROR",
            message=f"上游返回失败：{message}",
            status_code=502,
        )

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}
