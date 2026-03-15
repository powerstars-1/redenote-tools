from fastapi import APIRouter, Depends, Request

from service.app.api.dependencies import get_rednote_service, require_public_api_key
from service.app.core.rednote_service import RedNoteService
from service.app.core.responses import build_success_response, get_request_id
from service.app.models.rednote import DetailRequest, SearchRequest

router = APIRouter(
    prefix="/api/v1/rednote",
    tags=["rednote"],
    dependencies=[Depends(require_public_api_key)],
)


@router.post("/search", summary="获取小红书搜索结果")
def search_rednote(
    payload: SearchRequest,
    request: Request,
    service: RedNoteService = Depends(get_rednote_service),
) -> dict:
    result = service.search(payload)
    return build_success_response(
        request_id=get_request_id(request),
        data=result,
    )


@router.post("/detail", summary="通过 URL 获取笔记详情")
def get_rednote_detail(
    payload: DetailRequest,
    request: Request,
    service: RedNoteService = Depends(get_rednote_service),
) -> dict:
    result = service.detail(payload)
    return build_success_response(
        request_id=get_request_id(request),
        data=result,
    )
