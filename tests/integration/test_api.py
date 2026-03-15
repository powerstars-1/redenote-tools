from fastapi.testclient import TestClient

from service.app.core.rednote_service import RedNoteService
from service.app.main import create_app
from service.app.models.rednote import NoteDetailData, NoteType, SearchResultItem


class StubAdapter:
    def search_notes(self, **kwargs):
        return [
            SearchResultItem(
                note_id="note-1",
                title="防晒清单",
                note_type=NoteType.IMAGE,
                author_id="user-1",
                author_name="作者A",
                author_profile_url="https://www.xiaohongshu.com/user/profile/user-1",
                url="https://www.xiaohongshu.com/explore/note-1?xsec_token=test",
                cover="https://cdn.example.com/cover.jpg",
                liked_count="99",
                collected_count="10",
                comment_count="5",
                publish_time="2026-03-15T10:00:00Z",
                xsec_token="test",
            )
        ]

    def get_note_detail(self, **kwargs):
        return NoteDetailData(
            note_id="note-1",
            title="防晒清单",
            desc="正文内容",
            note_type=NoteType.IMAGE,
            author_id="user-1",
            author_name="作者A",
            author_profile_url="https://www.xiaohongshu.com/user/profile/user-1",
            liked_count="1.5w",
            collected_count="10",
            comment_count="5",
            share_count="1",
            publish_time="2026-03-15T10:00:00Z",
            last_update_time=None,
            images=["https://cdn.example.com/1.jpg"],
            video=None,
            tags=["防晒"],
            url="https://www.xiaohongshu.com/explore/note-1?xsec_token=test",
        )


def test_search_endpoint_returns_standard_envelope():
    app = create_app(rednote_service=RedNoteService(adapter=StubAdapter()))
    client = TestClient(app)

    response = client.post(
        "/api/v1/rednote/search",
        json={
            "keyword": "防晒",
            "note_type": "image",
            "publish_time": "7d",
            "sort_by": "latest",
            "page_count": 2,
            "cookie": "a1=test; web_session=session",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["page_count"] == 2
    assert body["data"]["items"][0]["note_id"] == "note-1"
    assert body["data"]["items"][0]["author_profile_url"] == "https://www.xiaohongshu.com/user/profile/user-1"
    assert body["data"]["items"][0]["liked_count"] == "99"
    assert body["request_id"].startswith("req_")


def test_root_page_serves_desk_html():
    app = create_app(rednote_service=RedNoteService(adapter=StubAdapter()))
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "RedNote Desk" in response.text
    assert "发布能力预留区" in response.text


def test_detail_endpoint_validates_cookie():
    app = create_app(rednote_service=RedNoteService(adapter=StubAdapter()))
    client = TestClient(app)

    response = client.post(
        "/api/v1/rednote/detail",
        json={
            "url": "https://www.xiaohongshu.com/explore/note-1?xsec_token=test",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENT"
