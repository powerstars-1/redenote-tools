from fastapi.testclient import TestClient

from service.app.config.settings import Settings
from service.app.core.rednote_service import RedNoteService
from service.app.main import create_app
from service.app.models.rednote import NoteDetailData, NoteType, SearchResultItem
from service.app.storage.sqlite_store import SQLiteRedNoteStore


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


def build_test_client(tmp_path) -> TestClient:
    settings = Settings(database_path=tmp_path / "app.db")
    store = SQLiteRedNoteStore(
        database_path=settings.resolved_database_path,
        default_sync_target=settings.default_sync_target,
    )
    store.initialize()
    app = create_app(
        settings=settings,
        rednote_store=store,
        rednote_service=RedNoteService(adapter=StubAdapter(), store=store),
    )
    return TestClient(app)


def test_search_endpoint_returns_standard_envelope(tmp_path):
    client = build_test_client(tmp_path)

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

    notes_response = client.get("/api/v1/storage/notes")
    notes_body = notes_response.json()
    assert notes_response.status_code == 200
    assert notes_body["data"]["items"][0]["note_id"] == "note-1"
    assert notes_body["data"]["items"][0]["liked_count_text"] == "99"

    pending_response = client.get("/api/v1/storage/sync/pending")
    pending_body = pending_response.json()
    assert pending_response.status_code == 200
    assert pending_body["data"]["items"][0]["note_id"] == "note-1"
    assert pending_body["data"]["items"][0]["task_type"] == "search_result"
    assert pending_body["data"]["items"][0]["payload"]["source"] == "search"


def test_root_page_serves_desk_html(tmp_path):
    client = build_test_client(tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "RedNote Desk" in response.text
    assert "发布能力预留区" in response.text


def test_detail_endpoint_validates_cookie(tmp_path):
    client = build_test_client(tmp_path)

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


def test_detail_endpoint_updates_note_and_sync_task(tmp_path):
    client = build_test_client(tmp_path)

    client.post(
        "/api/v1/rednote/search",
        json={
            "keyword": "防晒",
            "note_type": "image",
            "publish_time": "7d",
            "sort_by": "latest",
            "page_count": 1,
            "cookie": "a1=test; web_session=session",
        },
    )

    response = client.post(
        "/api/v1/rednote/detail",
        json={
            "url": "https://www.xiaohongshu.com/explore/note-1?xsec_token=test",
            "cookie": "a1=test; web_session=session",
        },
    )

    assert response.status_code == 200

    note_response = client.get("/api/v1/storage/notes/note-1")
    note_body = note_response.json()
    assert note_response.status_code == 200
    assert note_body["data"]["desc"] == "正文内容"
    assert note_body["data"]["images"] == ["https://cdn.example.com/1.jpg"]
    assert note_body["data"]["source_type"] == "detail"

    pending_response = client.get("/api/v1/storage/sync/pending")
    pending_body = pending_response.json()
    assert pending_response.status_code == 200
    task = pending_body["data"]["items"][0]
    assert task["task_type"] == "note_detail"
    assert task["payload"]["note"]["desc"] == "正文内容"

    success_response = client.post(
        f"/api/v1/storage/sync/tasks/{task['id']}/success",
        json={"bitable_record_id": "rec_123"},
    )
    success_body = success_response.json()
    assert success_response.status_code == 200
    assert success_body["data"]["status"] == "success"
    assert success_body["data"]["bitable_record_id"] == "rec_123"

    client.post(
        "/api/v1/rednote/detail",
        json={
            "url": "https://www.xiaohongshu.com/explore/note-1?xsec_token=test",
            "cookie": "a1=test; web_session=session",
        },
    )
    pending_again_response = client.get("/api/v1/storage/sync/pending")
    pending_again_body = pending_again_response.json()
    assert pending_again_response.status_code == 200
    assert pending_again_body["data"]["items"][0]["bitable_record_id"] == "rec_123"


def test_mark_sync_task_failed(tmp_path):
    client = build_test_client(tmp_path)

    client.post(
        "/api/v1/rednote/search",
        json={
            "keyword": "防晒",
            "note_type": "image",
            "publish_time": "7d",
            "sort_by": "latest",
            "page_count": 1,
            "cookie": "a1=test; web_session=session",
        },
    )

    pending_response = client.get("/api/v1/storage/sync/pending")
    task_id = pending_response.json()["data"]["items"][0]["id"]

    failed_response = client.post(
        f"/api/v1/storage/sync/tasks/{task_id}/failed",
        json={"error_message": "多维表格写入失败"},
    )

    body = failed_response.json()
    assert failed_response.status_code == 200
    assert body["data"]["status"] == "failed"
    assert body["data"]["retry_count"] == 1
    assert body["data"]["error_message"] == "多维表格写入失败"
