import asyncio
import multiprocessing
import os
import sys

from rich.prompt import IntPrompt
from rich.prompt import Prompt
from src.cli import terminal
from src.client import telegram_client
from src.log import app_logger
from src.utils import FileManager
from src.web import run_server
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
    elif ask_number == 4:
        terminal.info("Starting web server at http://localhost:5000")
        server_process = multiprocessing.Process(
            target=run_server, kwargs={"host": "127.0.0.1", "port": 5000}, daemon=True
        )
        server_process.start()

        terminal.console.print("\n[bold green]🚀 Web server started![/bold green]")
        terminal.console.print("[cyan]Address: http://localhost:5000[/cyan]")
        terminal.console.print("-" * 30)

        Prompt.ask("[bold yellow]Press Enter to stop the server and return to the menu[/bold yellow]")

        server_process.terminate()
        server_process.join()

        terminal.console.print("[bold red]❌ Web server stopped.[/bold red]\n")
    elif ask_number == 5:
        terminal.info("Exiting the application...")
    else:
        terminal.error("Invalid choice. Please enter a number between 1 and 5.")


async def main() -> None:
    await setup()
    ask = 0
    dialogs = await telegram_client.get_list_dialogs()
    while ask != 5:
        terminal.print_choices()
        ask = IntPrompt.ask("Enter the number with action what you want to do", default=5)
        await choicer(ask, dialogs)
    terminal.clear()
    terminal.success("Exiting the application. Goodbye!")


if __name__ == "__main__":
    try:
        os.environ["LOGGER"] = "Create"
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        app_logger.warning("Application stopped by user interruption.")
        terminal.clear()
        terminal.warning("\n[!] Execution interrupted by user. Closing safely...")
        sys.exit(0)
