from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from service.app.core.exceptions import ServiceError
from service.app.models.rednote import NoteDetailData, SearchResponseData, SearchResultItem
from service.app.models.storage import (
    StoredNoteData,
    StoredNotesResponseData,
    SyncTaskData,
    SyncTaskStatus,
)


class SQLiteRedNoteStore:
    def __init__(self, *, database_path: Path, default_sync_target: str = "openclaw_bitable") -> None:
        self._database_path = database_path
        self._default_sync_target = default_sync_target

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS rednote_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL DEFAULT 'rednote',
                    note_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL DEFAULT '',
                    desc TEXT NOT NULL DEFAULT '',
                    note_type TEXT NOT NULL DEFAULT 'default',
                    author_id TEXT NOT NULL DEFAULT '',
                    author_name TEXT NOT NULL DEFAULT '',
                    author_profile_url TEXT,
                    url TEXT NOT NULL DEFAULT '',
                    cover TEXT,
                    video TEXT,
                    publish_time TEXT,
                    last_update_time TEXT,
                    liked_count_text TEXT NOT NULL DEFAULT '0',
                    collected_count_text TEXT NOT NULL DEFAULT '0',
                    comment_count_text TEXT NOT NULL DEFAULT '0',
                    share_count_text TEXT NOT NULL DEFAULT '0',
                    images_json TEXT NOT NULL DEFAULT '[]',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    xsec_token TEXT,
                    source_type TEXT NOT NULL DEFAULT 'search',
                    raw_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sync_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL DEFAULT 'rednote',
                    biz_key TEXT NOT NULL,
                    note_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    payload_json TEXT NOT NULL,
                    bitable_record_id TEXT,
                    error_message TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    synced_at TEXT,
                    UNIQUE(platform, biz_key, target)
                );

                CREATE INDEX IF NOT EXISTS idx_rednote_notes_updated_at
                ON rednote_notes(updated_at DESC);

                CREATE INDEX IF NOT EXISTS idx_sync_tasks_status_target_updated_at
                ON sync_tasks(status, target, updated_at ASC);
                """,
            )

    def persist_search_response(self, response: SearchResponseData) -> None:
        try:
            with self._connect() as conn:
                for item in response.items:
                    self._upsert_search_note(conn, item=item)
                    self._upsert_sync_task(
                        conn,
                        note_id=item.note_id,
                        task_type="search_result",
                        payload={
                            "source": "search",
                            "keyword": response.keyword,
                            "filters": response.filters.model_dump(mode="json"),
                            "page_count": response.page_count,
                            "note": item.model_dump(mode="json"),
                        },
                    )
        except sqlite3.Error as exc:
            raise ServiceError(
                code="INTERNAL_ERROR",
                message="搜索结果写入本地数据库失败，请检查数据库文件和目录权限。",
                status_code=500,
            ) from exc

    def persist_note_detail(self, detail: NoteDetailData) -> None:
        try:
            with self._connect() as conn:
                self._upsert_detail_note(conn, detail=detail)
                self._upsert_sync_task(
                    conn,
                    note_id=detail.note_id,
                    task_type="note_detail",
                    payload={
                        "source": "detail",
                        "note": detail.model_dump(mode="json"),
                    },
                )
        except sqlite3.Error as exc:
            raise ServiceError(
                code="INTERNAL_ERROR",
                message="详情结果写入本地数据库失败，请检查数据库文件和目录权限。",
                status_code=500,
            ) from exc

    def list_notes(self, *, limit: int = 20) -> StoredNotesResponseData:
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM rednote_notes
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        except sqlite3.Error as exc:
            raise ServiceError(
                code="INTERNAL_ERROR",
                message="读取本地数据库失败，请检查数据库文件和目录权限。",
                status_code=500,
            ) from exc

        return StoredNotesResponseData(items=[self._note_from_row(row) for row in rows], limit=limit)

    def get_note(self, *, note_id: str) -> StoredNoteData:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT *
                    FROM rednote_notes
                    WHERE note_id = ?
                    LIMIT 1
                    """,
                    (note_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise ServiceError(
                code="INTERNAL_ERROR",
                message="读取本地数据库失败，请检查数据库文件和目录权限。",
                status_code=500,
            ) from exc

        if row is None:
            raise ServiceError(
                code="NOT_FOUND",
                message="未找到指定的笔记记录。",
                status_code=404,
            )

        return self._note_from_row(row)

    def list_pending_sync_tasks(self, *, target: str | None = None, limit: int = 20) -> list[SyncTaskData]:
        task_target = target or self._default_sync_target
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM sync_tasks
                    WHERE status = ? AND target = ?
                    ORDER BY updated_at ASC
                    LIMIT ?
                    """,
                    (SyncTaskStatus.PENDING.value, task_target, limit),
                ).fetchall()
        except sqlite3.Error as exc:
            raise ServiceError(
                code="INTERNAL_ERROR",
                message="读取同步任务失败，请检查数据库文件和目录权限。",
                status_code=500,
            ) from exc

        return [self._sync_task_from_row(row) for row in rows]

    def mark_sync_task_success(self, *, task_id: int, bitable_record_id: str | None = None) -> SyncTaskData:
        timestamp = _utc_now()
        try:
            with self._connect() as conn:
                row = self._get_sync_task_row(conn, task_id=task_id)
                existing_record_id = row["bitable_record_id"]
                conn.execute(
                    """
                    UPDATE sync_tasks
                    SET status = ?,
                        bitable_record_id = ?,
                        error_message = NULL,
                        updated_at = ?,
                        synced_at = ?
                    WHERE id = ?
                    """,
                    (
                        SyncTaskStatus.SUCCESS.value,
                        bitable_record_id or existing_record_id,
                        timestamp,
                        timestamp,
                        task_id,
                    ),
                )
                updated_row = self._get_sync_task_row(conn, task_id=task_id)
        except sqlite3.Error as exc:
            raise ServiceError(
                code="INTERNAL_ERROR",
                message="更新同步任务失败，请检查数据库文件和目录权限。",
                status_code=500,
            ) from exc

        return self._sync_task_from_row(updated_row)

    def mark_sync_task_failed(self, *, task_id: int, error_message: str) -> SyncTaskData:
        timestamp = _utc_now()
        try:
            with self._connect() as conn:
                row = self._get_sync_task_row(conn, task_id=task_id)
                conn.execute(
                    """
                    UPDATE sync_tasks
                    SET status = ?,
                        error_message = ?,
                        retry_count = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        SyncTaskStatus.FAILED.value,
                        error_message,
                        int(row["retry_count"]) + 1,
                        timestamp,
                        task_id,
                    ),
                )
                updated_row = self._get_sync_task_row(conn, task_id=task_id)
        except sqlite3.Error as exc:
            raise ServiceError(
                code="INTERNAL_ERROR",
                message="更新同步任务失败，请检查数据库文件和目录权限。",
                status_code=500,
            ) from exc

        return self._sync_task_from_row(updated_row)

    def _upsert_search_note(self, conn: sqlite3.Connection, *, item: SearchResultItem) -> None:
        timestamp = _utc_now()
        payload = item.model_dump(mode="json")
        conn.execute(
            """
            INSERT INTO rednote_notes (
                platform,
                note_id,
                title,
                note_type,
                author_id,
                author_name,
                author_profile_url,
                url,
                cover,
                publish_time,
                liked_count_text,
                collected_count_text,
                comment_count_text,
                xsec_token,
                source_type,
                raw_json,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(note_id) DO UPDATE SET
                title = excluded.title,
                note_type = excluded.note_type,
                author_id = excluded.author_id,
                author_name = excluded.author_name,
                author_profile_url = excluded.author_profile_url,
                url = excluded.url,
                cover = excluded.cover,
                publish_time = COALESCE(excluded.publish_time, rednote_notes.publish_time),
                liked_count_text = excluded.liked_count_text,
                collected_count_text = excluded.collected_count_text,
                comment_count_text = excluded.comment_count_text,
                xsec_token = COALESCE(excluded.xsec_token, rednote_notes.xsec_token),
                source_type = excluded.source_type,
                raw_json = excluded.raw_json,
                updated_at = excluded.updated_at
            """,
            (
                "rednote",
                item.note_id,
                item.title,
                item.note_type.value,
                item.author_id,
                item.author_name,
                item.author_profile_url,
                item.url,
                item.cover,
                item.publish_time,
                item.liked_count,
                item.collected_count,
                item.comment_count,
                item.xsec_token,
                "search",
                json.dumps(payload, ensure_ascii=False),
                timestamp,
                timestamp,
            ),
        )

    def _upsert_detail_note(self, conn: sqlite3.Connection, *, detail: NoteDetailData) -> None:
        timestamp = _utc_now()
        payload = detail.model_dump(mode="json")
        conn.execute(
            """
            INSERT INTO rednote_notes (
                platform,
                note_id,
                title,
                desc,
                note_type,
                author_id,
                author_name,
                author_profile_url,
                url,
                video,
                publish_time,
                last_update_time,
                liked_count_text,
                collected_count_text,
                comment_count_text,
                share_count_text,
                images_json,
                tags_json,
                source_type,
                raw_json,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(note_id) DO UPDATE SET
                title = excluded.title,
                desc = excluded.desc,
                note_type = excluded.note_type,
                author_id = excluded.author_id,
                author_name = excluded.author_name,
                author_profile_url = excluded.author_profile_url,
                url = excluded.url,
                video = excluded.video,
                publish_time = COALESCE(excluded.publish_time, rednote_notes.publish_time),
                last_update_time = COALESCE(excluded.last_update_time, rednote_notes.last_update_time),
                liked_count_text = excluded.liked_count_text,
                collected_count_text = excluded.collected_count_text,
                comment_count_text = excluded.comment_count_text,
                share_count_text = excluded.share_count_text,
                images_json = excluded.images_json,
                tags_json = excluded.tags_json,
                source_type = excluded.source_type,
                raw_json = excluded.raw_json,
                updated_at = excluded.updated_at
            """,
            (
                "rednote",
                detail.note_id,
                detail.title,
                detail.desc,
                detail.note_type.value,
                detail.author_id,
                detail.author_name,
                detail.author_profile_url,
                detail.url,
                detail.video,
                detail.publish_time,
                detail.last_update_time,
                detail.liked_count,
                detail.collected_count,
                detail.comment_count,
                detail.share_count,
                json.dumps(detail.images, ensure_ascii=False),
                json.dumps(detail.tags, ensure_ascii=False),
                "detail",
                json.dumps(payload, ensure_ascii=False),
                timestamp,
                timestamp,
            ),
        )

    def _upsert_sync_task(
        self,
        conn: sqlite3.Connection,
        *,
        note_id: str,
        task_type: str,
        payload: dict[str, Any],
        target: str | None = None,
    ) -> None:
        timestamp = _utc_now()
        task_target = target or self._default_sync_target
        biz_key = f"rednote:{note_id}"
        row = conn.execute(
            """
            SELECT id
            FROM sync_tasks
            WHERE platform = ? AND biz_key = ? AND target = ?
            LIMIT 1
            """,
            ("rednote", biz_key, task_target),
        ).fetchone()

        if row is None:
            conn.execute(
                """
                INSERT INTO sync_tasks (
                    platform,
                    biz_key,
                    note_id,
                    task_type,
                    target,
                    status,
                    payload_json,
                    retry_count,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "rednote",
                    biz_key,
                    note_id,
                    task_type,
                    task_target,
                    SyncTaskStatus.PENDING.value,
                    json.dumps(payload, ensure_ascii=False),
                    0,
                    timestamp,
                    timestamp,
                ),
            )
            return

        conn.execute(
            """
            UPDATE sync_tasks
            SET note_id = ?,
                task_type = ?,
                status = ?,
                payload_json = ?,
                error_message = NULL,
                retry_count = 0,
                updated_at = ?,
                synced_at = NULL
            WHERE id = ?
            """,
            (
                note_id,
                task_type,
                SyncTaskStatus.PENDING.value,
                json.dumps(payload, ensure_ascii=False),
                timestamp,
                int(row["id"]),
            ),
        )

    def _get_sync_task_row(self, conn: sqlite3.Connection, *, task_id: int) -> sqlite3.Row:
        row = conn.execute(
            """
            SELECT *
            FROM sync_tasks
            WHERE id = ?
            LIMIT 1
            """,
            (task_id,),
        ).fetchone()
        if row is None:
            raise ServiceError(
                code="NOT_FOUND",
                message="未找到指定的同步任务。",
                status_code=404,
            )
        return row

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _note_from_row(self, row: sqlite3.Row) -> StoredNoteData:
        return StoredNoteData(
            platform=str(row["platform"]),
            note_id=str(row["note_id"]),
            title=str(row["title"] or ""),
            desc=str(row["desc"] or ""),
            note_type=str(row["note_type"] or "default"),
            author_id=str(row["author_id"] or ""),
            author_name=str(row["author_name"] or ""),
            author_profile_url=row["author_profile_url"],
            url=str(row["url"] or ""),
            cover=row["cover"],
            video=row["video"],
            publish_time=row["publish_time"],
            last_update_time=row["last_update_time"],
            liked_count_text=str(row["liked_count_text"] or "0"),
            collected_count_text=str(row["collected_count_text"] or "0"),
            comment_count_text=str(row["comment_count_text"] or "0"),
            share_count_text=str(row["share_count_text"] or "0"),
            images=_loads_json_list(row["images_json"]),
            tags=_loads_json_list(row["tags_json"]),
            xsec_token=row["xsec_token"],
            source_type=str(row["source_type"] or "search"),
            raw_json=_loads_json_dict(row["raw_json"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _sync_task_from_row(self, row: sqlite3.Row) -> SyncTaskData:
        return SyncTaskData(
            id=int(row["id"]),
            platform=str(row["platform"]),
            biz_key=str(row["biz_key"]),
            note_id=str(row["note_id"]),
            task_type=str(row["task_type"]),
            target=str(row["target"]),
            status=SyncTaskStatus(str(row["status"])),
            payload=_loads_json_dict(row["payload_json"]),
            bitable_record_id=row["bitable_record_id"],
            error_message=row["error_message"],
            retry_count=int(row["retry_count"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            synced_at=row["synced_at"],
        )


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _loads_json_list(raw_value: Any) -> list[str]:
    if not raw_value:
        return []
    try:
        value = json.loads(str(raw_value))
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _loads_json_dict(raw_value: Any) -> dict[str, Any]:
    if not raw_value:
        return {}
    try:
        value = json.loads(str(raw_value))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}

