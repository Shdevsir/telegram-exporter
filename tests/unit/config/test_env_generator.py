from pathlib import Path

from src.config import EnvGenerator


def test_add_variable(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    env = EnvGenerator()
    env.add_variable("API_ID", 123)

    content = Path(".env").read_text()

    assert content == "API_ID=123\n"


def test_cleanup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    env = EnvGenerator()
    env.add_variable("TEST", "value")

    env.cleanup()

    content = Path(".env").read_text()

    assert content == ""
