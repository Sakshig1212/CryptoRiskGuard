# # risk_bot.py
# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
# import os, certifi

# os.environ["SSL_CERT_FILE"] = certifi.where()

# TOKEN = "7749628905:AAHtUYlgZZ1ofpWmwdZagskmZ3cLgo7zB8I"

# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     keyboard = [
#         [InlineKeyboardButton("📊 Portfolio Risk", callback_data='risk')],
#         [InlineKeyboardButton("🛡️ Hedge Position", callback_data='hedge')],
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
#     await update.message.reply_text("Welcome to CryptoRiskGuard Bot 🛡️", reply_markup=reply_markup)

# async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()
#     if query.data == 'risk':
#         await query.edit_message_text("📊 Risk metrics are being calculated...")
#     elif query.data == 'hedge':
#         await query.edit_message_text("🛡️ Setting up automatic hedge...")

# if __name__ == '__main__':
#     app = ApplicationBuilder().token(TOKEN).build()
#     app.add_handler(CommandHandler("start", start))
#     app.add_handler(CallbackQueryHandler(handle_buttons))
#     app.run_polling()

#-----------------------this code is for metrics added-------------
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import os
import certifi
import ccxt
import requests
import json
import ccxt
import requests
import config
from config import BYBIT_API_KEY, BYBIT_SECRET
from bybit_hedge import place_hedge_order
application = None  # global reference




user_portfolio = {
    "BTC/USDT": {
        "spot_qty": 0.8,
        "perp_qty": -0.5,
        "entry_price": 27350.0
    },
    "ETH/USDT": {
        "spot_qty": 2.0,
        "perp_qty": 0,
        "entry_price": 1500.0
    }
}
portfolio_data = {
    "OKX": {
        "spot_qty": 0.5,
        "perp_qty": -0.4,
        "entry_price": 30000
    },
    "Bybit": {
        "spot_qty": 1.2,
        "perp_qty": -1.1,
        "entry_price": 29000
    },
    "Deribit": {
        "spot_qty": 0.3,
        "perp_qty": -0.3,
        "entry_price": 31000
    }
}


def get_mid_price(ob):
    try:
        print("🛠️ [DEBUG] Received OB:", ob)
        
        # Check keys and non-empty lists
        if not isinstance(ob, dict):
            print("⚠️ Not a dictionary.")
            return None
        
        bids = ob.get("bids", [])
        asks = ob.get("asks", [])
        
        if not bids or not asks:
            print("⚠️ Bids or Asks empty.")
            return None
        
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = (best_bid + best_ask) / 2

        print(f"✅ Mid-price calculated: {mid_price}")
        return mid_price

    except Exception as e:
        print("❌ [get_mid_price] Error:", e)
        return None




def compute_risk_metrics(spot_qty, perp_qty, mid_price, entry_price):
    net_position = spot_qty + perp_qty
    position_value = net_position * mid_price
    delta = net_position
    pnl = (mid_price - entry_price) * perp_qty
    return position_value, delta, pnl

# --- Risk Metrics Formatter ---
def format_portfolio_risk(raw=False):
    responses = []
    structured = {}  # for raw output
    # structured1 = {
    #     "Bybit": {
    #         "mid": 117642.85,
    #         "spot_qty": 1.2,
    #         "perp_qty": -1.1,
    #         "value": 11764.28,
    #         "delta": 0.6,  # 🚨 Trigger: > 0.3 delta
    #         "pnl": -15000.00
    #     },
    #     "Deribit": {
    #         "mid": 117699.75,
    #         "spot_qty": 0.3,
    #         "perp_qty": -0.3,
    #         "value": 0.0,
    #         "delta": 0.0,
    #         "pnl": -25949.92
    #     },
    #     "portfolio": {
    #         "value": 11764.28,
    #         "delta": 0.6,  # 🚨 Trigger here too
    #         "pnl": -40949.92,
    #         "var": 234.86
    #     }
    # }
    sources = [
        ('Bybit', fetch_orderbook_bybit(raw=True)),
        ('Deribit', fetch_orderbook_deribit())
    ]

    for exchange, ob in sources:
        if "error" in ob:
            msg = f"❌ {exchange}: {ob['error']}"
            responses.append(msg)
            structured[exchange] = {"error": ob["error"]}
            continue

        mid = get_mid_price(ob)
        if mid is None:
            msg = f"⚠️ {exchange}: Mid-price unavailable. Skipping risk metrics."
            responses.append(msg)
            structured[exchange] = {"error": "Mid-price unavailable"}
            continue

        data = portfolio_data.get(exchange)
        if data is None:
            msg = f"⚠️ {exchange}: No portfolio data."
            responses.append(msg)
            structured[exchange] = {"error": "No portfolio data"}
            continue

        val, delta, pnl = compute_risk_metrics(
            data['spot_qty'], data['perp_qty'], mid, data['entry_price']
        )

        if raw:
            structured[exchange] = {
                "mid_price": mid,
                "spot_qty": data['spot_qty'],
                "perp_qty": data['perp_qty'],
                "value": val,
                "delta": delta,
                "pnl": pnl
            }
        else:
            responses.append(
                f"📊 {exchange}:\n"
                f"• Mid-Price: ${mid:,.2f}\n"
                f"• Spot Qty: {data['spot_qty']}\n"
                f"• Perp Qty: {data['perp_qty']}\n"
                f"• Value: ${val:,.2f}\n"
                f"• Delta: {delta:,.4f}\n"
                f"• PnL: ${pnl:,.2f}"
            )

    if raw:
        return structured
    return "\n\n".join(responses) if responses else "⚠️ No risk data found."
   

def calculate_hedge_amount(spot_qty, perp_qty):
    return -(spot_qty + perp_qty)  # opposite of current delta

def execute_auto_hedge():
    print("⚙️ Executing auto hedge...")

    # Load portfolio data
    data = portfolio_data.get("Bybit")
    if not data:
        return "❌ No portfolio data for Bybit."

    ob = fetch_orderbook_bybit(raw=True)
    if "error" in ob:
        return f"❌ Orderbook fetch error: {ob['error']}"

    mid = get_mid_price(ob)
    if mid is None:
        return "⚠️ Mid-price unavailable."

    _, delta, _ = compute_risk_metrics(data['spot_qty'], data['perp_qty'], mid, data['entry_price'])

    if abs(delta) < 0.0001:
        return "✅ Delta already neutral. No hedge needed."

    # Prepare hedge order
    hedge_side = 'sell' if delta > 0 else 'buy'
    hedge_qty = round(abs(delta), 3)

    try:
        bybit = ccxt.bybit({
            'apiKey': BYBIT_API_KEY, 
            'secret': BYBIT_SECRET,
            'enableRateLimit': True
        })

        bybit.load_markets()
        market = 'BTC/USDT:USDT'
        print(f"📈 Placing {hedge_side.upper()} order for {hedge_qty} BTC on Bybit Perp...")
        order = bybit.create_market_order(market, hedge_side, hedge_qty)

        # Update portfolio data to reflect new hedge
        if hedge_side == 'buy':
            data['perp_qty'] += hedge_qty
        else:
            data['perp_qty'] -= hedge_qty

        return f"✅ Hedged {hedge_qty} BTC via {hedge_side.upper()} on Bybit Perp."

    except Exception as e:
        return f"❌ Hedge order failed: {e}"



import threading
import asyncio
import time
import asyncio
import threading
import time
application = None  


def start_risk_scan(user_chat_id):
    def scan_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while True:
            try:
                print("[Risk Monitor] Scanning...")

                report = format_portfolio_risk(raw=True)
                if not isinstance(report, dict):
                    print("[Risk Monitor] Invalid report format.")
                    time.sleep(30)
                    continue

                # Delta-based risk alert
                if is_risk_high(report):
                    print("[Alert] High delta triggered!")
                    loop.run_until_complete(alert_telegram(
                        user_chat_id,
                        f"⚠️ High Delta:\n\n{format_portfolio_risk()}"
                    ))

                # Drawdown-based risk alert
                total_value = report.get("total_value", 0)
                if total_value <= 0:
                    print("[Risk Monitor] Skipping drawdown check due to invalid total_value.")
                    time.sleep(30)
                    continue

                drawdown = update_drawdown(total_value)
                if drawdown > drawdown_data["threshold"]:
                    print("[Alert] Drawdown threshold breached!")
                    loop.run_until_complete(alert_telegram(
                        user_chat_id,
                        f"⚠️ Drawdown Alert:\n"
                        f"Drawdown = {drawdown:.2%}\n"
                        f"Threshold = {drawdown_data['threshold']:.2%}\n\n"
                        f"{format_portfolio_risk()}"
                    ))

            except Exception as e:
                print("[ScanLoop Error]", str(e))

            time.sleep(30)

    threading.Thread(target=scan_loop, daemon=True).start()




def is_risk_high(risk_data):
    try:
        # If risk_data is a string, convert it to a dict-like fallback or skip
        if isinstance(risk_data, str):
            print("[Risk Check Error] Expected dict, got string.")
            return False
        
        portfolio = risk_data.get("portfolio", {})
        delta_val = portfolio.get("delta", 0)
        if abs(delta_val) > 0.3:
            return True
        return False
    except Exception as e:
        print("[Risk Check Error]", e)
        return False



async def alert_telegram(chat_id, report):
    try:
        await app.bot.send_message(chat_id=chat_id, text=f"⚠️ RISK THRESHOLD BREACHED:\n\n{report}")
    except Exception as e:
        print(f"[Alert Error] {e}")

async def hedge_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get current risk metrics
    risk = format_portfolio_risk(raw=True)  # raw=True returns a dict
    delta = risk.get("delta", 0)

    # Calculate required hedge qty
    hedge_qty = calculate_dynamic_hedge(delta)

    # Decide side (Buy if delta is negative, Sell if positive)
    side = "Buy" if delta < 0 else "Sell"

    # Place hedge order
    success, message = place_hedge_order(symbol="BTCUSDT", side=side, qty=str(hedge_qty))

    await update.message.reply_text(message)


async def hedge_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = format_portfolio_risk()
    if not report.strip():
        report = "❌ No hedge data available."
    await update.message.reply_text(f"📊 Hedge Status:\n{report}")

async def monitor_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    await update.message.reply_text("✅ Risk monitoring started. You’ll get alerts when risk thresholds are exceeded.")
    start_risk_scan(user_id)

async def auto_hedge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛡️ Auto-hedging activated. Currently placeholder logic.")

# hedge_utils.py

def calculate_dynamic_hedge(delta):
    """
    Returns hedge quantity needed to neutralize delta exposure.
    Ensures minimum qty for Bybit (0.001 BTC).
    """
    try:
        hedge_qty = round(abs(delta), 4)  # Hedge against total delta directly

        # Enforce exchange minimum contract size
        MIN_QTY = 0.001
        if hedge_qty < MIN_QTY:
            hedge_qty = MIN_QTY

        return hedge_qty
    except Exception as e:
        print("[HedgeCalc Error]", e)
        return 0



os.environ["SSL_CERT_FILE"] = certifi.where()
TOKEN = "7749628905:AAHtUYlgZZ1ofpWmwdZagskmZ3cLgo7zB8I"


# ========== EXCHANGE FETCHERS ==========


def fetch_orderbook_okx():
    try:
        okx = ccxt.okx({'enableRateLimit': True})
        okx.load_markets()
        ob = okx.fetch_order_book("BTC-USDT-SWAP")
        return {
            "exchange": "OKX",
            "bids": ob["bids"],
            "asks": ob["asks"]
        }
    except Exception as e:
        return {"exchange": "OKX", "error": str(e)}

import ccxt
from config import BYBIT_API_KEY, BYBIT_SECRET
def format_book(bids, asks):
    msg = "📉 Bids:\n"
    for price, qty in bids:
        msg += f"• {qty:.4f} @ ${price:.2f}\n"

    msg += "\n📈 Asks:\n"
    for price, qty in asks:
        msg += f"• {qty:.4f} @ ${price:.2f}\n"

    return msg
#     return {
#     "delta": 0.275,
#     "spot_size": 1.2,
#     "details": formatted_text
# }
def compute_portfolio_dashboard():
    total_val = 0
    total_delta = 0
    total_pnl = 0
    summary_lines = []

    for exchange in ["Bybit", "Deribit"]:
        try:
            ob = fetch_orderbook_bybit(raw=True) if exchange == "Bybit" else fetch_orderbook_deribit()
            mid = get_mid_price(ob)
            data = portfolio_data.get(exchange)

            if mid is None or data is None:
                continue

            val, delta, pnl = compute_risk_metrics(
                data['spot_qty'], data['perp_qty'], mid, data['entry_price']
            )

            total_val += val
            total_delta += delta
            total_pnl += pnl

            summary_lines.append(
                f"📍 {exchange}:\n"
                f"• Mid: ${mid:,.2f}\n"
                f"• Spot: {data['spot_qty']}, Perp: {data['perp_qty']}\n"
                f"• Value: ${val:,.2f}\n"
                f"• Delta: {delta:.4f}, PnL: ${pnl:.2f}\n"
            )

        except Exception as e:
            summary_lines.append(f"❌ {exchange} error: {e}")

    var_estimate = round(0.02 * total_val, 2)  # Simplified 2% VaR

    summary_lines.append("\n📊 Portfolio Summary:")
    summary_lines.append(f"• Total Value: ${total_val:,.2f}")
    summary_lines.append(f"• Total Delta: {total_delta:.4f}")
    summary_lines.append(f"• Total PnL: ${total_pnl:,.2f}")
    summary_lines.append(f"• Estimated VaR (2%): ${var_estimate:,.2f}")

    return "\n".join(summary_lines)


def fetch_orderbook_bybit(raw=False):
    try:
        bybit = ccxt.bybit({'enableRateLimit': True})
        bybit.load_markets()
        ob = bybit.fetch_order_book("BTC/USDT")
        
        if raw:
            return {
                "exchange": "Bybit",
                "bids": ob["bids"],
                "asks": ob["asks"]
            }
        
        # For normal display
        formatted = "🟡 Bybit\n📉 Bids:\n" + \
            "\n".join([f"• {b[1]:.4f} @ ${b[0]:,.2f}" for b in ob["bids"][:2]])
        formatted += "\n\n📈 Asks:\n" + \
            "\n".join([f"• {a[1]:.4f} @ ${a[0]:,.2f}" for a in ob["asks"][:2]])
        
        return formatted

    except Exception as e:
        if raw:
            return {"exchange": "Bybit", "error": str(e)}
        return f"❌ Bybit Error: {e}"




def fetch_orderbook_deribit():
    try:
        url = "https://www.deribit.com/api/v2/public/get_order_book?instrument_name=BTC-PERPETUAL"
        response = requests.get(url)
        data = response.json()["result"]
        return {
            "exchange": "Deribit",
            "bids": data["bids"],
            "asks": data["asks"]
        }
    except Exception as e:
        return {"exchange": "Deribit", "error": str(e)}
drawdown_data = {
    "peak_value": 0,
    "max_drawdown": 0,
    "threshold": 0.10  # 10% default
}

def update_drawdown(current_value):
    if current_value > drawdown_data["peak_value"]:
        drawdown_data["peak_value"] = current_value

    if drawdown_data["peak_value"] == 0:
        return 0

    drawdown = (drawdown_data["peak_value"] - current_value) / drawdown_data["peak_value"]
    drawdown_data["max_drawdown"] = max(drawdown_data["max_drawdown"], drawdown)

    return drawdown



# ========== TELEGRAM HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Portfolio Risk", callback_data='risk')],
        [InlineKeyboardButton("🛡️ Hedge Position", callback_data='hedge')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to CryptoRiskGuard Bot 🛡️", reply_markup=reply_markup)

async def portfolio_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = compute_portfolio_dashboard()
    await update.message.reply_text(report)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "risk":
        risk_report = format_portfolio_risk()
        if not risk_report.strip():
            risk_report = "❌ No risk data available."
        await query.edit_message_text(risk_report)

    # elif query.data == "hedge":
    #  await query.edit_message_text("🛡️ Placing hedge order...")

    # # Example: Buy 0.001 BTC at $10000
    # success, message = place_hedge_order(symbol="BTCUSDT", side="Buy", qty="0.001")
   
    elif query.data == "hedge":
           await query.edit_message_text("🛡️ Placing dynamic hedge...")

        # Step 1: Get current delta
           risk = format_portfolio_risk(raw=True)  # You must return dict with delta
           current_delta = risk.get("delta", 0)
           spot_size = risk.get("spot_size", 1)  # default to 1 BTC if not available

        # Step 2: Calculate hedge qty
           qty = calculate_dynamic_hedge(current_delta)

        # Step 3: Place hedge
           success, message = place_hedge_order(
            symbol="BTCUSDT", side="Sell" if current_delta > 0 else "Buy", qty=str(qty)
        )

           await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message
    )

async def set_drawdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        threshold = float(context.args[0])
        drawdown_data["threshold"] = threshold
        await update.message.reply_text(f"✅ Drawdown alert threshold set to {threshold:.2%}")
    except:
        await update.message.reply_text("❌ Usage: /set_drawdown <value>. Example: /set_drawdown 0.1")




# ========== BOOTSTRAP BOT ==========

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    print("Bot is running... Visit Telegram and click your buttons")
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("monitor_risk", monitor_risk))
    app.add_handler(CommandHandler("hedge_status", hedge_status))
    app.add_handler(CommandHandler("hedge_now", hedge_now_command))
    app.add_handler(CommandHandler("dashboard", portfolio_dashboard))
    app.add_handler(CommandHandler("set_drawdown", set_drawdown))


    app.add_handler(CallbackQueryHandler(handle_buttons))

   
    app.run_polling()











# import httpx
# import certifi

# client = httpx.Client(verify=certifi.where())
# try:
#     r = client.get("https://api.telegram.org/bot7749628905:AAHtUYlgZZ1ofpWmwdZagskmZ3cLgo7zB8I/getMe")
#     print(r.status_code)
#     print(r.text)
# except Exception as e:
#     print("Connection failed:", e)
