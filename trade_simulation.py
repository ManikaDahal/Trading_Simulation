import pandas as pd
import os
import numpy as np

# CONFIGURATION
DATA_DIR = "stocks"
START_DATE = pd.to_datetime("2021-01-25")
END_DATE = pd.to_datetime("2026-01-25")  

INITIAL_CASH_FILE = "remaining_cash.txt"
INITIAL_INVESTMENT_FILE = "initial_investment.csv"

# Strategy Parameters
MIN_SHARES = 15
TRAILING_STOP_PCT = 0.07  # 7% drop
PROFIT_TAKE_PCT = 1.0     # 100% gain
REGULAR_LOCK_DAYS = 4
MERGER_LOCK_DAYS = 15
MAX_POSITION_PCT = 0.05

# --- CORPORATE ACTIONS: MERGERS ---
MERGERS = {
    "NBB": {"target": "NABIL", "date": pd.Timestamp("2022-07-11"), "ratio": 0.43},
    "MEGA": {"target": "NIBL", "date": pd.Timestamp("2023-01-12"), "ratio": 10/9},
}

# Moving Averages
SMA_FAST = 10
SMA_SLOW = 30

# Track last sell dates
last_sell_dates = {}

# --- LOAD INITIAL PORTFOLIO ---
portfolio = {}
try:
    initial_df = pd.read_csv(INITIAL_INVESTMENT_FILE)
    for _, row in initial_df.iterrows():
        stock = row["Stock"]
        portfolio[stock] = {
            "Qty": row["Quantity"],
            "Entry_Price": row["Buy_Price"],
            "Max_Price": row["Buy_Price"],
            "Buy_Date": pd.to_datetime(row["Buy_Date"])
        }
    initial_invested = initial_df["Invested_Amount"].sum()
except FileNotFoundError:
    print(f"{INITIAL_INVESTMENT_FILE} not found")
    exit()

# Load cash
try:
    with open(INITIAL_CASH_FILE, "r") as f:
        cash = float(f.read().strip())
except FileNotFoundError:
    cash = 0.0

initial_total_value = initial_invested + cash
target_value = initial_total_value * 2

# --- LOAD MARKET DATA ---
market_data = {}
all_stocks = []

for file in os.listdir(DATA_DIR):
    if not file.endswith(".csv"):
        continue
    stock_name = file.replace(".csv","")
    df = pd.read_csv(os.path.join(DATA_DIR,file))
    if "published_date" not in df.columns or "close" not in df.columns:
        continue
    df["published_date"] = pd.to_datetime(df["published_date"])
    df = df.sort_values("published_date").drop_duplicates("published_date").set_index("published_date")
    df["SMA_FAST"] = df["close"].rolling(SMA_FAST).mean()
    df["SMA_SLOW"] = df["close"].rolling(SMA_SLOW).mean()
    df = df[df.index >= (START_DATE - pd.Timedelta(days=365))]
    market_data[stock_name] = df
    all_stocks.append(stock_name)

# --- MERGER FUNCTION (Fixed) ---
def apply_mergers(current_date, today_prices, transactions, cash, portfolio):
    for legacy, info in MERGERS.items():
        if current_date >= info["date"]:
            if legacy in portfolio:
                old = portfolio[legacy]
                qty = old["Qty"]
                new_qty = qty * info.get("ratio",1.0)
                price_today = today_prices.get(info["target"], {}).get("Close", old["Entry_Price"])
                
                # Calculate total portfolio snapshot for logging
                other_stocks_val = sum(
                    portfolio[s]["Qty"] * today_prices.get(s, {}).get("Close", portfolio[s]["Entry_Price"])
                    for s in portfolio if s != legacy
                )
                
                # Record swap
                transactions.append({
                    "Date": current_date.strftime("%d-%b-%Y"),
                    "Stock": legacy,
                    "Action": "MERGER_SWAP",
                    "Qty": qty,
                    "Price": price_today, 
                    "Total_Amount": new_qty * price_today,
                    "Cash_In_Hand": cash,
                    "Profit_Loss": 0,
                    "Gain_Loss_Pct": 0,
                    "Portfolio_Value": round(cash + other_stocks_val + (new_qty * price_today), 2),
                    "Reason": f"Swapped {qty} {legacy} into {new_qty:.2f} {info['target']}"
                })
                
                ratio = info.get("ratio", 1.0)
                if info["target"] in portfolio:
                    existing = portfolio[info["target"]]
                    total_qty = existing["Qty"] + new_qty
                    # Weighted average for entry price (adjusted for ratio)
                    legacy_value = (old["Entry_Price"] / ratio) * new_qty
                    existing_value = existing["Entry_Price"] * existing["Qty"]
                    avg_entry = (legacy_value + existing_value) / total_qty
                    portfolio[info["target"]] = {
                        "Qty": total_qty,
                        "Entry_Price": avg_entry,
                        "Max_Price": max(existing["Max_Price"], price_today),
                        "Buy_Date": current_date,
                        "Is_Merged": True
                    }
                    print(f"          Merged {qty} {legacy} into existing {existing['Qty']} {info['target']}. New Total: {total_qty:.2f}")
                else:
                    portfolio[info["target"]] = {
                        "Qty": new_qty,
                        "Entry_Price": old["Entry_Price"] / ratio, # Adjusted cost basis
                        "Max_Price": price_today,
                        "Buy_Date": current_date,
                        "Is_Merged": True
                    }
                    print(f"          Converted {qty} {legacy} into {new_qty:.2f} {info['target']}")
                del portfolio[legacy]
            
            # Update tradable universe
            if legacy in all_stocks:
                all_stocks.remove(legacy)
            if info["target"] not in all_stocks and info["target"] in market_data:
                all_stocks.append(info["target"])

# --- SIMULATION LOOP ---
dates = pd.date_range(START_DATE, END_DATE, freq='D')
transactions = []
daily_stats = []

for current_date in dates:
    current_portfolio_value = 0
    today_prices = {s:{
        "Close": market_data[s].loc[current_date]["close"],
        "SMA_FAST": market_data[s].loc[current_date]["SMA_FAST"],
        "SMA_SLOW": market_data[s].loc[current_date]["SMA_SLOW"]
    } for s in all_stocks if current_date in market_data[s].index}
    
    if not today_prices:
        continue

    apply_mergers(current_date, today_prices, transactions, cash, portfolio)

    # Update portfolio values
    for stock, data in portfolio.items():
        if stock in today_prices:
            price = today_prices[stock]["Close"]
            current_portfolio_value += data["Qty"] * price
            if price > data["Max_Price"]:
                portfolio[stock]["Max_Price"] = price

    total_equity = cash + current_portfolio_value
    daily_stats.append({"Date":current_date,"Total_Equity":total_equity,"Cash":cash})

    # --- SELL LOGIC ---
    positions_to_sell = []
    for stock, data in portfolio.items():
        if stock not in today_prices:
            continue
        lock_days = MERGER_LOCK_DAYS if data.get("Is_Merged", False) else REGULAR_LOCK_DAYS
        if (current_date - data["Buy_Date"]).days < lock_days:
            continue

        if data.get("Is_Merged", False) and (current_date - data["Buy_Date"]).days >= MERGER_LOCK_DAYS:
            portfolio[stock]["Is_Merged"] = False

        current_price = today_prices[stock]["Close"]
        stop_price = data["Max_Price"]*(1-TRAILING_STOP_PCT)
        take_profit_price = data["Entry_Price"]*(1+PROFIT_TAKE_PCT)
        reason=""
        if current_price < stop_price:
            reason=f"Trailing Stop ({TRAILING_STOP_PCT*100:.0f}% drop)"
        elif current_price >= take_profit_price:
            reason=f"Take Profit ({PROFIT_TAKE_PCT*100:.0f}% gain)"
        if reason:
            positions_to_sell.append((stock, reason))

    for stock, reason in positions_to_sell:
        price = today_prices[stock]["Close"]
        qty = portfolio[stock]["Qty"]
        entry_price = portfolio[stock]["Entry_Price"]
        revenue = qty * price
        cost = qty * entry_price
        pnl = revenue - cost
        gain_loss_pct = (pnl/cost)*100 if cost>0 else 0
        cash += revenue
        last_sell_dates[stock] = current_date
        del portfolio[stock]
        current_portfolio_value -= revenue
        transactions.append({
            "Date": current_date.strftime("%d-%b-%Y"),
            "Stock": stock,
            "Action": "SELL",
            "Qty": qty,
            "Price": round(price,2),
            "Total_Amount": round(revenue,2),
            "Cash_In_Hand": round(cash,2),
            "Profit_Loss": round(pnl,2),
            "Gain_Loss_Pct": f"{gain_loss_pct:.2f}%",
            "Portfolio_Value": round(cash + current_portfolio_value,2),
            "Reason": reason
        })

    # --- BUY LOGIC ---
    if cash>1000:
        potential_buys=[]
        for stock in all_stocks:
            if stock in portfolio:
                continue
            if stock in last_sell_dates and (current_date - last_sell_dates[stock]).days < REGULAR_LOCK_DAYS:
                continue
            if stock not in today_prices:
                continue
            price = today_prices[stock]["Close"]
            sma_fast = today_prices[stock]["SMA_FAST"]
            sma_slow = today_prices[stock]["SMA_SLOW"]
            if pd.notna(sma_fast) and pd.notna(sma_slow):
                if price>sma_fast and sma_fast>sma_slow:
                    strength = (price - sma_slow)/sma_slow
                    potential_buys.append((stock,strength))
        potential_buys.sort(key=lambda x:x[1], reverse=True)
        if potential_buys:
            for target_stock, strength in potential_buys:
                price = today_prices[target_stock]["Close"]
                max_allocation = total_equity * MAX_POSITION_PCT
                invest_amount = min(cash, max_allocation)
                qty_to_buy = int(invest_amount // price)
                if qty_to_buy >= MIN_SHARES:
                    cost = qty_to_buy*price
                    cash -= cost
                    portfolio[target_stock] = {"Qty":qty_to_buy,"Entry_Price":price,"Max_Price":price,"Buy_Date":current_date}
                    current_portfolio_value += cost
                    transactions.append({
                        "Date": current_date.strftime("%d-%b-%Y"),
                        "Stock": target_stock,
                        "Action": "BUY",
                        "Qty": qty_to_buy,
                        "Price": round(price,2),
                        "Total_Amount": round(-cost,2),
                        "Cash_In_Hand": round(cash,2),
                        "Profit_Loss":0,
                        "Gain_Loss_Pct":"0.00%",
                        "Portfolio_Value": round(cash+current_portfolio_value,2),
                        "Reason": f"Trend Entry (Str:{strength:.2f})"
                    })

# --- FINAL REPORTS ---
final_portfolio_val = 0
for stock, data in portfolio.items():
    # Use price at END_DATE or last available in sim range
    if stock in market_data:
        sim_range_prices = market_data[stock][market_data[stock].index <= END_DATE]
        if not sim_range_prices.empty:
            price = sim_range_prices.iloc[-1]["close"]
        else:
            price = data["Entry_Price"]
    else:
        price = data["Entry_Price"]
    final_portfolio_val += data["Qty"] * price

final_total_equity = cash + final_portfolio_val
total_profit = final_total_equity - initial_total_value
profit_pct = (total_profit/initial_total_value)*100 if initial_total_value>0 else 0

print("="*30)
print("FINAL RESULTS")
print("="*30)
print(f"Initial Value:       {initial_total_value:,.2f}")
print(f"Final Value:         {final_total_equity:,.2f}")
print(f"Total Profit:        {total_profit:,.2f}")
print(f"Return (%):          {profit_pct:.2f}%")
print("="*30)

# 1. Generate Portfolio Comparison Report
try:
    comparison_records = []
    added_stocks = set()
    
    # Add stocks from initial investment
    for _, row in initial_df.iterrows():
        stock = row["Stock"]
        added_stocks.add(stock)
        
        # Get current price within simulation range
        cur_price = 0
        if stock in market_data:
            sim_range = market_data[stock][market_data[stock].index <= END_DATE]
            if not sim_range.empty:
                cur_price = sim_range.iloc[-1]["close"]
                
        if stock in portfolio:
            cur_qty = portfolio[stock]["Qty"]
            # If we don't have a market price, use entry price
            if cur_price == 0: cur_price = portfolio[stock]["Entry_Price"]
            cur_val = cur_qty * cur_price
        else:
            cur_qty = 0
            cur_val = 0
            
        comparison_records.append({
            "Stock": stock,
            "Initial_Buy_Date": pd.to_datetime(row["Buy_Date"]).strftime("%d-%b-%Y") if pd.notna(row["Buy_Date"]) else "-",
            "Initial_Qty": row["Quantity"],
            "Initial_Price": row["Buy_Price"],
            "Initial_Value": row["Invested_Amount"],
            "Current_Qty": cur_qty,
            "Current_Price": round(cur_price, 2),
            "Current_Value": round(cur_val, 2)
        })
        
    # Add new stocks acquired during simulation
    for stock, data in portfolio.items():
        if stock not in added_stocks:
            cur_qty = data["Qty"]
            cur_price = 0
            if stock in market_data:
                sim_range = market_data[stock][market_data[stock].index <= END_DATE]
                if not sim_range.empty:
                    cur_price = sim_range.iloc[-1]["close"]
            
            if cur_price == 0: cur_price = data["Entry_Price"]
            cur_val = cur_qty * cur_price
            
            comparison_records.append({
                "Stock": stock,
                "Initial_Buy_Date": "-",
                "Initial_Qty": 0,
                "Initial_Price": 0,
                "Initial_Value": 0,
                "Current_Qty": cur_qty,
                "Current_Price": round(cur_price, 2),
                "Current_Value": round(cur_val, 2)
            })
            
    # Add Cash In Hand
    comparison_records.append({
        "Stock": "CASH",
        "Initial_Buy_Date": "-",
        "Initial_Qty": 0,
        "Initial_Price": 0,
        "Initial_Value": 0,
        "Current_Qty": 0,
        "Current_Price": 0,
        "Current_Value": round(cash, 2)
    })
    
    comp_df = pd.DataFrame(comparison_records)
    
    # Add Total Row
    totals = {
        "Stock": "TOTAL",
        "Initial_Buy_Date": "-",
        "Initial_Qty": comp_df["Initial_Qty"].sum(),
        "Initial_Price": "-",
        "Initial_Value": round(comp_df["Initial_Value"].sum(), 2),
        "Current_Qty": comp_df["Current_Qty"].sum(),
        "Current_Price": "-",
        "Current_Value": round(comp_df["Current_Value"].sum(), 2)
    }
    comp_df = pd.concat([comp_df, pd.DataFrame([totals])], ignore_index=True)
    
    comp_df.to_csv("portfolio_comparison.csv", index=False)
    print(f"Comparison report written: portfolio_comparison.csv")
except Exception as e:
    print(f"Failed to generate comparison report: {e}")

# 2. Write Summary to TXT
try:
    summary_file = "trading_summary.txt"
    with open(summary_file, "w") as f:
        f.write("=" * 35 + "\n")
        f.write("       TRADING SIMULATION RESULTS\n")
        f.write("=" * 35 + "\n")
        f.write(f"Initial Investment : {initial_total_value:>12,.2f}\n")
        f.write(f"Final Value        : {final_total_equity:>12,.2f}\n")
        f.write(f"Total Profit       : {total_profit:>12,.2f}\n")
        f.write(f"Return (%)         : {profit_pct:>11.2f}%\n")
        f.write("=" * 35 + "\n")
except Exception as e:
    print(f"Failed to write summary TXT: {e}")

# 3. Write Trade History CSV
if transactions:
    df_trades = pd.DataFrame(transactions)
    # Ensure correct column order if possible
    expected_cols = ["Date", "Stock", "Action", "Qty", "Price", "Total_Amount", "Cash_In_Hand", "Profit_Loss", "Gain_Loss_Pct", "Portfolio_Value", "Reason"]
    cols_to_use = [c for c in expected_cols if c in df_trades.columns]
    df_trades[cols_to_use].to_csv("trading_report.csv", index=False)
else:
    pd.DataFrame().to_csv("trading_report.csv", index=False)

print("All reports generated successfully.")