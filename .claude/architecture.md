# System Architecture & Database Schema

## 1. Database Layer (SQLite 3NF)

The project leverages **SQLite3** running in Write-Ahead Logging (WAL) mode for concurrency. The schema is fully normalized into the **3rd Normal Form (3NF)** to eliminate data redundancy and prevent update anomalies (especially concerning string-based trade outcome labels).

### Database File: `trading_journal.db`

#### Schema definition (`db/schema.sql`):

**1. `trade_results` (Reference Lookup)**
- `id` (INTEGER PK)
- `code` (TEXT UNIQUE) — Enum: `'PENDING'`, `'WIN'`, `'LOSS'`, `'MISSED'`
- `label_th` (TEXT) — Human-readable Thai UI text (e.g., `'WIN (TP)'`)

**2. `screenshots` (Entity)**
- `id` (INTEGER PK)
- `filename` (TEXT UNIQUE) — Path to the `.png` file.
- `ai_analysis` (TEXT) — The raw LLM output reasoning for the trade.

**3. `journal_entries` (Transaction)**
- `id` (INTEGER PK)
- `screenshot_id` (INTEGER FK) → `screenshots(id)`
- `result_id` (INTEGER FK) → `trade_results(id)`
- `rr` (TEXT) — Risk:Reward string (e.g., `'1:2'`)
- `pnl_usd` (REAL) — Actual profit/loss in Dollars (e.g., `15.50` or `-10.00`). NULL if missing.
- `recorded_at` (DATETIME) — Default `CURRENT_TIMESTAMP`.

### 2. Service Layer Boundaries

- **`services.db`**: Responsible ONLY for raw connection (`sqlite3.connect`), pragmas (`foreign_keys=ON`), creating tables via `schema.sql`, and the one-time `migrate_from_csv()` function.
- **`services.journal`**: Responsible for the *Business Logic* using SQL CRUD.
  - `save_to_journal()` handles **UPSERT** logic (it inserts a screenshot if it doesn't exist, then updates or inserts the related `journal_entries` record based on the chosen outcome).
  - `get_stats()` performs strict **SQL Aggregation** (via `SUM`, `COUNT`, `COALESCE`) to calculate overall metrics instantly, completely bypassing Python memory loops.
  - `clear_all_history()` drops all internal journal records and purges the CSV file to prevent recursive reimports.

### 3. Telegram Interaction Layer
- The Bot utilizes `telebot.TeleBot(token)`.
- It dynamically uses the `register_next_step_handler` pattern for multi-step prompts. For example, when a user clicks 'WIN', the bot traps the next user message to parse the `rr` (Risk:Reward) parameter, and traps the specific subsequent message for `pnl_usd`.

### 4. Web App UI Layer (Telegram Mini App)
- **Frontend (`webapp/`)**: Built with HTML, CSS (Glassmorphism), and Vanilla JS (`app.js`). It reads Telegram's theme variables. 
- **Backend (`web_server.py`)**: A lightweight `Flask` server running on port `5055` inside a daemon thread alongside `main.py`. It exposes the `GET /api/trades` endpoint by pulling data from `services/journal.get_stats()`.
- **Tunneling (`ngrok`)**: Required to expose localhost via an HTTPS URL since Telegram strictly requires secure domains for `WebAppInfo` buttons.
