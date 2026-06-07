import pandas as pd 
import os 
import soccerdata as sd 

START_YEAR = 1995
END_YEAR = 2023

leagues = {
    'ENG-Premier League': 'premier_league', 
    'ESP-La Liga': 'la_liga', 
    'GER-Bundesliga': 'bundesliga', 
    'FRA-Ligue 1': 'ligue_1', 
    'ITA-Seria A': 'seria_a'
}

def scrape_all(): 
    os.makedir('/Users/muhammadhamza/striker_era_ranking/data/raw/fbref', exist_ok = True)
    
    fbref = sd.FBref(leagues=list(leagues.key()), seasons = list(range(START_YEAR, END_YEAR + 1)))
    
    df = fbref.read_player_season_stats(stat_type='standard')
    df = df.reset_index()
    
    print(df.head().to_string())
    
    df.to_csv('/Users/muhammadhamza/striker_era_ranking/data/raw/fbref/combined_data_football.csv', index = False)
    
if __name__ == '__main__': 
    scrape_all()