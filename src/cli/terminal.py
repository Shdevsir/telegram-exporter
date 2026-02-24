from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.table import Table
from src.config.credentials import credentials
from src.config.env_generator import env_generator
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, MofNCompleteColumn, TaskProgressColumn
import math
import os
import re

class Terminal:
    def __init__(self) -> None:
        self.console = Console()
    
    def slugify(self, text: str) -> str:
        return re.sub(r'[^\w\s-]', '', text).strip().replace(' ', '_')
        
    def prepare_export_path(self, chat_name: str, chat_id: int) -> dict:
        base_name = f"{self.slugify(chat_name)}_{chat_id}"
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
    
    def error(self, message: str) -> None:
        self.console.print(message, style="bold red")
    
    def info(self, message: str) -> None:
        self.console.print(message)
    
    def success(self, message: str) -> None:
        self.console.print(message, style="bold green")
    
    def warning(self, message: str) -> None:
        self.console.print(message, style="bold yellow")

    def setup(self) -> None:
        """
        This method checks if the necessary credentials are available. 
        If not, it prompts the user to input them and saves them to the .env file.
        """
        self.success("Welcome to Telegram Exporter!")
        if not credentials.api_id:
            self.warning("Please ensure you have your Telegram API credentials ready.")
            self.warning("You can generate these credentials at https://my.telegram.org/apps")
            self.error("API ID is missing. Please enter your API ID:")
            api_id = IntPrompt.ask("API ID")
            env_generator.add_variable("API_ID_TELEGRAM", api_id)
        if not credentials.api_hash:
            self.error("API Hash is missing. Please enter your API Hash:")
            api_hash = Prompt.ask("API Hash")
            env_generator.add_variable("API_HASH_TELEGRAM", api_hash)
        if not credentials.phone_number:
            self.error("Phone number is missing. Please enter your phone number (with country code):")
            phone_number = Prompt.ask("Phone Number")
            env_generator.add_variable("PHONE_NUMBER_TELEGRAM", phone_number)
        if not credentials.session_name:
            self.error("Session name is missing. Please enter a session name (e.g., 'session_name1'):")
            session_name = Prompt.ask("Session Name")
            env_generator.add_variable("SESSION_NAME_TELEGRAM", session_name)
        credentials.__init__()  # Reload credentials after adding them to .env

    def cleanup(self) -> None:
        self.error("Cleaning up resources...")
        env_generator.cleanup()   
        credentials.cleanup()

    def clear(self) -> None:
        self.console.clear()

    def get_dialog_type(self, dialog) -> str:
        if dialog.is_user:
            return "User"
        elif dialog.is_group:
            return "Group"
        elif dialog.is_channel:
            return "Channel"
        else:
            return "Unknown"
    
    def get_dialog_table(self, dialogs_slice: list, start_idx: int, total: int) -> Table:
        table = Table(
            title=f"Telegram Dialogs (Show {start_idx + 1}-{start_idx + len(dialogs_slice)} з {total})",
            title_style="bold blue"
        )
        table.add_column("№", style="cyan", min_width=4)
        table.add_column("Title", style="magenta", min_width=70)
        table.add_column("Type", style="magenta", min_width=10)
        for idx, dialog in enumerate(dialogs_slice):
            dialog_type = self.get_dialog_type(dialog)
            name = dialog.name if dialog.name else "Deleted Account"
            table.add_row(str(start_idx + idx), name, dialog_type)
        return table
    

    def show_dialogs(self, dialogs: list) -> None:
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
            
            choice = Prompt.ask(
                "\nDo you want to see the next set of dialogs?", 
                choices=["y", "n", "all"], 
                default="y"
            )
            
            if choice == "y":
                current_index += page_size
            elif choice == "all":
                page_size = total
                current_index += 0  
            else:
                break
    
    def show_statistics(self, chat_name: str, stats: dict, duration: float):
        self.clear()
        table = Table(title=f"Statistics for: {chat_name}", title_style="bold magenta", show_footer=True)
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Size (MB/GB)", style="green", footer=self.format_size(stats["Total Messages"][1]))

        for key, value in stats.items():
            if key == "Total Messages":
                continue
            table.add_row(key, str(value[0]), self.format_size(value[1]))
        
        self.console.print(table)
        self.success(f"\n✅ Analysis completed in {duration:.2f} seconds.")

    def get_progress_bar(self):
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),          
            console=self.console,
            transient=True
        )
    
    def format_size(self, size_bytes: int) -> str:
        if size_bytes == 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"
    
    def print_choices(self) -> None:
        self.info("\nAvailable actions:")
        self.info("1. Show dialogs")
        self.info("2. -")
        self.info("3. -")
        self.info("4. -")
        self.info("5. -")
        self.info("6. -")
        self.info("7. -")
        self.info("8. -")
        self.info("9. -")
        self.info("10. Exit\n")    
        
terminal = Terminal()

__all__ = ["terminal"]
