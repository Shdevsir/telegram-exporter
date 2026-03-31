import json
import logging
import math
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from typing import cast

from flask import abort
from flask import Flask
from flask import render_template
from flask import request
from flask import send_from_directory
from flask.typing import ResponseReturnValue

from src.log import app_logger


class LoggerWriter:
    """A helper class to redirect Flask's internal logs to the application's logger."""

    def __init__(self, level: Callable[[str], None]) -> None:
        self.level = level

    def write(self, message: str) -> None:
        if message.strip():
            self.level(message.strip())

    def flush(self) -> None:
        pass


BASE_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR), static_url_path="/static"
)


log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)
EXPORT_DIR = os.path.abspath("telegram_data")


def _load_json(path: str) -> dict[Any, Any] | list[Any]:
    try:
        with open(path, encoding="utf-8") as file:
            loaded = json.load(file)
            return cast(dict[Any, Any] | list[Any], loaded)
    except (json.JSONDecodeError, OSError):
        return {}


def _resolve_media_url(chat_id: str, media_path: str | None) -> str | None:
    if not media_path:
        return None

    normalized = media_path.replace("\\", "/")
    marker = f"{chat_id}/"
    if marker in normalized:
        normalized = normalized.split(marker, 1)[1]
    return f"/media/{chat_id}/{normalized}"


def _detect_media_kind(media_path: str | None) -> str | None:
    if not media_path:
        return None

    normalized = media_path.replace("\\", "/").lower()
    if "/photos/" in normalized or "/stickers/" in normalized:
        return "image"
    if "/videos/" in normalized:
        return "video"
    if "/round_messages/" in normalized:
        return "round"
    if "/audio/" in normalized:
        return "audio"
    if "/gifs/" in normalized:
        return "gif"
    return "file"


def _build_display_messages(chat_id: str, raw_messages: list[dict]) -> list[dict]:
    prepared = []
    for msg in raw_messages:
        media_path = msg.get("media")
        media_url = _resolve_media_url(chat_id, media_path)
        date_str = str(msg.get("date", ""))
        time_text = ""
        if " " in date_str:
            time_text = date_str.split(" ", 1)[1][:5]

        prepared.append(
            {
                "id": msg.get("id"),
                "text": msg.get("text", ""),
                "date": date_str,
                "time_text": time_text,
                "sender_id": msg.get("sender_id"),
                "media_path": media_path,
                "media_url": media_url,
                "media_kind": _detect_media_kind(media_path),
            }
        )
    return prepared


def _scan_chats() -> list[dict[str, str | None]]:
    chats: list[dict[str, str | None]] = []
    if not os.path.exists(EXPORT_DIR):
        return chats

    for dirname in os.listdir(EXPORT_DIR):
        chat_path = os.path.join(EXPORT_DIR, dirname)
        if not os.path.isdir(chat_path):
            continue

        info_path = os.path.join(chat_path, "Info", "info.json")
        info_data = _load_json(info_path) if os.path.exists(info_path) else {}
        about = info_data.get("about", {}) if isinstance(info_data, dict) else {}

        first_name = about.get("first_name")
        last_name = about.get("last_name")
        full_name = " ".join(part for part in [first_name, last_name] if part)
        display_name = about.get("title") or full_name or dirname

        chats.append(
            {
                "id": dirname,
                "name": display_name,
                "type": info_data.get("chat_type", "Unknown") if isinstance(info_data, dict) else "Unknown",
                "username": about.get("username"),
            }
        )

    chats.sort(key=lambda x: str(x["name"]).lower())
    return chats


def _paginate(items: list[Any], page: int, per_page: int) -> dict[str, Any]:
    total_items = len(items)
    total_pages = max(1, math.ceil(total_items / per_page))
    current_page = min(max(1, page), total_pages)

    start_idx = (current_page - 1) * per_page
    end_idx = start_idx + per_page
    return {
        "items": items[start_idx:end_idx],
        "current_page": current_page,
        "per_page": per_page,
        "total_pages": total_pages,
        "total_items": total_items,
    }


@app.route("/")
def index() -> str:
    """List all archived chats with pagination."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 12, type=int)
    per_page = 12 if per_page <= 0 else min(per_page, 100)

    all_chats = _scan_chats()
    page_data = _paginate(all_chats, page, per_page)

    return cast(
        str,
        render_template(
            "index.html",
            chats=page_data["items"],
            current_page=page_data["current_page"],
            per_page=page_data["per_page"],
            total_pages=page_data["total_pages"],
            total_chats=page_data["total_items"],
        ),
    )


@app.route("/media/<chat_id>/<path:filename>")
def serve_media(chat_id: str, filename: str) -> ResponseReturnValue:
    """Serve media files for a specific chat safely."""
    clean_filename = filename.split(f"{chat_id}/", 1)[-1]
    chat_path = os.path.join(EXPORT_DIR, chat_id)

    if not os.path.isdir(chat_path):
        abort(404)

    resolved = os.path.realpath(os.path.join(chat_path, clean_filename))
    if not resolved.startswith(os.path.realpath(chat_path)) or not os.path.exists(resolved):
        abort(404)

    return send_from_directory(chat_path, clean_filename)


@app.route("/chat/<chat_id>")
def view_chat(chat_id: str) -> str:
    """View a paginated chat history by chat id."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = 20 if per_page <= 0 else min(per_page, 100)

    chat_path = os.path.join(EXPORT_DIR, chat_id)
    history_path = os.path.join(chat_path, "Text", "history.json")
    info_path = os.path.join(chat_path, "Info", "info.json")

    if not os.path.exists(history_path):
        abort(404)

    history_data = _load_json(history_path)
    if not isinstance(history_data, list):
        history_data = []

    info_raw = _load_json(info_path) if os.path.exists(info_path) else {}
    if not isinstance(info_raw, dict):
        info_raw = {}

    info = {
        "about": info_raw.get("about", {}),
        "chat_type": info_raw.get("chat_type", "Unknown"),
        "exported_at": info_raw.get("exported_at", ""),
        "export_stats": info_raw.get("export_stats", {}),
    }

    prepared_messages = _build_display_messages(chat_id, history_data)
    page_data = _paginate(prepared_messages, page, per_page)

    all_chats = _scan_chats()
    selected_chat = next((chat for chat in all_chats if chat["id"] == chat_id), None)

    avatar_exists = os.path.exists(os.path.join(chat_path, "Info", "avatar.jpg"))

    return cast(
        str,
        render_template(
            "chat.html",
            chat_id=chat_id,
            chat=selected_chat,
            messages=page_data["items"],
            info=info,
            avatar_exists=avatar_exists,
            current_page=page_data["current_page"],
            per_page=page_data["per_page"],
            total_pages=page_data["total_pages"],
            total_messages=page_data["total_items"],
            chat_menu=all_chats,
        ),
    )


def run_server(host: str = "localhost", port: int = 5000) -> None:
    sys.stdout = LoggerWriter(app_logger.info)
    sys.stderr = LoggerWriter(app_logger.error)
    app.run(host=host, port=port, debug=False, use_reloader=False)
