from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class NoteType(str, Enum):
    DEFAULT = "default"
    IMAGE = "image"
    VIDEO = "video"


class PublishTime(str, Enum):
    DEFAULT = "default"
    DAY_1 = "1d"
    DAY_7 = "7d"
    DAY_180 = "180d"


class SortBy(str, Enum):
    GENERAL = "general"
    LATEST = "latest"
    MOST_LIKED = "most_liked"
    MOST_COMMENTED = "most_commented"
    MOST_COLLECTED = "most_collected"


class SearchRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=100)
    note_type: NoteType = NoteType.DEFAULT
    publish_time: PublishTime = PublishTime.DEFAULT
    sort_by: SortBy = SortBy.GENERAL
    page_count: int = Field(default=1, ge=1, le=10)
    cookie: str = Field(min_length=1)

    @field_validator("keyword", "cookie")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("字段不能为空")
        return cleaned


class DetailRequest(BaseModel):
    url: str = Field(min_length=1, max_length=1000)
    cookie: str = Field(min_length=1)

    @field_validator("url", "cookie")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("字段不能为空")
        return cleaned

    @field_validator("url")
    @classmethod
    def ensure_http_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("url 必须以 http:// 或 https:// 开头")
        return value


class SearchFilters(BaseModel):
    note_type: NoteType
    publish_time: PublishTime
    sort_by: SortBy


class SearchResultItem(BaseModel):
    note_id: str
    title: str = ""
    note_type: NoteType
    author_id: str = ""
    author_name: str = ""
    author_profile_url: str | None = None
    url: str
    cover: str | None = None
    liked_count: str = "0"
    collected_count: str = "0"
    comment_count: str = "0"
    publish_time: str | None = None
    xsec_token: str | None = None


class SearchResponseData(BaseModel):
    keyword: str
    filters: SearchFilters
    page_count: int
    items: list[SearchResultItem]


class NoteDetailData(BaseModel):
    note_id: str
    title: str = ""
    desc: str = ""
    note_type: NoteType
    author_id: str = ""
    author_name: str = ""
    author_profile_url: str | None = None
    liked_count: str = "0"
    collected_count: str = "0"
    comment_count: str = "0"
    share_count: str = "0"
    publish_time: str | None = None
    last_update_time: str | None = None
    images: list[str] = Field(default_factory=list)
    video: str | None = None
    tags: list[str] = Field(default_factory=list)
    url: str
