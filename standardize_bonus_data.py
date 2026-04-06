import os
import glob
import csv
import pandas as pd

directory = r'c:\Users\User\Desktop\Trading_Simulation\bonus_data'
files = glob.glob(os.path.join(directory, '*.csv'))

def standardize_file(file_path):
    print(f"Processing {os.path.basename(file_path)}...")
    
    if not os.path.exists(file_path): return
    
    if os.path.getsize(file_path) == 0:
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Bonus Dividend(%)", "Date"])
        return

    try:
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            # Use csv.reader to handle quoted fields correctly
            reader = csv.reader(f)
            header = next(reader, None)
            
            for row in reader:
                if not row: continue
                # Basic cleaning: strip whitespace from each field
                row = [field.strip() for field in row]
                
                if len(row) >= 2:
                    bonus = row[0]
                    # If row has more than 2 columns, it means the date's comma split it (unquoted input)
                    # We join them back together.
                    date_str = ", ".join(row[1:])
                    
                    try:
                        # Normalize date format
                        dt = pd.to_datetime(date_str, errors='coerce')
                        if not pd.isna(dt):
                            formatted_date = dt.strftime('%b %d, %Y')
                        else:
                            formatted_date = date_str
                    except:
                        formatted_date = date_str
                        
                    data.append((bonus, formatted_date))
        
        # Write back with proper quoting
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            # QUOTE_MINIMAL will quote the date because it contains a comma
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(["Bonus Dividend(%)", "Date"])
            writer.writerows(data)
            
    except Exception as e:
        print(f"  Error processing {os.path.basename(file_path)}: {e}")

for file in files:
    standardize_file(file)

print("Standardization complete (files are now correctly quoted).")
