import csv
import os
import sys
from datetime import datetime

# Configuration
START_DATE = datetime(2016, 1, 22)
END_DATE = datetime(2026, 1, 21)
HISTORY_FILE = "bonus_compounding_history.csv"
BONUS_DATA_DIR = "bonus_data"
REPORT_FILE = "bonus_verification_report.txt"

def parse_date(date_str):
    """Normalize various date formats to datetime object."""
    if not date_str or date_str == "-": return None
    for fmt in ("%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

def main():
    print(f"Starting Bonus Verification...")
    
    # 1. Load Applied History from CSV
    applied_bonuses = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = parse_date(row['Bonus Date'])
                if d:
                    try:
                        pct_val = float(row['Bonus Percentage'].replace('%',''))
                        applied_bonuses.append({
                            'Initial_Stock': row['Stock'],
                            'Symbol': row['Bonus Symbol'].upper(),
                            'Date': d,
                            'Pct': pct_val,
                            'Matched': False
                        })
                    except:
                        continue
    else:
        print(f"Error: {HISTORY_FILE} not found. Run simulation first.")
        return

    # 2. Iterate through source files in bonus_data/
    results = {
        "verified": 0,
        "missing": [],
        "mismatch": [],
        "extra": []
    }
    
    source_bonuses_count = 0
    
    if not os.path.exists(BONUS_DATA_DIR):
        print(f"Error: {BONUS_DATA_DIR} directory not found.")
        return

    for filename in sorted(os.listdir(BONUS_DATA_DIR)):
        if not filename.endswith('.csv'): continue
        
        # Source Symbol extraction (e.g. adbl_bonus.csv -> ADBL)
        source_sym = filename.split('_')[0].upper()
        
        file_path = os.path.join(BONUS_DATA_DIR, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            # Simple check for delimiter
            first_line = f.readline()
            f.seek(0)
            delim = '\t' if '\t' in first_line else ','
            
            reader = csv.DictReader(f, delimiter=delim)
            for row in reader:
                # Map column names (handles inconsistent CSV headers)
                pct_str = row.get('Bonus Dividend') or row.get('bonus_dividend') or row.get('Bonus Dividend (%)') or row.get('Bonus Dividend(%)')
                date_str = row.get('Date') or row.get('date') or row.get('published_date')
                
                if pct_str is None or date_str is None: continue
                
                try:
                    pct = float(str(pct_str).strip().replace('%',''))
                    d = parse_date(str(date_str).strip())
                except: continue
                
                if not d: continue
                
                # Filter for timeframe
                if d < START_DATE or d > END_DATE: continue
                
                source_bonuses_count += 1
                
                # Match logic: look for matches (one source bonus can apply to multiple positions)
                found = False
                
                # Find all records in simulation for this symbol and date
                matches = [a for a in applied_bonuses if a['Symbol'] == source_sym and a['Date'].date() == d.date()]
                
                if matches:
                    # Check if any match has the correct percentage
                    exact_matches = [m for m in matches if abs(m['Pct'] - pct) < 0.01]
                    
                    if exact_matches:
                        for m in exact_matches:
                            m['Matched'] = True
                        results['verified'] += 1
                        found = True
                    else:
                        # If no exact percentage match, flag a mismatch for the first one and mark all as matched to avoid "Unexpected"
                        first_m = matches[0]
                        results['mismatch'].append(f"{source_sym} on {d.strftime('%b %d, %Y')}: Source {pct}%, Simulation Applied {first_m['Pct']}%")
                        for m in matches:
                            m['Matched'] = True
                        found = True
                
                if not found:
                    results['missing'].append(f"{source_sym} on {d.strftime('%b %d, %Y')}: {pct}% in source but MISSING from simulation history.")


    # 3. Detect "Extra" bonuses (in report but not in source)
    for applied in applied_bonuses:
        if not applied['Matched']:
            results['extra'].append(f"{applied['Symbol']} on {applied['Date'].strftime('%b %d, %Y')}: {applied['Pct']}% in report but NOT found in {BONUS_DATA_DIR} files.")

    # 4. Generate Final Report
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("           BONUS DATA UTILIZATION VERIFICATION REPORT\n")
        f.write("="*70 + "\n\n")
        f.write(f"Generated On: {datetime.now().strftime('%b %d, %Y %H:%M:%S')}\n")
        f.write(f"Simulation Window: {START_DATE.strftime('%B %d, %Y')} to {END_DATE.strftime('%B %d, %Y')}\n\n")
        
        f.write("SUMMARY OF FINDINGS:\n")
        f.write(f"  - Range-Valid Bonuses in Source CSVs: {source_bonuses_count}\n")
        f.write(f"  - Successfully Verified (Matches):    {results['verified']}\n")
        f.write(f"  - Discrepancies Found:                {len(results['missing']) + len(results['mismatch']) + len(results['extra'])}\n\n")
        
        if results['missing']:
            f.write("-" * 25 + " [!] MISSING BONUSES (" + str(len(results['missing'])) + ") " + "-" * 25 + "\n")
            f.write("These bonuses exist in your source data files but were NOT utilized by the simulation.\n")
            for item in results['missing']: f.write(f"  * {item}\n")
            f.write("\n")

        if results['mismatch']:
            f.write("-" * 25 + " [!] PERCENTAGE MISMATCHES (" + str(len(results['mismatch'])) + ") " + "-" * 23 + "\n")
            f.write("The bonus was applied, but the percentage does not match the source data.\n")
            for item in results['mismatch']: f.write(f"  * {item}\n")
            f.write("\n")

        if results['extra']:
            f.write("-" * 25 + " [?] UNEXPECTED BONUSES (" + str(len(results['extra'])) + ") " + "-" * 24 + "\n")
            f.write("These bonus events appear in the report but were NOT found in any file in /bonus_data.\n")
            for item in results['extra']: f.write(f"  * {item}\n")
            f.write("\n")

        if results['verified'] > 0 and not (results['missing'] or results['mismatch'] or results['extra']):
            f.write("\n[SUCCESS] PERFECT MATCH! All source data within the period is correctly reflected in the simulation.\n")
        elif source_bonuses_count == 0:
             f.write("\n[INFO] No bonuses were found in the source files for this specific date range.\n")

        f.write("\n" + "="*70 + "\n")

    print(f"Verification complete. Details saved to: {REPORT_FILE}")

if __name__ == "__main__":
    main()
