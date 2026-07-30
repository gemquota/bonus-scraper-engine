import pandas as pd
import sys

def clean_bonuses(csv_file):
    df = pd.read_csv(csv_file)
    
    # Convert amount to numeric
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    
    # Remove zero/negative amounts and NaN
    df = df[df['amount'] > 0].copy()
    
    # Drop id, transactiontype, bonusfixed, balance (internal fields)
    for c in ['id', 'transactiontype', 'bonusfixed', 'balance']:
        if c in df.columns:
            df = df.drop(columns=[c])
    
    # Convert numeric columns
    for col in ['minwithdraw', 'maxwithdraw', 'rollover', 'perceived_value']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Calculate ratio for reference
    df['ratio'] = (df['minwithdraw'] / df['amount']).round(2)
    
    # Only remove extreme outliers: ratio > 500x (meaningless bonuses)
    df = df[df['ratio'] <= 500].copy()
    
    # Deduplicate by url + name + amount
    before = len(df)
    df = df.drop_duplicates(subset=['url', 'name', 'amount'], keep='first')
    
    # Sort by perceived value descending
    if 'perceived_value' in df.columns:
        df = df.sort_values('perceived_value', ascending=False)
    
    # Move ratio after rollover
    cols = df.columns.tolist()
    if 'ratio' in cols and 'rollover' in cols:
        cols.remove('ratio')
        ri = cols.index('rollover')
        cols.insert(ri + 1, 'ratio')
        df = df[cols]
    
    print(f"Filtered: {before} -> {len(df)} rows ({before - len(df)} removed)")
    return df

if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "data/Dayne_Bonuses.csv"
    df = clean_bonuses(csv_file)
    df.to_csv('data/Dayne_Bonuses_Cleaned.csv', index=False)
    print(f'Saved: data/Dayne_Bonuses_Cleaned.csv ({len(df)} rows)')
