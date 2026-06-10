"""
Parse FBref Big 5 HTML pages into CSV files.
Handles all seasons from 1995-96 to 2022-23 including
edge cases in older season page structures.

Usage:
    python src/pipeline/parse_fbref_html.py
"""

import pandas as pd
from io import StringIO
import os
from bs4 import BeautifulSoup
from pathlib import Path

INPUT_DIR  = "/Users/muhammadhamza/striker_era_ranking/data/html_files"
OUTPUT_DIR = "/Users/muhammadhamza/striker_era_ranking/data/raw/fbref"


def parse_html_file(filepath):
    """
    Parse a saved FBref Big 5 HTML page and extract
    the Player Standard Stats table.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    table = soup.find('table', {'id': 'stats_standard'})

    if table is None:
        print(f"  WARNING: No stats table found in {filepath}")
        return None

    df = pd.read_html(StringIO(str(table)))[0]

    # Flatten multi-level column headers
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            col[1] if col[1] != col[0] else col[0]
            for col in df.columns
        ]

    # Drop duplicate column names — keep first occurrence
    df = df.loc[:, ~df.columns.duplicated()]

    return df


def clean_age(val):
    """
    Handle FBref age formats:
      "28"     -> 28
      "28-150" -> 28   (years-days format used in older seasons)
    """
    try:
        return int(str(val).split('-')[0].strip())
    except (ValueError, TypeError):
        return None


def clean_dataframe(df, season):
    """
    Standardise column names, remove junk rows,
    convert numeric columns, handle missing data.
    """
    # Rename columns to consistent names
    col_map = {
        'Player': 'player',
        'Nation': 'nationality',
        'Pos':    'position',
        'Squad':  'team',
        'Comp':   'league',
        'Age':    'age',
        'MP':     'matches',
        'Min':    'minutes',
        'Gls':    'goals',
        'Ast':    'assists',
    }
    cols_available = {k: v for k, v in col_map.items() if k in df.columns}
    df = df[list(cols_available.keys())].rename(columns=cols_available)

    # Remove junk rows — FBref repeats header row every 25 rows
    # and adds Squad Total / Opponent Total at the bottom
    df = df[df['player'].notna()]
    df = df[~df['player'].isin([
        'Player', 'Squad Total', 'Opponent Total'
    ])]

    # Reset index after filtering
    df = df.reset_index(drop=True)

    # Clean age — handles "28-150" format in older seasons
    if 'age' in df.columns:
        df['age'] = df['age'].apply(clean_age)

    # Convert numeric columns
    for col in ['minutes', 'goals', 'assists', 'matches']:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str)
                       .str.replace(',', '', regex=False)
                       .str.strip(),
                errors='coerce'
            )

    # Fill missing assists with 0
    # Early seasons for non-EPL leagues have no assist data
    # Capture the NaN mask BEFORE fillna — once filled, NaN info is lost
    if 'assists' in df.columns:
        assists_missing_mask = df['assists'].isna()
        n_missing = assists_missing_mask.sum()
        if n_missing > 0:
            print(f"  NOTE: {n_missing} rows have no assist data "
                  f"-> filling with 0")
        df['assists'] = df['assists'].fillna(0).astype(int)
    else:
        # Assists column absent entirely — all rows are missing
        print("  NOTE: No assists column found -> adding as 0")
        df['assists'] = 0
        assists_missing_mask = pd.Series(True, index=df.index)

    # Fill missing goals with 0
    if 'goals' in df.columns:
        df['goals'] = df['goals'].fillna(0).astype(int)
    else:
        df['goals'] = 0

    # Fill missing minutes with 0
    if 'minutes' in df.columns:
        df['minutes'] = df['minutes'].fillna(0).astype(int)
    else:
        df['minutes'] = 0

    # Fill missing matches with 0
    if 'matches' in df.columns:
        df['matches'] = df['matches'].fillna(0).astype(int)

    # Clean nationality — FBref writes "eg EGY", keep last 3 chars
    if 'nationality' in df.columns:
        df['nationality'] = (
            df['nationality']
            .astype(str)
            .str.strip()
            .str[-3:]
            .str.upper()
        )

    # Clean league name — strip language prefix
    # "eng Premier League" -> "Premier League"
    # "de Bundesliga"      -> "Bundesliga"
    if 'league' in df.columns:
        df['league'] = (
            df['league']
            .astype(str)
            .str.replace(r'^[a-z]{2,3}\s+', '', regex=True)
            .str.strip()
        )
    else:
        # Older seasons may not have Comp column
        # Infer from filename if possible
        df['league'] = 'Unknown'
        print("  NOTE: No league column found -> set to 'Unknown'")

    # Add season column
    df['season'] = season

    # assists_missing = True  → FBref had no data for this row (NaN before fill)
    # assists_missing = False → FBref had a real value (0 or more)
    # Any zero where assists_missing is False is a genuine recorded zero
    df['assists_missing'] = assists_missing_mask

    # Compute ga_per_90 — only where minutes > 0
    df['ga_per_90'] = None
    mask = df['minutes'] > 0
    df.loc[mask, 'ga_per_90'] = (
        (df.loc[mask, 'goals'] + df.loc[mask, 'assists'])
        / (df.loc[mask, 'minutes'] / 90)
    ).round(4)

    return df


def process_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_data = []

    # Find all HTML files named big5_YYYY-YYYY.html
    html_files = sorted(Path(INPUT_DIR).glob("big5_*.html"))

    if not html_files:
        print(f"No HTML files found in {INPUT_DIR}")
        print("Name files as big5_YYYY-YYYY.html e.g. big5_2022-2023.html")
        return

    print(f"Found {len(html_files)} HTML files to process\n")

    for filepath in html_files:
        season = filepath.stem.replace('big5_', '')
        print(f"Processing {season}...")

        df_raw = parse_html_file(filepath)
        if df_raw is None:
            continue

        df_clean = clean_dataframe(df_raw, season)

        # Save individual season CSV
        out_path = Path(OUTPUT_DIR) / f"big5_{season}.csv"
        df_clean.to_csv(out_path, index=False)
        print(f"  Saved {len(df_clean)} rows -> {out_path.name}")

        all_data.append(df_clean)

    if not all_data:
        print("No data processed.")
        return

    # Combine all seasons into one file
    combined = pd.concat(all_data, ignore_index=True)
    combined_path = Path(OUTPUT_DIR) / "all_seasons_combined.csv"
    combined.to_csv(combined_path, index=False)

    # Summary
    print(f"\n{'='*55}")
    print(f"  Seasons processed : {len(all_data)}")
    print(f"  Total rows        : {len(combined)}")
    print(f"  Seasons           : {sorted(combined['season'].unique())}")
    print(f"  Leagues           : {combined['league'].unique().tolist()}")
    print(f"  Combined file     : {combined_path}")

    # Assists coverage report — critical for methodology decision
    print("\n  Assists coverage by season:")
    assist_report = combined.groupby('season').agg(
        total_players=('player', 'count'),
        missing_assists=('assists_missing', 'sum'),
    )
    assist_report['coverage_pct'] = (
        (1 - assist_report['missing_assists'] / assist_report['total_players']) * 100
    ).round(1)
    print(assist_report.to_string())


if __name__ == '__main__':
    process_all()