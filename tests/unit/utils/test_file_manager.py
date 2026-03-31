import os
import shutil

from src.utils import FileManager


def test_format_size():
    assert FileManager.format_size(0) == "0 B"
    assert FileManager.format_size(500) == "500.0 B"
    assert FileManager.format_size(1024) == "1.0 KB"
    assert FileManager.format_size(1048576) == "1.0 MB"
    assert FileManager.format_size(1073741824) == "1.0 GB"
    assert FileManager.format_size(1099511627776) == "1.0 TB"


def test_prepare_export_path():
    chat_name = "Test Chat"
    chat_id = 12345
    expected_base = "telegram_data/Test_Chat_12345"

    paths = FileManager.prepare_export_path(chat_name, chat_id)

    assertion_data = {
        "text": f"{expected_base}/Text",
        "photos": f"{expected_base}/Files/Photos",
        "videos": f"{expected_base}/Files/Videos",
        "audio": f"{expected_base}/Files/Audio",
        "rounds": f"{expected_base}/Files/Round_Messages",
        "docs": f"{expected_base}/Files/Documents",
        "stickers": f"{expected_base}/Files/Stickers",
        "gifs": f"{expected_base}/Files/GIFs",
        "info": f"{expected_base}/Info",
        "base": expected_base,
    }
    for key, expected_path in assertion_data.items():
        assert paths[key] == expected_path, f"Path for {key} not match. Got: {paths[key]}, Expected: {expected_path}"
        assert os.path.exists(paths[key]), f"Directory for {key} was not created at: {paths[key]}"
    if os.path.exists(expected_base):
        shutil.rmtree(expected_base)
