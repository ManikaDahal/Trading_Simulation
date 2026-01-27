import pandas as pd

# Read daily CSV in chunks
chunksize = 10_000_000  # large but manageable
monthly_list = []

for chunk in pd.read_csv("portfolio_simulation.csv", chunksize=chunksize, parse_dates=['Date']):
    chunk['Date'] = pd.to_datetime(chunk['Date'])
    # Resample by month, keep last value of each month
    monthly = chunk.resample('ME', on='Date').last()
    monthly_list.append(monthly)

# Combine all monthly chunks
portfolio_monthly = pd.concat(monthly_list).groupby('Date').last().reset_index()

# Save Excel-friendly CSV
portfolio_monthly.to_csv("portfolio_simulation_monthly.csv", index=False)
print("Monthly CSV created: portfolio_simulation_monthly.csv")

# Total return
initial = portfolio_monthly['Portfolio Value'].iloc[0]
final = portfolio_monthly['Portfolio Value'].iloc[-1]
return_percent = ((final - initial) / initial) * 100
print(f"Total return over 5 years: {return_percent:.2f}%")
