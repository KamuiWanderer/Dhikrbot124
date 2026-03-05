# Telethon Bot Architect (Master Branch)

This project is a professional-grade Telegram bot template using the **Telethon Master Branch (v2.0)**. It includes a modern React dashboard for management and a clean, modular Python structure.

## 🚀 Features

- **Telethon v2.0 (Master)**: Uses the latest async features and improved API.
- **Interactive Buttons**: Implementation of colored inline buttons (Success, Danger, Primary) using emojis and robust callback handling.
- **Full-Stack Dashboard**: React + Express dashboard to monitor and control the bot process.
- **Modular Structure**: Clean separation of configuration and bot logic.

## 🛠 Setup Instructions

### 1. Prerequisites
- Python 3.10 or higher.
- Node.js 18 or higher.

### 2. Environment Variables
Create a `.env` file (or set these in your environment) with the following:
```env
TELEGRAM_API_ID="your_api_id"
TELEGRAM_API_HASH="your_api_hash"
TELEGRAM_BOT_TOKEN="your_bot_token"
```
Get these from [my.telegram.org](https://my.telegram.org) and [@BotFather](https://t.me/BotFather).

### 3. Installation
Install Python dependencies:
```bash
pip install -r bot/requirements.txt
```
*Note: This installs Telethon directly from the GitHub master branch as requested.*

Install Node.js dependencies:
```bash
npm install
```

### 4. Running the Project
Start the development server (Dashboard + Bot Manager):
```bash
npm run dev
```
The dashboard will be available at `http://localhost:3000`. You can start/stop the bot process directly from the UI.

## 📂 Project Structure

- `bot/`: Python bot source code.
  - `main.py`: Entry point and handler definitions.
  - `config.py`: Environment configuration.
  - `requirements.txt`: Python dependencies.
- `src/`: React frontend source code.
- `server.ts`: Express backend for process management.
- `package.json`: Node.js configuration and scripts.

## 🔧 Troubleshooting

- **Buttons not responding**: Ensure you are using `event.answer()` in your callback handlers. This template handles this correctly.
- **Master Branch Compatibility**: Telethon v2.0 has breaking changes from v1.x. This project is built specifically for v2.0.
