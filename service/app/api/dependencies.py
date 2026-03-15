from fastapi import Request

from service.app.adapters.spider_xhs.client import SpiderXHSClient
from service.app.config.settings import Settings
from service.app.core.rednote_service import RedNoteService
from service.app.storage.sqlite_store import SQLiteRedNoteStore


def build_default_rednote_store(settings: Settings) -> SQLiteRedNoteStore:
    store = SQLiteRedNoteStore(
        database_path=settings.resolved_database_path,
        default_sync_target=settings.default_sync_target,
    )
    store.initialize()
    return store


def build_default_rednote_service(settings: Settings, *, store: SQLiteRedNoteStore) -> RedNoteService:
    return RedNoteService(adapter=SpiderXHSClient(settings=settings), store=store)


def get_rednote_service(request: Request) -> RedNoteService:
    return request.app.state.rednote_service


def get_rednote_store(request: Request) -> SQLiteRedNoteStore:
    return request.app.state.rednote_store
