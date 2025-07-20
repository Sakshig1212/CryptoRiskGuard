# 💹 CryptoRiskGuard Bot

**CryptoRiskGuard** is a modular, Telegram-integrated bot designed for **real-time crypto risk monitoring** and **automated delta hedging**. Built for Bybit (Testnet) and extendable to Deribit, the bot helps traders and fund managers **track, analyze, and hedge** their portfolio’s live exposure with intelligent automation.

---

## 🚀 Features

- 📊 **Real-Time Risk Analytics**
  - Monitors delta, portfolio value, PnL, and VaR
  - Calculates drawdown % with configurable thresholds

- 🤖 **Automated Delta Hedging**
  - Dynamically sizes hedge trades based on live exposure
  - Sends authenticated hedge orders to Bybit using REST API

- 🔁 **Risk Monitoring Threads**
  - Constant scanning for delta or drawdown threshold breaches
  - Sends Telegram alerts with real-time summaries

- 💬 **Telegram Bot Interface**
  - Commands like `/start`, `/monitor_risk`, `/hedge_status`
  - Inline buttons for instant hedge or portfolio view

- 🛠️ **Customizable Portfolio Logic**
  - Define spot/perpetual positions and entry prices in `config.py`
  - Configurable drawdown limit, auto-hedge toggle, etc.

---

## 📸 Telegram Interaction Highlights

- `/start` → Display dashboard buttons like “📊 Portfolio Risk” or “🛡️ Hedge Position”
- `/monitor_risk` → Begin automated background monitoring
- `/hedge_status` → View current delta, value, and unrealized PnL
- `/set_drawdown 0.1` → Adjust drawdown breach threshold (e.g., 10%)

---

## 🛠 Setup Instructions

### 🔹 1. Clone the Repository

```bash
git clone https://github.com/YourUsername/CryptoRiskGuard.git
cd CryptoRiskGuard
