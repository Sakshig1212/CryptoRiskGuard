from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import database as db
import os
import certifi
import ccxt
import requests
import json
import threading
import asyncio
import time
active_monitors = {}
# --- ASSUMED TO EXIST IN YOUR PROJECT ---
# Make sure you have these files and they are correctly set up
# import config 
# from bybit_hedge import place_hedge_order
# For this example, we will create a placeholder for place_hedge_order
def place_hedge_order(symbol, side, qty):
    print(f"--- MOCK HEDGE: Placing {side} order for {qty} {symbol} ---")
    return True, f"✅ Mock hedge successful: {side} {qty} {symbol}"
# ----------------------------------------


application = None


def get_mid_price(ob):
    try:
        if not isinstance(ob, dict) or not ob.get("bids") or not ob.get("asks"): return None
        return (ob["bids"][0][0] + ob["asks"][0][0]) / 2
    except (IndexError, TypeError, KeyError) as e:
        print(f"❌ [get_mid_price] Error: {e}")
        return None

def compute_risk_metrics(spot_qty, perp_qty, mid_price, entry_price):
    net_position = spot_qty + perp_qty
    position_value = net_position * mid_price
    delta = net_position
    pnl = (mid_price - entry_price) * perp_qty if entry_price else 0
    return position_value, delta, pnl

def format_portfolio_risk(user_id, raw=False):
    portfolio_data = db.get_portfolio(user_id)
    if not portfolio_data:
        return "Your portfolio is empty. Use /add_position or /sync."

    responses, structured = [], {}
    total_value, total_delta, total_pnl = 0, 0, 0

    # These can be dynamic based on user's portfolio exchanges
    sources = [('Bybit', fetch_orderbook_bybit(raw=True)), ('Deribit', fetch_orderbook_deribit())]

    for exchange, ob in sources:
        if exchange not in portfolio_data: continue
        data = portfolio_data[exchange]
        
        if "error" in ob:
            msg, structured[exchange] = f"❌ {exchange}: {ob['error']}", {"error": ob["error"]}
            responses.append(msg)
            continue

        mid = get_mid_price(ob)
        if mid is None:
            msg, structured[exchange] = f"⚠️ {exchange}: Mid-price unavailable.", {"error": "Mid-price unavailable"}
            responses.append(msg)
            continue

        val, delta, pnl = compute_risk_metrics(data['spot_qty'], data['perp_qty'], mid, data['entry_price'])
        total_value += val
        total_delta += delta
        total_pnl += pnl

        if raw:
            structured[exchange] = {"mid_price": mid, "spot_qty": data['spot_qty'], "perp_qty": data['perp_qty'], "value": val, "delta": delta, "pnl": pnl}
        else:
            responses.append(f"📊 *{exchange} ({data['symbol']})*:\n"
                             f"• Mid-Price: `${mid:,.2f}`\n"
                             f"• Spot/Perp Qty: `{data['spot_qty']}` / `{data['perp_qty']}`\n"
                             f"• Value: `${val:,.2f}`\n"
                             f"• Delta: `{delta:,.4f}`\n"
                             f"• PnL: `${pnl:,.2f}`")

    if raw:
        var_estimate = round(0.02 * total_value, 2)
        structured['portfolio'] = {"value": total_value, "delta": total_delta, "pnl": total_pnl, "var": var_estimate}
        return structured
    
    return "\n\n".join(responses) if responses else "⚠️ No risk data found for your portfolio."

def calculate_dynamic_hedge(delta):
    hedge_qty = round(abs(delta), 3) # Bybit has 3 decimal precision for BTCUSDT orders
    MIN_QTY = 0.001
    return max(hedge_qty, MIN_QTY)

def start_risk_scan(user_id: int, stop_event: threading.Event):
    """
    The main risk scanning loop.
    This version is user-specific, stoppable, and uses the database correctly.
    """
    def scan_loop():
        # Each thread needs its own asyncio event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # The loop now checks the stop signal to terminate gracefully
        while not stop_event.is_set():
            try:
                print(f"[Risk Monitor] Scanning for user {user_id}...")
                
                risk_data = format_portfolio_risk(user_id, raw=True)
                
                if not isinstance(risk_data, dict):
                    print(f"[Risk Monitor] Invalid report format for user {user_id}.")
                    stop_event.wait(timeout=60) # Wait longer if there's an issue
                    continue

                # --- Delta-based risk alert ---
                if is_risk_high(risk_data):
                    print(f"[Alert] High delta triggered for user {user_id}!")
                    report_text = f"⚠️ *High Delta Alert\\!* \n\n{format_portfolio_risk(user_id)}"
                    loop.run_until_complete(alert_telegram(user_id, report_text))

                # --- Drawdown-based risk alert (using the database) ---
                portfolio_summary = risk_data.get("portfolio", {})
                total_value = portfolio_summary.get("value", 0)
                if total_value > 0:
                    drawdown_settings = db.get_or_create_drawdown_settings(user_id)
                    current_peak = drawdown_settings['peak_value']
                    
                    if total_value > current_peak:
                        db.update_drawdown_peak(user_id, total_value)
                        current_peak = total_value

                    if current_peak > 0:
                        drawdown = (current_peak - total_value) / current_peak
                        if drawdown > drawdown_settings['threshold']:
                            print(f"[Alert] Drawdown threshold breached for user {user_id}!")
                            drawdown_esc = escape_markdown(f"{drawdown:.2%}")
                            threshold_esc = escape_markdown(f"{drawdown_settings['threshold']:.2%}")
                            report_text = (f"⚠️ *Drawdown Alert\\!* \n"
                                           f"Drawdown: `{drawdown_esc}` \\(Threshold: `{threshold_esc}`\\)\n\n"
                                           f"{format_portfolio_risk(user_id)}")
                            loop.run_until_complete(alert_telegram(user_id, report_text))
            except Exception as e:
                print(f"[ScanLoop Error] for user {user_id}: {e}")
            
            # Wait for 30 seconds OR until the stop event is set
            stop_event.wait(timeout=30)
            
        print(f"[Risk Monitor] Stopped for user {user_id}.")

    threading.Thread(target=scan_loop, daemon=True).start()


def is_risk_high(risk_data: dict) -> bool:
    """Checks if the delta in the risk data exceeds the threshold."""
    try:
        if not isinstance(risk_data, dict):
            return False
        
        portfolio_summary = risk_data.get("portfolio", {})
        delta_val = portfolio_summary.get("delta", 0)
        
        # Set your delta risk threshold here
        if abs(delta_val) > 0.3:
            return True
        return False
    except Exception as e:
        print(f"[is_risk_high Error] {e}")
        return False


async def alert_telegram(chat_id: int, report: str):
    """Sends an alert message to the user using the global application instance."""
    global application
    try:
        if application:
            await application.bot.send_message(chat_id=chat_id, text=report, parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        print(f"[Alert Error] Failed to send message to {chat_id}: {e}")


async def monitor_risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Starts the background risk monitoring for the user.
    This function manages the 'active_monitors' dictionary.
    """
    global active_monitors
    
    user_id = update.effective_chat.id

    if user_id in active_monitors:
        await update.message.reply_text("ℹ️ Risk monitoring is already active.")
        return

    stop_event = threading.Event()
    active_monitors[user_id] = stop_event
    
    start_risk_scan(user_id, stop_event)
    
    await update.message.reply_text("✅ Risk monitoring started. You'll get alerts for high delta or drawdown. Use /stop_monitor to end.")


async def stop_monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Stops the background risk monitoring for the user.
    This function also manages the 'active_monitors' dictionary.
    """
    global active_monitors
    
    user_id = update.effective_chat.id
    
    if user_id in active_monitors:
        stop_event = active_monitors[user_id]
        stop_event.set()
        
        del active_monitors[user_id]
        
        await update.message.reply_text("✅ Risk monitoring has been stopped.")
    else:
        await update.message.reply_text("ℹ️ Risk monitoring is not currently active.")
# ========== EXCHANGE FETCHERS ==========
os.environ["SSL_CERT_FILE"] = certifi.where()
TOKEN = "7749628905:AAHtUYlgZZ1ofpWmwdZagskmZ3cLgo7zB8I"  # Replace with your bot token

def fetch_orderbook_bybit(raw=False):
    try:
        bybit = ccxt.bybit({'enableRateLimit': True})
        ob = bybit.fetch_order_book("BTC/USDT")
        return {"exchange": "Bybit", "bids": ob["bids"], "asks": ob["asks"]}
    except Exception as e:
        return {"exchange": "Bybit", "error": str(e)}

def fetch_orderbook_deribit():
    try:
        url = "https://www.deribit.com/api/v2/public/get_order_book?instrument_name=BTC-PERPETUAL"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()["result"]
        return {"exchange": "Deribit", "bids": data["bids"], "asks": data["asks"]}
    except Exception as e:
        return {"exchange": "Deribit", "error": str(e)}

# ========== TELEGRAM HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.get_or_create_drawdown_settings(update.effective_chat.id) # Ensure user exists in drawdown table
    keyboard = [[InlineKeyboardButton("📊 Portfolio Risk", callback_data='risk')], [InlineKeyboardButton("🛡️ Hedge Position", callback_data='hedge')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to CryptoRiskGuard Bot 🛡️\n"
                                    "Use /view_portfolio, /add_position, /sync, and /add_api to manage your data.", reply_markup=reply_markup)

async def portfolio_dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    risk_data = format_portfolio_risk(user_id, raw=True)
    if isinstance(risk_data, str):
        await update.message.reply_text(risk_data)
        return
    
    summary = risk_data.get('portfolio', {})
    report = (f"📊 *Portfolio Dashboard*\n\n"
              f"• Total Value: `${summary.get('value', 0):,.2f}`\n"
              f"• Total Delta: `{summary.get('delta', 0):,.4f}`\n"
              f"• Total PnL: `${summary.get('pnl', 0):,.2f}`\n"
              f"• Est. VaR (2%): `${summary.get('var', 0):,.2f}`\n\n"
              f"*{'-'*20}*\n\n"
              f"{format_portfolio_risk(user_id)}") # Append detailed breakdown
    await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id 
    
    if query.data == "risk":
        risk_report = format_portfolio_risk(user_id)
        await query.edit_message_text(risk_report, parse_mode=ParseMode.MARKDOWN)
    elif query.data == "hedge":
        await query.edit_message_text("🛡️ Calculating dynamic hedge...")
        risk_data = format_portfolio_risk(user_id, raw=True)
        if isinstance(risk_data, str):
            await context.bot.send_message(chat_id=user_id, text=f"❌ Cannot hedge: {risk_data}")
            return
        current_delta = risk_data.get('portfolio', {}).get('delta', 0)
        if abs(current_delta) < 0.001:
            await context.bot.send_message(chat_id=user_id, text="✅ Delta is neutral. No hedge needed.")
            return
        qty, side = calculate_dynamic_hedge(current_delta), "Sell" if current_delta > 0 else "Buy"
        success, message = place_hedge_order(symbol="BTCUSDT", side=side, qty=str(qty))
        await context.bot.send_message(chat_id=user_id, text=message)

# --- REPLACEMENT hedge_status_command ---
async def hedge_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides a preview of the hedge action without executing it."""
    user_id = update.effective_chat.id
    await update.message.reply_text("🔎 Checking hedge status...")

    risk_data = format_portfolio_risk(user_id, raw=True)
    if isinstance(risk_data, str):
        # We will NOT use any markdown here to be safe
        await update.message.reply_text(f"❌ Cannot check status: {risk_data}")
        return

    current_delta = risk_data.get('portfolio', {}).get('delta', 0)
    
    # --- NEUTRAL STATUS ---
    if abs(current_delta) < 0.001:
        # NO MARKDOWN
        report = (
            f"Hedge Status: Delta Neutral\n\n"
            f"Your current total delta is {current_delta:.4f}.\n"
            f"No hedge action is required."
        )
        await update.message.reply_text(report) # NO PARSE MODE
        return

    # --- ACTION REQUIRED STATUS ---
    qty_to_hedge = calculate_dynamic_hedge(current_delta)
    side_to_hedge = "Sell" if current_delta > 0 else "Buy"

    # NO MARKDOWN
    report = (
        f"Hedge Status: Action Required\n\n"
        f"Your current total delta is {current_delta:.4f}.\n\n"
        f"Proposed Hedge Action:\n"
        f"  - Side: {side_to_hedge}\n"
        f"  - Quantity: {qty_to_hedge:.3f} BTC\n\n"
        f"To execute this trade, run /hedge_now or use the inline button."
    )
    await update.message.reply_text(report) # NO PARSE MODE

def escape_markdown(text: str) -> str:
    """Helper function to escape telegram markdown v2 characters."""
    # Note: We escape a specific set of characters required by Telegram's MarkdownV2
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in str(text))
async def hedge_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executes the hedge action immediately."""
    user_id = update.effective_chat.id
    await update.message.reply_text("🛡️ Executing hedge now...")

    risk_data = format_portfolio_risk(user_id, raw=True)
    if isinstance(risk_data, str):
        await update.message.reply_text(f"❌ Cannot hedge: {risk_data}")
        return

    current_delta = risk_data.get('portfolio', {}).get('delta', 0)
    
    if abs(current_delta) < 0.001:
        await update.message.reply_text("✅ Delta is already neutral. No hedge needed.")
        return

    qty = calculate_dynamic_hedge(current_delta)
    side = "Sell" if current_delta > 0 else "Buy"

    # This calls your existing function to place the order
    success, message = place_hedge_order(symbol="BTCUSDT", side=side, qty=str(qty))
    
    # Send the result back to the user
    await update.message.reply_text(message)
async def set_drawdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    try:
        threshold = float(context.args[0])
        if not (0 < threshold < 1): raise ValueError("Threshold must be between 0 and 1.")
        db.set_drawdown_threshold(user_id, threshold)
        await update.message.reply_text(f"✅ Drawdown alert threshold set to {threshold:.2%}")
    except (ValueError, IndexError):
        # --- MODIFIED: Cleaned up usage string for MARKDOWN_V2 ---
        usage = (
            "❌ *Invalid Usage*\n"
            "Usage: `/set_drawdown <value>`\n"
            "Example: `/set_drawdown 0.15` for 15%"
        )
        await update.message.reply_text(usage, parse_mode=ParseMode.MARKDOWN_V2)

# --- NEW COMMANDS FOR PORTFOLIO & API MANAGEMENT ---
async def view_portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = format_portfolio_risk(update.effective_chat.id)
    await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)

async def add_position_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, args = update.effective_chat.id, context.args
    # --- MODIFIED: Cleaned up usage string for MARKDOWN_V2 ---
    usage = (
        "Usage: `/add_position <Exchange> <Symbol> <SpotQty> <PerpQty> <Entry>`\n"
        "Example: `/add_position Bybit BTC/USDT 1.2 -1.1 29000`"
    )
    if len(args) != 5:
        # --- MODIFIED: Using MARKDOWN_V2 ---
        await update.message.reply_text(usage, parse_mode=ParseMode.MARKDOWN_V2)
        return
    try:
        exchange, symbol, spot_qty, perp_qty, entry = args
        db.add_or_update_position(user_id, exchange.title(), symbol.upper(), float(spot_qty), float(perp_qty), float(entry))
        await update.message.reply_text(f"✅ Position for {symbol.upper()} on {exchange.title()} saved.")
    except ValueError:
        await update.message.reply_text(f"Invalid number format.\n\n{usage}", parse_mode=ParseMode.MARKDOWN_V2)

async def remove_position_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, args = update.effective_chat.id, context.args
    # --- MODIFIED: Cleaned up usage string for MARKDOWN_V2 ---
    usage = (
        "Usage: `/remove_position <Exchange> <Symbol>`\n"
        "Example: `/remove_position Bybit BTC/USDT`"
    )
    if len(args) != 2:
        # --- MODIFIED: Using MARKDOWN_V2 ---
        await update.message.reply_text(usage, parse_mode=ParseMode.MARKDOWN_V2)
        return
    exchange, symbol = args
    db.remove_position(user_id, exchange.title(), symbol.upper())
    await update.message.reply_text(f"✅ Position for {symbol.upper()} on {exchange.title()} removed.")

async def add_api_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, args = update.effective_chat.id, context.args
    # --- MODIFIED: Cleaned up usage string for MARKDOWN_V2 ---
    usage = (
        "Usage: `/add_api <Exchange> <ApiKey> <SecretKey>`\n\n"
        "⚠️ *Warning: API keys are stored in a local database\\.*" # Note the escaped dot
    )
    if len(args) != 3:
        # --- MODIFIED: Using MARKDOWN_V2 ---
        await update.message.reply_text(usage, parse_mode=ParseMode.MARKDOWN_V2)
        return
    exchange, api_key, secret = args
    db.save_api_keys(user_id, exchange.title(), api_key, secret)
    await update.message.reply_text(f"✅ API keys for {exchange.title()} saved. Use `/sync` to fetch positions.")

async def sync_bybit_portfolio(user_id):
    keys = db.get_api_keys(user_id, "Bybit")
    if not keys: return "No Bybit API keys found. Use /add_api."
    try:
        bybit = ccxt.bybit({**keys, 'options': {'defaultType': 'swap'}})
        positions = bybit.fetch_positions(params={'category': 'linear'})
        btc_perp = next((p for p in positions if p['info']['symbol'] == 'BTCUSDT'), None)
        perp_qty = float(btc_perp['contracts']) * (-1 if btc_perp['side'] == 'short' else 1) if btc_perp else 0
        entry_price = float(btc_perp['entryPrice']) if btc_perp else 0
        balances = bybit.fetch_balance(params={'accountType': 'UNIFIED'})
        spot_qty = float(balances.get('BTC', {}).get('total', 0))
        db.add_or_update_position(user_id, "Bybit", "BTC/USDT", spot_qty, perp_qty, entry_price)
        return f"✅ *Bybit Sync Complete:*\n  - Spot: `{spot_qty}` BTC\n  - Perp: `{perp_qty}` BTC"
    except Exception as e:
        return f"❌ *Bybit Sync Failed:*\n`{str(e)}`"

async def sync_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    await update.message.reply_text("🔄 Syncing portfolio from exchanges...")
    bybit_status = await sync_bybit_portfolio(user_id)
    await update.message.reply_text(bybit_status, parse_mode=ParseMode.MARKDOWN)

# ========== BOOTSTRAP BOT ==========
if __name__ == "__main__":
    db.init_db()
    app_builder = ApplicationBuilder().token(TOKEN)
    application = app_builder.build()
    print("Bot is running...")

    handlers = [
        CommandHandler("start", start),
        CommandHandler("dashboard", portfolio_dashboard_command),
        CommandHandler("monitor_risk", monitor_risk_command),
        CommandHandler("hedge_status", hedge_status_command),
        CommandHandler("hedge_now", hedge_now_command),
        CommandHandler("stop_monitor", stop_monitor_command),
        CommandHandler("set_drawdown", set_drawdown_command),
        CommandHandler("view_portfolio", view_portfolio_command),
        CommandHandler("add_position", add_position_command),
        CommandHandler("remove_position", remove_position_command),
        CommandHandler("add_api", add_api_command),
        CommandHandler("sync", sync_command),
        CallbackQueryHandler(handle_buttons)
    ]
    application.add_handlers(handlers)
    application.run_polling()