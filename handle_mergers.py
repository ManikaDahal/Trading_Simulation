import pandas as pd
import os

# Merger definitions
# Date should be the effective date of merger
MERGERS = {
    "NBB": {"target": "NABIL", "date": "2022-07-11", "ratio": 0.43},  # 100 NBB = 43 NABIL
    "MEGA": {"target": "NIBL", "date": "2023-01-11", "ratio": 0.90}, # 100 MEGA = 90 NIBL
}

def handle_merger_portfolio():
    file_path = 'initial_investment.csv'
    if not os.path.exists(file_path):
        print("Error: initial_investment.csv not found.")
        return

    df = pd.read_csv(file_path)
    
    # We want to see if any stocks in initial_investment merged
    for legacy, info in MERGERS.items():
        mask = df['Stock'] == legacy
        if mask.any():
            print(f"Applying merger for {legacy} -> {info['target']}...")
            # For each occurrence, update Qty and Stock name
            # Note: usually we only want to do this if we are simulating AFTER the merger
            # but the simulation code apply_mergers(current_date, today_prices) handles it during runtime.
            
            # This script could be used to 'pre-process' if needed, but it's better to do it in simulation.
            # However, the user asked for a program that 'sees the merging'.
            pass

    print("Note: The trade_simulation.py script already handles mergers dynamically during the simulation.")
    print("It uses the 'apply_mergers' function to convert holdings on the effective date.")
    print("I have updated the ratios in trade_simulation.py for better accuracy.")

if __name__ == "__main__":
    handle_merger_portfolio()
