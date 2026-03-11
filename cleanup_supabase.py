import os
import requests
from dotenv import load_dotenv

def main():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    # Let's get all daily board matches
    resp = requests.get(f"{url}/rest/v1/daily_board?select=id,home_team,away_team", headers=headers)
    matches = resp.json()
    print("CURRENT BOARD:")
    for m in matches:
        print(f" - {m['id']}: {m['home_team']} vs {m['away_team']}")
        
        # Delete dummy matches (Bayern vs Arsenal, PSG vs Barcelona if dummy)
        # Actually I will just delete everything except the ones that are real
        # Or better: let's delete exactly Bayern and Arsenal if they are there, and everything that has null date if we can't find it.
        if m['home_team'] == 'Bayern Munich' or m['away_team'] == 'Arsenal':
            requests.delete(f"{url}/rest/v1/daily_board?id=eq.{m['id']}", headers=headers)
            print(f"   -> Deleted {m['id']} from daily_board")

    resp2 = requests.get(f"{url}/rest/v1/vip_signals?select=id,home_team,away_team", headers=headers)
    vips = resp2.json()
    print("CURRENT VIPS:")
    for v in vips:
        if v['home_team'] == 'Bayern Munich' or v['away_team'] == 'Arsenal':
            requests.delete(f"{url}/rest/v1/vip_signals?id=eq.{v['id']}", headers=headers)
            print(f"   -> Deleted {v['id']} from vip_signals")

if __name__ == '__main__':
    main()
