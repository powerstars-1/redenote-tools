from service.app.core.rednote_service import RedNoteService
from service.app.models.rednote import DetailRequest, NoteDetailData, NoteType, SearchRequest, SearchResultItem


class FakeAdapter:
    def __init__(self) -> None:
        self.search_calls = []
        self.detail_calls = []

    def search_notes(self, **kwargs):
        self.search_calls.append(kwargs)
        return [
            SearchResultItem(
                note_id="note-1",
                title="面霜测评",
                note_type=NoteType.IMAGE,
                author_id="user-1",
                author_name="作者A",
                author_profile_url="https://www.xiaohongshu.com/user/profile/user-1",
                url="https://www.xiaohongshu.com/explore/note-1?xsec_token=test",
                cover="https://cdn.example.com/cover.jpg",
                liked_count="12",
                collected_count="3",
                comment_count="1",
                publish_time="2026-03-15T10:00:00Z",
                xsec_token="test",
            )
        ]

    def get_note_detail(self, **kwargs):
        self.detail_calls.append(kwargs)
        return NoteDetailData(
            note_id="note-1",
            title="面霜测评",
            desc="正文内容",
            note_type=NoteType.IMAGE,
            author_id="user-1",
            author_name="作者A",
            author_profile_url="https://www.xiaohongshu.com/user/profile/user-1",
            liked_count="1.5w",
            collected_count="3",
            comment_count="1",
            share_count="0",
            publish_time="2026-03-15T10:00:00Z",
            last_update_time=None,
            images=["https://cdn.example.com/1.jpg"],
            video=None,
            tags=["护肤"],
            url="https://www.xiaohongshu.com/explore/note-1?xsec_token=test",
        )


def test_search_service_wraps_adapter_result():
    adapter = FakeAdapter()
    service = RedNoteService(adapter=adapter)

    result = service.search(
        SearchRequest(
            keyword="护肤",
            note_type="image",
            publish_time="7d",
            sort_by="latest",
            page_count=2,
            cookie="a1=test; web_session=session",
        )
    )

    assert result.keyword == "护肤"
    assert result.page_count == 2
    assert result.items[0].note_id == "note-1"
    assert result.items[0].author_profile_url == "https://www.xiaohongshu.com/user/profile/user-1"
    assert result.items[0].liked_count == "12"
    assert adapter.search_calls[0]["page_count"] == 2
    assert adapter.search_calls[0]["sort_by"] == "latest"


def test_detail_service_returns_note_detail():
    adapter = FakeAdapter()
    service = RedNoteService(adapter=adapter)

    result = service.detail(
        DetailRequest(
            url="https://www.xiaohongshu.com/explore/note-1?xsec_token=test",
            cookie="a1=test; web_session=session",
        )
    )

    assert result.note_id == "note-1"
    assert result.tags == ["护肤"]
    assert result.author_profile_url == "https://www.xiaohongshu.com/user/profile/user-1"
    assert result.liked_count == "1.5w"
    assert adapter.detail_calls[0]["url"].startswith("https://www.xiaohongshu.com/explore/")
