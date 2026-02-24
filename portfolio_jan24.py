import pandas as pd
import os

DATA_DIR = "stocks"
INITIAL_INVESTMENT_FILE = "initial_investment.csv"
REMAINING_CASH_FILE = "remaining_cash.txt"
TARGET_DATE = "1/24/2021"

def calculate_portfolio():
    # 1. Load initial investment data
    if not os.path.exists(INITIAL_INVESTMENT_FILE):
        print(f"Error: {INITIAL_INVESTMENT_FILE} not found. Run pre_invest.py first.")
        return

    df_invest = pd.read_csv(INITIAL_INVESTMENT_FILE)
    
    # 2. Load remaining cash
    remaining_cash = 0.0
    if os.path.exists(REMAINING_CASH_FILE):
        with open(REMAINING_CASH_FILE, "r") as f:
            remaining_cash = float(f.read().strip())
    
    records = []
    total_initial_value = 0.0
    total_current_value = 0.0
    
    print(f"Calculating portfolio value for {TARGET_DATE}...")
    
    for _, row in df_invest.iterrows():
        stock = row["Stock"]
        buy_price = row["Buy_Price"]
        quantity = row["Quantity"]
        initial_value = row["Invested_Amount"]
        
        file_path = os.path.join(DATA_DIR, f"{stock}.csv")
        if not os.path.exists(file_path):
            print(f"Warning: Data for {stock} not found at {file_path}")
            continue
            
        df_stock = pd.read_csv(file_path)
        
        df_stock["published_date"] = pd.to_datetime(df_stock["published_date"])
        target_dt = pd.to_datetime(TARGET_DATE)
        
        day_data = df_stock[df_stock["published_date"] == target_dt]
        
        if day_data.empty:
            day_data = df_stock[df_stock["published_date"] <= target_dt].sort_values("published_date", ascending=False).head(1)
            
        if day_data.empty:
            print(f"Warning: No price data found for {stock} on or before {TARGET_DATE}")
            continue
            
        current_price = day_data.iloc[0]["close"]
        current_value = quantity * current_price
        
        records.append({
            "Stock": stock,
            "Quantity": quantity,
            "Buy_Price": buy_price,
            "Initial_Value": initial_value,
            "Price_Jan_24": current_price,
            "Current_Value": current_value
        })
        
        total_initial_value += initial_value
        total_current_value += current_value
        
    # Create final report
    report_df = pd.DataFrame(records)
    
    # Calculate totals for final row
    total_row = {
        "Stock": "TOTAL",
        "Quantity": report_df["Quantity"].sum(),
        "Buy_Price": "",  
        "Initial_Value": total_initial_value,
        "Price_Jan_24": "", 
        "Current_Value": total_current_value
    }
    
    report_df = pd.concat([report_df, pd.DataFrame([total_row])], ignore_index=True)
    
    portfolio_value = total_current_value + remaining_cash
    
    print("\nPortfolio Summary (Jan 24, 2021)")
    print("-" * 40)
    print(f"Total Invested (Initial Value): {total_initial_value:,.2f}")
    print(f"Total Current Value of Stocks: {total_current_value:,.2f}")
    print(f"Remaining Cash:                {remaining_cash:,.2f}")
    print(f"Total Portfolio Value:         {portfolio_value:,.2f}")
    print("-" * 40)
    
    # Save to CSV
    report_df.to_csv("portfolio_value_jan_24_2021.csv", index=False)
    print(f"\nDetailed report saved to portfolio_value_jan_24_2021.csv")

if __name__ == "__main__":
    calculate_portfolio()
