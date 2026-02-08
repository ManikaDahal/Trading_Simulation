import pandas as pd
import os

DATA_DIR = "stocks"
INITIAL_CAPITAL = 200000
START_DATE = pd.to_datetime("2021-01-25")

records = []
remaining_cash = INITIAL_CAPITAL

files = os.listdir(DATA_DIR)
capital_per_stock = INITIAL_CAPITAL / len(files)  # initial capital allocation per stock

for file in files:
    stock = file.replace(".csv", "")
    df = pd.read_csv(os.path.join(DATA_DIR, file))
    df["published_date"] = pd.to_datetime(df["published_date"])
    df = df.sort_values("published_date")

    # Only consider prices before trading starts
    df_before = df[df["published_date"] < START_DATE]

    if df_before.empty:
        print(f"Skipping {stock} — no data before START_DATE")
        continue

    # Find the row with the lowest price before start date
    min_row = df_before.loc[df_before["close"].idxmin()]
    min_price = min_row["close"]
    
    # Max possible shares we can buy at min_price using allocated capital
    max_qty_possible = int(capital_per_stock // min_price)

    if max_qty_possible < 15:
        print(f"Skipping {stock} — cannot buy at least 15 shares even at historical low")
        continue

    # Buy as many as capital allows (at least 15)
    qty = max_qty_possible
    invested = qty * min_price
    remaining_cash -= invested

    records.append({
        "Stock": stock,
        "Buy_Date": min_row["published_date"].date(),  # date of historical low
        "Buy_Price": min_price,
        "Quantity": qty,
        "Invested_Amount": invested
    })

# Save initial investment
pd.DataFrame(records).to_csv("initial_investment15.csv", index=False)

# Save cash summary
pd.DataFrame([{
    "Total_Invested": sum(r["Invested_Amount"] for r in records),
    "Remaining_Cash": remaining_cash
}]).to_csv("cash_summary15.csv", index=False)

print("Pre-investment completed before trading start.")