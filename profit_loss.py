import pandas as pd
import os

DATA_DIR = "stocks"
END_DATE = pd.to_datetime("2026-01-25")

# Load final holdings from trade_simulation.py
holdings = pd.read_csv("final_holdings.csv")

# Get last price for each stock from stock CSVs
last_prices = {}
for file in os.listdir(DATA_DIR):
    stock = file.replace(".csv", "")
    df = pd.read_csv(os.path.join(DATA_DIR, file))
    df["published_date"] = pd.to_datetime(df["published_date"])
    df = df[df["published_date"] <= END_DATE].sort_values("published_date")
    if not df.empty:
        last_prices[stock] = df["close"].iloc[-1]

last_prices_df = pd.DataFrame(list(last_prices.items()), columns=["Stock", "Last_Price"])

# Merge holdings with last prices
df = holdings.merge(last_prices_df, on="Stock", how="left")

# Calculate market value and profit/loss per stock
df["Market_Value"] = df["Quantity"] * df["Last_Price"]
df["Profit_Loss"] = df["Market_Value"] - df["Invested_Amount"]

# Add remaining cash
cash = pd.read_csv("daily_portfolio_value.csv")["Cash"].iloc[-1]

# Save profit/loss CSV
df.to_csv("profit_loss.csv", index=False)

# Calculate total profit/loss
total_profit = cash + df["Market_Value"].sum() - df["Invested_Amount"].sum()
print("profit_loss.csv created!")
print(f"Remaining cash: {cash}")
print(f"Total Profit/Loss: {total_profit}")
