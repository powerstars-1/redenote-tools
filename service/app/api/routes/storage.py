from fastapi import APIRouter, Depends, Query, Request

from service.app.api.dependencies import get_rednote_store
from service.app.core.responses import build_success_response, get_request_id
from service.app.models.storage import (
    MarkSyncTaskFailedRequest,
    MarkSyncTaskSuccessRequest,
    PendingSyncTasksResponseData,
)
from service.app.storage.sqlite_store import SQLiteRedNoteStore

router = APIRouter(prefix="/api/v1/storage", tags=["storage"])


@router.get("/notes", summary="获取已落库的笔记列表")
def list_stored_notes(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    store: SQLiteRedNoteStore = Depends(get_rednote_store),
) -> dict:
    result = store.list_notes(limit=limit)
    return build_success_response(
        request_id=get_request_id(request),
        data=result,
    )


@router.get("/notes/{note_id}", summary="获取单条已落库笔记")
def get_stored_note(
    note_id: str,
    request: Request,
    store: SQLiteRedNoteStore = Depends(get_rednote_store),
) -> dict:
    result = store.get_note(note_id=note_id)
    return build_success_response(
        request_id=get_request_id(request),
        data=result,
    )


@router.get("/sync/pending", summary="获取待同步到 OpenClaw 的任务")
def list_pending_sync_tasks(
    request: Request,
    target: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    store: SQLiteRedNoteStore = Depends(get_rednote_store),
) -> dict:
    task_target = target or request.app.state.settings.default_sync_target
    result = PendingSyncTasksResponseData(
        items=store.list_pending_sync_tasks(target=task_target, limit=limit),
        target=task_target,
        limit=limit,
    )
    return build_success_response(
        request_id=get_request_id(request),
        data=result,
    )


@router.post("/sync/tasks/{task_id}/success", summary="标记同步任务成功")
def mark_sync_task_success(
    task_id: int,
    payload: MarkSyncTaskSuccessRequest,
    request: Request,
    store: SQLiteRedNoteStore = Depends(get_rednote_store),
) -> dict:
    result = store.mark_sync_task_success(
        task_id=task_id,
        bitable_record_id=payload.bitable_record_id,
    )
    return build_success_response(
        request_id=get_request_id(request),
        data=result,
    )


@router.post("/sync/tasks/{task_id}/failed", summary="标记同步任务失败")
def mark_sync_task_failed(
    task_id: int,
    payload: MarkSyncTaskFailedRequest,
    request: Request,
    store: SQLiteRedNoteStore = Depends(get_rednote_store),
) -> dict:
    result = store.mark_sync_task_failed(
        task_id=task_id,
        error_message=payload.error_message,
    )
    return build_success_response(
        request_id=get_request_id(request),
        data=result,
    )

