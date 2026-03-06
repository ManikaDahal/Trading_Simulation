import pandas as pd
import os

def create_stock_wise_report():
    input_file = 'trading_report.csv'
    output_file = 'stock_wise_report.csv'
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    # Load the report
    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file)
    
    # Convert 'Date' to datetime for sorting
    # Format is DD-Mon-YY or DD-Mon-YYYY (depending on when it was generated)
    df['Sort_Date'] = pd.to_datetime(df['Date'], format='mixed', dayfirst=True)
    
    # Sort by Stock (Alphabetical) and then by Sort_Date (Ascending)
    print("Sorting by Stock and Date...")
    df_sorted = df.sort_values(by=['Stock', 'Sort_Date'], ascending=[True, True])
    
    # Drop the temporary sort column
    df_sorted = df_sorted.drop(columns=['Sort_Date'])
    
    # Save to CSV
    df_sorted.to_csv(output_file, index=False)
    print(f"Success! Stock-wise report saved to {output_file}")

if __name__ == "__main__":
    create_stock_wise_report()
