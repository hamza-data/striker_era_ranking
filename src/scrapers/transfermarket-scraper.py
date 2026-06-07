import pandas as pd 
import os 
import re 
import requests 
from bs4 import BeautifulSoup
import time

START_YEAR = 1995 
END_YEAR = 2023

DELAY = 4 

leagues = {
    "premier_league": {"slug": "premier-league", "code": "GB1"},
    "la_liga": {"slug": "laliga", "code": "ES1"},
    "serie_a": {"slug": "serie-a", "code": "IT1"},
    "bundesliga": {"slug": "bundesliga", "code": "L1"},
    "ligue_1": {"slug": "ligue-1", "code": "FR1"},
}

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.transfermarkt.co.uk/",
    "Sec-Ch-Ua": '"Chromium";v="120", "Google Chrome";v="120", "Not-A.Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

def build_league_url(slug, code, season_year): 
    return (
        f"https://www.transfermarkt.co.uk"
        f"/{slug}/startseite/wettbewerb/{code}"
        f"/plus/?saison_id={season_year}"
    )
    
def build_player_stats_url(player_slug, player_id): 
    return (
        f"https://www.transfermarkt.co.uk"
        f"/{player_slug}/leistungsdaten/spieler/{player_id}/plus/0"
    )
    
def create_session(): 
    session = requests.Session()
    session.headers.update(headers)
    return session

def fetch_page(session, url): 
    try: 
        response = session.get(url, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'lxml')
    except requests.RequestException as e: 
        print(f"Error fetching {url}: {e}")
        return None
    
def get_clubs(session, slug, code, season_year): 
    url = build_league_url(slug, code, season_year)
    soup = fetch_page(session, url)
    if soup is None: 
        return []
    
    clubs = []
    table = soup.find('table', class_='items')
    if table is None: 
        return []
    
    for row in table.find_all('tr', class_=['odd', 'even']): 
        link = row.find('a', href=True)
        if link is None: 
            continue
        
        href = link['href']
        if '/startseite/verein/' not in href: 
            continue
        
        club_name = link.get_text(strip=True)
        clubs.append({
            'name': club_name, 
            'url': 'https://www.transfermarkt.co.uk' + href,
        })
    
    return clubs

def get_players(session, club_url, season_year): 
    
    squad_url = re.sub(r'saison_id/\d+', f'saison_id/{season_year}', club_url)
    squad_url = squad_url.replace('/startseite/', '/kader/')
    
    soup = fetch_page(session, squad_url) 
    if soup is None: 
        return []
    
    players = []
    table = soup.find('table', class_ = 'items')
    if table is None: 
        return []
    
    for row in table.find_all('tr', class_=['odd', 'even']): 
        name_cell = row.find('td', class_='hauptlink')
        if name_cell is None: 
            continue
        
        link = name_cell.find('a', href=True)
        if link is None:
            continue
        
        href = link['href']
        name = link.get_text(strip=True)
        
        match = re.search(r'/(.+?)/profil/spieler/(\d+)', href)
        if match is None: 
            continue
        
        player_slug = match.group(1)
        player_id = match.group(2)
        
        pos_cell = row.find('td', class_='posrela')
        position = pos_cell.get_text(strip=True) if pos_cell else ''
        
        nat_img = row.find('img', class_='flaggenrahmen')
        nationality = nat_img['title'] if nat_img else ''
        
        players.append({
            'name': name, 
            'player_id': player_id, 
            'player_slug': player_slug, 
            'position': position, 
            'nationality': nationality
        })
        
    return players

def get_player_stats(session, player_slug, player_id, target_season): 
    url = build_player_stats_url(player_slug, player_id)
    soup = fetch_page(session, url)
    if soup is None: 
        return None
    
    table = soup.find('table', class_='items')
    if table is None: 
        return None
    
    for row in table.find_all('tr', class_=['odd', 'even']): 
        cells = row.find_all('td')
        if len(cells) < 8: 
            continue
        
        season_text = cells[0].get_text(strip=True)
        if not season_text.startswith(str(target_season)):
            continue
        
        def cell_text(i): 
            return cells[i].get_text(strip=True) if i < len(cells) else ''
        
        def to_int(val): 
            cleaned = re.sub(r'[^\d]', '', val)
            return int(cleaned) if cleaned else 0 
        
        mins_raw = cell_text(8)
        
        minutes = to_int(mins_raw.replace('.', '').replace("'", ''))
        
        return {
            'appearance': to_int(cell_text(3)),
            'goals': to_int(cell_text(5)),
            'assists': to_int(cell_text(6)), 
            'minutes': minutes
        }
        
    return None

def scrape_all(): 
    
    os.makedirs('/Users/muhammadhamza/striker_era_ranking/data/raw/fbref', exist_ok=True)
    session = create_session()
    all_data = []
    
    for league_key, league_info in leagues.item(): 
        print(f"Scraping {league_key}")
        
        for season_year in range(START_YEAR, END_YEAR + 1): 
            print(f"Season {season_year} - {season_year + 1} ")
            season_label = f"{season_year} - {season_year + 1}"
            
            clubs = get_clubs(
                session, 
                league_info['slug'],
                league_info['code'], 
                season_year
            )
            print(f'Found {len(clubs)} clubs')
            
            for club in clubs: 
                time.sleep(DELAY)
                players = get_players(session, club['url'], season_year)
                
                for player in players: 
                    time.sleep(DELAY)
                    stats = get_player_stats(
                        session, 
                        player['player_slug'], 
                        player['player_id'], 
                        season_year
                    )
                    
                    if stats is None: 
                        continue
                    
                    all_data.append({
                        'season': season_label, 
                        'league': league_key, 
                        'team': club['name'], 
                        'player': player['name'], 
                        'nationality': player['nationality'], 
                        'position': player['position'],
                        'appearances': stats['appearances'], 
                        'goals': stats['goals'], 
                        'assists': stats['assists'], 
                        'minutes': stats['minutes']
                    })
            if all_data: 
                df = pd.DataFrame(all_data)
                df.to_csv(f'/Users/muhammadhamza/striker_era_ranking/data/raw/fbref/{league_key}_{season_label}.csv')
                print(f'Saved {len(df)} records so far')
    if all_data:
        df_final = pd.DataFrame(all_data)
        df_final['ga_per_90'] = (
            (df_final['goals'] + df_final['assists']) / (df_final['minutes']/90)
        )
        df_final.to_csv('/Users/muhammadhamza/striker_era_ranking/data/raw/fbref/all_leagues_combined.csv', index = False)
        print(f'Done, total records: {len(df_final)}')
        print(df_final.head().to_string(index = False))
        
if __name__ == '__main__':
    session = create_session()

    # Test: get clubs for Premier League 2022 season only
    clubs = get_clubs(session, 'premier-league', 'GB1', 2022)
    print(f"Clubs found: {len(clubs)}")
    for c in clubs[:5]:
        print(f"  {c['name']} — {c['url']}")                