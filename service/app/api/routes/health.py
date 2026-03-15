from fastapi import APIRouter, Request

from service.app.core.responses import build_success_response, get_request_id

router = APIRouter(tags=["system"])


@router.get("/healthz", summary="健康检查")
def healthz(request: Request) -> dict:
    return build_success_response(
        request_id=get_request_id(request),
        data={"status": "ok"},
    )
