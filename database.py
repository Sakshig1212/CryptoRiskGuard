# database.py
import sqlite3

DATABASE_NAME = "risk_bot.db"

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Table for storing user portfolio positions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolio (
        user_id INTEGER NOT NULL,
        exchange TEXT NOT NULL,
        symbol TEXT NOT NULL,
        spot_qty REAL DEFAULT 0,
        perp_qty REAL DEFAULT 0,
        entry_price REAL DEFAULT 0,
        PRIMARY KEY (user_id, exchange, symbol)
    )""")

    # Table for API keys
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_keys (
        user_id INTEGER NOT NULL,
        exchange TEXT NOT NULL,
        api_key TEXT NOT NULL,
        secret_key TEXT NOT NULL,
        PRIMARY KEY (user_id, exchange)
    )""")
    
    # Table for user-specific drawdown tracking
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS drawdown (
        user_id INTEGER PRIMARY KEY,
        peak_value REAL DEFAULT 0,
        threshold REAL DEFAULT 0.10
    )""")

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def add_or_update_position(user_id, exchange, symbol, spot_qty, perp_qty, entry_price):
    """Adds a new position or updates an existing one for a user."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO portfolio (user_id, exchange, symbol, spot_qty, perp_qty, entry_price)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id, exchange, symbol) DO UPDATE SET
        spot_qty = excluded.spot_qty,
        perp_qty = excluded.perp_qty,
        entry_price = excluded.entry_price
    """, (user_id, exchange, symbol, spot_qty, perp_qty, entry_price))
    conn.commit()
    conn.close()

def remove_position(user_id, exchange, symbol):
    """Removes a specific position for a user."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio WHERE user_id = ? AND exchange = ? AND symbol = ?", (user_id, exchange, symbol))
    conn.commit()
    conn.close()

def get_portfolio(user_id):
    """Retrieves the entire portfolio for a given user as a dictionary."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT exchange, symbol, spot_qty, perp_qty, entry_price FROM portfolio WHERE user_id = ?", (user_id,))
    portfolio_data = {}
    for row in cursor.fetchall():
        exchange, symbol, spot_qty, perp_qty, entry_price = row
        portfolio_data[exchange] = {"symbol": symbol, "spot_qty": spot_qty, "perp_qty": perp_qty, "entry_price": entry_price}
    conn.close()
    return portfolio_data

def save_api_keys(user_id, exchange, api_key, secret_key):
    """Saves or updates API keys for a user and exchange."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO api_keys (user_id, exchange, api_key, secret_key) VALUES (?, ?, ?, ?)
    ON CONFLICT(user_id, exchange) DO UPDATE SET api_key = excluded.api_key, secret_key = excluded.secret_key
    """, (user_id, exchange, api_key, secret_key))
    conn.commit()
    conn.close()

def get_api_keys(user_id, exchange):
    """Retrieves API keys for a user and exchange."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT api_key, secret_key FROM api_keys WHERE user_id = ? AND exchange = ?", (user_id, exchange))
    keys = cursor.fetchone()
    conn.close()
    return {'apiKey': keys[0], 'secret': keys[1]} if keys else None

def get_or_create_drawdown_settings(user_id):
    """Gets drawdown settings for a user, creating them if they don't exist."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT peak_value, threshold FROM drawdown WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    if data is None:
        cursor.execute("INSERT INTO drawdown (user_id) VALUES (?)", (user_id,))
        conn.commit()
        data = (0, 0.10) # Default values
    conn.close()
    return {'peak_value': data[0], 'threshold': data[1]}

def update_drawdown_peak(user_id, new_peak):
    """Updates the peak value for a user."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE drawdown SET peak_value = ? WHERE user_id = ?", (new_peak, user_id))
    conn.commit()
    conn.close()

# In database.py

def set_drawdown_threshold(user_id, threshold):
    """Sets the drawdown alert threshold for a user (upsert logic)."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # --- THIS IS THE CORRECTED "UPSERT" SYNTAX ---
    # We try to INSERT. If the user_id already exists (conflict), we UPDATE the threshold.
    cursor.execute("""
    INSERT INTO drawdown (user_id, threshold) 
    VALUES (?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
        threshold = excluded.threshold
    """, (user_id, threshold))
    
    conn.commit()
    conn.close()