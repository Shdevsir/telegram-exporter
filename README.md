# 📝 Telegram Exporter & Analyzer

A professional-grade tool for exporting message history and analyzing Telegram chat statistics. It allows you to download media files, sort them automatically by type, and generate detailed participant activity reports.

## ✨ Features
* 📥 **Full Export:** Save message history in a clean JSON format.

* 📂 **Smart Sorting:** Automatically categorizes media (photos, videos, stickers, voice notes) into dedicated folders.

* 📊 **Deep Analytics:** Statistics on data volume, message counts, and content distribution.

* 🚀 **High Performance:** Built with the asynchronous Telethon library and managed by the ultra-fast uv package manager.

## 🚀 Quick Start

1. Install `uv`

`uv` is the only tool you need to manage Python versions and dependencies.

* macOS / Linux:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

* Windows (PowerShell):
    ```PowerShell
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

2. Clone and run
You don't even need to have `Python` installed manually. `uv` will handle everything.
    ```bash
    git clone https://github.com/Shdevsir/telegram-exporter.git
    cd telegram-exporter
    uv run main.py
    ```
    *Note: Upon the first run, uv will automatically download the correct Python version (3.12+) and install all required dependencies in an isolated environment.*

## ⚙️ Configuration
On the first launch, the program will prompt you for your credentials:

* **API ID & API Hash:** Obtain these at my.telegram.org.

* **Phone Number:** Your Telegram account number in international format.

These details will be securely saved in a `.env` file. Never share your `.env` file with anyone!

## 🛠 Development
If you want to contribute or add new features:
1. install dependencies:
    ```bash
    uv sync
    ```
2. Install pre-commit hooks:
    ```bash
    uv run pre-commit install
    ```
    *Note: If you want run pre-commit hooks manually use `uv run pre-commit run --all-files`*
