import os
import sys
import json
import glob
from datetime import datetime
import dotenv
import requests

dotenv.load_dotenv()

PRONOSTICOS_DIR = "Pronosticos"
DB_DIR = "database"
TRACKING_FILE = os.path.join(DB_DIR, "tracking_metrics.json")
FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY")
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"

def load_json(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

def fetch_match_result(local_team, away_team):
    """
    Mock function for now. Real implementation would call Football-Data.org
    to see if the match is FINISHED and grab the score.
    """
    # Para la fase actual de desarrollo vamos a simular la resolución
    # basado en un placeholder, ya que no queremos gastar cuotas de la API buscando partidos futuros
    return {
        "status": "FINISHED",
        "score": {
            "home": 2,
            "away": 1
        }
    }

def get_pick_outcome(pick, result_score):
    """
    Evalúa si un pick se ganó, perdió o anuló según el resultado.
    """
    if result_score is None:
        return "PENDING"
    
    hs = result_score["home"]
    as_ = result_score["away"]
    
    mercado = pick.get("mercado", "")
    if mercado == "1x2_local":
        return "WON" if hs > as_ else "LOST"
    elif mercado == "1x2_empate":
        return "WON" if hs == as_ else "LOST"
    elif mercado == "1x2_visitante":
        return "WON" if as_ > hs else "LOST"
    elif mercado in ("over_2.5", "over25"):
        return "WON" if (hs + as_) > 2.5 else "LOST"
    elif mercado == "btts":
        return "WON" if (hs > 0 and as_ > 0) else "LOST"
    
    return "PENDING"

def calculate_metrics(history):
    total_staked = 0.0
    total_returned = 0.0
    wins = 0
    losses = 0
    
    for bet in history:
        if bet["outcome"] == "WON":
            wins += 1
            total_staked += 1.0  # Unit stake
            total_returned += bet["cuota"] * 1.0
        elif bet["outcome"] == "LOST":
            losses += 1
            total_staked += 1.0
            # Returns 0
    
    winrate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    net_profit = total_returned - total_staked
    roi_yield = (net_profit / total_staked) * 100 if total_staked > 0 else 0
    
    return {
        "total_picks": wins + losses,
        "wins": wins,
        "losses": losses,
        "winrate_pct": round(winrate, 2),
        "total_staked_units": round(total_staked, 2),
        "net_profit_units": round(net_profit, 2),
        "yield_pct": round(roi_yield, 2)
    }

def main():
    print("========================================================")
    print("  PODIUM SaaS — Tracker Engine (Forward-Testing)")
    print("========================================================")
    
    os.makedirs(DB_DIR, exist_ok=True)
    
    # Load existing tracking db or create new
    db_data = load_json(TRACKING_FILE) or {"history": []}
    history = db_data["history"]
    
    # Get all processed predictions
    files = glob.glob(os.path.join(PRONOSTICOS_DIR, "*.json"))
    pending_files = [f for f in files if "ALERT" not in f]
    
    new_resolutions = 0
    
    for fpath in pending_files:
        data = load_json(fpath)
        if not data:
            continue
            
        picks = data.get("top_3_picks", [])
        if not picks:
            continue
            
        # We only track VIP / Positive EV picks for the Yield calculation
        vip_picks = [p for p in picks if p.get("ev_pct", 0) > 0]
        
        # Check if they are already in history
        for p in vip_picks:
            pick_id = f"{fpath}_{p['mercado']}"
            if any(h["pick_id"] == pick_id for h in history):
                continue # Already resolved
                
            # Resolve the match
            match = fetch_match_result("Local", "Visit") # Mock
            if match["status"] == "FINISHED":
                outcome = get_pick_outcome(p, match["score"])
                history.append({
                    "pick_id": pick_id,
                    "date_logged": datetime.now().isoformat(),
                    "mercado": p["mercado"],
                    "cuota": p["cuota"],
                    "ev_initial": p["ev_pct"],
                    "outcome": outcome,
                    "simulated_score": match["score"]
                })
                new_resolutions += 1
                print(f"  [RESOLVED] {p['mercado']} @ {p['cuota']} ({fpath}) -> {outcome}")

    if new_resolutions > 0:
        db_data["history"] = history
        db_data["metrics"] = calculate_metrics(history)
        
        with open(TRACKING_FILE, "w", encoding="utf-8") as f:
            json.dump(db_data, f, ensure_ascii=False, indent=2)
            
        print(f"\n  [OK] {new_resolutions} nuevos picks resueltos y añadidos al tracker.")
        print(f"  [YIELD] Yield Actual: {db_data['metrics']['yield_pct']}% | Winrate: {db_data['metrics']['winrate_pct']}%")
    else:
        print("  [OK] No hay nuevos partidos pendientes de resolución.")
        
    print("========================================================\n")

if __name__ == "__main__":
    main()
