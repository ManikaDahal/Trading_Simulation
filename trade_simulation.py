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
TRAILING_STOP_PCT = 0.07  # Very tight 7% drop
PROFIT_TAKE_PCT = 1.0     # Hold for long-term profit (100% gain)
MAX_POSITION_PCT = 0.05    # Distribute across more stocks (max 20)

# --- CORPORATE ACTIONS: MERGERS ---
# some companies (e.g. banks) stopped trading under the old symbol
# after a merger.  we keep a map of legacy symbols -> target symbols
# along with the effective date and conversion ratio.  when the
# simulation reaches the merge date we convert any outstanding
# holdings and then stop trading the old symbol thereafter.
# the dates below should be adjusted to the actual merger closing
# dates for the securities in question.
MERGERS = {
    "NBB": {"target": "NABIL", "date": pd.Timestamp("2022-07-11"), "ratio": 0.43},  # 100 NBB = 43 NABIL
    "MEGA": {"target": "NIBL", "date": pd.Timestamp("2023-01-11"), "ratio": 10/9},  # 90 MEGA = 100 NIBL
}


def apply_mergers(current_date, today_prices, transactions, cash):
    """Convert legacy holdings to the new symbol after the merge date."""
    for legacy, info in MERGERS.items():
        if current_date >= info["date"]:
            if legacy in portfolio:
                old = portfolio[legacy]
                qty = old["Qty"]
                new_qty = qty * info.get("ratio", 1.0)
                price_today = today_prices.get(info["target"], {}).get("Close", old["Entry_Price"])
                
                print(f"[{current_date.strftime('%Y-%m-%d')}] MERGER: {qty} {legacy} -> {new_qty:.2f} {info['target']} (Ratio: {info.get('ratio')})")
                
                # Record in transactions
                transactions.append({
                    "Date": current_date.strftime("%d-%b-%Y"),
                    "Stock": legacy,
                    "Action": "MERGER_SWAP",
                    "Qty": qty,
                    "Price": info.get("ratio", 1.0),
                    "Total_Amount": new_qty, 
                    "Cash_In_Hand": cash,
                    "Profit_Loss": 0,
                    "Gain_Loss_Pct": 0,
                    "Portfolio_Value": 0, # Calculated later
                    "Reason": f"Swapped {qty} {legacy} into {new_qty:.2f} {info['target']}"
                })

                portfolio[info["target"]] = {
                    "Qty": new_qty,
                    "Entry_Price": price_today,
                    "Max_Price": price_today,
                    "Buy_Date": current_date,
                }
                del portfolio[legacy]

            # update tradable universe
            if legacy in all_stocks:
                all_stocks.remove(legacy)
            if info["target"] not in all_stocks:
                if info["target"] in market_data:
                    all_stocks.append(info["target"])
                else:
                    print(f"Warning: merge target {info['target']} not loaded; add its CSV to continue trading after merge.")

# Moving Averages (Super Fast Trend)
SMA_FAST = 10
SMA_SLOW = 30

# Track last sell dates for 4-day gap
last_sell_dates = {}

# LOAD DATA
print("Loading initial investment data...")

# Load Initial Portfolio
try:
    initial_df = pd.read_csv(INITIAL_INVESTMENT_FILE)
    portfolio = {}
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
    print(f"Error: {INITIAL_INVESTMENT_FILE} not found. Please run pre_invest.py first.")
    exit()

# Load Initial Cash
try:
    with open(INITIAL_CASH_FILE, "r") as f:
        cash = float(f.read().strip())
except FileNotFoundError:
    cash = 0.0

initial_total_value = initial_invested + cash
target_value = initial_total_value * 2

print(f"Initial Portfolio Value: {initial_total_value:,.2f}")
print(f"Target Value (Double):   {target_value:,.2f}")

# Load Market Data
print("Loading stock market data...")
market_data = {}
all_stocks = []

for file in os.listdir(DATA_DIR):
    if not file.endswith(".csv"):
        continue
    
    stock_name = file.replace(".csv", "")
    file_path = os.path.join(DATA_DIR, file)
    
    try:
        df = pd.read_csv(file_path)
        if "published_date" not in df.columns or "close" not in df.columns:
            continue
            
        df["published_date"] = pd.to_datetime(df["published_date"])
        df = df.sort_values("published_date").drop_duplicates("published_date").set_index("published_date")        
        
        # Calculate Indicators
        df["SMA_FAST"] = df["close"].rolling(window=SMA_FAST).mean()
        df["SMA_SLOW"] = df["close"].rolling(window=SMA_SLOW).mean()
        
        # Filter for simulation period (with some buffer for SMA)
        mask = df.index >= (START_DATE - pd.Timedelta(days=365))
        df = df[mask]
        
        market_data[stock_name] = df
        all_stocks.append(stock_name)
        
    except Exception as e:
        print(f"Skipping {stock_name}: {e}")

print(f"Loaded data for {len(market_data)} stocks.")

# SIMULATION LOOP
print("Starting simulation...")

dates = pd.date_range(START_DATE, END_DATE, freq='D')
transactions = []
daily_stats = []

for current_date in dates:
    # 1. Update Portfolio Value & Check Exists
    current_portfolio_value = 0
    
    # Pre-fetch prices for valid stocks today
    today_prices = {}
    
    for stock in all_stocks:
        df = market_data[stock]
        if current_date in df.index:
            today_prices[stock] = {
                "Close": df.loc[current_date]["close"],
                "SMA_FAST": df.loc[current_date]["SMA_FAST"],
                "SMA_SLOW": df.loc[current_date]["SMA_SLOW"]
            }
    
    if not today_prices:
        continue # Weekend or Holiday

    # check for any corporate mergers and convert holdings / universe
    apply_mergers(current_date, today_prices, transactions, cash)
        
    # Calculate Equity
    for stock, data in portfolio.items():
        if stock in today_prices:
            price = today_prices[stock]["Close"]
            current_portfolio_value += data["Qty"] * price
            
            # Update Max Price for Trailing Stop
            if price > data["Max_Price"]:
                portfolio[stock]["Max_Price"] = price

    total_equity = cash + current_portfolio_value
    
    # Log Daily Stats
    daily_stats.append({
        "Date": current_date,
        "Total_Equity": total_equity,
        "Cash": cash
    })

    # STRATEGY EXECUTION    
    # 2. SELL LOGIC (Trailing Stop & Take Profit & 4-Day Gap PER STOCK)
    positions_to_sell = []
    
    for stock, data in portfolio.items():
        if stock not in today_prices:
            continue
            
        # 4-Day Gap condition (per stock)
        if (current_date - data["Buy_Date"]).days < 4:
            continue

        current_price = today_prices[stock]["Close"]
        max_price = data["Max_Price"]
        entry_price = data["Entry_Price"]
        
        # Conditions
        stop_price = max_price * (1 - TRAILING_STOP_PCT)
        take_profit_price = entry_price * (1 + PROFIT_TAKE_PCT)
        
        reason = ""
        if current_price < stop_price:
            reason = f"Trailing Stop ({TRAILING_STOP_PCT*100:.0f}% drop)"
        elif current_price >= take_profit_price:
            reason = f"Take Profit ({PROFIT_TAKE_PCT*100:.0f}% gain)"
            
        if reason:
            positions_to_sell.append((stock, reason))
    
    for stock, reason in positions_to_sell:
        price = today_prices[stock]["Close"]
        qty = portfolio[stock]["Qty"]
        entry_price = portfolio[stock]["Entry_Price"]
        
        revenue = qty * price
        cost = qty * entry_price
        pnl = revenue - cost
        gain_loss_pct = (pnl / cost) * 100 if cost > 0 else 0
        
        cash += revenue
        last_sell_dates[stock] = current_date
        del portfolio[stock]
        
        # Update current equity for report column
        current_portfolio_value -= revenue
        
        transactions.append({
            "Date": current_date.strftime("%d-%b-%Y"),
            "Stock": stock,
            "Action": "SELL",
            "Qty": qty,
            "Price": round(price, 2),
            "Total_Amount": round(revenue, 2),
            "Cash_In_Hand": round(cash, 2),
            "Profit_Loss": round(pnl, 2),
            "Gain_Loss_Pct": f"{gain_loss_pct:.2f}%",
            "Portfolio_Value": round(cash + current_portfolio_value, 2),
            "Reason": reason
        })

    # 3. BUY LOGIC (Trend Strength Sorting + 4-Day Gap PER STOCK)
    if cash > 1000:
        potential_buys = []
        
        for stock in all_stocks:
            if stock in portfolio:
                continue
            
            # 4-Day Gap condition per stock
            if stock in last_sell_dates and (current_date - last_sell_dates[stock]).days < 4:
                continue
            
            if stock not in today_prices:
                continue
                
            price = today_prices[stock]["Close"]
            sma_fast = today_prices[stock]["SMA_FAST"] 
            sma_slow = today_prices[stock]["SMA_SLOW"] 
            
            if pd.notna(sma_fast) and pd.notna(sma_slow):
                if price > sma_fast and sma_fast > sma_slow:
                     # Calculate Trend Strength
                     strength = (price - sma_slow) / sma_slow
                     potential_buys.append((stock, strength))
        
        # Sort potential buys by Trend Strength (Descending)
        potential_buys.sort(key=lambda x: x[1], reverse=True)
        
        if potential_buys:
            for target_stock, strength in potential_buys:
                price = today_prices[target_stock]["Close"]
                
                # Position Sizing (5% per stock)
                max_allocation = total_equity * MAX_POSITION_PCT
                invest_amount = min(cash, max_allocation)
                
                qty_to_buy = int(invest_amount // price)
                
                if qty_to_buy >= MIN_SHARES:
                    cost = qty_to_buy * price
                    cash -= cost
                    
                    portfolio[target_stock] = {
                        "Qty": qty_to_buy,
                        "Entry_Price": price,
                        "Max_Price": price,
                        "Buy_Date": current_date
                    }
                    
                    transactions.append({
                        "Date": current_date.strftime("%d-%b-%Y"),
                        "Stock": target_stock,
                        "Action": "BUY",
                        "Qty": qty_to_buy,
                        "Price": round(price, 2),
                        "Total_Amount": round(-cost, 2),
                        "Cash_In_Hand": round(cash, 2),
                        "Profit_Loss": 0,
                        "Gain_Loss_Pct": "0.00%",
                        "Portfolio_Value": round(cash + (current_portfolio_value + cost), 2),
                        "Reason": f"Trend Entry (Str: {strength:.2f})"
                    })
                    
                    current_portfolio_value += cost

# FINAL SUMMARY & REPORT GENERATION
print("\nSimulation Complete.")

# 1. Calculate Final Stats
final_portfolio_val = 0
for stock, data in portfolio.items():
    if stock in market_data:
        last_price = market_data[stock].iloc[-1]["close"]
    else:
        last_price = data["Entry_Price"]
    final_portfolio_val += data["Qty"] * last_price

final_total_equity = cash + final_portfolio_val
total_profit = final_total_equity - initial_total_value
profit_pct = (total_profit / initial_total_value) * 100 if initial_total_value > 0 else 0

# Console Output
print("="*30)
print("FINAL RESULTS")
print("="*30)
print(f"Initial Value:       {initial_total_value:,.2f}")
print(f"Final Value:         {final_total_equity:,.2f}")
print(f"Total Profit:        {total_profit:,.2f}")
print(f"Return (%):          {profit_pct:.2f}%")
print("="*30)

# 2. Generate Portfolio Comparison Report
try:
    initial_comp_df = pd.read_csv(INITIAL_INVESTMENT_FILE)
    comparison_records = []
    
    # Track stocks we've already added to avoid duplicates
    added_stocks = set()
    
    # 1. Add stocks from initial investment
    for _, row in initial_comp_df.iterrows():
        stock = row["Stock"]
        added_stocks.add(stock)
        if stock in portfolio:
            cur_qty = portfolio[stock]["Qty"]
            cur_price = market_data[stock].iloc[-1]["close"] if stock in market_data else portfolio[stock]["Entry_Price"]
            cur_val = cur_qty * cur_price
        else:
            cur_qty = 0
            cur_price = market_data[stock].iloc[-1]["close"] if stock in market_data else 0
            cur_val = 0
            
        formatted_date = pd.to_datetime(row["Buy_Date"]).strftime("%d-%b-%Y") if row["Buy_Date"] != "-" else "-"
        comparison_records.append({
            "Stock": stock,
            "Initial_Buy_Date": formatted_date,
            "Initial_Qty": row["Quantity"],
            "Initial_Price": row["Buy_Price"],
            "Initial_Value": row["Invested_Amount"],
            "Current_Qty": cur_qty,
            "Current_Price": round(cur_price, 2),
            "Current_Value": round(cur_val, 2)
        })
        
    # 2. Add new stocks acquired during simulation
    for stock, data in portfolio.items():
        if stock not in added_stocks:
            cur_qty = data["Qty"]
            cur_price = market_data[stock].iloc[-1]["close"] if stock in market_data else data["Entry_Price"]
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
            
    # 3. Add Cash In Hand
    comparison_records.append({
        "Stock": "CASH",
        "Initial_Buy_Date": "-",
        "Initial_Qty": 0,
        "Initial_Price": 0,
        "Initial_Value": 0, # Could technically put initial cash here if tracked
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
        "Initial_Price": round(comp_df["Initial_Price"].sum(), 2),
        "Initial_Value": round(comp_df["Initial_Value"].sum(), 2),
        "Current_Qty": comp_df["Current_Qty"].sum(),
        "Current_Price": round(comp_df["Current_Price"].sum(), 2),
        "Current_Value": round(comp_df["Current_Value"].sum(), 2)
    }
    comp_df = pd.concat([comp_df, pd.DataFrame([totals])], ignore_index=True)
    
    comparison_file = "portfolio_comparison.csv"
    comp_df.to_csv(comparison_file, index=False)
    print(f"Comparison report written: {comparison_file}")
except Exception as e:
    print(f"Failed to generate comparison report: {e}")

# 3. Write Summary to TXT
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

# 4. Write Trade History CSV
report_file = "trading_report.csv"
if transactions:
    df_trades = pd.DataFrame(transactions)
    cols = ["Date", "Stock", "Action", "Qty", "Price", "Total_Amount", "Cash_In_Hand", "Profit_Loss", "Gain_Loss_Pct", "Portfolio_Value", "Reason"]
    df_trades = df_trades[cols]
    df_trades.to_csv(report_file, index=False)
else:
    pd.DataFrame(columns=["Date","Stock","Action","Qty","Price","Total_Amount","Cash_In_Hand","Profit_Loss","Gain_Loss_Pct","Portfolio_Value","Reason"]).to_csv(report_file, index=False)

print(f"Trade history written: {report_file}")
print("All files generated successfully.")