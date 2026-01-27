import pandas as pd
import glob

# Parameters
start_date = '2021-01-25'
end_date = '2026-01-25'
initial_cash = 200000

# Get all stock CSV files
files = glob.glob("stocks/*.csv")
num_stocks = len(files)
print(f"Found {num_stocks} stock files.")

# Count stocks with data in last 5 years
valid_files = []
for file in files:
    df = pd.read_csv(file)[["published_date", "close"]]
    df['published_date'] = pd.to_datetime(df['published_date'])
    df = df[(df['published_date'] >= start_date) & (df['published_date'] <= end_date)]
    if not df.empty:
        valid_files.append(file)
    else:
        print(f"Skipping {file}: no data in last 5 years")

num_valid_stocks = len(valid_files)
if num_valid_stocks == 0:
    print("No stock data available in last 5 years. Exiting.")
    exit()

investment_per_stock = initial_cash / num_valid_stocks
print(f"Investing Rs.{investment_per_stock:.2f} per stock (for {num_valid_stocks} valid stocks).")

# Initialize portfolio as empty DataFrame
portfolio = pd.DataFrame()

# Process each stock incrementally
for i, file in enumerate(valid_files, 1):
    df = pd.read_csv(file)[["published_date", "close"]]
    df['published_date'] = pd.to_datetime(df['published_date'])
    df = df[(df['published_date'] >= start_date) & (df['published_date'] <= end_date)]
    
    first_price = df['close'].iloc[0]
    shares = investment_per_stock / first_price
    df['Value'] = df['close'] * shares
    df = df[['published_date', 'Value']].rename(columns={'published_date': 'Date'})
    
    if portfolio.empty:
        portfolio = df.copy()
    else:
        # Merge incrementally and sum into Portfolio Value
        portfolio = pd.merge(portfolio, df, on='Date', how='outer', suffixes=('', '_tmp'))
        portfolio['Value'] = portfolio['Value'].fillna(0) + portfolio['Value_tmp'].fillna(0)
        portfolio = portfolio[['Date', 'Value']]

# Finalize portfolio
portfolio = portfolio.rename(columns={'Value': 'Portfolio Value'})
portfolio = portfolio.sort_values('Date').ffill().reset_index(drop=True)

# Save CSV
portfolio.to_csv("portfolio_simulation.csv", index=False)
print(f"Portfolio simulation saved as 'portfolio_simulation.csv' ")
