import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock

import pytest
from src.client.telegram_client import TelegramClient
from src.schemas import ChatStats
from telethon.tl.types import Channel
from telethon.tl.types import Chat
from telethon.tl.types import MessageEntityTextUrl
from telethon.tl.types import MessageEntityUrl
from telethon.tl.types import MessageMediaWebPage
from telethon.tl.types import User

tg_module = importlib.import_module("src.client.telegram_client")


async def _async_iter(items):
    for item in items:
        yield item


@pytest.fixture
def mock_credentials(monkeypatch):
    creds = SimpleNamespace(
        session_name="test_session",
        api_id=12345,
        api_hash="hash",
        phone_number="+380000000000",
    )
    monkeypatch.setattr(tg_module, "credentials", creds)
    return creds


@pytest.fixture
def client_instance(mock_credentials):
    return TelegramClient()


@pytest.mark.asyncio
async def test_setup_success_already_authorized(client_instance, monkeypatch):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.is_user_authorized = AsyncMock(return_value=True)
    mock_client.send_code_request = AsyncMock()
    mock_tg_ctor = MagicMock(return_value=mock_client)
    monkeypatch.setattr(tg_module, "tg_client", mock_tg_ctor)

    success, message = await client_instance.setup()

    assert success is True
    assert "already authorized" in message
    mock_client.send_code_request.assert_not_called()


@pytest.mark.asyncio
async def test_setup_success_with_code_flow(client_instance, mock_credentials, monkeypatch):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.is_user_authorized = AsyncMock(return_value=False)
    mock_client.send_code_request = AsyncMock()
    mock_client.sign_in = AsyncMock()
    mock_tg_ctor = MagicMock(return_value=mock_client)
    monkeypatch.setattr(tg_module, "tg_client", mock_tg_ctor)
    monkeypatch.setattr(tg_module.Prompt, "ask", Mock(return_value="123456"))

    success, message = await client_instance.setup()

    assert success is True
    assert "setup successfully" in message
    mock_client.send_code_request.assert_awaited_once_with(phone=mock_credentials.phone_number)
    mock_client.sign_in.assert_awaited_once_with(phone=mock_credentials.phone_number, code="123456")


@pytest.mark.asyncio
async def test_get_messages_count_returns_total(client_instance):
    client_instance.client = MagicMock()
    client_instance.client.get_messages = AsyncMock(return_value=SimpleNamespace(total=20))

    result = await client_instance.get_messages_count(MagicMock())

    assert result == 20


@pytest.mark.asyncio
async def test_get_messages_count_fallback_to_chat_message_id(client_instance):
    client_instance.client = MagicMock()
    client_instance.client.get_messages = AsyncMock(return_value=SimpleNamespace(total=2147483647))
    chat = SimpleNamespace(message=SimpleNamespace(id=321))

    result = await client_instance.get_messages_count(chat)

    assert result == 321


@pytest.mark.asyncio
async def test_get_messages_count_returns_none_when_total_over_limit_without_message(client_instance):
    client_instance.client = MagicMock()
    client_instance.client.get_messages = AsyncMock(return_value=SimpleNamespace(total=2147483647))

    result = await client_instance.get_messages_count(SimpleNamespace())

    assert result is None


def test_calculate_stats_text_media_and_link(client_instance):
    stats = ChatStats()
    message = SimpleNamespace(
        text="hello",
        media=object(),
        file=SimpleNamespace(size=120),
        sticker=False,
        gif=False,
        photo=True,
        video_note=False,
        video=False,
        voice=False,
        audio=False,
        document=False,
        entities=[MessageEntityUrl(offset=0, length=5)],
    )

    client_instance._calculate_stats(stats, message)

    assert stats.total.count == 1
    assert stats.text.count == 1
    assert stats.photos.count == 1
    assert stats.links == 1
    assert stats.service == 0
    assert stats.total.size == len(b"hello") + 120


@pytest.mark.asyncio
async def test_get_chat_statistics_reports_progress_every_50_messages(client_instance):
    messages = [SimpleNamespace(text="x", media=None, entities=None) for _ in range(51)]
    mock_client = MagicMock()
    mock_client.iter_messages = MagicMock(return_value=_async_iter(messages))
    client_instance.client = mock_client

    progress_callback = AsyncMock()

    stats, duration = await client_instance.get_chat_statistics(
        chat=MagicMock(),
        total_count=51,
        progress_callback=progress_callback,
    )

    assert stats.total.count == 51
    assert duration >= 0
    progress_callback.assert_any_await(50, 51)
    progress_callback.assert_any_await(51, 51)


def test_get_target_folder_mapping(client_instance):
    paths = {
        "stickers": "stickers-dir",
        "gifs": "gifs-dir",
        "photos": "photos-dir",
        "rounds": "rounds-dir",
        "videos": "videos-dir",
        "audio": "audio-dir",
        "docs": "docs-dir",
    }

    assert client_instance._get_target_folder(SimpleNamespace(sticker=True), paths) == "stickers-dir"
    assert client_instance._get_target_folder(SimpleNamespace(sticker=False, gif=True), paths) == "gifs-dir"
    assert (
        client_instance._get_target_folder(SimpleNamespace(sticker=False, gif=False, photo=True), paths) == "photos-dir"
    )
    assert (
        client_instance._get_target_folder(
            SimpleNamespace(sticker=False, gif=False, photo=False, video_note=True), paths
        )
        == "rounds-dir"
    )
    assert (
        client_instance._get_target_folder(
            SimpleNamespace(sticker=False, gif=False, photo=False, video_note=False, video=True), paths
        )
        == "videos-dir"
    )
    assert (
        client_instance._get_target_folder(
            SimpleNamespace(sticker=False, gif=False, photo=False, video_note=False, video=False, audio=True), paths
        )
        == "audio-dir"
    )
    assert (
        client_instance._get_target_folder(
            SimpleNamespace(
                sticker=False,
                gif=False,
                photo=False,
                video_note=False,
                video=False,
                audio=False,
                voice=True,
            ),
            paths,
        )
        == "audio-dir"
    )
    assert (
        client_instance._get_target_folder(
            SimpleNamespace(
                sticker=False,
                gif=False,
                photo=False,
                video_note=False,
                video=False,
                audio=False,
                voice=False,
                document=True,
            ),
            paths,
        )
        == "docs-dir"
    )
    assert (
        client_instance._get_target_folder(
            SimpleNamespace(
                sticker=False,
                gif=False,
                photo=False,
                video_note=False,
                video=False,
                audio=False,
                voice=False,
                document=False,
            ),
            paths,
        )
        is None
    )


@pytest.mark.parametrize(
    "chat, expected",
    [
        (
            (lambda x: (setattr(x, "id", 1), x)[1])(User.__new__(User)),
            "User (Private Chat)",
        ),
        (
            (lambda x: (setattr(x, "id", 2), x)[1])(Chat.__new__(Chat)),
            "Group",
        ),
        (
            (lambda x: (setattr(x, "broadcast", True), x)[1])(Channel.__new__(Channel)),
            "Channel",
        ),
        (
            (lambda x: (setattr(x, "broadcast", False), x)[1])(Channel.__new__(Channel)),
            "Supergroup (Large Group)",
        ),
    ],
)
def test_get_chat_type(client_instance, chat, expected):
    assert client_instance._get_chat_type(chat) == expected


@pytest.mark.asyncio
async def test_setup_returns_error_on_invalid_api(client_instance, monkeypatch):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(side_effect=tg_module.ApiIdInvalidError(request=None))
    mock_tg_ctor = MagicMock(return_value=mock_client)
    monkeypatch.setattr(tg_module, "tg_client", mock_tg_ctor)

    success, message = await client_instance.setup()

    assert success is False
    assert message == "Invalid API ID or API Hash."


@pytest.mark.asyncio
async def test_setup_returns_error_on_invalid_phone_number(client_instance, monkeypatch):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.is_user_authorized = AsyncMock(return_value=False)
    mock_client.send_code_request = AsyncMock(side_effect=tg_module.PhoneNumberInvalidError(request=None))
    mock_tg_ctor = MagicMock(return_value=mock_client)
    monkeypatch.setattr(tg_module, "tg_client", mock_tg_ctor)

    success, message = await client_instance.setup()

    assert success is False
    assert message == "Invalid phone number."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error, expected_message",
    [
        (tg_module.PhoneCodeInvalidError(request=None), "Invalid code."),
        (tg_module.PhoneCodeEmptyError(request=None), "Empty code."),
        (tg_module.SendCodeUnavailableError(request=None), "Failed to send code. Please try again later."),
    ],
)
async def test_setup_returns_error_on_code_failures(client_instance, monkeypatch, error, expected_message):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.is_user_authorized = AsyncMock(return_value=False)
    mock_client.send_code_request = AsyncMock()
    mock_client.sign_in = AsyncMock(side_effect=error)
    mock_tg_ctor = MagicMock(return_value=mock_client)
    monkeypatch.setattr(tg_module, "tg_client", mock_tg_ctor)
    monkeypatch.setattr(tg_module.Prompt, "ask", Mock(return_value="123456"))

    success, message = await client_instance.setup()

    assert success is False
    assert message == expected_message


@pytest.mark.asyncio
async def test_setup_uses_password_when_2fa_required(client_instance, mock_credentials, monkeypatch):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.is_user_authorized = AsyncMock(return_value=False)
    mock_client.send_code_request = AsyncMock()
    mock_client.sign_in = AsyncMock(side_effect=[tg_module.SessionPasswordNeededError(request=None), None])
    mock_tg_ctor = MagicMock(return_value=mock_client)
    monkeypatch.setattr(tg_module, "tg_client", mock_tg_ctor)

    prompt_values = iter(["123456", "secret_password"])
    monkeypatch.setattr(tg_module.Prompt, "ask", Mock(side_effect=lambda _msg: next(prompt_values)))

    success, message = await client_instance.setup()

    assert success is True
    assert message == "Telegram client setup successfully!"
    assert mock_client.sign_in.await_count == 2
    mock_client.sign_in.assert_any_await(phone=mock_credentials.phone_number, code="123456")
    mock_client.sign_in.assert_any_await(password="secret_password")


@pytest.mark.asyncio
async def test_get_list_dialogs_info_and_disconnect(client_instance):
    dialogs = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    me = SimpleNamespace(id=100)
    mock_client = MagicMock()
    mock_client.get_dialogs = AsyncMock(return_value=dialogs)
    mock_client.get_me = AsyncMock(return_value=me)
    mock_client.disconnect = AsyncMock()
    client_instance.client = mock_client

    got_dialogs = await client_instance.get_list_dialogs()
    got_me = await client_instance.info()
    await client_instance.disconnect()

    assert got_dialogs == dialogs
    assert got_me == me
    mock_client.disconnect.assert_awaited_once()


def test_calculate_stats_service_message_and_text_url_entity(client_instance):
    stats = ChatStats()
    message = SimpleNamespace(
        text="",
        media=MessageMediaWebPage(webpage=SimpleNamespace()),
        file=None,
        sticker=False,
        gif=False,
        photo=False,
        video_note=False,
        video=False,
        voice=False,
        audio=False,
        document=False,
        entities=[MessageEntityTextUrl(offset=0, length=4, url="https://example.com")],
    )

    client_instance._calculate_stats(stats, message)

    assert stats.total.count == 1
    assert stats.service == 1
    assert stats.links == 1


@pytest.mark.asyncio
async def test_export_chat_downloads_new_media_and_saves_history(client_instance, tmp_path):
    text_dir = tmp_path / "Text"
    info_dir = tmp_path / "Info"
    photos_dir = tmp_path / "Photos"
    for path in [text_dir, info_dir, photos_dir]:
        path.mkdir(parents=True, exist_ok=True)

    paths = {
        "text": str(text_dir),
        "info": str(info_dir),
        "photos": str(photos_dir),
        "stickers": str(tmp_path / "Stickers"),
        "gifs": str(tmp_path / "GIFs"),
        "rounds": str(tmp_path / "Rounds"),
        "videos": str(tmp_path / "Videos"),
        "audio": str(tmp_path / "Audio"),
        "docs": str(tmp_path / "Docs"),
    }

    message = SimpleNamespace(
        id=7,
        date="2026-01-01",
        text="photo message",
        sender_id=10,
        media=object(),
        file=SimpleNamespace(size=50),
        sticker=False,
        gif=False,
        photo=True,
        video_note=False,
        video=False,
        voice=False,
        audio=False,
        document=False,
        entities=None,
    )

    mock_client = MagicMock()
    mock_client.get_messages = AsyncMock(return_value=SimpleNamespace(total=1))
    mock_client.iter_messages = MagicMock(return_value=_async_iter([message]))
    mock_client.download_media = AsyncMock(return_value=str(photos_dir / "7_.jpg"))
    client_instance.client = mock_client
    client_instance._save_chat_info = AsyncMock()

    progress_callback = AsyncMock()
    exported = await client_instance.export_chat(SimpleNamespace(id=1), paths, progress_callback)

    assert exported == 1
    mock_client.download_media.assert_awaited_once()
    progress_callback.assert_awaited_once_with(1, 1)


@pytest.mark.asyncio
async def test_export_chat_uses_existing_media_and_handles_non_media_message(client_instance, tmp_path):
    text_dir = tmp_path / "Text"
    info_dir = tmp_path / "Info"
    photos_dir = tmp_path / "Photos"
    for path in [text_dir, info_dir, photos_dir]:
        path.mkdir(parents=True, exist_ok=True)

    existing_file = photos_dir / "7_existing.jpg"
    existing_file.write_text("already here")

    paths = {
        "text": str(text_dir),
        "info": str(info_dir),
        "photos": str(photos_dir),
        "stickers": str(tmp_path / "Stickers"),
        "gifs": str(tmp_path / "GIFs"),
        "rounds": str(tmp_path / "Rounds"),
        "videos": str(tmp_path / "Videos"),
        "audio": str(tmp_path / "Audio"),
        "docs": str(tmp_path / "Docs"),
    }

    media_message = SimpleNamespace(
        id=7,
        date="2026-01-01",
        text="cached media",
        sender_id=10,
        media=object(),
        file=SimpleNamespace(size=50),
        sticker=False,
        gif=False,
        photo=True,
        video_note=False,
        video=False,
        voice=False,
        audio=False,
        document=False,
        entities=None,
    )
    plain_message = SimpleNamespace(
        id=8,
        date="2026-01-02",
        text="",
        sender_id=11,
        media=None,
        file=None,
        sticker=False,
        gif=False,
        photo=False,
        video_note=False,
        video=False,
        voice=False,
        audio=False,
        document=False,
        entities=None,
    )

    mock_client = MagicMock()
    mock_client.get_messages = AsyncMock(return_value=SimpleNamespace(total=2))
    mock_client.iter_messages = MagicMock(return_value=_async_iter([media_message, plain_message]))
    mock_client.download_media = AsyncMock()
    client_instance.client = mock_client
    client_instance._save_chat_info = AsyncMock()

    exported = await client_instance.export_chat(SimpleNamespace(id=1), paths, progress_callback=None)

    assert exported == 2
    mock_client.download_media.assert_not_called()


@pytest.mark.asyncio
async def test_export_chat_skips_download_when_target_folder_is_none(client_instance, tmp_path):
    text_dir = tmp_path / "Text"
    info_dir = tmp_path / "Info"
    text_dir.mkdir(parents=True, exist_ok=True)
    info_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "text": str(text_dir),
        "info": str(info_dir),
        "photos": str(tmp_path / "Photos"),
        "stickers": str(tmp_path / "Stickers"),
        "gifs": str(tmp_path / "GIFs"),
        "rounds": str(tmp_path / "Rounds"),
        "videos": str(tmp_path / "Videos"),
        "audio": str(tmp_path / "Audio"),
        "docs": str(tmp_path / "Docs"),
    }

    unknown_media_message = SimpleNamespace(
        id=9,
        date="2026-01-03",
        text="unknown media",
        sender_id=12,
        media=object(),
        file=SimpleNamespace(size=10),
        sticker=False,
        gif=False,
        photo=False,
        video_note=False,
        video=False,
        voice=False,
        audio=False,
        document=False,
        entities=None,
    )

    mock_client = MagicMock()
    mock_client.get_messages = AsyncMock(return_value=SimpleNamespace(total=1))
    mock_client.iter_messages = MagicMock(return_value=_async_iter([unknown_media_message]))
    mock_client.download_media = AsyncMock()
    client_instance.client = mock_client
    client_instance._save_chat_info = AsyncMock()

    exported = await client_instance.export_chat(SimpleNamespace(id=1), paths, progress_callback=None)

    assert exported == 1
    mock_client.download_media.assert_not_called()


@pytest.mark.asyncio
async def test_save_chat_info_writes_info_json_and_downloads_avatar(client_instance, tmp_path):
    info_dir = tmp_path / "Info"
    info_dir.mkdir(parents=True, exist_ok=True)
    paths = {"info": str(info_dir)}

    chat = SimpleNamespace(
        id=99,
        title="Chat title",
        first_name="First",
        last_name="Last",
        username="user_name",
        phone="123",
    )
    stats = ChatStats()
    stats.total.count = 3

    mock_client = MagicMock()
    mock_client.download_profile_photo = AsyncMock()
    client_instance.client = mock_client

    await client_instance._save_chat_info(chat, paths, stats)

    mock_client.download_profile_photo.assert_awaited_once_with(chat, file=str(info_dir / "avatar.jpg"))
    info_file = info_dir / "info.json"
    assert info_file.exists()

    loaded = tg_module.json.loads(info_file.read_text(encoding="utf-8"))
    assert loaded["about"]["id"] == 99
    assert loaded["chat_type"] == "Unknown"
    assert loaded["export_stats"]["Total Messages"][0] == 3
