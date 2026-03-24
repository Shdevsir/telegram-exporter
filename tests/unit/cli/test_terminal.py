from types import SimpleNamespace
from unittest.mock import MagicMock

import src.cli.rich_terminal as cli_module
from rich.progress import Progress
from src.cli import Terminal


def test_color_messages():
    terminal = Terminal()
    terminal.console = MagicMock()

    terminal.info("info")
    terminal.console.print.assert_called_with("info")
    terminal.success("success")
    terminal.console.print.assert_called_with("success", style="bold green")
    terminal.warning("warning")
    terminal.console.print.assert_called_with("warning", style="bold yellow")
    terminal.error("fail")
    terminal.console.print.assert_called_with("fail", style="bold red")


def test_setup(monkeypatch):
    terminal = Terminal()

    fake_credentials = MagicMock()
    fake_credentials.api_id = None
    fake_credentials.api_hash = None
    fake_credentials.phone_number = None
    fake_credentials.session_name = None

    fake_env = MagicMock()

    monkeypatch.setattr(cli_module, "credentials", fake_credentials)
    monkeypatch.setattr(cli_module, "env_generator", fake_env)

    monkeypatch.setattr("rich.prompt.IntPrompt.ask", lambda _: 123)
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda _: "value")

    terminal.console = MagicMock()

    terminal.setup()

    assert fake_env.add_variable.call_count == 4
    fake_credentials.load.assert_called_once()


def test_cleanup(monkeypatch):
    terminal = Terminal()
    fake_env = MagicMock()
    fake_credentials = MagicMock()

    monkeypatch.setattr(cli_module, "credentials", fake_credentials)
    monkeypatch.setattr(cli_module, "env_generator", fake_env)

    terminal.console = MagicMock()

    terminal.cleanup()

    fake_env.cleanup.assert_called_once()
    fake_credentials.cleanup.assert_called_once()


def test_clear():
    terminal = Terminal()
    terminal.console = MagicMock()
    terminal.clear()
    terminal.console.clear.assert_called_once()


def test_print_choices():
    terminal = Terminal()
    terminal.info = MagicMock()

    terminal.print_choices()

    assert terminal.info.call_count == 6


def test_get_dialog_type():
    term = Terminal()

    dialog = SimpleNamespace(is_user=True, is_group=False, is_channel=False)
    assert term.get_dialog_type(dialog) == "User"

    dialog = SimpleNamespace(is_user=False, is_group=True, is_channel=False)
    assert term.get_dialog_type(dialog) == "Group"

    dialog = SimpleNamespace(is_user=False, is_group=False, is_channel=True)
    assert term.get_dialog_type(dialog) == "Channel"

    dialog = SimpleNamespace(is_user=False, is_group=False, is_channel=False)
    assert term.get_dialog_type(dialog) == "Unknown"


def test_get_dialog_table():
    terminal = Terminal()

    dialog = SimpleNamespace(name="Test chat", is_user=True, is_group=False, is_channel=False)

    table = terminal.get_dialog_table([dialog], 0, 1)

    assert table.row_count == 1


def test_get_progress_bar():
    terminal = Terminal()
    assert isinstance(terminal.get_progress_bar(), Progress) == True


def test_show_statistics():
    terminal = Terminal()
    terminal.console = MagicMock()
    terminal.clear = MagicMock()
    terminal.success = MagicMock()

    mock_stats = MagicMock()
    mock_stats.total.count = 100
    mock_stats.total.formatted_size = "10.5 MB"
    mock_stats.to_dict.return_value = {"Total Messages": (100, "10.5 MB"), "Photos": (50, "5 MB")}

    terminal.show_statistics("Test Chat", mock_stats, 5.25)

    terminal.clear.assert_called_once()
    terminal.console.print.assert_called_once()
    terminal.success.assert_called()
    args, _ = terminal.success.call_args
    assert "100" in args[0]
    assert "5.25" in args[0]


def test_show_dialogs_short_list():
    terminal = Terminal()
    terminal.console = MagicMock()

    dialogs = [SimpleNamespace(name=f"Chat {i}", is_user=True, is_group=False, is_channel=False) for i in range(5)]

    terminal.show_dialogs(dialogs)
    assert terminal.console.print.call_count == 2
    terminal.console.print.assert_any_call("This is the end of the list.")


def test_show_dialogs_pagination_next(monkeypatch):
    terminal = Terminal()
    terminal.console = MagicMock()

    dialogs = [SimpleNamespace(name=f"Chat {i}", is_user=True, is_group=False, is_channel=False) for i in range(25)]

    input_generator = iter(["y", "n"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: next(input_generator))

    terminal.show_dialogs(dialogs)

    assert terminal.console.print.call_count == 2


def test_show_dialogs_all(monkeypatch):
    terminal = Terminal()
    terminal.console = MagicMock()

    dialogs = [SimpleNamespace(name=f"Chat {i}", is_user=True, is_group=False, is_channel=False) for i in range(25)]

    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: "all")

    terminal.show_dialogs(dialogs)

    assert terminal.console.print.call_count == 3
    terminal.console.print.assert_any_call("This is the end of the list.")
