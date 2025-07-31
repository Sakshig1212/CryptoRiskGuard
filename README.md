# 💹 CryptoRiskGuard Bot

**CryptoRiskGuard** is a sophisticated, database-backed Telegram bot designed for **real-time cryptocurrency risk monitoring** and **automated delta hedging**. Built to be interactive and persistent, the bot helps traders and portfolio managers **track, analyze, and manage** their portfolio’s live exposure with intelligent automation and proactive alerting.

The bot connects to Bybit and Deribit, calculates critical risk metrics, and allows for full portfolio management and mock hedging directly through a simple Telegram interface.

---

## 🚀 Key Features

-   🗃️ **Dynamic & Persistent Portfolio Management**
    -   **Database-Backed:** All user data (portfolios, API keys, settings) is stored in a local **SQLite database**, ensuring data persists between restarts.
    -   **Manual Control:** Users can manually manage their positions across exchanges with `/add_position`, `/remove_position`, and `/view_portfolio`.
    -   **Automated Syncing:** Securely add read-only API keys with `/add_api` and use `/sync` to automatically fetch and update live spot and perpetual positions from Bybit.

-   📊 **Real-Time Risk Analysis**
    -   **Consolidated Dashboard:** The `/dashboard` command provides a high-level summary of total portfolio value, aggregate delta, and PnL.
    -   **Hedge Preview (`/hedge_status`):** A crucial "dry run" feature that shows the current delta and the exact trade (side and quantity) required to neutralize it, empowering users to make informed decisions.
    -   **Detailed Risk View:** An inline button provides a granular, exchange-by-exchange breakdown of all risk metrics.

-   🛡️ **Automated Hedging & Execution**
    -   **One-Click Hedging:** The `/hedge_now` command or an inline button instantly calculates the precise trade to neutralize the portfolio's delta and executes a mock order.
    -   **Clear Execution Logic:** The bot provides clear confirmation messages upon successful trade execution.

-   🤖 **Proactive & Stoppable Risk Monitoring**
    -   **Persistent Background Threads:** The `/monitor_risk` command activates a dedicated background thread that continuously scans the user's risk profile.
    -   **Multi-Condition Alerts:** Automatically sends a Telegram alert if the total delta exceeds a predefined threshold or if the portfolio experiences a significant **drawdown**.
    -   **User-Controlled Service:** The monitoring is fully controllable and can be gracefully stopped at any time with the `/stop_monitor` command.
    -   **Customizable Thresholds:** Users can set their own personal drawdown alert percentage using the `/set_drawdown` command.

---

## 🏗️ Architectural Overview & Code Explanation

The bot is built with a modular and robust architecture, separating concerns for scalability and maintenance.

### 1. Core Application & User Interaction (`main.py`)
-   **Entry Point:** The application uses a standard `if __name__ == "__main__":` block to call a `main()` function, ensuring that the bot setup logic only runs when the script is executed directly.
-   **Asynchronous Core:** It is built on `python-telegram-bot`'s `asyncio`-based `ApplicationBuilder`, allowing for non-blocking, concurrent handling of multiple user requests.
-   **Command Handling:** Each Telegram command (e.g., `/start`) is linked to a specific `async` function (e.g., `start_command`) via a `CommandHandler`. This modular system keeps the logic for each command separate and clean.
-   **Global State Management:** A global `application` variable holds the bot instance, making it accessible to background threads for sending alerts. A global `active_monitors` dictionary tracks running threads for each user to prevent duplicates and enable stopping.

### 2. Data Persistence (`database.py`)
-   **Technology:** Uses Python's built-in **SQLite3** for a serverless, file-based database (`risk_bot.db`) that is created automatically.
-   **Key Functions:**
    -   `init_db()`: Creates all necessary tables (`portfolio`, `api_keys`, `drawdown`) if they don't exist upon startup.
    -   `add_or_update_position()`: An "upsert" function that uses `INSERT ... ON CONFLICT DO UPDATE` to add a new portfolio position or modify an existing one for a user.
    -   `get_portfolio()`: Retrieves all positions for a specific `user_id` and formats them into a dictionary for the risk engine.
    -   `save_api_keys()`: Securely saves (mock) user API keys for the `/sync` functionality.
    -   `get_or_create_drawdown_settings()`: Manages user-specific drawdown thresholds and peak portfolio values, creating a default entry for new users.

### 3. Risk Calculation Engine (`main.py`)
-   **Core Logic:** The `compute_risk_metrics()` function performs the fundamental financial calculations, taking quantities and prices to return portfolio value, delta, and PnL.
-   **Data Aggregation:** The `format_portfolio_risk()` function acts as the central engine. It retrieves a user's portfolio from the database, fetches live market prices from exchanges, calls `compute_risk_metrics` for each position, and aggregates the results into a structured report (either raw data or formatted text).
-   **Safe Text Formatting:** A helper function `escape_markdown()` is used to sanitize all dynamic text before sending it to Telegram, preventing `BadRequest` errors by escaping special characters required for `ParseMode.MARKDOWN_V2`.

### 4. Exchange Integration & Data Fetching (`main.py`)
-   **Standardized Access:** `fetch_orderbook_bybit()` uses the **`ccxt`** library to connect to Bybit, providing a standardized way to get order book data.
-   **Direct API Calls:** `fetch_orderbook_deribit()` uses the **`requests`** library to make a direct HTTP GET request to Deribit's public API, demonstrating flexibility in data fetching.
-   **Automated Syncing:** The `sync_bybit_portfolio()` function uses `ccxt` with user-provided API keys to access private endpoints, fetching their actual spot balances and perpetual positions to automate portfolio setup.

### 5. Background Monitoring & Concurrency (`main.py`)
-   **Non-Blocking Threads:** The `/monitor_risk` command spawns a new background process using Python's **`threading.Thread`**. This is crucial as it allows the bot to remain fully responsive to other user commands while the monitor runs independently.
-   **Graceful Termination:** Each thread is given a unique `threading.Event` object. The thread's main loop (`while not stop_event.is_set():`) continuously checks this event. The `/stop_monitor` command simply calls `.set()` on the event, signaling the thread to finish its current loop and exit cleanly.
-   **Thread-Safe Alerting:** The background thread cannot directly call `async` Telegram functions. Instead, it creates its own `asyncio` event loop to run the `alert_telegram` coroutine, which then safely uses the global `application` object to send the message.

---

## 🗂️ File Structure

```
CryptoRiskGuard/
│
├── venv/                   # Python Virtual Environment
├── main.py                 # Main application script, contains all bot logic and handlers
├── database.py             # Handles all SQLite database interactions
├── bybit_hedge.py          # (Placeholder) Contains logic for executing hedge orders
├── config.py               # Stores API keys and other sensitive configuration
├── requirements.txt        # Lists all project dependencies
└── risk_bot.db             # The SQLite database file (created automatically)
```

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/YourUsername/CryptoRiskGuard.git
cd CryptoRiskGuard
```

### 2. Set Up a Virtual Environment

Using a virtual environment is strongly recommended to manage dependencies cleanly.

```bash
# Create the virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

Create a `requirements.txt` file with the following content:

```txt
python-telegram-bot==20.8
ccxt
requests
certifi
```

Then, install the packages from the file:

```bash
pip install -r requirements.txt
```

### 4. Configure Your Bot

-   **Telegram Token:** Open `main.py` and replace the placeholder value for the `TOKEN` variable with your own bot token obtained from Telegram's @BotFather.
    ```python
    TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
    ```

### 5. Run the Bot

Execute the main script from your terminal. The bot will automatically create and initialize the `risk_bot.db` database file on its first run.

```bash
python main.py
```

Your bot is now live! Open your Telegram client and send the `/start` command to begin interacting with it.

---

## 📘 Full Command Reference

| Command             | Description                                                                    | Example                                             |
| ------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------- |
| **Core**            |                                                                                |                                                     |
| `/start`            | Initializes the bot and displays the main action buttons.                      | `/start`                                            |
| `/dashboard`        | Shows a complete summary of your portfolio's value, delta, and PnL.            | `/dashboard`                                        |
| **Portfolio**       |                                                                                |                                                     |
| `/add_position`     | Manually adds or updates a position in your portfolio.                         | `/add_position Bybit BTC/USDT 1.0 -0.8 65000`        |
| `/remove_position`  | Removes a specific position from your portfolio.                               | `/remove_position Bybit BTC/USDT`                   |
| `/view_portfolio`   | Displays all current positions stored in the database.                         | `/view_portfolio`                                   |
| **API & Sync**      |                                                                                |                                                     |
| `/add_api`          | Saves your exchange API keys to the database for use with `/sync`.             | `/add_api Bybit <key> <secret>`                     |
| `/sync`             | Automatically fetches and updates your portfolio from an exchange.             | `/sync`                                             |
| **Hedging**         |                                                                                |                                                     |
| `/hedge_status`     | Shows a preview of the required hedge without executing it.                    | `/hedge_status`                                     |
| `/hedge_now`        | Immediately calculates and executes the required hedge trade.                  | `/hedge_now`                                        |
| **Monitoring**      |                                                                                |                                                     |
| `/monitor_risk`     | Starts the background risk monitoring service.                                 | `/monitor_risk`                                     |
| `/stop_monitor`     | Stops the background risk monitoring service.                                  | `/stop_monitor`                                     |
| `/set_drawdown`     | Sets your custom drawdown alert threshold (as a decimal).                      | `/set_drawdown 0.15`                                |

## 🎬 Demo

### 📱 Telegram Bot Interaction

![Start Command](demo/start.png)
<img width="975" height="528" alt="image" src="https://github.com/user-attachments/assets/9fecd4c3-6768-4320-98d2-de20ff1a1494" />

*Initial dashboard with risk actions*

![Risk Alert](demo/risk_alert.png)
*Real-time drawdown alert sent to Telegram*
<img width="975" height="646" alt="image" src="https://github.com/user-attachments/assets/aa440685-5d91-4a75-913b-480f2e9b7995" />
<img width="975" height="671" alt="image" src="https://github.com/user-attachments/assets/ff5e06e1-50aa-4535-bffd-e0a398304a0b" />


![Hedge Triggered](demo/hedge_trigger.gif)
*Hedging executed via inline button with confirmation*
<img width="975" height="576" alt="image" src="https://github.com/user-attachments/assets/d48bcc58-5272-4cdb-abb9-1f8cb0a00da3" />
<img width="975" height="627" alt="image" src="https://github.com/user-attachments/assets/84337516-8de1-4af1-b1c2-bed3926aa0e5" />
<img width="975" height="525" alt="image" src="https://github.com/user-attachments/assets/e90189cb-bd33-49f8-bb2e-6748c45ba147" />

---

## 🛠 Setup Instructions

### 🔹 1. Clone the Repository

```bash
git clone https://github.com/YourUsername/CryptoRiskGuard.git
cd CryptoRiskGuard
