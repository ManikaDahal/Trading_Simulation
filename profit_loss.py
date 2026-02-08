import pandas as pd
import os

DATA_DIR = "stocks"
END_DATE = pd.to_datetime("2026-01-25")

# --- LOAD FINAL HOLDINGS ---
holdings = pd.read_csv("final_holdings15.csv")  # only Stock + Quantity

# --- GET LAST PRICE OF EACH STOCK ---
last_prices = {}
for file in os.listdir(DATA_DIR):
    stock = file.replace(".csv", "")
    df = pd.read_csv(os.path.join(DATA_DIR, file))
    df["published_date"] = pd.to_datetime(df["published_date"])
    df = df[df["published_date"] <= END_DATE].sort_values("published_date")
    if not df.empty:
        last_prices[stock] = df["close"].iloc[-1]

last_prices_df = pd.DataFrame(list(last_prices.items()), columns=["Stock", "Last_Price"])

# --- MERGE WITH HOLDINGS ---
df = holdings.merge(last_prices_df, on="Stock", how="left")

# --- CALCULATE MARKET VALUE ---
df["Market_Value"] = df["Quantity"] * df["Last_Price"]

# --- CALCULATE PROFIT/LOSS PER STOCK USING TRANSACTIONS ---
tx = pd.read_csv("transactions15.csv")
tx["Amount"] = tx["Price"] * tx["Quantity"]

# total bought and sold per stock
buy_df = tx[tx["Action"] == "BUY"].groupby("Stock")["Amount"].sum().reset_index()
buy_df.rename(columns={"Amount": "Total_Bought"}, inplace=True)

sell_df = tx[tx["Action"] == "SELL"].groupby("Stock")["Amount"].sum().reset_index()
sell_df.rename(columns={"Amount": "Total_Sold"}, inplace=True)

# merge totals into df
df = df.merge(buy_df, on="Stock", how="left").merge(sell_df, on="Stock", how="left")
df[["Total_Bought", "Total_Sold"]] = df[["Total_Bought", "Total_Sold"]].fillna(0)

# profit/loss from trades (realized)
df["Realized_PnL"] = df["Total_Sold"] - df["Total_Bought"]

# unrealized PnL = current market value of remaining shares - amount spent on those shares
# calculate cost of remaining shares proportionally
df["Cost_Remaining_Shares"] = df["Total_Bought"] - df["Total_Sold"]
df["Unrealized_PnL"] = df["Market_Value"] - df["Cost_Remaining_Shares"]

# total PnL
df["Total_PnL"] = df["Realized_PnL"] + df["Unrealized_PnL"]

# --- ADD REMAINING CASH ---
cash = pd.read_csv("daily_portfolio_value15.csv")["Cash"].iloc[-1]
total_portfolio_value = cash + df["Market_Value"].sum()

# --- SAVE CSV ---
df.to_csv("profit_loss15.csv", index=False)

# --- SUMMARY ---
print("profit_loss15.csv created!")
print(f"Remaining cash: {cash}")
print(f"Total Portfolio Value: {total_portfolio_value}")
print(f"Total Profit/Loss: {total_portfolio_value - 200000}")  # initial investment