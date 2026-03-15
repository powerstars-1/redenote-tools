from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from service.app.models.rednote import NoteDetailData, NoteType, SearchResultItem


def normalize_search_item(item: dict[str, Any]) -> SearchResultItem:
    note_card = _as_dict(item.get("note_card"))
    author = _as_dict(note_card.get("user") or item.get("user") or item.get("author"))
    author_id = str(author.get("user_id") or author.get("id") or "")
    note_id = str(item.get("id") or note_card.get("note_id") or note_card.get("id") or "")
    xsec_token = item.get("xsec_token")
    params = {"xsec_source": "pc_search"}
    if xsec_token:
        params["xsec_token"] = xsec_token
    url = f"https://www.xiaohongshu.com/explore/{note_id}"
    if params:
        url = f"{url}?{urlencode(params)}"

    interact_info = _as_dict(note_card.get("interact_info"))

    return SearchResultItem(
        note_id=note_id,
        title=_first_non_empty(
            note_card.get("display_title"),
            note_card.get("title"),
            item.get("title"),
            "",
        ),
        note_type=_normalize_note_type(note_card.get("type") or item.get("note_type")),
        author_id=author_id,
        author_name=str(author.get("nickname") or author.get("name") or ""),
        author_profile_url=_build_author_profile_url(author_id),
        url=url,
        cover=_extract_media_url(note_card.get("cover") or item.get("cover")),
        liked_count=_to_count_text(interact_info.get("liked_count")),
        collected_count=_to_count_text(interact_info.get("collected_count")),
        comment_count=_to_count_text(interact_info.get("comment_count")),
        publish_time=_to_iso8601(note_card.get("time") or item.get("publish_time")),
        xsec_token=str(xsec_token) if xsec_token else None,
    )


def normalize_detail_item(item: dict[str, Any], url: str) -> NoteDetailData:
    note_card = _as_dict(item.get("note_card"))
    author = _as_dict(note_card.get("user"))
    author_id = str(author.get("user_id") or author.get("id") or "")
    interact_info = _as_dict(note_card.get("interact_info"))
    image_list = note_card.get("image_list") or []

    return NoteDetailData(
        note_id=str(item.get("id") or note_card.get("note_id") or ""),
        title=_first_non_empty(note_card.get("title"), ""),
        desc=_first_non_empty(note_card.get("desc"), ""),
        note_type=_normalize_note_type(note_card.get("type")),
        author_id=author_id,
        author_name=str(author.get("nickname") or author.get("name") or ""),
        author_profile_url=_build_author_profile_url(author_id),
        liked_count=_to_count_text(interact_info.get("liked_count")),
        collected_count=_to_count_text(interact_info.get("collected_count")),
        comment_count=_to_count_text(interact_info.get("comment_count")),
        share_count=_to_count_text(interact_info.get("share_count")),
        publish_time=_to_iso8601(note_card.get("time")),
        last_update_time=_to_iso8601(note_card.get("last_update_time")),
        images=[img for img in (_extract_media_url(entry) for entry in image_list) if img],
        video=_extract_video_url(note_card.get("video")),
        tags=_extract_tags(note_card.get("tag_list")),
        url=url,
    )


def _normalize_note_type(raw_value: Any) -> NoteType:
    value = str(raw_value or "").lower()
    if value == "video":
        return NoteType.VIDEO
    if value in {"normal", "image"}:
        return NoteType.IMAGE
    return NoteType.DEFAULT


def _to_iso8601(value: Any) -> str | None:
    if value in (None, "", 0):
        return None
    if isinstance(value, str) and "T" in value:
        return value
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return None
    if ts > 10_000_000_000:
        ts = ts / 1000
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _extract_tags(raw_tags: Any) -> list[str]:
    tags: list[str] = []
    if not isinstance(raw_tags, list):
        return tags
    for entry in raw_tags:
        if isinstance(entry, dict):
            name = entry.get("name")
            if isinstance(name, str) and name:
                tags.append(name)
    return tags


def _extract_video_url(video: Any) -> str | None:
    payload = _as_dict(video)
    stream = _as_dict(payload.get("media")).get("stream")
    h264 = _as_dict(stream).get("h264") if isinstance(stream, dict) else None
    if isinstance(h264, list):
        for entry in h264:
            url = _extract_media_url(entry)
            if url:
                return url
    consumer = _as_dict(payload.get("consumer"))
    origin_key = consumer.get("origin_video_key")
    if origin_key:
        return f"https://sns-video-bd.xhscdn.com/{origin_key}"
    return None


def _extract_media_url(payload: Any) -> str | None:
    if isinstance(payload, str) and payload:
        return payload
    if isinstance(payload, list):
        for entry in reversed(payload):
            url = _extract_media_url(entry)
            if url:
                return url
        return None
    if not isinstance(payload, dict):
        return None

    for key in ("master_url", "url_default", "url_pre", "url"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value

    info_list = payload.get("info_list")
    if isinstance(info_list, list):
        for entry in reversed(info_list):
            url = _extract_media_url(entry)
            if url:
                return url

    url_list = payload.get("url_list")
    if isinstance(url_list, list):
        for entry in url_list:
            if isinstance(entry, str) and entry:
                return entry

    return None


def _to_count_text(value: Any) -> str:
    if value in (None, ""):
        return "0"
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or "0"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    return str(value)


def _build_author_profile_url(author_id: str) -> str | None:
    if not author_id:
        return None
    return f"https://www.xiaohongshu.com/user/profile/{author_id}"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""
