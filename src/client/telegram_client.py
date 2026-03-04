import json
import os
import time
from collections.abc import Awaitable
from collections.abc import Callable

from rich.prompt import Prompt
from telethon import TelegramClient as tg_client
from telethon.errors import SessionPasswordNeededError
from telethon.errors.rpcerrorlist import ApiIdInvalidError
from telethon.errors.rpcerrorlist import PhoneCodeEmptyError
from telethon.errors.rpcerrorlist import PhoneCodeInvalidError
from telethon.errors.rpcerrorlist import PhoneNumberInvalidError
from telethon.errors.rpcerrorlist import SendCodeUnavailableError
from telethon.tl.custom import Dialog
from telethon.tl.custom import Message
from telethon.tl.types import Channel
from telethon.tl.types import Chat
from telethon.tl.types import MessageEntityTextUrl
from telethon.tl.types import MessageEntityUrl
from telethon.tl.types import MessageMediaWebPage
from telethon.tl.types import User

from src.config.credentials import credentials
from src.log.logger import app_logger

ProgressCallbackType = Callable[[int, int | None], Awaitable[None]]


class TelegramClient:
    def __init__(self) -> None:
        self.client: tg_client = None

    async def setup(self) -> tuple[bool, str]:
        """
        This method connects to the Telegram client and handles the authentication process.
        If the user is not authorized, it sends a code request to the user's phone number and prompts them to enter
        the code. If two-step verification is enabled, it also prompts for the password.
        """
        try:
            self.client = tg_client(f"session/{credentials.session_name}", credentials.api_id, credentials.api_hash)
            await self.client.connect()
            if not await self.client.is_user_authorized():
                await self.client.send_code_request(phone=credentials.phone_number)
            else:
                return True, "Telegram client is already authorized."
        except ApiIdInvalidError:
            return False, "Invalid API ID or API Hash."
        except PhoneNumberInvalidError:
            return False, "Invalid phone number."
        try:
            code = Prompt.ask("Enter the code you received from Telegram")
            await self.client.sign_in(phone=credentials.phone_number, code=code)
        except PhoneCodeInvalidError:
            return False, "Invalid code."
        except PhoneCodeEmptyError:
            return False, "Empty code."
        except SendCodeUnavailableError:
            return False, "Failed to send code. Please try again later."
        except SessionPasswordNeededError:
            password = Prompt.ask("Two-step verification is enabled. Please enter your password")
            await self.client.sign_in(password=password)
        return True, "Telegram client setup successfully!"

    async def get_list_dialogs(self) -> list[Dialog]:
        """Fetches the list of dialogs (chats) from the Telegram client."""
        dialogs: list[Dialog] = await self.client.get_dialogs()
        return dialogs

    async def info(self) -> User:
        """Retrieves information about the currently logged-in user."""
        me = await self.client.get_me()
        return me

    async def get_messages_count(self, chat: User | Chat | Channel) -> int | None:
        count = await self.client.get_messages(chat, limit=1)
        app_logger.debug(count)
        if count.total >= 2147483647:
            app_logger.debug("Enter")
            if hasattr(chat, "message") and hasattr(chat.message, "id"):
                app_logger.debug(chat.message.id)
                return int(chat.message.id)
            app_logger.debug("Exit")
            return None
        return int(count.total)

    def _calculate_stats(self, stats: dict[str, list[int]], message: Message) -> None:
        stats["Total Messages"][0] += 1

        msg_text_size = len(message.text.encode("utf-8")) if message.text else 0
        stats["Total Messages"][1] += msg_text_size

        if message.text:
            stats["Text/Captions"][0] += 1
            stats["Text/Captions"][1] += msg_text_size

        if message.media:
            file_size = message.file.size if message.file else 0
            stats["Total Messages"][1] += file_size

            media_map = {
                "sticker": "Stickers",
                "gif": "GIFs",
                "photo": "Photos",
                "video": "Videos",
                "voice": "Voice Messages",
                "video_note": "Video Notes (Rounds)",
                "audio": "Audios",
                "document": "Files/Docs",
            }

            for attr, stat_key in media_map.items():
                if getattr(message, attr, None):
                    stats[stat_key][0] += 1
                    stats[stat_key][1] += file_size
                    break

        elif not message.text:
            stats["Service Messages"][0] += 1

        if message.entities:
            if any(isinstance(e, (MessageEntityUrl, MessageEntityTextUrl)) for e in message.entities):
                stats["Links"][0] += 1

    async def get_chat_statistics(
        self, chat: User | Chat | Channel, total_count: int | None, progress_callback: ProgressCallbackType | None
    ) -> tuple[dict[str, list[int]], float]:
        """
        Analyzes the messages in a chat and collects various statistics such as total messages, text/captions,
        media types, etc."""
        stats = {
            "Total Messages": [0, 0],
            "Text/Captions": [0, 0],
            "Photos": [0, 0],
            "Videos": [0, 0],
            "Voice Messages": [0, 0],
            "Video Notes (Rounds)": [0, 0],
            "Audios": [0, 0],
            "Files/Docs": [0, 0],
            "Links": [0, 0],
            "Service Messages": [0, 0],
            "Stickers": [0, 0],
            "GIFs": [0, 0],
        }

        start_time = time.perf_counter()

        async for message in self.client.iter_messages(chat):
            self._calculate_stats(stats, message)

            if progress_callback and (
                stats["Total Messages"][0] % 50 == 0 or stats["Total Messages"][0] == total_count
            ):
                await progress_callback(stats["Total Messages"][0], total_count)

        end_time = time.perf_counter()
        duration = end_time - start_time

        return stats, duration

    async def disconnect(self) -> None:
        """Disconnects the Telegram client session."""
        await self.client.disconnect()

    async def export_chat(
        self, chat: User | Chat | Channel, paths: dict, progress_callback: ProgressCallbackType | None
    ) -> int:
        """
        Exports the messages from a chat, including downloading media files and saving message history in JSON format.
        """
        exported_count = 0
        total_messages = (await self.client.get_messages(chat, limit=0)).total

        history_file = os.path.join(paths["text"], "history.json")
        history_data = []

        async for message in self.client.iter_messages(chat):
            exported_count += 1

            msg_entry = {
                "id": message.id,
                "date": str(message.date),
                "text": message.text or "",
                "sender_id": message.sender_id,
                "media": None,
            }

            if message.media and not isinstance(message.media, MessageMediaWebPage):
                target_folder = self._get_target_folder(message, paths)

                # Create a unique file prefix based on message ID to avoid collisions
                if target_folder:
                    file_prefix = f"{message.id}_"

                    # Check if a file with the same prefix already exists in the target folder
                    existing_files = os.listdir(target_folder)
                    already_downloaded = any(f.startswith(file_prefix) for f in existing_files)

                    if not already_downloaded:
                        path_template = os.path.join(target_folder, file_prefix)
                        downloaded_path = await self.client.download_media(message, file=path_template)
                        msg_entry["media"] = downloaded_path
                        app_logger.info(f"Successfully migrated media: ID {message.id} to {downloaded_path}")
                    else:
                        app_logger.debug(f"Skipped media (already exists): ID {message.id}")
                        for f in existing_files:
                            if f.startswith(file_prefix):
                                msg_entry["media"] = os.path.join(target_folder, f)
                                break

            history_data.append(msg_entry)

            if progress_callback and (exported_count % 5 == 0 or exported_count == total_messages):
                await progress_callback(exported_count, total_messages)

        with open(history_file, "w", encoding="utf-8") as file:
            json.dump(history_data, file, ensure_ascii=False, indent=4)

        return exported_count

    def _get_target_folder(self, message: Message, paths: dict[str, str]) -> str | None:
        """Determines the appropriate folder for downloading media based on the message's media type."""
        if message.sticker:
            return paths["stickers"]
        if message.gif:
            return paths["gifs"]
        if message.photo:
            return paths["photos"]
        if message.video_note:
            return paths["rounds"]
        if message.video:
            return paths["videos"]
        if message.audio or message.voice:
            return paths["audio"]
        if message.document:
            return paths["docs"]

        return None


telegram_client = TelegramClient()

__all__ = ["telegram_client"]
