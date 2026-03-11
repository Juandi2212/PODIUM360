import os
import requests
from dotenv import load_dotenv

load_dotenv('c:/Users/Juan/Desktop/CLAUDE DL/.env')
key = os.environ.get('ODDS_API_KEY')

url = f'https://api.the-odds-api.com/v4/sports/soccer_uefa_champs_league/odds/?apiKey={key}&regions=eu&markets=h2h,spreads,totals'
r = requests.get(url)
events = r.json()

if isinstance(events, list) and len(events) > 0:
    for ev in events[:1]:
        print(f"Match: {ev.get('home_team')} vs {ev.get('away_team')}")
        all_markets = {}
        for bookmaker in ev.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                m_key = market.get('key')
                if m_key not in all_markets:
                    all_markets[m_key] = set()
                for out in market.get('outcomes', []):
                    name = out.get('name')
                    point = out.get('point', '') # if there's a point (like 2.5)
                    all_markets[m_key].add(f"{name} {point}".strip())
        
        for m, opts in all_markets.items():
            print(f"Market: {m}")
            for o in sorted(opts):
                print(f"  - {o}")
else:
    print('No events found or error', events)
