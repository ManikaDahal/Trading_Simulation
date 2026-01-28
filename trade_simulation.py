import pandas as pd
import os

DATA_DIR = "stocks"

START_DATE = pd.to_datetime("2021-01-25")
END_DATE   = pd.to_datetime("2026-01-25")

BUY_QTY = 5
MA_WINDOW = 10

portfolio = pd.read_csv("initial_investment.csv").set_index("Stock")
cash = pd.read_csv("cash_summary.csv")["Remaining_Cash"][0]

transactions = []
daily_values = []

stock_data = {}

for file in os.listdir(DATA_DIR):
    stock = file.replace(".csv", "")
    df = pd.read_csv(os.path.join(DATA_DIR, file))
    df["published_date"] = pd.to_datetime(df["published_date"])
    df = df.sort_values("published_date")

    #  TRADING DATE CONSTRAINT
    df = df[(df["published_date"] >= START_DATE) &
            (df["published_date"] <= END_DATE)]

    df["MA10"] = df["close"].rolling(MA_WINDOW).mean()
    stock_data[stock] = df

# unified trading calendar
trading_days = sorted(
    set(date for df in stock_data.values() for date in df["published_date"])
)

for date in trading_days:
    total_value = cash

    for stock, df in stock_data.items():
        if stock not in portfolio.index:
            continue

        row = df[df["published_date"] == date]
        if row.empty:
            continue

        price = row["close"].values[0]
        ma10 = row["MA10"].values[0]
        qty = portfolio.loc[stock, "Quantity"]

        if not pd.isna(ma10):

            # BUY
            if price < ma10 and cash >= price * BUY_QTY:
                qty += BUY_QTY
                cash -= price * BUY_QTY
                transactions.append(
                    [date.date(), stock, "BUY", price, BUY_QTY, cash]
                )

            # SELL
            elif price > ma10 and qty >= BUY_QTY:
                qty -= BUY_QTY
                cash += price * BUY_QTY
                transactions.append(
                    [date.date(), stock, "SELL", price, BUY_QTY, cash]
                )

        portfolio.loc[stock, "Quantity"] = qty
        total_value += qty * price

    daily_values.append([date.date(), cash, total_value])

pd.DataFrame(
    transactions,
    columns=["Date", "Stock", "Action", "Price", "Quantity", "Cash_After"]
).to_csv("transactions.csv", index=False)

pd.DataFrame(
    daily_values,
    columns=["Date", "Cash", "Total_Portfolio_Value"]
).to_csv("daily_portfolio_value.csv", index=False)

portfolio.reset_index().to_csv("final_holdings.csv", index=False)

print("Trading simulation finished within date range.")
