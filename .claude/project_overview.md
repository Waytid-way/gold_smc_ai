# Project Overview: Telegram Trading Journal Bot (SQLite Edition)

## Objective
A Telegram bot designed to automate the trading journal process for XAUUSD (Gold) using Smart Money Concepts (SMC). The workflow starts from taking a screenshot on the user's PC, analyzing it via Google Gemini AI, presenting the analysis in Telegram, and permanently logging the trade outcome (Win/Loss/Missed, RR, PnL) into a relational SQLite database.

## Tech Stack
- **Language**: Python 3.10+
- **Bot Framework**: `pyTelegramBotAPI` (telebot)
- **AI Engine**: Google Gemini API (`google-genai`)
- **Database**: `sqlite3` (built-in, 3rd Normal Form Schema)
- **Desktop Automation**: `pyautogui`, `pygetwindow`, `keyboard` (for `/snap`)

## Core Modules
- `main.py`: Entry point. Initializes the DB, triggers CSV migration if needed, and starts the infinite polling loops for the bot and the pending trade reminder thread.
- `config.py`: Configuration central. Manages `python-dotenv` loading, paths (`trading_journal.db`), and API keys.
- `services/`: The business logic layer containing:
  - `db.py`: SQLite connection management (`PRAGMA WAL`, `foreign_keys=ON`) and automated migrations.
  - `gemini_api.py`: Connects to Gemini. Includes sliding-window conversation history to maintain context of previous chats.
  - `journal.py`: Handles all Database interactions (`SELECT`, `INSERT OR IGNORE`, `SUM`, `COUNT`) relating to trades and stats rendering.
  - `screenshot.py`: Captures the screen window specifically running "TradingView".
- `bot/`: The presentation layer containing:
  - `handlers.py`: Message handlers for Commands like `/snap`, `/stats`, `/clear_pending`, and general chat.
  - `callbacks.py`: Inline Keyboard handlers (`callback_query_handler`) to record TP, SL, or MISSED decisions via simple interactive buttons.

## Primary Use Case
1. User sees a setup on TradingView and types `snap` in Telegram.
2. PC takes a screenshot locally, uploads it to Gemini.
3. Gemini replies with SMC analysis. Bot forwards this to Telegram with buttons [Win], [Loss], [Missed].
4. User clicks a button. Bot asks for Risk:Reward (e.g., `1:3`) and PnL (e.g., `15.5`).
5. Trade is saved to `trading_journal.db`. User can fetch performance charts anytime using `/stats`.
