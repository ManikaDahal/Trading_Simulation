import pandas as pd
import os

DATA_DIR = "stocks"
INITIAL_CAPITAL = 200000

START_DATE = pd.to_datetime("2021-01-25")

records = []
remaining_cash = INITIAL_CAPITAL

files = os.listdir(DATA_DIR)
capital_per_stock = INITIAL_CAPITAL / len(files)

for file in files:
    stock = file.replace(".csv", "")
    df = pd.read_csv(os.path.join(DATA_DIR, file))
    df["published_date"] = pd.to_datetime(df["published_date"])
    df = df.sort_values("published_date")

    
    df_before = df[df["published_date"] < START_DATE]

    if df_before.empty:
        print(f"Skipping {stock} — no data before START_DATE")
        continue

    row = df_before.iloc[-1]  # last trading day before trading starts
    price = row["close"]

    qty = int(capital_per_stock // price)
    invested = qty * price
    remaining_cash -= invested

    records.append({
        "Stock": stock,
        "Buy_Date": row["published_date"].date(),
        "Buy_Price": price,
        "Quantity": qty,
        "Invested_Amount": invested
    })

pd.DataFrame(records).to_csv("initial_investment.csv", index=False)

pd.DataFrame([{
    "Total_Invested": sum(r["Invested_Amount"] for r in records),
    "Remaining_Cash": remaining_cash
}]).to_csv("cash_summary.csv", index=False)

print("Pre-investment completed before trading start.")
