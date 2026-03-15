from __future__ import annotations

from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from service.app.api.dependencies import build_default_rednote_service, build_default_rednote_store
from service.app.api.routes.health import router as health_router
from service.app.api.routes.rednote import router as rednote_router
from service.app.api.routes.storage import router as storage_router
from service.app.config.settings import Settings, get_settings
from service.app.core.exceptions import ServiceError
from service.app.core.responses import build_error_response, get_request_id
from service.app.observability.logging import configure_logging, get_logger


def create_app(
    *,
    settings: Settings | None = None,
    rednote_service=None,
    rednote_store=None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.settings = settings
    app.state.rednote_store = rednote_store or build_default_rednote_store(settings)
    app.state.rednote_service = rednote_service or build_default_rednote_service(
        settings,
        store=app.state.rednote_store,
    )
    web_dir = Path(__file__).resolve().parent / "web"

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex[:16]}"
        request.state.request_id = request_id
        started_at = perf_counter()
        response = await call_next(request)
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_access request_id=%s method=%s path=%s status_code=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
        logger.warning(
            "service_error request_id=%s code=%s message=%s path=%s",
            get_request_id(request),
            exc.code,
            exc.message,
            request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_response(
                request_id=get_request_id(request),
                code=exc.code,
                message=exc.message,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        message = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'][1:])}: {error['msg']}"
            for error in exc.errors()
        )
        return JSONResponse(
            status_code=400,
            content=build_error_response(
                request_id=get_request_id(request),
                code="INVALID_ARGUMENT",
                message=message or "请求参数不合法。",
            ),
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unexpected_error request_id=%s path=%s",
            get_request_id(request),
            request.url.path,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content=build_error_response(
                request_id=get_request_id(request),
                code="INTERNAL_ERROR",
                message="服务内部异常，请稍后重试。",
            ),
        )

    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def desk_home():
        return FileResponse(web_dir / "index.html")

    app.include_router(health_router)
    app.include_router(rednote_router)
    app.include_router(storage_router)
    return app


app = create_app()
