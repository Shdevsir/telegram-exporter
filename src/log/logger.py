import logging
import os
from datetime import datetime
from pathlib import Path


class Logger:
    def __init__(self, name: str = "telegram_exporter") -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        if not os.environ.get("LOGGER"):
            if not self.logger.handlers:
                self.logger.addHandler(logging.NullHandler())
            return

        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
        log_file = log_dir / f"{timestamp}.log"

        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            self.logger.addHandler(file_handler)

    def info(self, message: str) -> None:
        self.logger.info(message)

    def error(self, message: str) -> None:
        self.logger.error(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def debug(self, message: str) -> None:
        self.logger.debug(message)
