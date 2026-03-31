from src.schemas import ChatStats


def test_chat_stats():
    chat_stats = ChatStats().to_dict()
    expected_keys = [
        "Total Messages",
        "Text/Captions",
        "Photos",
        "Videos",
        "Voice Messages",
        "Round Videos",
        "Audios",
        "Files",
        "Stickers",
        "GIFs",
        "Links",
        "Service Messages",
    ]
    assert set(chat_stats.keys()) == set(expected_keys), "ChatStats keys do not match expected keys"
    for key, value in chat_stats.items():
        assert isinstance(value, list) and len(value) == 2, f"Value for {key} should be list of [count, formatted_size]"
        count, formatted_size = value
        assert isinstance(count, int), f"Count for {key} should be an integer"
        assert isinstance(formatted_size, str), f"Formatted size for {key} should be a string"
