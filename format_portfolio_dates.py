import pandas as pd
import os

def format_dates(file_path):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    print(f"Reading {file_path}...")
    try:
        # Read the CSV
        df = pd.read_csv(file_path)
        
        # Identify date columns (Initial_Buy_Date)
        if "Initial_Buy_Date" in df.columns:
            # Convert to datetime, handling '-' for the TOTAL row
            # We use errors='coerce' to turn '-' into NaT, then fill it back later
            df["Initial_Buy_Date"] = pd.to_datetime(df["Initial_Buy_Date"], errors='coerce')
            
            # Format to 'DD-Mon-YYYY'
            # NaT results in NaN/None which we'pythonll replace with '-'
            formatted_dates = df["Initial_Buy_Date"].dt.strftime("%d-%b-%Y").fillna("-")
            df["Initial_Buy_Date"] = formatted_dates
            
            # Save back to CSV
            df.to_csv(file_path, index=False)
            print(f"Successfully updated date format in {file_path}")
        else:
            print(f"Column 'Initial_Buy_Date' not found in {file_path}")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    target_file = "portfolio_comparison.csv"
    format_dates(target_file)
