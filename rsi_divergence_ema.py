import pandas as pd
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.ion()
import os
os.makedirs("backtests", exist_ok=True)

# ------------------------------------------
# Data Fetching (6 months)
# ------------------------------------------
def fetch_data(symbol="BTC/USD", interval="1h", api_key=None):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize=4000&apikey={api_key}"
    response = requests.get(url)
    data = response.json()

    if 'values' not in data:
        raise Exception(f"Error fetching data: {data.get('message', 'Unknown error')}")

    df = pd.DataFrame(data['values'])
    df = df.rename(columns={'datetime': 'date', 'close': 'close'})
    df['date'] = pd.to_datetime(df['date'])
    df['close'] = df['close'].astype(float)
    df = df.sort_values('date').reset_index(drop=True)
    return df

# ------------------------------------------
# Indicators
# ------------------------------------------
def calculate_indicators(df, rsi_period=14):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=rsi_period).mean()
    avg_loss = loss.rolling(window=rsi_period).mean()

    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    return df

# ------------------------------------------
# Detect Bullish Divergence + EMA Filter
# ------------------------------------------
def find_divergence_signals(df):
    signals = []
    for i in range(2, len(df) - 2):
        if df['RSI'].iloc[i - 2] < df['RSI'].iloc[i] < 35:  # Bullish RSI divergence (simplified)
            if df['close'].iloc[i] > df['EMA_50'].iloc[i] > df['EMA_200'].iloc[i]:
                signals.append((df['date'].iloc[i], 'BUY'))
    return signals

# ------------------------------------------
# Backtesting
# ------------------------------------------
def calculate_max_drawdown(pnl_list):
    equity = [0]
    for p in pnl_list:
        equity.append(equity[-1] + p)

    peak = equity[0]
    drawdowns = []
    for val in equity:
        if val > peak:
            peak = val
        drawdown = peak - val
        drawdowns.append(drawdown)
    return max(drawdowns)

def backtest_with_tp_sl(df, signals, tp_pct=0.02, sl_pct=0.01, max_hold=10):
    trades = []
    pnl = []

    for time, signal in signals:
        if signal != "BUY":
            continue

        entry_index = df.index[df['date'] == time].tolist()
        if not entry_index:
            continue
        entry_index = entry_index[0]
        entry_price = df.at[entry_index, 'close']
        tp_price = entry_price * (1 + tp_pct)
        sl_price = entry_price * (1 - sl_pct)

        exit_price = None
        outcome = None

        for j in range(1, max_hold + 1):
            if entry_index + j >= len(df):
                break
            current_price = df.at[entry_index + j, 'close']
            if current_price >= tp_price:
                exit_price = tp_price
                outcome = 'TP'
                break
            elif current_price <= sl_price:
                exit_price = sl_price
                outcome = 'SL'
                break

        if not exit_price:
            exit_price = df.at[min(entry_index + max_hold, len(df)-1), 'close']
            outcome = 'TimeExit'

        profit = exit_price - entry_price
        pnl.append(profit)
        trades.append((time, entry_price, exit_price, profit, outcome))

    if not pnl:
        print("\nNo trades executed based on TP/SL logic.")
        return []

    win_rate = sum(1 for p in pnl if p > 0) / len(pnl) * 100
    total_pnl = sum(pnl)
    max_drawdown = calculate_max_drawdown(pnl)

    print("\nBacktest with TP/SL:")
    print(f"Total Trades: {len(pnl)}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total PnL: {total_pnl:.2f}")
    print(f"Max Drawdown: {max_drawdown:.2f}")

    for trade in trades:
        print(f"\nBUY @ {trade[0]}: Entry = {trade[1]:.2f}, Exit = {trade[2]:.2f}, PnL = {trade[3]:.2f}, Outcome = {trade[4]}")

 # Export to CSV
    df_trades = pd.DataFrame(trades, columns=["Timestamp", "Entry Price", "Exit Price", "PnL", "Outcome"])
    df_trades.to_csv("backtests/buy_only_trades.csv", index=False)
    print("\n✅ Trade results exported to 'backtests/buy_only_trades.csv'")
    return trades

# ------------------------------------------
# Plotting
# ------------------------------------------
def plot_strategy(df, signals, trades):
    plt.figure(figsize=(14, 8))
    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(df['date'], df['close'], label='Close Price', color='blue', linewidth=1)
    ax1.plot(df['date'], df['EMA_50'], label='EMA 50', color='orange', linestyle='--')
    ax1.plot(df['date'], df['EMA_200'], label='EMA 200', color='red', linestyle='--')

    for time, signal in signals:
        if signal == "BUY":
            price = df[df['date'] == time]['close'].values[0]
            ax1.scatter(time, price, marker='^', color='green', s=100, label='BUY')

    for trade in trades:
        exit_time = trade[0]
        outcome = trade[4]
        price = df[df['date'] == exit_time]['close'].values[0]
        color = 'red' if outcome == 'SL' else 'gold' if outcome == 'TimeExit' else 'green'
        ax1.scatter(exit_time, price, marker='v', color=color, s=100, label=outcome)

    ax1.set_title("BTC/USD - RSI Divergence + EMA Strategy")
    ax1.legend()
    ax1.grid(True)

    ax2 = plt.subplot(2, 1, 2)
    ax2.plot(df['date'], df['RSI'], label='RSI 14', color='purple')
    ax2.axhline(70, linestyle='--', color='red')
    ax2.axhline(30, linestyle='--', color='green')
    ax2.set_title("RSI (14)")
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout()
    plt.savefig("backtests/trade_chart.png")
    print("📊 Trade chart saved as 'backtests/trade_chart.png'")
# ------------------------------------------
# Main
# ------------------------------------------
def main():
    with open("config/api_key.txt", "r") as f:
        api_key = f.read().strip()
        print("API Key Loaded")

    symbol = "BTC/USD"
    df = fetch_data(symbol=symbol, api_key=api_key)
    df = calculate_indicators(df)
    signals = find_divergence_signals(df)

    print(f"\nTotal signals: {len(signals)}")
    for sig in signals[-5:]:
        print(sig)

    trades = backtest_with_tp_sl(df, signals, tp_pct=0.02, sl_pct=0.01, max_hold=10)
    if trades:
        plot_strategy(df, signals, trades)

# ------------------------------------------
# Entry Point
# ------------------------------------------
if __name__ == "__main__":
    main()

