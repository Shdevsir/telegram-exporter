import os

from dotenv import load_dotenv


class Credentials:
    def __init__(self) -> None:
        self.load()

    def load(self) -> None:
        """Reloads the credentials from the .env file."""
        load_dotenv()
        if not os.path.exists("session"):
            os.makedirs("session")
        val = os.getenv("API_ID_TELEGRAM")
        self.api_id: int | None = int(val) if val else None
        self.api_hash = os.getenv("API_HASH_TELEGRAM")
        self.phone_number = os.getenv("PHONE_NUMBER_TELEGRAM")
        self.session_name = os.getenv("SESSION_NAME_TELEGRAM")

    def cleanup(self) -> None:
        """Cleans up the session files by removing all files in the 'session' directory."""
        for filename in os.listdir("session"):
            file_path = os.path.join("session", filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
