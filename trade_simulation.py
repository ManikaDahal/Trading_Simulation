import pandas as pd
import os

# --- CONFIGURATION ---
DATA_DIR = "stocks"
START_DATE = pd.to_datetime("2021-01-25")
END_DATE = pd.to_datetime("2026-01-25")

MIN_BUY_QTY = 15        # Minimum shares per trade
BASE_CASH_PERCENT = 0.2 # Fraction of cash to use per trade
TAKE_PROFIT = 1.10      # 10% rise
STOP_LOSS = 0.95        # 5% fall

# --- LOAD INITIAL PORTFOLIO ---
portfolio = pd.read_csv("initial_investment15.csv").set_index("Stock")[["Quantity"]]
cash = pd.read_csv("cash_summary15.csv")["Remaining_Cash"][0]

transactions = [] 

# --- LOAD STOCK DATA ---
stock_data = {}
last_buy_price = {}

for file in os.listdir(DATA_DIR):
    stock = file.replace(".csv", "")
    df = pd.read_csv(os.path.join(DATA_DIR, file))
    df["published_date"] = pd.to_datetime(df["published_date"])
    df = df.sort_values("published_date")
    
    # remove duplicate dates, keep last price
    df = df.drop_duplicates(subset="published_date", keep="last")
    
   # set index
    df = df.set_index("published_date")[["close"]]

# reindex to full calendar, forward-fill missing prices
    full_calendar = pd.date_range(start=START_DATE, end=END_DATE, freq="D")
    df = df.reindex(full_calendar)
    df["close"] = df["close"].ffill()
    
    stock_data[stock] = df
    last_buy_price[stock] = None
    
    # ensure stock exists in portfolio
    if stock not in portfolio.index:
        portfolio.loc[stock] = {"Quantity": 0}

# --- TRADING SIMULATION ---
full_calendar = pd.date_range(start=START_DATE, end=END_DATE, freq="D")
daily_values = []

for date in full_calendar:
    total_value = cash

    for stock, df in stock_data.items():
        price = df.loc[date, "close"]

        qty = portfolio.loc[stock, "Quantity"]

        # --- BUY LOGIC ---
        trade_cash = cash * BASE_CASH_PERCENT
        buy_qty = max(MIN_BUY_QTY, int(trade_cash // price))
        if buy_qty * price <= cash:
            qty += buy_qty
            cash -= buy_qty * price
            last_buy_price[stock] = price
            portfolio.loc[stock, "Quantity"] = qty
            transactions.append([date.strftime("%Y-%m-%d"), stock, "BUY", price, buy_qty, cash])

        # --- SELL LOGIC ---
        sell_qty = 0
        if last_buy_price[stock]:
            if price >= last_buy_price[stock] * TAKE_PROFIT or price <= last_buy_price[stock] * STOP_LOSS:
                sell_qty = qty  # sell all

        if sell_qty > 0:
            qty -= sell_qty
            cash += sell_qty * price
            last_buy_price[stock] = None
            portfolio.loc[stock, "Quantity"] = qty
            transactions.append([date.strftime("%Y-%m-%d"), stock, "SELL", price, sell_qty, cash])

        total_value += qty * price

    daily_values.append([date.strftime("%Y-%m-%d"), cash, total_value])

# --- SAVE CSV FILES ---
pd.DataFrame(transactions, columns=["Date", "Stock", "Action", "Price", "Quantity", "Cash_After"]) \
    .to_csv("transactions15.csv", index=False)

pd.DataFrame(daily_values, columns=["Date", "Cash", "Total_Portfolio_Value"]) \
    .to_csv("daily_portfolio_value15.csv", index=False)

portfolio.reset_index().to_csv("final_holdings15.csv", index=False)

print("Simulation completed successfully!")
print("Files generated: transactions15.csv, daily_portfolio_value15.csv, final_holdings15.csv")