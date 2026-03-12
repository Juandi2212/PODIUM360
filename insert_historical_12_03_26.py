"""
Script único: archiva los partidos del 12-Mar-2026 en historical_results
con resultados reales ya conocidos.

Ejecutar DESPUÉS de haber creado la tabla con migrations/create_historical_results.sql
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

# Resultados reales del 12-Mar-2026 (UEL Round of 16 - 1st leg)
RESULTADOS = {
    "2026-03-12_Bologna_AS_Roma":              ("1-1", "loss"),   # VIP: 1x2_visitante Roma
    "2026-03-12_Celta_Vigo_Lyon":              ("1-0", "loss"),   # VIP: 1x2_visitante Lyon
    "2026-03-12_Genk_Freiburg":                ("1-0", "loss"),   # VIP: over25
    "2026-03-12_Lille_Aston_Villa":            ("0-1", "loss"),   # VIP: 1x2_local Lille
    "2026-03-12_Nottingham_Forest_Midtjylland":("0-0", "loss"),   # VIP: 1x2_visitante Midtjylland
    "2026-03-12_Panathinaikos_Real_Betis":     ("1-0", "win"),    # VIP: 1x2_local Panathinaikos ✅
    "2026-03-12_Stuttgart_Porto":              ("1-2", "win"),    # VIP: 1x2_visitante Porto ✅
}

def get_daily_board():
    """Lee todos los partidos del 12-Mar de daily_board."""
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/daily_board?match_date=eq.2026-03-12&select=*",
        headers=HEADERS,
    )
    if r.status_code != 200:
        print(f"[ERROR] No se pudo leer daily_board: {r.status_code} {r.text[:200]}")
        return []
    return r.json()


def build_archive_rows(rows):
    """Construye las filas para historical_results."""
    archive = []
    for row in rows:
        rid = row.get("id")
        resultado, win_loss = RESULTADOS.get(rid, (None, "pending"))
        archive.append({
            "id":                  rid,
            "match_date":          row.get("match_date"),
            "home_team":           row.get("home_team"),
            "away_team":           row.get("away_team"),
            "competition":         "Europa League",
            "hora_utc":            row.get("hora_utc"),
            "poisson_1":           row.get("poisson_1"),
            "poisson_x":           row.get("poisson_x"),
            "poisson_2":           row.get("poisson_2"),
            "xg_diff":             row.get("xg_diff"),
            "estado_mercado":      row.get("estado_mercado"),
            "mercados_completos":  row.get("mercados_completos"),
            "ai_analysis":         row.get("ai_analysis"),
            "status":              "finished",
            "actual_result":       resultado,
            "status_win_loss":     win_loss,
        })
    return archive


def insert_historical(rows):
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/historical_results",
        headers=HEADERS,
        json=rows,
    )
    if r.status_code in [200, 201]:
        print(f"[OK] {len(rows)} partido(s) insertado(s) en historical_results.")
    else:
        print(f"[ERROR] HTTP {r.status_code}: {r.text[:400]}")


def main():
    print("=== INSERT HISTORICAL — 12 Mar 2026 ===")
    rows = get_daily_board()
    if not rows:
        print("[WARN] No se encontraron partidos en daily_board para 2026-03-12.")
        return

    archive_rows = build_archive_rows(rows)
    print(f"[INFO] Preparando {len(archive_rows)} registros...")
    for r in archive_rows:
        wl = r['status_win_loss'].upper()
        print(f"  {r['id']:55s} | {r['actual_result']:5s}  {wl}")

    insert_historical(archive_rows)


if __name__ == "__main__":
    main()
