import pandas as pd
import os

def merge_csvs():
    # File paths
    comparison_file = 'portfolio_comparison.csv'
    jan_24_file = 'portfolio_value_jan_24_2021.csv'
    
    if not os.path.exists(comparison_file) or not os.path.exists(jan_24_file):
        print("Error: Required CSV files not found.")
        return

    # Read the data
    df_comparison = pd.read_csv(comparison_file)
    df_jan_24 = pd.read_csv(jan_24_file)

    print("Original Comparison CSV columns:", df_comparison.columns.tolist())
    print("Jan 24 CSV columns:", df_jan_24.columns.tolist())

    # Rename columns in Jan 24 dataframe for clarity
    df_jan_24_subset = df_jan_24[['Stock', 'Price_Jan_24', 'Current_Value']].copy()
    df_jan_24_subset.columns = ['Stock', 'Price_Jan_24', 'Value_Jan_24']

    # Merge on 'Stock'
    # We want to keep all rows from df_comparison and add the Jan 24 data where it matches
    merged_df = pd.merge(df_comparison, df_jan_24_subset, on='Stock', how='left')

    
    cols = list(merged_df.columns)
    # Remove 'Price_Jan_24', 'Value_Jan_24' from the end
    cols.remove('Price_Jan_24')
    cols.remove('Value_Jan_24')
    
    # Insert them after 'Initial_Value' (index 5)
    cols.insert(5, 'Price_Jan_24')
    cols.insert(6, 'Value_Jan_24')
    
    merged_df = merged_df[cols]

   
    merged_df.to_csv(comparison_file, index=False)
    print(f"Successfully merged data into {comparison_file}")

if __name__ == "__main__":
    merge_csvs()
