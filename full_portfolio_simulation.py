import pandas as pd
import os

INITIAL_CASH = 200000
BUY_QTY = 10
START_DATE = "2021-01-25"
END_DATE = "2026-01-25"

DATA_DIR = "stocks"

# ================= STATE =================
cash = INITIAL_CASH
holdings = {}
trade_log = []

# ================= LOAD ALL STOCKS =================
all_data = []

for file in os.listdir(DATA_DIR):
    if not file.endswith(".csv"):
        continue
    stock = file.replace(".csv", "")
    df = pd.read_csv(os.path.join(DATA_DIR, file))

    df["published_date"] = pd.to_datetime(df["published_date"])
    df = df.sort_values("published_date")

    # Filter 5 years only
    df = df[(df["published_date"] >= START_DATE) &
            (df["published_date"] <= END_DATE)]

    if df.empty:
        continue

    # MA10 calculation
    df["MA10"] = df["close"].rolling(10).mean()

    df["Stock"] = stock
    all_data.append(df)

# Combine all stocks
combined_df = pd.concat(all_data)
combined_df = combined_df.sort_values("published_date")

# Initialize holdings
for stock in combined_df["Stock"].unique():
    holdings[stock] = 0

# ================= SIMULATION =================
for date, daily_data in combined_df.groupby("published_date"):
    for _, row in daily_data.iterrows():
        stock = row["Stock"]
        price = row["close"]
        ma10 = row["MA10"]

        if pd.isna(ma10):
            continue  # skip first 10 days

        # BUY if price < MA10
        if price < ma10:
            cost = price * BUY_QTY
            if cash >= cost:
                cash -= cost
                holdings[stock] += BUY_QTY
                trade_log.append([date, stock, "BUY", price, BUY_QTY, cost, cash, holdings[stock]])

        # SELL if price > MA10
        elif price > ma10:
            if holdings[stock] >= BUY_QTY:
                revenue = price * BUY_QTY
                cash += revenue
                holdings[stock] -= BUY_QTY
                trade_log.append([date, stock, "SELL", price, BUY_QTY, revenue, cash, holdings[stock]])

# ================= CREATE DATAFRAMES =================

# 1️⃣ Trade history
trade_df = pd.DataFrame(
    trade_log,
    columns=["Date", "Stock", "Action", "Price", "Quantity", "Amount", "Remaining_Cash", "Total_Shares"]
)

# 2️⃣ Stock holdings
holdings_df = pd.DataFrame([
    {"Stock": stock, "Shares_Held": shares}
    for stock, shares in holdings.items()
])

# 3️⃣ Portfolio summary
latest_prices = {}

for stock in holdings.keys():
    df = pd.read_csv(os.path.join(DATA_DIR, f"{stock}.csv"))
    latest_prices[stock] = df["close"].iloc[-1]

total_stock_value = sum(holdings[stock] * latest_prices.get(stock, 0) for stock in holdings)

portfolio_summary_df = pd.DataFrame([{
    "Initial_Investment": INITIAL_CASH,
    "Final_Remaining_Cash": cash,
    "Total_Stock_Value": total_stock_value,
    "Total_Portfolio_Value": cash + total_stock_value,
    "Profit_or_Loss": (cash + total_stock_value) - INITIAL_CASH
}])

# ================= EXPORT TO CSV =================
trade_df.to_csv("trade_history_MA10.csv", index=False)
holdings_df.to_csv("stock_holdings_MA10.csv", index=False)
portfolio_summary_df.to_csv("portfolio_summary_MA10.csv", index=False)

print(" CSV files created: trade_history_MA10.csv, stock_holdings_MA10.csv, portfolio_summary_MA10.csv")
