from __future__ import annotations

from logging import Logger
from typing import Protocol

from service.app.models.rednote import DetailRequest, NoteDetailData, SearchRequest, SearchResponseData
from service.app.observability.logging import get_logger


class RedNoteAdapter(Protocol):
    def search_notes(
        self,
        *,
        keyword: str,
        note_type: str,
        publish_time: str,
        sort_by: str,
        page_count: int,
        cookie: str,
    ) -> list:
        ...

    def get_note_detail(
        self,
        *,
        url: str,
        cookie: str,
    ) -> NoteDetailData:
        ...


class RedNoteStore(Protocol):
    def persist_search_response(self, response: SearchResponseData) -> None:
        ...

    def persist_note_detail(self, detail: NoteDetailData) -> None:
        ...


class RedNoteService:
    def __init__(
        self,
        adapter: RedNoteAdapter,
        *,
        store: RedNoteStore | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._adapter = adapter
        self._store = store
        self._logger = logger or get_logger(__name__)

    def search(self, payload: SearchRequest) -> SearchResponseData:
        self._logger.info(
            "rednote_search_requested keyword=%s page_count=%s note_type=%s publish_time=%s sort_by=%s cookie_present=%s",
            payload.keyword,
            payload.page_count,
            payload.note_type.value,
            payload.publish_time.value,
            payload.sort_by.value,
            bool(payload.cookie),
        )

        items = self._adapter.search_notes(
            keyword=payload.keyword,
            note_type=payload.note_type.value,
            publish_time=payload.publish_time.value,
            sort_by=payload.sort_by.value,
            page_count=payload.page_count,
            cookie=payload.cookie,
        )

        result = SearchResponseData(
            keyword=payload.keyword,
            filters={
                "note_type": payload.note_type,
                "publish_time": payload.publish_time,
                "sort_by": payload.sort_by,
            },
            page_count=payload.page_count,
            items=items,
        )
        if self._store is not None:
            self._store.persist_search_response(result)
        return result

    def detail(self, payload: DetailRequest) -> NoteDetailData:
        self._logger.info(
            "rednote_detail_requested url=%s cookie_present=%s",
            payload.url,
            bool(payload.cookie),
        )
        result = self._adapter.get_note_detail(url=payload.url, cookie=payload.cookie)
        if self._store is not None:
            self._store.persist_note_detail(result)
        return result
