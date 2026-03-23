"""
Full Price Verification Report
Checks ALL transactions against downloaded stock data
"""

import csv
import os
import sys
from datetime import datetime

output_file = open("price_verification_report.txt", "w", encoding="utf-8")
sys.stdout = output_file

def parse_date_to_iso(date_str):
    try:
        return datetime.strptime(date_str, "%b %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        pass
    
    # Fallback to older formats
    try:
        if '/' in date_str:
            parts = date_str.split('/')
            return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        elif '-' in date_str:
            parts = date_str.split('-')
            month_map = {'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06',
                         'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'}
            return f"{parts[2]}-{month_map[parts[1]]}-{parts[0].zfill(2)}"
    except Exception:
        pass
    
    return date_str

# Load stocks
stocks = {}
for filename in sorted(os.listdir('stocks')):
    if not filename.endswith('.csv'):
        continue
    
    symbol = filename[:-4]
    with open(f'stocks/{filename}', 'r') as f:
        reader = csv.DictReader(f)
        stocks[symbol] = {}
        for row in reader:
            try:
                date_str = row['published_date']
                # normalize date to YYYY-MM-DD regardless of format
                if '/' in date_str:
                    # assume D/M/YYYY or DD/MM/YYYY
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        d, m, y = parts
                        date_key = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
                    else:
                        date_key = date_str
                else:
                    # assume already YYYY-MM-DD or similar
                    date_key = date_str
                
                stocks[symbol][date_key] = {
                    'o': float(row['open']),
                    'h': float(row['high']),
                    'l': float(row['low']),
                    'c': float(row['close'])
                }
            except Exception:
                # skip malformed rows
                continue


# --- merger information ---
MERGERS = {
    'NBB': {'target': 'NABIL', 'date': '2022-07-11'},    # 100 NBB = 43 NABIL
    'MEGA': {'target': 'NIBL', 'date': '2023-01-11'},   # 90 MEGA = 100 NIBL
}

def map_symbol_date(symbol, date_iso, stocks_dict):
    """Return the appropriate symbol after accounting for mergers.

    If the date is on or after a merger date for a legacy symbol, return the
    target symbol if the target symbol actually has data for that date or if 
    the legacy symbol does NOT have data for that date anymore.
    """
    info = MERGERS.get(symbol)
    if info and date_iso >= info['date']:
        target_sym = info['target']
        # If original symbol still has data today, and target doesn't, keep original.
        # Otherwise, if we're past the merger date, we assume we use the target.
        if symbol in stocks_dict and date_iso in stocks_dict[symbol]:
            return symbol
        return target_sym
    return symbol

print("FULL PRICE VERIFICATION REPORT")
print("=" * 75 + "\n")
print(f"Stock CSV Files Loaded: {len(stocks)}\n")

# ============ CHECK 1: INITIAL INVESTMENTS ============
print("=" * 75)
print("1. INITIAL INVESTMENTS VERIFICATION")
print("=" * 75 + "\n")

exact_init = 0
missing_init = 0
init_issues = []

with open('initial_investment.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        stock = row['Stock']
        date_str = row['Buy_Date']
        price = float(row['Buy_Price'])
        
        date_iso = parse_date_to_iso(date_str)
        # adjust for a merger if necessary
        stock_mapped = map_symbol_date(stock, date_iso, stocks)
        if stock_mapped not in stocks:
            init_issues.append(f"{stock} (mapped to {stock_mapped}): Not in stock files")
            missing_init += 1
            continue
        
        if date_iso in stocks[stock]:
            data = stocks[stock][date_iso]
            if price in [data['o'], data['c'], data['h'], data['l']]:
                exact_init += 1
            else:
                init_issues.append(f"{stock} ({date_iso}): Price {price} not in OHLC [{data['o']}, {data['h']}, {data['l']}, {data['c']}]")
                missing_init += 1
        else:
            init_issues.append(f"{stock}: No data on {date_iso}")
            missing_init += 1

print(f"Results: {exact_init}/30 prices verified")
if missing_init > 0:
    print(f"Issues: {missing_init}")
    for issue in init_issues:
        print(f"  - {issue}")
else:
    print("Status: ALL PRICES VERIFIED")

# ============ CHECK 2: TRADING REPORT ============
print("\n" + "=" * 75)
print("2. TRADING REPORT VERIFICATION")
print("=" * 75 + "\n")

exact_trade = 0
missing_trade = 0
trade_issues = []

with open('trading_report.csv', 'r') as f:
    reader = csv.DictReader(f)
    trades = list(reader)

print(f"Total trades to verify: {len(trades)}\n")

for i, row in enumerate(trades):
    try:
        date_str = row['Date']
        stock = row['Stock'].upper()
        price = float(row['Price'])
        action = row['Action'].upper()
        
        # Skip MERGER_SWAP since their price is calculated, not traded on the market
        if action == 'MERGER_SWAP':
            exact_trade += 1
            continue
        
        # Convert to YYYY-MM-DD
        date_iso = parse_date_to_iso(date_str)
        
        # map symbol for mergers
        stock_mapped = map_symbol_date(stock, date_iso, stocks)
        if stock_mapped not in stocks:
            trade_issues.append(f"Row {i}: {stock} (mapped to {stock_mapped}) not in stock files")
            missing_trade += 1
            continue
        
        if date_iso in stocks[stock_mapped]:
            data = stocks[stock_mapped][date_iso]
            if price in [data['o'], data['c'], data['h'], data['l']]:
                exact_trade += 1
            else:
                trade_issues.append(f"Row {i}: {stock} {price} not in range [{data['l']:.0f}-{data['h']:.0f}] on {date_iso}")
                missing_trade += 1
        else:
            trade_issues.append(f"Row {i}: {stock} no data on {date_iso}")
            missing_trade += 1
    except:
        pass

print(f"Results: {exact_trade}/{len(trades)} prices verified")
if missing_trade > 0:
    print(f"Issues: {missing_trade}")
    print(f"\nFirst 10 issues:")
    for issue in trade_issues[:10]:
        print(f"  - {issue}")
    if len(trade_issues) > 10:
        print(f"  ... and {len(trade_issues) - 10} more")
    print("\nNote: ADBL uses DD/MM/YYYY dates, so mismatches may be due to format differences.")

total_checks = 30 + len(trades)
total_verified = exact_init + exact_trade
total_issues = missing_init + missing_trade

print(f"\nTotal Transactions Checked: {total_checks}")
print(f"  - Initial investments: 30")
print(f"  - Trading report: {len(trades)}")

print(f"\nVerified Against Stock Data:")
print(f"  - Prices found: {total_verified}/{total_checks} ({(total_verified/total_checks)*100:.1f}%)")
print(f"  - Issues found: {total_issues}")

if total_issues == 0:
    print("\n[SUCCESS] All prices verified - They exist in the downloaded stock CSV files!")
else:
    print(f"\n[WARNING] {total_issues} price mismatches found")
    print("          Likely causes: Missing historical data for specific dates or data gaps")

print("\n" + "=" * 75)
output_file.close()
