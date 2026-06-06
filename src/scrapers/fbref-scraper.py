import pandas as pd 
import requests 
import os 
from bs4 import BeautifulSoup
import re 
import time 
import cloudscraper

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

START_YEAR = 1995
END_YEAR = 2023
delay = 4

leagues = {
    "premier_league": {"id": "9",  "name": "Premier-League"},
    "la_liga": {"id": "12", "name": "La-Liga"},
    "serie_a": {"id": "11", "name": "Serie-A"},
    "bundesliga": {"id": "20", "name": "Bundesliga"},
    "ligue_1": {"id": "13", "name": "Ligue-1"},
}

def build_url(league_id, league_name, start_year):
    end_year = start_year + 1
    return (
        f"https://fbref.com/en/comps/{league_id}"
        f"/{start_year}-{end_year}/stats"
        f"/{start_year}-{end_year}-{league_name}-Stats"
    )

def fetch_season(league_key, start_year, session):
    league   = leagues[league_key]
    url      = build_url(league["id"], league["name"], start_year)
    end_year = start_year + 1
    season   = f"{start_year}-{end_year}"

    print(f"  Fetching {league_key} {season}...")

    try:
        time.sleep(delay)
        response = session.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  ERROR: {e}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, 'lxml')

    table = soup.find('table', {'id': 'stats_standard'})
    if table is None:
        print(f"  WARNING: No stats table found for {league_key} {season}")
        return pd.DataFrame()

    df = pd.read_html(str(table))[0]

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            col[1] if col[1] != col[0] else col[0]
            for col in df.columns
        ]

    return df, season, league_key

def clean_season(df, season, league_key): 
    
    col_map = {
        'Player': 'player', 
        'Nation': 'nationality', 
        'Pos': 'position', 
        'Squad': 'team', 
        'Age': 'age', 
        'MP': 'matches', 
        'Min': 'minutes', 
        'Gls': 'goals', 
        'Ast': 'assists'
    }
    
    cols_avaialble = {k: v for k, v in col_map.items() if k in df.columns}
    df = df[list(cols_avaialble.keys())].rename(columns=cols_avaialble)
    
    df = df[df['player'].notna()]
    df = df[~df['player'].isin(['Player', 'Squad Total', 'Opponent Total'])]
    
    for col in ['minutes', 'goals', 'assists', 'matches']: 
        for col in df.columns: 
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(',', ''), 
                errors='coerce'
            )
            
    if 'nationality' in df.columns: 
        df['nationality'] = df['nationality'].str.strip().str[-3:]
        
    df['season'] = season
    df['league'] = league_key
    
    df['ga_per_90'] = (df['goals'] + df['assists']) / (df['minutes']/90)
    
    return df 

def scrape_all():
    os.makedirs('data/raw/fbref', exist_ok=True)
    all_data = []

    session = cloudscraper.create_scraper()

    # Visit the FBref homepage first to get cookies
    print("Initialising session...")
    session.get("https://fbref.com/en/", timeout=20)
    time.sleep(3)

    for league_key in leagues.keys():
        print(f"\nScraping {league_key}...")

        for start_year in range(START_YEAR, END_YEAR + 1):
            result = fetch_season(league_key, start_year, session)

            if isinstance(result, pd.DataFrame) and result.empty:
                continue

            df_raw, season, lkey = result
            df_clean = clean_season(df_raw, season, lkey)

            out_path = f"data/raw/fbref/{league_key}_{season}.csv"
            df_clean.to_csv(out_path, index=False)

            all_data.append(df_clean)

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined.to_csv('data/raw/fbref/all_leagues_combined.csv', index=False)
        print(f"\nDone. {len(combined)} total player-season records.")
        print(combined.head(10).to_string(index=False))
        
if __name__ == '__main__':
    session = requests.Session()
    session.headers.update(headers)

    print("Initialising session...")
    session.get("https://fbref.com/en/", timeout=20)
    time.sleep(3)

    result = fetch_season('premier_league', 2022, session)
    if not isinstance(result, pd.DataFrame):
        df_raw, season, lkey = result
        df_clean = clean_season(df_raw, season, lkey)
        print(df_clean.head(20).to_string(index=False))

    # scrape_all()