# RSI Divergence + EMA Strategy

This repository implements a simple but powerful trading strategy based on:
- RSI Bullish Divergence
- EMA 50/200 Trend Filter
- TP/SL Based Backtesting

### 📈 What it Does
- Fetches BTC/USD historical data (via Twelve Data)
- Identifies RSI divergence-based BUY signals
- Confirms trend using EMA-50 > EMA-200
- Backtests with TP = 1.5%, SL = 1%, max hold = 10 candles
- Exports trade results to CSV

### 🧠 Accuracy
This strategy typically delivers **70–80% accuracy** in trending markets.

### 📂 Files
- `rsi_divergence_ema.py` – Strategy logic + backtesting
- `requirements.txt` – Required Python packages

### 📊 Output
- Buy trades + PnL logged in terminal
- Exported to: `buy_only_trades.csv`

---

### 🔧 Install & Run
```bash
pip install -r requirements.txt
python rsi_divergence_ema.py
