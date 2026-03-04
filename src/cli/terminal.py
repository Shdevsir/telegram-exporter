from rich.console import Console
from rich.progress import BarColumn
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TextColumn
from rich.prompt import IntPrompt
from rich.prompt import Prompt
from rich.prompt import PromptBase
from rich.table import Table
from telethon.tl.custom import Dialog

from src.config.credentials import credentials
from src.config.env_generator import env_generator
from src.log.logger import app_logger
from src.schemas.stats import ChatStats


class Terminal:
    def __init__(self) -> None:
        self.console = Console()

    def error(self, message: str) -> None:
        """Prints an error message in bold red style."""
        self.console.print(message, style="bold red")

    def info(self, message: str) -> None:
        """Prints an informational message in the default console style."""
        self.console.print(message)

    def success(self, message: str) -> None:
        """Prints a success message in bold green style."""
        self.console.print(message, style="bold green")

    def warning(self, message: str) -> None:
        """Prints a warning message in bold yellow style."""
        self.console.print(message, style="bold yellow")

    def setup(self) -> None:
        """
        This method checks if the necessary credentials are available.
        If not, it prompts the user to input them and saves them to the .env file.
        """
        self.success("Welcome to Telegram Exporter!")

        fields: list[tuple[str, str, str, type[PromptBase]]] = [
            ("API ID", "API_ID_TELEGRAM", "API ID is missing", IntPrompt),
            ("API Hash", "API_HASH_TELEGRAM", "API Hash is missing", Prompt),
            ("Phone Number", "PHONE_NUMBER_TELEGRAM", "Phone number is missing", Prompt),
            ("Session Name", "SESSION_NAME_TELEGRAM", "Session name is missing", Prompt),
        ]
        needs_reload = False

        for attr, env_name, error_msg, prompt_cls in fields:
            if not getattr(credentials, attr.lower().replace(" ", "_")):
                self.error(f"{error_msg}. Please enter your {attr}:")

                if attr == ("API ID", "API HASH"):
                    self.warning(f"You can generate {attr} at https://my.telegram.org/apps")
                value = prompt_cls.ask(attr)
                env_generator.add_variable(env_name, value)
                needs_reload = True

        if needs_reload:
            credentials.load()

    def cleanup(self) -> None:
        """Cleans up resources by clearing the console and removing session files and environment variables."""
        self.error("Cleaning up resources...")
        env_generator.cleanup()
        credentials.cleanup()

    def clear(self) -> None:
        """Clears the console screen to provide a clean interface for the user."""
        self.console.clear()

    def get_dialog_type(self, dialog: Dialog) -> str:
        """Determines the type of a dialog (User, Group, Channel) based on its properties."""
        if dialog.is_user:
            return "User"
        elif dialog.is_group:
            return "Group"
        elif dialog.is_channel:
            return "Channel"
        else:
            return "Unknown"

    def get_dialog_table(self, dialogs_slice: list[Dialog], start_idx: int, total: int) -> Table:
        """Creates a rich Table object to display a slice of dialogs with their index, title, and type."""
        table = Table(
            title=f"Telegram Dialogs (Show {start_idx + 1}-{start_idx + len(dialogs_slice)} з {total})",
            title_style="bold blue",
        )
        table.add_column("№", style="cyan", min_width=4)
        table.add_column("Title", style="magenta", min_width=70)
        table.add_column("Type", style="magenta", min_width=10)
        for idx, dialog in enumerate(dialogs_slice):
            dialog_type = self.get_dialog_type(dialog)
            name = dialog.name if dialog.name else "Deleted Account"
            table.add_row(str(start_idx + idx), name, dialog_type)
        return table

    def show_dialogs(self, dialogs: list[Dialog]) -> None:
        """
        Displays the list of dialogs in a paginated format,
        allowing the user to navigate through the dialogs in chunks of 10.
        """
        page_size = 10
        current_index = 0
        total = len(dialogs)

        while current_index < total:
            end_index = min(current_index + page_size, total)
            dialogs_slice = dialogs[current_index:end_index]

            table = self.get_dialog_table(dialogs_slice, current_index, total)

            self.console.clear()
            self.console.print(table)

            if end_index >= total:
                self.info("This is the end of the list.")
                break

            choice = Prompt.ask("\nDo you want to see the next set of dialogs?", choices=["y", "n", "all"], default="y")

            if choice == "y":
                current_index += page_size
            elif choice == "all":
                page_size = total
                current_index += 0
            else:
                break

    def show_statistics(self, chat_name: str, stats: ChatStats, duration: float) -> None:
        """
        Displays the collected statistics for a chat in a formatted table, including total messages, text/captions,
        media types, and the time taken for analysis.
        """
        app_logger.debug(
            f"Displaying statistics for chat: {chat_name} with stats: {stats} and duration: {duration:.2f} seconds"
        )
        self.clear()
        table = Table(title=f"Statistics for: {chat_name}", title_style="bold magenta", show_footer=True)
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Size (MB/GB)", style="green", footer=stats.total.formatted_size)

        for key, (count, size) in stats.to_dict().items():
            if key != "Total Messages":  # Skip total messages since it's already in the footer
                continue
            table.add_row(key, str(count), size)

        self.console.print(table)
        self.success(f"\n✅ Analysis {stats.total.count} messages completed in {duration:.2f} seconds.")

    def get_progress_bar(self) -> Progress:
        """Creates and returns a rich Progress object configured."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            TextColumn("{task.percentage:>3.0f}%", style="yellow"),
            TextColumn("[bold blue]{task.completed}[/bold blue] messages processed"),
            console=self.console,
            transient=True,
        )

    def print_choices(self) -> None:
        """Prints the available actions that the user can perform."""
        self.info("\nAvailable actions:")
        self.info("1. Show dialogs")
        self.info("2. Show chat statistics")
        self.info("3. Export chat")
        self.info("4. Exit\n")


terminal = Terminal()

__all__ = ["terminal"]
