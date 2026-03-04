import asyncio
import sys

from rich.prompt import IntPrompt
from src.cli.terminal import terminal
from src.client.telegram_client import telegram_client
from src.log.logger import app_logger
from src.utils.file_manager import FileManager
from telethon.tl.custom import Dialog


async def setup() -> None:
    """Initializes the Telegram client and handles the authentication process."""
    terminal.setup()
    status, message = await telegram_client.setup()
    if status:
        info = await telegram_client.info()
        terminal.success(f"Logged in as: {info.first_name} {info.last_name} (@{info.username})")
        terminal.success(message)
    else:
        terminal.error(f"Telegram client setup failed: {message}")
        terminal.cleanup()


async def choicer(ask_number: int, dialogs: list[Dialog]) -> None:
    """Handles the user's choice and performs the corresponding action based on the input number."""
    if ask_number == 1:
        terminal.show_dialogs(dialogs)
    elif ask_number == 2:
        chat_idx = IntPrompt.ask("Enter the № of the chat you want to analyze")
        if 0 <= chat_idx < len(dialogs):
            target_chat = dialogs[chat_idx]
            terminal.info(f"Starting analysis of [bold]{target_chat.name}...")
            total_messages = await telegram_client.get_messages_count(target_chat)
            with terminal.get_progress_bar() as progress:
                task = progress.add_task("Analyzing messages...", total=total_messages)

                async def update_progress(current: int, total: int | None) -> None:
                    progress.update(task, completed=current, total=total)

                stats, duration = await telegram_client.get_chat_statistics(
                    target_chat, total_messages, update_progress
                )

            terminal.show_statistics(target_chat.name, stats, duration)
        else:
            terminal.error("Invalid chat number.")

    elif ask_number == 3:
        chat_idx = IntPrompt.ask("Choose the № of the chat you want to export")

        if 0 <= chat_idx < len(dialogs):
            target_chat = dialogs[chat_idx]

            paths = FileManager.prepare_export_path(target_chat.name, target_chat.id)
            terminal.info(f"📁 Folders created in: {paths['base']}")

            total_to_export = await telegram_client.get_messages_count(target_chat)

            with terminal.get_progress_bar() as progress:
                task = progress.add_task("[bold cyan]Downloading data...", total=total_to_export)

                async def update_progress(current: int, total: int | None) -> None:
                    progress.update(task, completed=current, total=total)

                count = await telegram_client.export_chat(target_chat, paths, update_progress)

            terminal.success(f"✅ Export completed! Processed {count} messages.")
            terminal.info(f"Text history: {paths['text']}/history.json")
    else:
        terminal.error("Invalid choice. Please enter a number between 1 and 9.")


async def main() -> None:
    await setup()
    ask = 0
    dialogs = await telegram_client.get_list_dialogs()
    while ask != 4:
        terminal.print_choices()
        # try:
        ask = IntPrompt.ask("Enter the number with action what you want to do", default=4)
        # except EOFError:
        #     terminal.error("No input detected. Exiting the application.")
        #     break
        await choicer(ask, dialogs)
    terminal.clear()
    terminal.success("Exiting the application. Goodbye!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        app_logger.warning("Application stopped by user interruption.")
        terminal.clear()
        terminal.warning("\n[!] Execution interrupted by user. Closing safely...")
        sys.exit(0)
