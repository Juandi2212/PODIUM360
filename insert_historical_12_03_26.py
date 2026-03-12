"""
Script único: archiva los picks VIP del 12-Mar-2026 en historical_results.
Un registro por pick VIP (igual que los IDs de vip_signals).

Resultados reales confirmados:
  Bologna 1-1 AS Roma
  Celta Vigo 1-1 Lyon
  Genk 1-0 Freiburg
  Lille 0-1 Aston Villa
  Nottingham Forest 0-1 Midtjylland
  Panathinaikos 1-0 Real Betis
  Stuttgart 1-2 Porto
"""

import os, requests, json
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates",
}

# Resultados y evaluacion por pick-level ID (mismo formato que vip_signals)
# over25 requiere >2.5 goles totales (3+). Con 2 goles = LOSS.
PICKS = [
    # Bologna 1-1 AS Roma
    {
        "id":             "2026-03-12_Bologna_AS_Roma_1x2_visitante",
        "home_team":      "Bologna",
        "away_team":      "AS Roma",
        "competition":    "Europa League",
        "match_date":     "2026-03-12",
        "mercado":        "1x2_visitante",
        "cuota":          2.62,
        "ev_pct":         10.88,
        "actual_result":  "1-1",
        "status_win_loss":"loss",   # Roma no gano (empate)
    },
    # Celta Vigo 1-1 Lyon
    {
        "id":             "2026-03-12_Celta_Vigo_Lyon_1x2_visitante",
        "home_team":      "Celta Vigo",
        "away_team":      "Lyon",
        "competition":    "Europa League",
        "match_date":     "2026-03-12",
        "mercado":        "1x2_visitante",
        "cuota":          4.10,
        "ev_pct":         28.12,
        "actual_result":  "1-1",
        "status_win_loss":"loss",   # Lyon no gano (empate)
    },
    {
        "id":             "2026-03-12_Celta_Vigo_Lyon_over25",
        "home_team":      "Celta Vigo",
        "away_team":      "Lyon",
        "competition":    "Europa League",
        "match_date":     "2026-03-12",
        "mercado":        "over25",
        "cuota":          2.08,
        "ev_pct":         6.87,
        "actual_result":  "1-1",
        "status_win_loss":"loss",   # 2 goles totales, necesitaba 3+
    },
    # Genk 1-0 Freiburg
    {
        "id":             "2026-03-12_Genk_Freiburg_over25",
        "home_team":      "Genk",
        "away_team":      "Freiburg",
        "competition":    "Europa League",
        "match_date":     "2026-03-12",
        "mercado":        "over25",
        "cuota":          2.20,
        "ev_pct":         19.83,
        "actual_result":  "1-0",
        "status_win_loss":"loss",   # 1 gol total
    },
    {
        "id":             "2026-03-12_Genk_Freiburg_1x2_visitante",
        "home_team":      "Genk",
        "away_team":      "Freiburg",
        "competition":    "Europa League",
        "match_date":     "2026-03-12",
        "mercado":        "1x2_visitante",
        "cuota":          2.92,
        "ev_pct":         8.36,
        "actual_result":  "1-0",
        "status_win_loss":"loss",   # Genk gano
    },
    # Lille 0-1 Aston Villa
    {
        "id":             "2026-03-12_Lille_Aston_Villa_1x2_local",
        "home_team":      "Lille",
        "away_team":      "Aston Villa",
        "competition":    "Europa League",
        "match_date":     "2026-03-12",
        "mercado":        "1x2_local",
        "cuota":          3.57,
        "ev_pct":         20.31,
        "actual_result":  "0-1",
        "status_win_loss":"loss",   # Lille no gano
    },
    {
        "id":             "2026-03-12_Lille_Aston_Villa_over25",
        "home_team":      "Lille",
        "away_team":      "Aston Villa",
        "competition":    "Europa League",
        "match_date":     "2026-03-12",
        "mercado":        "over25",
        "cuota":          2.32,
        "ev_pct":         18.37,
        "actual_result":  "0-1",
        "status_win_loss":"loss",   # 1 gol total
    },
    # Nottingham Forest 0-1 Midtjylland
    {
        "id":             "2026-03-12_Nottingham_Forest_Midtjylland_1x2_visitante",
        "home_team":      "Nottingham Forest",
        "away_team":      "Midtjylland",
        "competition":    "Europa League",
        "match_date":     "2026-03-12",
        "mercado":        "1x2_visitante",
        "cuota":          6.75,
        "ev_pct":         138.68,
        "actual_result":  "0-1",
        "status_win_loss":"win",    # Midtjylland gano ✅
    },
    {
        "id":             "2026-03-12_Nottingham_Forest_Midtjylland_over25",
        "home_team":      "Nottingham Forest",
        "away_team":      "Midtjylland",
        "competition":    "Europa League",
        "match_date":     "2026-03-12",
        "mercado":        "over25",
        "cuota":          1.83,
        "ev_pct":         10.97,
        "actual_result":  "0-1",
        "status_win_loss":"loss",   # 1 gol total
    },
    # Panathinaikos 1-0 Real Betis
    {
        "id":             "2026-03-12_Panathinaikos_Real_Betis_1x2_local",
        "home_team":      "Panathinaikos",
        "away_team":      "Real Betis",
        "competition":    "Europa League",
        "match_date":     "2026-03-12",
        "mercado":        "1x2_local",
        "cuota":          3.70,
        "ev_pct":         50.66,
        "actual_result":  "1-0",
        "status_win_loss":"win",    # Panathinaikos gano ✅
    },
    {
        "id":             "2026-03-12_Panathinaikos_Real_Betis_over25",
        "home_team":      "Panathinaikos",
        "away_team":      "Real Betis",
        "competition":    "Europa League",
        "match_date":     "2026-03-12",
        "mercado":        "over25",
        "cuota":          2.21,
        "ev_pct":         10.81,
        "actual_result":  "1-0",
        "status_win_loss":"loss",   # 1 gol total
    },
    # Stuttgart 1-2 Porto
    {
        "id":             "2026-03-12_Stuttgart_Porto_1x2_visitante",
        "home_team":      "Stuttgart",
        "away_team":      "Porto",
        "competition":    "Europa League",
        "match_date":     "2026-03-12",
        "mercado":        "1x2_visitante",
        "cuota":          4.60,
        "ev_pct":         69.65,
        "actual_result":  "1-2",
        "status_win_loss":"win",    # Porto gano ✅
    },
]


def insert_historical(rows):
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/historical_results",
        headers=HEADERS,
        json=rows,
    )
    if r.status_code in [200, 201]:
        print(f"[OK] {len(rows)} picks insertados en historical_results.")
    else:
        print(f"[ERROR] HTTP {r.status_code}: {r.text[:400]}")


def main():
    print("=== INSERT HISTORICAL (pick-level) -- 12 Mar 2026 ===")
    wins  = [p for p in PICKS if p["status_win_loss"] == "win"]
    loses = [p for p in PICKS if p["status_win_loss"] == "loss"]
    print(f"[INFO] {len(PICKS)} picks totales | {len(wins)} WIN / {len(loses)} LOSS")
    for p in PICKS:
        tag = "WIN " if p["status_win_loss"] == "win" else "LOSS"
        print(f"  [{tag}] {p['id']}")

    insert_historical(PICKS)


if __name__ == "__main__":
    main()
