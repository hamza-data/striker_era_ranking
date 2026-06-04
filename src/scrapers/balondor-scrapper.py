import pandas as pd 
from bs4 import BeautifulSoup
import os 
import re 
import requests 

URL = 'https://en.wikipedia.org/wiki/Ballon_d%27Or'

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko)"
        "Chrome/137.0.0.0 Safari/537.36"
    )
}

def fetch_page(URL): 
    response = requests.get(URL, headers=headers, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'lxml')

def find_winners_table(soup): 
    for table in soup.find_all('table', class_='wikitable'):
        caption = table.find('caption')
        if caption and 'winner' in caption.get_text(strip=True).lower():
            return table
        headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
        if 'year' in headers and 'player' in headers:
            return table
    return None

def extract_flag_country(cell): 
    flagicon = cell.find('span', class_='flagicon')
    if flagicon is None:
        return ''
    
    img = flagicon.find('img')
    if img: 
        return img.get('alt', '').strip()
    
    return ''    

_FOOTNOTE  = re.compile(r'\[\w+\]')
_WIN_COUNT = re.compile(r'\s*\(\d+\)\s*')

def clean_name(raw): 
    name = _FOOTNOTE.sub('', raw)
    name = _WIN_COUNT.sub('', raw)
    return name.strip()
def name_from_cell(cell): 
    for a in cell.find_all('a', href=True): 
        if a.find_parent('span', class_='flagicon'): 
            continue
        text = a.got_text(strip=True)
        if text: 
            return clean_name(text)
    return clean_name(cell.get_text(strip=True))

def parse_winners_table(table):
    records = []
    current_year = None

    for row in table.find_all('tr'):
        cells = row.find_all(['td', 'th'])
        if not cells:
            continue

        first_text = cells[0].get_text(strip=True)
        year_match = re.match(r'^(\d{4})$', first_text)

        if year_match:
            current_year = int(year_match.group(1))
            cells = cells[1:]

        if current_year is None:
            continue

        if len(cells) < 3:
            continue

        rank_text = cells[0].get_text(strip=True)
        rank = int(re.match(r'(\d+)', rank_text).group(1)) if re.match(r'(\d+)', rank_text) else 0
        if rank == 0:
            continue

        player       = name_from_cell(cells[1])
        nationality  = extract_flag_country(cells[1])
        team         = name_from_cell(cells[2])
        club_country = extract_flag_country(cells[2])
        points       = int(re.sub(r'[^\d]', '', cells[3].get_text(strip=True)) or 0) if len(cells) >= 4 else 0

        records.append({
            'year':         current_year,
            'rank':         rank,
            'player':       player,
            'nationality':  nationality,
            'team':         team,
            'club_country': club_country,
            'points':       points,
        })

    return records

def main(): 
    os.makedirs('/Users/muhammadhamza/striker_era_ranking/data/raw/ballon_dor', exist_ok=True)
    
    soup = fetch_page(URL)
    table = find_winners_table(soup)
    
    if table is None: 
        raise RuntimeError('Could not find winner table')
    
    records = parse_winners_table(table)
    
    df = pd.DataFrame(records)
    df = df[df['year'] != 2020] # no award given that year due to covid
    df = df.sort_values(['year', 'rank']).reset_index(drop=True)
    
    output_path = '/Users/muhammadhamza/striker_era_ranking/data/raw/ballon_dor/ballon_dor_winners.csv'
    df.to_csv(output_path, index=False)
    
    print(f"Done. {len(df)} rows saved to {output_path}")
    print(df.head(10).to_string(index=False))
    
if __name__ == '__main__': 
    main()