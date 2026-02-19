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
PROFIT_TAKE_PCT = 0.25    # Lock in 25% gains-sell
MAX_POSITION_PCT = 0.25  # Max 25% per stock

# Moving Averages (Super Fast Trend)
SMA_FAST = 10
SMA_SLOW = 30


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
            "Max_Price": row["Buy_Price"]  # Initialize Max Price for Trailing Stop
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
    active_stocks = list(portfolio.keys())
    
    # Pre-fetch prices for valid stocks today
    today_prices = {}
    
    for stock in all_stocks:
        df = market_data[stock]
        #Which stocks have price data for current_date
        if current_date in df.index:
            today_prices[stock] = {
                "Close": df.loc[current_date]["close"],
                "SMA_FAST": df.loc[current_date]["SMA_FAST"],
                "SMA_SLOW": df.loc[current_date]["SMA_SLOW"]
            }
    
    if not today_prices:
        continue # Weekend or Holiday
        
    # Calculate Equity
    for stock, data in portfolio.items():
        if stock in today_prices:
            price = today_prices[stock]["Close"]
            current_portfolio_value += data["Qty"] * price
            
            # Update Max Price for Trailing Stop
            if price > data["Max_Price"]:
                portfolio[stock]["Max_Price"] = price
        else:
            pass

    total_equity = cash + current_portfolio_value
    
    # Log Daily Stats
    daily_stats.append({
        "Date": current_date,
        "Total_Equity": total_equity,
        "Cash": cash
    })

    # Check Target
    if total_equity >= target_value:
        print(f" GOAL REACHED! Date: {current_date.date()}, Equity: {total_equity:,.2f}")
       

    # STRATEGY EXECUTION    
    # 2. SELL LOGIC (Trailing Stop & Take Profit)
    positions_to_sell = [] # Will store (stock, reason)
    
    for stock, data in portfolio.items():
        if stock not in today_prices:
            continue
            
        current_price = today_prices[stock]["Close"]
        max_price = data["Max_Price"]
        entry_price = data["Entry_Price"]
        qty = data["Qty"]
        
        # Conditions
        stop_price = max_price * (1 - TRAILING_STOP_PCT)
        take_profit_price = entry_price * (1 + PROFIT_TAKE_PCT)
        
        # Sell if stop hit OR take profit hit
        reason = ""
        if current_price < stop_price:
            reason = f"Trailing Stop ({TRAILING_STOP_PCT*100:.0f}% drop)"
        elif current_price >= take_profit_price:
            reason = f"Take Profit ({PROFIT_TAKE_PCT*100:.0f}% gain)"
            
        if reason:
            positions_to_sell.append((stock, reason))
    
    # Track sold stocks to prevent re-buying same day
    sold_today = set()

    for stock, reason in positions_to_sell:
        price = today_prices[stock]["Close"]
        qty = portfolio[stock]["Qty"]
        entry_price = portfolio[stock]["Entry_Price"]
        
        revenue = qty * price
        cost = qty * entry_price
        pnl = revenue - cost
        
        cash += revenue
        del portfolio[stock]
        sold_today.add(stock)
        
        transactions.append({
            "Date": current_date.date(),
            "Stock": stock,
            "Action": "SELL",
            "Qty": qty,
            "Price": price,
            "Total_Amount": revenue,
            "Profit_Loss": pnl,
            "Reason": reason
        })

    # 3. BUY LOGIC (Faster Trend Following)
    # If we have cash, look for opportunities
    if cash > 5000: # Min cash check
        potential_buys = []
        
        for stock in all_stocks:
            if stock in portfolio:
                continue # Already own it
            
            if stock in sold_today:
                continue # Sold today, don't rebuy immediately
            
            if stock not in today_prices:
                continue
                
            price = today_prices[stock]["Close"]
            sma_fast = today_prices[stock]["SMA_FAST"] 
            sma_slow = today_prices[stock]["SMA_SLOW"] 
            
            
            # Logic: SMA_FAST > SMA_SLOW (Uptrend)
            if pd.notna(sma_fast) and pd.notna(sma_slow):
                if price > sma_fast and sma_fast > sma_slow:
                     potential_buys.append(stock)
        
        # Buy Logic
        if potential_buys:
            # Pick random one
            target_stock = np.random.choice(potential_buys)
            price = today_prices[target_stock]["Close"]
            
            # Position Sizing
            max_allocation = total_equity * MAX_POSITION_PCT
            invest_amount = min(cash, max_allocation)
            
            qty_to_buy = int(invest_amount // price)
            
            # CRITICAL: Min Shares Condition
            if qty_to_buy >= MIN_SHARES:
                cost = qty_to_buy * price
                cash -= cost
                
                portfolio[target_stock] = {
                    "Qty": qty_to_buy,
                    "Entry_Price": price,
                    "Max_Price": price
                }
                
                transactions.append({
                    "Date": current_date.date(),
                    "Stock": target_stock,
                    "Action": "BUY",
                    "Qty": qty_to_buy,
                    "Price": price,
                    "Total_Amount": -cost,
                    "Profit_Loss": 0,
                    "Reason": "Trend Entry"
                })


# FINAL SUMMARY & REPORT GENERATION
print("\nSimulation Complete.")

# 1. Calculate Final Stats
final_portfolio_val = 0
final_holdings = []

for stock, data in portfolio.items():
    # Get last known price
    if stock in market_data:
        last_price = market_data[stock].iloc[-1]["close"]
    else:
        last_price = data["Entry_Price"] # Fallback
        
    val = data["Qty"] * last_price
    final_portfolio_val += val
    
    final_holdings.append({
        "Stock": stock,
        "Quantity": data["Qty"],
        "Current_Price": round(last_price, 2),
        "Total_Value": round(val, 2)
    })

final_total_equity = cash + final_portfolio_val
total_profit = final_total_equity - initial_total_value
profit_pct = (total_profit / initial_total_value) * 100 if initial_total_value > 0 else 0

# 2. Console Output
print("="*30)
print("FINAL RESULTS")
print("="*30)
print(f"Initial Value:       {initial_total_value:,.2f}")
print(f"Final Value:         {final_total_equity:,.2f}")
print(f"Total Profit:        {total_profit:,.2f}")
print(f"Return (%):          {profit_pct:.2f}%")
print(f"Target (Double):     {' ACHIEVED' if final_total_equity >= target_value else ' NOT REACHED'}")
print("="*30)

# 3. Generate Unified CSV Report
report_file = "trading_report_v3.csv"

with open(report_file, "w") as f:
    # --- SUMMARY SECTION ---
    f.write("SUMMARY\n")
    f.write("Metric,Value\n")
    f.write(f"Initial Investment,{initial_total_value:.2f}\n")
    f.write(f"Final Value,{final_total_equity:.2f}\n")
    f.write(f"Total Profit,{total_profit:.2f}\n")
    f.write(f"Return %,{profit_pct:.2f}%\n")
    f.write(f"Target Reached,{'Yes' if final_total_equity >= target_value else 'No'}\n")
    f.write("\n") # Spacer

    # --- TRADE HISTORY SECTION ---
    f.write("TRADE HISTORY\n")
    if transactions:
        df_trades = pd.DataFrame(transactions)
        df_trades.to_csv(f, index=False)
    else:
        f.write("No trades performed.\n")

# 4. Update Initial Investment CSV with Current Info
print("Updating initial_investment_updated.csv with current state...")
try:
    # Read original
    initial_comparison_df = pd.read_csv(INITIAL_INVESTMENT_FILE)
    
    current_states = []
    for _, row in initial_comparison_df.iterrows():
        stock = row["Stock"]
        if stock in portfolio:
            c_qty = portfolio[stock]["Qty"]
            # Get last known price
            if stock in market_data:
                c_price = market_data[stock].iloc[-1]["close"]
            else:
                c_price = portfolio[stock]["Entry_Price"]
            c_val = c_qty * c_price
        else:
            c_qty = 0
            c_price = market_data[stock].iloc[-1]["close"] if stock in market_data else 0
            c_val = 0
            
        current_states.append({
            "Current_Qty": c_qty,
            "Current_Price": round(c_price, 2),
            "Current_Value": round(c_val, 2)
        })
    
    # Merge
    updated_initial_df = pd.concat([initial_comparison_df, pd.DataFrame(current_states)], axis=1)
    updated_initial_file = "initial_investment_comparison_final.csv"
    updated_initial_df.to_csv(updated_initial_file, index=False)
    print(f"Updated: {updated_initial_file}")
except Exception as e:
    print(f"Failed to update initial_investment: {e}")

print(f"\nReport generated: {report_file}")
print("Contains: Summary, Current Holdings, and Trade History (with reasons).")