import asyncio

from src.client.telegram_client import telegram_client
from src.cli.terminal import terminal
from rich.prompt import IntPrompt
import time


async def setup():
    terminal.setup()
    status, message = await telegram_client.setup()
    if status:
        info = await telegram_client.info()
        terminal.success(f"Logged in as: {info.first_name} {info.last_name} (@{info.username})")
        terminal.success(message)
    else:
        terminal.error(f"Telegram client setup failed: {message}")
        terminal.cleanup()

async def choicer(ask_number: int):
    if ask_number == 1:
        dialogs = await telegram_client.get_list_dialogs()
        terminal.show_dialogs(dialogs)
    elif ask_number == 2:
        dialogs = await telegram_client.get_list_dialogs()
        chat_idx = IntPrompt.ask("Enter the № of the chat you want to analyze")
        if 0 <= chat_idx < len(dialogs):
            target_chat = dialogs[chat_idx]
            terminal.info(f"Starting analysis of [bold]{target_chat.name}...")
            total_messages = await telegram_client.get_messages_count(target_chat)
            with terminal.get_progress_bar() as progress:
                task = progress.add_task("Analyzing messages...", total=total_messages)
                async def update_progress(current, total):
                    progress.update(task, completed=current, total=total)
                
                stats, duration = await telegram_client.get_chat_statistics(
                    target_chat, total_messages, update_progress
                )
            
            terminal.show_statistics(target_chat.name, stats, duration)
        else:
            terminal.error("Invalid chat number.")
        
    elif ask_number == 3:
        dialogs = await telegram_client.get_list_dialogs()
        terminal.show_dialogs(dialogs)
        
        chat_idx = IntPrompt.ask("Choose the № of the chat you want to export")
        
        if 0 <= chat_idx < len(dialogs):
            target_chat = dialogs[chat_idx]
            
            paths = terminal.prepare_export_path(target_chat.name, target_chat.id)
            terminal.info(f"📁 Folders created in: {paths['base']}")
            
            total_to_export = await telegram_client.get_messages_count(target_chat)
            
            with terminal.get_progress_bar() as progress:
                task = progress.add_task("[bold cyan]Downloading data...", total=total_to_export)
                
                async def update_progress(current, total):
                    progress.update(task, completed=current, total=total)
                
                count = await telegram_client.export_chat(target_chat, paths, update_progress)
            
            terminal.success(f"✅ Export completed! Processed {count} messages.")
            terminal.info(f"Text history: {paths['text']}/history.json")
    elif ask_number == 4:
        pass
    elif ask_number == 5:
        pass
    elif ask_number == 6:
        pass
    elif ask_number == 7:
        pass
    elif ask_number == 8:
        pass
    elif ask_number == 9:
        pass
    else:
        terminal.error("Invalid choice. Please enter a number between 1 and 9.")
    

async def main():
    await setup()
    ask = 0
    while ask != 10:
        terminal.print_choices()
        ask = IntPrompt.ask("Enter the number with action what you want to do", default=10)
        await choicer(ask)
    terminal.clear()
    terminal.success("Exiting the application. Goodbye!")
    



if __name__ == "__main__":
    asyncio.run(main())


