from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SyncTaskStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class StoredNoteData(BaseModel):
    platform: str = "rednote"
    note_id: str
    title: str = ""
    desc: str = ""
    note_type: str = "default"
    author_id: str = ""
    author_name: str = ""
    author_profile_url: str | None = None
    url: str
    cover: str | None = None
    video: str | None = None
    publish_time: str | None = None
    last_update_time: str | None = None
    liked_count_text: str = "0"
    collected_count_text: str = "0"
    comment_count_text: str = "0"
    share_count_text: str = "0"
    images: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    xsec_token: str | None = None
    source_type: str = "search"
    raw_json: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class StoredNotesResponseData(BaseModel):
    items: list[StoredNoteData]
    limit: int


class SyncTaskData(BaseModel):
    id: int
    platform: str = "rednote"
    biz_key: str
    note_id: str
    task_type: str
    target: str
    status: SyncTaskStatus
    payload: dict[str, Any] = Field(default_factory=dict)
    bitable_record_id: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    created_at: str
    updated_at: str
    synced_at: str | None = None


class PendingSyncTasksResponseData(BaseModel):
    items: list[SyncTaskData]
    target: str
    limit: int


class MarkSyncTaskSuccessRequest(BaseModel):
    bitable_record_id: str | None = Field(default=None, max_length=200)

    @field_validator("bitable_record_id")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class MarkSyncTaskFailedRequest(BaseModel):
    error_message: str = Field(min_length=1, max_length=1000)

    @field_validator("error_message")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("字段不能为空")
        return cleaned

