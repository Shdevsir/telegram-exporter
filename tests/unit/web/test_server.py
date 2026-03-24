import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import src.web.server as server


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _create_chat_dir(base: Path, chat_id: str, history_payload, info_payload=None, avatar=False):
    chat_dir = base / chat_id
    (chat_dir / "Text").mkdir(parents=True, exist_ok=True)
    _write_json(chat_dir / "Text" / "history.json", history_payload)

    if info_payload is not None:
        (chat_dir / "Info").mkdir(parents=True, exist_ok=True)
        _write_json(chat_dir / "Info" / "info.json", info_payload)

    if avatar:
        (chat_dir / "Info").mkdir(parents=True, exist_ok=True)
        (chat_dir / "Info" / "avatar.jpg").write_bytes(b"avatar")

    return chat_dir


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "EXPORT_DIR", str(tmp_path))
    server.app.config.update(TESTING=True)
    with server.app.test_client() as app_client:
        yield app_client, tmp_path


def test_logger_writer_write_and_flush():
    sink = MagicMock()
    writer = server.LoggerWriter(sink)

    writer.write("  hello world  \n")
    writer.write("   ")
    writer.flush()

    sink.assert_called_once_with("hello world")


def test_load_json_success_and_errors(tmp_path):
    valid = tmp_path / "valid.json"
    invalid = tmp_path / "invalid.json"

    valid.write_text('{"k": 1}', encoding="utf-8")
    invalid.write_text("{", encoding="utf-8")

    assert server._load_json(str(valid)) == {"k": 1}
    assert server._load_json(str(invalid)) == {}
    assert server._load_json(str(tmp_path / "missing.json")) == {}


def test_resolve_media_url_variants():
    assert server._resolve_media_url("chat1", None) is None
    assert (
        server._resolve_media_url("chat1", "telegram_data/chat1/Files/Photos/a.jpg")
        == "/media/chat1/Files/Photos/a.jpg"
    )
    assert server._resolve_media_url("chat1", "Files\\Photos\\a.jpg") == "/media/chat1/Files/Photos/a.jpg"


def test_detect_media_kind_all_branches():
    assert server._detect_media_kind(None) is None
    assert server._detect_media_kind("x/Photos/a.jpg") == "image"
    assert server._detect_media_kind("x/Stickers/s.webp") == "image"
    assert server._detect_media_kind("x/Videos/v.mp4") == "video"
    assert server._detect_media_kind("x/Round_Messages/r.mp4") == "round"
    assert server._detect_media_kind("x/Audio/a.ogg") == "audio"
    assert server._detect_media_kind("x/GIFs/g.mp4") == "gif"
    assert server._detect_media_kind("x/Documents/f.pdf") == "file"


def test_build_display_messages_formats_time_and_media_kind():
    raw = [
        {
            "id": 1,
            "text": "hello",
            "date": "2026-03-24 10:30:22+00:00",
            "sender_id": 10,
            "media": "chat42/Files/Photos/a.jpg",
        },
        {
            "id": 2,
            "date": "2026-03-24",
            "media": None,
        },
    ]

    built = server._build_display_messages("chat42", raw)

    assert built[0]["time_text"] == "10:30"
    assert built[0]["media_url"] == "/media/chat42/Files/Photos/a.jpg"
    assert built[0]["media_kind"] == "image"
    assert built[1]["time_text"] == ""
    assert built[1]["text"] == ""


def test_scan_chats_missing_export_dir(monkeypatch, tmp_path):
    missing = tmp_path / "missing"
    monkeypatch.setattr(server, "EXPORT_DIR", str(missing))

    assert server._scan_chats() == []


def test_scan_chats_reads_info_and_sorts(tmp_path, monkeypatch):
    export_dir = tmp_path / "export"
    export_dir.mkdir()

    _create_chat_dir(
        export_dir,
        "chat_b",
        history_payload=[],
        info_payload={
            "about": {"first_name": "Beta", "last_name": "User", "username": "beta"},
            "chat_type": "User",
        },
    )
    _create_chat_dir(
        export_dir,
        "chat_a",
        history_payload=[],
        info_payload={
            "about": {"title": "Alpha Room"},
            "chat_type": "Channel",
        },
    )
    _create_chat_dir(export_dir, "chat_c", history_payload=[])

    # Non-directory entry should be ignored.
    (export_dir / "README.txt").write_text("ignore", encoding="utf-8")

    # Invalid info type should exercise isinstance=False branch.
    (export_dir / "chat_c" / "Info").mkdir(parents=True, exist_ok=True)
    _write_json(export_dir / "chat_c" / "Info" / "info.json", ["not", "dict"])

    monkeypatch.setattr(server, "EXPORT_DIR", str(export_dir))

    chats = server._scan_chats()

    assert [c["id"] for c in chats] == ["chat_a", "chat_b", "chat_c"]
    assert chats[0]["name"] == "Alpha Room"
    assert chats[1]["name"] == "Beta User"
    assert chats[1]["username"] == "beta"
    assert chats[2]["type"] == "Unknown"


def test_paginate_bounds_and_empty():
    page = server._paginate([1, 2, 3, 4, 5], page=99, per_page=2)
    assert page["current_page"] == 3
    assert page["items"] == [5]

    empty = server._paginate([], page=-5, per_page=10)
    assert empty["current_page"] == 1
    assert empty["total_pages"] == 1
    assert empty["items"] == []


def test_index_route_ok_and_per_page_normalization(client):
    app_client, tmp_path = client
    _create_chat_dir(tmp_path, "chat1", history_payload=[])

    response = app_client.get("/?page=1&per_page=0")

    assert response.status_code == 200
    assert b"Telegram Archive Gallery" in response.data


def test_serve_media_success_and_missing_chat(client):
    app_client, tmp_path = client
    chat_dir = _create_chat_dir(tmp_path, "chat1", history_payload=[])
    media_file = chat_dir / "Files" / "Photos" / "img.jpg"
    media_file.parent.mkdir(parents=True, exist_ok=True)
    media_file.write_bytes(b"jpg")

    ok = app_client.get("/media/chat1/Files/Photos/img.jpg")
    missing_chat = app_client.get("/media/nochat/Files/Photos/img.jpg")

    assert ok.status_code == 200
    assert ok.data == b"jpg"
    assert missing_chat.status_code == 404


def test_serve_media_blocks_traversal(client):
    app_client, tmp_path = client
    _create_chat_dir(tmp_path, "chat1", history_payload=[])

    response = app_client.get("/media/chat1/../../etc/passwd")

    assert response.status_code == 404


def test_view_chat_404_when_history_missing(client):
    app_client, tmp_path = client
    (tmp_path / "chat1").mkdir(parents=True, exist_ok=True)

    response = app_client.get("/chat/chat1")

    assert response.status_code == 404


def test_view_chat_renders_with_missing_info_and_avatar_false(client):
    app_client, tmp_path = client
    _create_chat_dir(
        tmp_path,
        "chat1",
        history_payload=[
            {"id": 1, "date": "2026-03-24 11:00:00+00:00", "text": "hello", "sender_id": 1, "media": None}
        ],
        info_payload=None,
        avatar=False,
    )

    response = app_client.get("/chat/chat1?page=1&per_page=20")

    assert response.status_code == 200
    assert b"chat1" in response.data
    assert b"hello" in response.data


def test_view_chat_handles_invalid_history_and_info_types(client):
    app_client, tmp_path = client
    _create_chat_dir(
        tmp_path,
        "chat1",
        history_payload={"bad": True},
        info_payload=["not", "dict"],
        avatar=True,
    )

    response = app_client.get("/chat/chat1?page=1&per_page=-5")

    assert response.status_code == 200
    assert b"No messages available on this page." in response.data


def test_view_chat_selects_chat_from_menu(client):
    app_client, tmp_path = client
    _create_chat_dir(tmp_path, "chat1", history_payload=[], info_payload={"about": {"title": "One"}})
    _create_chat_dir(tmp_path, "chat2", history_payload=[], info_payload={"about": {"title": "Two"}})

    response = app_client.get("/chat/chat2?page=999&per_page=1")

    assert response.status_code == 200
    assert b"Archived Chats" in response.data
    assert b"Two" in response.data


def test_run_server_sets_stream_redirects_and_runs(monkeypatch):
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    run_mock = MagicMock()
    monkeypatch.setattr(server.app, "run", run_mock)

    server.run_server(host="127.0.0.1", port=5050)

    try:
        assert isinstance(sys.stdout, server.LoggerWriter)
        assert isinstance(sys.stderr, server.LoggerWriter)
        run_mock.assert_called_once_with(host="127.0.0.1", port=5050, debug=False, use_reloader=False)
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
