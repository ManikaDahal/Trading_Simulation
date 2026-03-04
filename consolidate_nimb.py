import pandas as pd
import os
import glob
import re

NEPSE_DATA_DIR = r"c:\Users\User\Desktop\nepse_data"
OUTPUT_FILE = r"c:\Users\User\Desktop\Trading_Simulation\stocks\NIBL.csv"
TARGET_SYMBOL = "NIMB" # NIMB is the merged entity but user calls it NIBL in logic

def consolidate():
    files = glob.glob(os.path.join(NEPSE_DATA_DIR, "*.csv"))
    records = []
    
    print(f"Processing {len(files)} files...")
    
    for file in files:
        # Get date from filename 2024_03_04.csv
        basename = os.path.basename(file)
        date_match = re.search(r"(\d{4})_(\d{2})_(\d{2})", basename)
        if not date_match:
            continue
            
        date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        
        try:
            df = pd.read_csv(file)
            # Find row for NIMB
            nimb_row = df[df['Symbol'] == TARGET_SYMBOL]
            if nimb_row.empty:
                # Try NIBL just in case
                nimb_row = df[df['Symbol'] == 'NIBL']
            
            if not nimb_row.empty:
                row = nimb_row.iloc[0]
                records.append({
                    'published_date': date_str,
                    'open': row['Open'],
                    'high': row['High'],
                    'low': row['Low'],
                    'close': row['Close'],
                    'per_change': row['Diff %'],
                    'traded_quantity': str(row['Vol']).replace(',', ''), # Vol might have commas
                    'traded_amount': str(row['Turnover']).replace(',', ''),
                    'status': 0
                })
        except Exception as e:
            print(f"Error processing {basename}: {e}")
            
    if records:
        output_df = pd.DataFrame(records)
        output_df['published_date'] = pd.to_datetime(output_df['published_date'])
        output_df = output_df.sort_values('published_date').drop_duplicates('published_date')
        output_df['published_date'] = output_df['published_date'].dt.strftime('%Y-%m-%d')
        
        # Ensure numeric columns are clean
        for col in ['open', 'high', 'low', 'close', 'traded_quantity', 'traded_amount']:
            output_df[col] = output_df[col].astype(str).str.replace(',', '').astype(float)
            
        output_df.to_csv(OUTPUT_FILE, index=False)
        print(f"Success! Saved {len(output_df)} rows to {OUTPUT_FILE}")
    else:
        print("No NIMB/NIBL records found in the source files.")

if __name__ == "__main__":
    consolidate()
