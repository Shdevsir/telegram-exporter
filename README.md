# 📝 Telegram Exporter & Analyzer

A tool for exporting Telegram chat history to a local archive and analyzing chat statistics. It downloads all messages, automatically sorts media files by type, and generates detailed activity reports. An optional built-in web server lets you browse the exported archive through a browser.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📥 **Full export** | Saves the complete message history as a structured JSON file |
| 📂 **Smart media sorting** | Automatically categorises photos, videos, audio, stickers, GIFs, documents, and voice/round messages into dedicated sub-folders |
| 📊 **Chat statistics** | Counts messages, calculates total data volume, and breaks down content by type |
| 🌐 **Web archive viewer** | Browse exported chats and their media through a local Flask web server |
| ⚡ **Async performance** | Built on [Telethon](https://docs.telethon.dev/) — a fully async Telegram MTProto client |

---

## 🚀 Quick Start

The only tool you need is **`uv`** — it manages the Python version and all dependencies automatically.

### 1. Install `uv`

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone the repository and run

```bash
git clone https://github.com/Shdevsir/telegram-exporter.git
cd telegram-exporter
uv run main.py
```

> **Note:** On the first run, `uv` will automatically download the required Python version (≥ 3.12)
> and install all dependencies into an isolated virtual environment — no manual setup needed.

---

## ⚙️ First-Run Configuration

On the very first launch the program will ask for three credentials and save them to a local `.env` file:

| Prompt | Where to get it |
|---|---|
| **API ID** | [my.telegram.org](https://my.telegram.org) → *API development tools* |
| **API Hash** | Same page as above |
| **Phone number** | Your Telegram account number in international format, e.g. `+380501234567` |

These values are stored in `.env` **only on your local machine**. A Telethon session file is saved to the `session/` directory so you are not prompted again on subsequent runs.

> ⚠️ **Never commit or share your `.env` file.** It contains your personal API credentials.
> The `.gitignore` already excludes `.env` and `session/`.

---

## 🗂 Export Structure

After running an export, data is saved under `telegram_data/` relative to the project root:

```
telegram_data/
└── <Chat_Name>_<chat_id>/
    ├── Info/
    │   └── info.json          # Chat metadata (title, type, export timestamp)
    ├── Text/
    │   └── history.json       # Complete message history
    └── Files/
        ├── Audio/
        ├── Documents/
        ├── GIFs/
        ├── Photos/
        ├── Round_Messages/
        ├── Stickers/
        └── Videos/
```

---

## 🌐 Web Archive Viewer

After exporting one or more chats you can browse them locally:

1. Start the application: `uv run main.py`
2. Choose option **4 — Open web viewer** from the menu.
3. Open [http://localhost:5000](http://localhost:5000) in your browser.
4. Press **Enter** in the terminal to stop the server and return to the menu.

The viewer shows a gallery of all exported chats, lets you paginate through messages, and serves the downloaded media files directly.

---

## 🛠 Development

### Set up a development environment

```bash
# Install all dependencies (including dev tools)
uv sync

# Install pre-commit hooks (runs ruff + mypy automatically before each commit)
uv run pre-commit install
```

### Run the test suite

```bash
uv run pytest
```

Coverage is measured automatically. To see a full HTML report:

```bash
uv run pytest --cov-report=html
# Open htmlcov/index.html in a browser
```

### Run linting and type checking manually

```bash
# Linter + auto-fixer (ruff)
uv run ruff check . --fix

# Static type checker (mypy)
uv run mypy src

# All pre-commit hooks at once
uv run pre-commit run --all-files
```

### Project layout

```
telegram-exporter/
├── main.py                  # Entry point — interactive CLI menu
├── pyproject.toml           # Project metadata, dependencies, tool config
├── src/
│   ├── cli/                 # Rich terminal UI (prompts, progress bars, tables)
│   ├── client/              # Telegram client wrapper (Telethon)
│   ├── config/              # Credentials loading and .env file management
│   ├── log/                 # Application logger
│   ├── schemas/             # Data classes (Stats, StatItem)
│   ├── utils/               # File / path helpers
│   └── web/                 # Flask web server + Jinja2 templates
├── tests/
│   └── unit/                # Unit tests mirroring the src/ structure
├── session/                 # Telethon session files (gitignored)
├── logs/                    # Application log files (gitignored)
└── telegram_data/           # Exported chat archives (gitignored)
```

### Toolchain

| Tool | Purpose |
|---|---|
| [`uv`](https://docs.astral.sh/uv/) | Package manager, virtual-env, Python version management |
| [`ruff`](https://docs.astral.sh/ruff/) | Linter and formatter (replaces flake8, isort, pyupgrade) |
| [`mypy`](https://mypy.readthedocs.io/) | Static type checking |
| [`pytest`](https://docs.pytest.org/) + `pytest-cov` | Test runner with coverage reporting |
| [`pre-commit`](https://pre-commit.com/) | Git hooks to enforce quality before every commit |

---

## 🔑 Environment Variables

The application reads the following variables from `.env` (created automatically on first run):

| Variable | Description |
|---|---|
| `API_ID_TELEGRAM` | Telegram API ID (integer) |
| `API_HASH_TELEGRAM` | Telegram API Hash (32-char hex string) |
| `PHONE_TELEGRAM` | Account phone number in international format |
| `SESSION_NAME_TELEGRAM` | Name of the Telethon session file (stored in `session/`) |

You can also edit `.env` manually if you need to change credentials without re-running the setup prompt.
