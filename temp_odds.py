import os
import requests
from dotenv import load_dotenv

load_dotenv('c:/Users/Juan/Desktop/CLAUDE DL/.env')
key = os.environ.get('ODDS_API_KEY')

url = f'https://api.the-odds-api.com/v4/sports/soccer_uefa_champs_league/odds/?apiKey={key}&regions=eu&markets=h2h'
r = requests.get(url)
events = r.json()

if isinstance(events, list):
    for event in events:
        print(f"{event.get('home_team')} vs {event.get('away_team')}")
else:
    print("Error:", events)
