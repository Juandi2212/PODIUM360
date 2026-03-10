"""Test SofaScore API for per-match xG data."""
import requests, json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.sofascore.com/",
}

# Step 1: Search for Arsenal
r = requests.get("https://api.sofascore.com/api/v1/search/teams?q=Arsenal",
                 headers=HEADERS, timeout=15)
print("Search status:", r.status_code)
if r.status_code == 200:
    teams = r.json().get("teams", [])
    for t in teams[:3]:
        print(f"  id={t['id']}  name={t['name']}  country={t.get('country',{}).get('name','?')}")
    arsenal_id = next((t["id"] for t in teams if t["name"] == "Arsenal"), None)
    print("Arsenal id:", arsenal_id)
else:
    # Try hardcoded Arsenal id = 42
    arsenal_id = 42

# Step 2: Get last events for Arsenal
print(f"\nFetching last events for team {arsenal_id}...")
r2 = requests.get(f"https://api.sofascore.com/api/v1/team/{arsenal_id}/events/last/0",
                  headers=HEADERS, timeout=15)
print("Events status:", r2.status_code)
if r2.status_code == 200:
    evts = r2.json().get("events", [])
    print(f"Events returned: {len(evts)}")
    if evts:
        e = evts[-1]
        print("Event keys:", list(e.keys()))
        print("Sample event:", json.dumps(e, indent=2)[:400])

# Step 3: Get statistics (xG) for one event
if r2.status_code == 200 and evts:
    eid = evts[-1]["id"]
    r3 = requests.get(f"https://api.sofascore.com/api/v1/event/{eid}/statistics",
                      headers=HEADERS, timeout=15)
    print(f"\nStatistics status for event {eid}:", r3.status_code)
    if r3.status_code == 200:
        stats_data = r3.json()
        raw = json.dumps(stats_data)
        for kw in ["xg", "xG", "expectedGoal", "Expected"]:
            idx = raw.lower().find(kw.lower())
            if idx >= 0:
                print(f"Found '{kw}': {raw[max(0,idx-30):idx+120]}")
                break
        else:
            print("xG NOT found. Top groups:", [g.get("groupName") for g in stats_data.get("statistics", [])][:5])
