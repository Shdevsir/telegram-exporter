from dotenv import load_dotenv
import os


class Credentials:
    def __init__(self) -> None:
        load_dotenv()
        if not os.path.exists("session"):
            os.makedirs("session")
        self.api_id = int(os.getenv("API_ID_TELEGRAM")) if os.getenv("API_ID_TELEGRAM") else None
        self.api_hash = os.getenv("API_HASH_TELEGRAM")
        self.phone_number = os.getenv("PHONE_NUMBER_TELEGRAM")
        self.session_name = os.getenv("SESSION_NAME_TELEGRAM")

    def cleanup(self) -> None:
        for filename in os.listdir("session"):
            file_path = os.path.join("session", filename)
            if os.path.isfile(file_path):
                os.remove(file_path)


credentials = Credentials()

__all__ = ["credentials"]
