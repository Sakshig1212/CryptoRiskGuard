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
---

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
