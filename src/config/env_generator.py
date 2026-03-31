from pathlib import Path


class EnvGenerator:
    def __init__(self) -> None:
        Path(".env").touch(exist_ok=True)

    def add_variable(self, key: str, value: str | int) -> None:
        """Adds a key-value pair to the .env file, allowing for dynamic configuration of environment variables."""
        with open(".env", "a") as env_file:
            env_file.write(f"{key}={value}\n")

    def cleanup(self) -> None:
        """Cleans up the .env file"""
        with open(".env", "w") as env_file:
            env_file.write("")
