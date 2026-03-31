import logging
import uuid

from src.log.logger import Logger


def _clear_logger(name: str) -> None:
    logger = logging.getLogger(name)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def test_logger_without_env_uses_null_handler(monkeypatch):
    monkeypatch.delenv("LOGGER", raising=False)
    name = f"test_logger_no_env_{uuid.uuid4().hex}"

    _clear_logger(name)
    logger_wrapper = Logger(name)

    assert logger_wrapper.logger.level == logging.DEBUG
    assert len(logger_wrapper.logger.handlers) == 1
    assert isinstance(logger_wrapper.logger.handlers[0], logging.NullHandler)

    _clear_logger(name)


def test_logger_without_env_does_not_add_duplicate_handler(monkeypatch):
    monkeypatch.delenv("LOGGER", raising=False)
    name = f"test_logger_no_env_dupe_{uuid.uuid4().hex}"

    _clear_logger(name)
    first = Logger(name)
    second = Logger(name)

    assert len(first.logger.handlers) == 1
    assert len(second.logger.handlers) == 1
    assert isinstance(second.logger.handlers[0], logging.NullHandler)

    _clear_logger(name)


def test_logger_with_env_creates_file_handler_and_logs_messages(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGGER", "1")
    monkeypatch.chdir(tmp_path)
    name = f"test_logger_env_{uuid.uuid4().hex}"

    _clear_logger(name)
    logger_wrapper = Logger(name)

    assert logger_wrapper.logger.level == logging.DEBUG
    assert len(logger_wrapper.logger.handlers) == 1
    file_handler = logger_wrapper.logger.handlers[0]
    assert isinstance(file_handler, logging.FileHandler)
    assert file_handler.level == logging.DEBUG

    logger_wrapper.info("info message")
    logger_wrapper.error("error message")
    logger_wrapper.warning("warning message")
    logger_wrapper.debug("debug message")

    for handler in logger_wrapper.logger.handlers:
        handler.flush()

    log_files = list((tmp_path / "logs").glob("*.log"))
    assert len(log_files) == 1
    content = log_files[0].read_text(encoding="utf-8")
    assert "[INFO]" in content
    assert "[ERROR]" in content
    assert "[WARNING]" in content
    assert "[DEBUG]" in content
    assert "info message" in content
    assert "error message" in content
    assert "warning message" in content
    assert "debug message" in content

    _clear_logger(name)


def test_logger_with_env_reuses_existing_handler(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGGER", "1")
    monkeypatch.chdir(tmp_path)
    name = f"test_logger_env_reuse_{uuid.uuid4().hex}"

    _clear_logger(name)
    first = Logger(name)
    first_handler = first.logger.handlers[0]
    second = Logger(name)

    assert len(second.logger.handlers) == 1
    assert second.logger.handlers[0] is first_handler

    _clear_logger(name)
