from pathlib import Path

class EnvGenerator:
    def __init__(self):
        Path(".env").touch(exist_ok=True)
    
    def add_variable(self, key: str, value: str) -> None:
        with open(".env", "a") as env_file:
            env_file.write(f"{key}={value}\n")
    
    def cleanup(self) -> None:
        with open(".env", "w") as env_file:
            env_file.write("")


env_generator = EnvGenerator()

__all__ = ["env_generator"]
