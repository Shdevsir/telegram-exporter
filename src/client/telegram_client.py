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

from src.config import credentials
from src.log import app_logger
from src.schemas import ChatStats

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

    def _calculate_stats(self, stats: ChatStats, message: Message) -> None:
        stats.total.count += 1
        stats.total.size += len(message.text.encode("utf-8")) if message.text else 0

        if message.text:
            stats.text.count += 1
            stats.text.size += len(message.text.encode("utf-8"))

        if message.media and not isinstance(message.media, MessageMediaWebPage):
            file_size = message.file.size if message.file else 0
            stats.total.size += file_size

            media_map = {
                "sticker": stats.stickers,
                "gif": stats.gifs,
                "photo": stats.photos,
                "video_note": stats.rounds,
                "video": stats.videos,
                "voice": stats.voice,
                "audio": stats.audios,
                "document": stats.files,
            }

            for attr, stat_key in media_map.items():
                if getattr(message, attr, None):
                    stat_key.count += 1
                    stat_key.size += file_size
                    break

        elif not message.text:
            stats.service += 1

        if message.entities:
            if any(isinstance(e, (MessageEntityUrl, MessageEntityTextUrl)) for e in message.entities):
                stats.links += 1

    async def get_chat_statistics(
        self, chat: User | Chat | Channel, total_count: int | None, progress_callback: ProgressCallbackType | None
    ) -> tuple[ChatStats, float]:
        """
        Analyzes the messages in a chat and collects various statistics such as total messages, text/captions,
        media types, etc."""
        stats = ChatStats()

        start_time = time.perf_counter()

        async for message in self.client.iter_messages(chat):
            self._calculate_stats(stats, message)

            if progress_callback and (stats.total.count % 50 == 0 or stats.total.count == total_count):
                await progress_callback(stats.total.count, total_count)

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
        stats = ChatStats()
        total_messages = (await self.client.get_messages(chat, limit=0)).total

        history_file = os.path.join(paths["text"], "history.json")
        history_data = []

        async for message in self.client.iter_messages(chat):
            exported_count += 1

            self._calculate_stats(stats, message)

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

        await self._save_chat_info(chat, paths, stats)

        return exported_count

    async def _save_chat_info(self, chat: User | Chat | Channel, paths: dict[str, str], stats: ChatStats) -> None:
        """Stores metadata about the chat, including basic information and export statistics, in a JSON file."""
        info_path = paths["info"]

        await self.client.download_profile_photo(chat, file=os.path.join(info_path, "avatar.jpg"))

        chat_info = {
            "about": {
                "id": chat.id,
                "title": getattr(chat, "title", None),
                "first_name": getattr(chat, "first_name", None),
                "last_name": getattr(chat, "last_name", None),
                "username": getattr(chat, "username", None),
                "phone": getattr(chat, "phone", None),
            },
            "export_stats": stats.to_dict(),
            "exported_at": str(time.ctime()),
            "chat_type": self._get_chat_type(chat),
        }

        with open(os.path.join(info_path, "info.json"), "w", encoding="utf-8") as file:
            json.dump(chat_info, file, ensure_ascii=False, indent=4)

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

    def _get_chat_type(self, chat: User | Chat | Channel) -> str:
        """Determines the type of a chat entity (User, Group, Channel) based on its properties."""
        entity_type = "Unknown"
        if isinstance(chat, User):
            entity_type = "User (Private Chat)"
        elif isinstance(chat, Chat):
            entity_type = "Group"
        elif isinstance(chat, Channel):
            # In Telethon style channel and supergroup are both
            if getattr(chat, "broadcast", False):
                entity_type = "Channel"
            else:
                entity_type = "Supergroup (Large Group)"
        return entity_type
