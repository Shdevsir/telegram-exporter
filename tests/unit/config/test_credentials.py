import os

from src.config import Credentials


def test_credentials_load(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert os.path.exists("session") == False, "Session directory should be empty before loading credentials"
    creds = Credentials()
    assert os.path.exists("session") == True, "Session directory should be created after loading credentials"
    assert creds.api_id is None or isinstance(creds.api_id, int), "API ID should be an integer or None"
    assert creds.api_hash is None or isinstance(creds.api_hash, str), "API Hash should be a string or None"
    assert creds.phone_number is None or isinstance(creds.phone_number, str), "Phone number should be a string or None"
    assert creds.session_name is None or isinstance(creds.session_name, str), "Session name should be a string or None"


def test_credentials_cleanup(tmp_path, monkeypatch):
    session_dir = tmp_path / "session"
    if not session_dir.exists():
        session_dir.mkdir()
    test_file = session_dir / "test.session"
    test_file.write_text("data")

    monkeypatch.chdir(tmp_path)
    creds = Credentials()
    creds.cleanup()

    assert not test_file.exists()
