import math
import os
import re


class FileManager:
    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Formats a file size in bytes into a human-readable string with appropriate units (B, KB, MB, etc.)."""
        if size_bytes == 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    @staticmethod
    def _slugify(text: str) -> str:
        """Converts a string into a slug format by removing special characters and replacing spaces with underscores."""
        return re.sub(r"[^\w\s-]", "", text).strip().replace(" ", "_")

    @staticmethod
    def prepare_export_path(chat_name: str, chat_id: int) -> dict[str, str]:
        """Prepares the directory structure for exporting chat data"""
        base_name = f"{FileManager._slugify(chat_name)}_{chat_id}"
        base_path = os.path.join("telegram_data", base_name)

        paths = {
            "base": base_path,
            "text": os.path.join(base_path, "Text"),
            "photos": os.path.join(base_path, "Files", "Photos"),
            "videos": os.path.join(base_path, "Files", "Videos"),
            "audio": os.path.join(base_path, "Files", "Audio"),
            "rounds": os.path.join(base_path, "Files", "Round_Messages"),
            "docs": os.path.join(base_path, "Files", "Documents"),
            "stickers": os.path.join(base_path, "Files", "Stickers"),
            "gifs": os.path.join(base_path, "Files", "GIFs"),
        }

        for p in paths.values():
            os.makedirs(p, exist_ok=True)

        return paths
