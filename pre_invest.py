import pandas as pd
import os

DATA_DIR = "stocks"
INITIAL_CAPITAL = 200000
SEARCH_START_DATE = pd.to_datetime("2012-01-01")
SEARCH_END_DATE = pd.to_datetime("2016-01-21")
MIN_SHARES = 15
SKIP_STOCKS = ["NIBL"]

files = os.listdir(DATA_DIR)
selected_files = [f for f in files if f.endswith(".csv") and f.replace(".csv", "") not in SKIP_STOCKS]

stock_min_prices = []

# Phase 1: Gather Min Prices
print("Gathering minimum prices...")
for file in selected_files:
    stock = file.replace(".csv", "")
    file_path = os.path.join(DATA_DIR, file)
    
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading {stock}: {e}")
        continue

    if "published_date" not in df.columns:
        print(f"Skipping {stock}: 'published_date' column missing")
        continue
        
    df["published_date"] = pd.to_datetime(df["published_date"])
    df = df.sort_values("published_date")
    
    mask = (df["published_date"] >= SEARCH_START_DATE) & (df["published_date"] < SEARCH_END_DATE)
    df_period = df[mask]

    if df_period.empty:
        print(f"Skipping {stock}: No data in range {SEARCH_START_DATE.date()} - {SEARCH_END_DATE.date()}")
        continue

    min_row = df_period.loc[df_period["close"].idxmin()]
    min_price = min_row["close"]
    min_date = min_row["published_date"]

    stock_min_prices.append({
        "Stock": stock,
        "Min_Price": min_price,
        "Date": min_date
    })

# Phase 2: Check Feasibility
total_min_cost = sum(item["Min_Price"] * MIN_SHARES for item in stock_min_prices)

print(f"Total stocks found: {len(stock_min_prices)}")
print(f"Minimum capital required for 15 shares each: {total_min_cost:.2f}")

if total_min_cost > INITIAL_CAPITAL:
    print(f"CRITICAL WARNING: Cannot buy 15 shares of all {len(stock_min_prices)} stocks with {INITIAL_CAPITAL}. Short by {total_min_cost - INITIAL_CAPITAL}")

else:
    print("Optimization: Sufficient capital. Distributing remaining capital...")
    
    # Strategy: Buy 15 of each first.
    remaining_cash = INITIAL_CAPITAL - total_min_cost
    
    # Distribute remaining cash equally to buy more shares
    extra_cash_per_stock = remaining_cash / len(stock_min_prices)
    
    records = []
    
    for item in stock_min_prices:
        stock = item["Stock"]
        price = item["Min_Price"]
        date = item["Date"]
        
        # Base 15 shares
        qty = MIN_SHARES
        
        # Add extra shares
        extra_qty = int(extra_cash_per_stock // price)
        qty += extra_qty
        
        invested = qty * price
        
        records.append({
            "Stock": stock,
            "Buy_Date": date.date(),
            "Buy_Price": price,
            "Quantity": qty,
            "Invested_Amount": invested
        })
        
    final_df = pd.DataFrame(records)
    final_df["Buy_Date"] = pd.to_datetime(final_df["Buy_Date"]).dt.strftime("%b %d, %Y")
    final_df.to_csv("initial_investment.csv", index=False)
    
    real_invested = final_df["Invested_Amount"].sum()
    final_cash = INITIAL_CAPITAL - real_invested
    
    print(f"Investment Summary:")
    print(f"Total Invested: {real_invested}")
    print(f"Remaining Cash: {final_cash}")
    print(f"Stocks Bought: {len(final_df)}")
    
    with open("remaining_cash.txt", "w") as f:
        f.write(str(final_cash))