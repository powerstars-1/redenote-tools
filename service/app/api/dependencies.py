from secrets import compare_digest

from fastapi import Header, Request

from service.app.adapters.spider_xhs.client import SpiderXHSClient
from service.app.config.settings import Settings
from service.app.core.exceptions import ServiceError
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


def require_public_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    settings: Settings = request.app.state.settings
    _validate_api_key(
        provided_key=x_api_key,
        allowed_keys=settings.public_allowed_api_keys,
        auth_enabled=settings.auth_enabled,
        scope_label="公开接口",
    )


def require_internal_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    settings: Settings = request.app.state.settings
    _validate_api_key(
        provided_key=x_api_key,
        allowed_keys=settings.internal_allowed_api_keys,
        auth_enabled=settings.auth_enabled,
        scope_label="内部同步接口",
    )


def _validate_api_key(
    *,
    provided_key: str | None,
    allowed_keys: tuple[str, ...],
    auth_enabled: bool,
    scope_label: str,
) -> None:
    if not auth_enabled:
        return

    if not provided_key:
        raise ServiceError(
            code="UNAUTHORIZED",
            message=f"{scope_label}缺少 API Key，请在请求头中传入 X-API-Key。",
            status_code=401,
        )

    if any(compare_digest(provided_key, allowed_key) for allowed_key in allowed_keys):
        return

    raise ServiceError(
        code="UNAUTHORIZED",
        message=f"{scope_label}的 API Key 无效或未授权。",
        status_code=401,
    )
