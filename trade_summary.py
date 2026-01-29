import pandas as pd

# Load pre-investment data
pre = pd.read_csv("initial_investment.csv")

pre_summary = pre.groupby("Stock").agg(
    Pre_Invest_Qty=("Quantity", "sum"),
    Pre_Invest_Amount=("Invested_Amount", "sum")
)

# Load transactions
tx = pd.read_csv("transactions.csv")
tx["Amount"] = tx["Price"] * tx["Quantity"]

buy_df = tx[tx["Action"] == "BUY"]
sell_df = tx[tx["Action"] == "SELL"]

buy_summary = buy_df.groupby("Stock").agg(
    Trade_Buy_Qty=("Quantity", "sum"),
    Trade_Buy_Amount=("Amount", "sum")
)

sell_summary = sell_df.groupby("Stock").agg(
    Trade_Sell_Qty=("Quantity", "sum"),
    Trade_Sell_Amount=("Amount", "sum")
)

# Merge all summaries
summary = pre_summary.merge(
    buy_summary, on="Stock", how="outer"
).merge(
    sell_summary, on="Stock", how="outer"
).fillna(0)

# Calculations
summary["Net_Trade_Qty"] = summary["Trade_Buy_Qty"] - summary["Trade_Sell_Qty"]
summary["Final_Qty"] = summary["Pre_Invest_Qty"] + summary["Net_Trade_Qty"]

summary["Total_Invested"] = summary["Pre_Invest_Amount"] + summary["Trade_Buy_Amount"]
summary["Total_Received"] = summary["Trade_Sell_Amount"]

summary["Trading_PnL"] = summary["Total_Received"] - summary["Trade_Buy_Amount"]

summary = summary.reset_index()

# Save result
summary.to_csv("complete_stock_summary.csv", index=False)

print("complete_stock_summary.csv created successfully!")
