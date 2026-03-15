from fastapi import Request

from service.app.adapters.spider_xhs.client import SpiderXHSClient
from service.app.config.settings import Settings
from service.app.core.rednote_service import RedNoteService


def build_default_rednote_service(settings: Settings) -> RedNoteService:
    return RedNoteService(adapter=SpiderXHSClient(settings=settings))


def get_rednote_service(request: Request) -> RedNoteService:
    return request.app.state.rednote_service
