#!/usr/bin/env python3
"""
result_updater.py — Podium 360 · ROI Auto-Updater
===================================================
Consulta historical_results (solo status_win_loss='pending'),
obtiene el score final de Football-Data.org y actualiza win/loss/push.

Uso:
    python result_updater.py
"""

import os
import re
import json
import requests
from dotenv import load_dotenv
from utils.naming import normalize_team_name

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FD_KEY       = os.getenv("FOOTBALL_DATA_KEY")
FD_BASE      = "https://api.football-data.org/v4"

# ──────────────────────────────────────────────────────────────────────────────
# Supabase helpers
# ──────────────────────────────────────────────────────────────────────────────

def _supa_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def get_pending_matches():
    """Solo las columnas necesarias, solo filas con status_win_loss=pending."""
    cols = "id,home_team,away_team,match_date,mercados_completos"
    url = (
        f"{SUPABASE_URL}/rest/v1/historical_results"
        f"?status_win_loss=eq.pending&select={cols}"
    )
    resp = requests.get(url, headers=_supa_headers(), timeout=10)
    if resp.status_code != 200:
        print(f"[ERROR] No se pudo leer historical_results (HTTP {resp.status_code}): {resp.text}")
        return []
    return resp.json()


def update_match_result(row_id, actual_result, win_loss):
    """PATCH solo las dos columnas de resultado en la fila correcta."""
    url = f"{SUPABASE_URL}/rest/v1/historical_results?id=eq.{row_id}"
    payload = {"actual_result": actual_result, "status_win_loss": win_loss}
    resp = requests.patch(url, headers=_supa_headers(), json=payload, timeout=10)
    if resp.status_code not in [200, 204]:
        print(f"  [WARN] No se pudo actualizar '{row_id}': {resp.text}")
        return False
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Football-Data helpers (con caché en memoria por fecha)
# ──────────────────────────────────────────────────────────────────────────────

_fd_cache: dict[str, list] = {}  # "YYYY-MM-DD" → [match_objects]


def _fd_headers():
    return {"X-Auth-Token": FD_KEY}


def _get_matches_on_date(date_str: str) -> list:
    """Carga todos los partidos de FD para una fecha (caché en memoria)."""
    if date_str in _fd_cache:
        return _fd_cache[date_str]

    url = f"{FD_BASE}/matches?dateFrom={date_str}&dateTo={date_str}"
    try:
        resp = requests.get(url, headers=_fd_headers(), timeout=15)
        if resp.status_code == 200:
            matches = resp.json().get("matches", [])
            print(f"  [FD] {len(matches)} partido(s) encontrado(s) para {date_str}")
        elif resp.status_code == 429:
            print(f"  [FD] Rate limit alcanzado para {date_str}. Reintenta más tarde.")
            matches = []
        else:
            print(f"  [FD] HTTP {resp.status_code} para {date_str}")
            matches = []
    except Exception as e:
        print(f"  [FD] Error de red para {date_str}: {e}")
        matches = []

    _fd_cache[date_str] = matches
    return matches


def find_fd_match(home: str, away: str, date_str: str) -> dict | None:
    """
    Busca un partido por nombre normalizado en la respuesta de FD.
    Intenta match exacto primero; si falla, intenta substring bidireccional.
    """
    matches = _get_matches_on_date(date_str)
    for m in matches:
        fd_home = normalize_team_name(m.get("homeTeam", {}).get("name", ""))
        fd_away = normalize_team_name(m.get("awayTeam", {}).get("name", ""))
        if fd_home == home and fd_away == away:
            return m

    # Segundo intento: coincidencia por subcadena (misma lógica que fuzzy_match en naming.py)
    home_u = home.upper()
    away_u = away.upper()
    for m in matches:
        fd_home = normalize_team_name(m.get("homeTeam", {}).get("name", "")).upper()
        fd_away = normalize_team_name(m.get("awayTeam", {}).get("name", "")).upper()
        home_ok = home_u in fd_home or fd_home in home_u
        away_ok = away_u in fd_away or fd_away in away_u
        if home_ok and away_ok:
            return m

    return None


# ──────────────────────────────────────────────────────────────────────────────
# Lógica de pick y evaluación
# ──────────────────────────────────────────────────────────────────────────────

def get_best_pick(mercados_completos) -> dict | None:
    """
    Selecciona el mercado a evaluar en este orden de prioridad:
      1. Pick con es_vip=True y mayor ev_pct
      2. Pick con mayor ev_pct (positivo)
      3. Primer pick de la lista como fallback
    """
    if isinstance(mercados_completos, str):
        try:
            mercados_completos = json.loads(mercados_completos)
        except Exception:
            return None

    if not isinstance(mercados_completos, list) or not mercados_completos:
        return None

    # Excluir entradas de IA que no representan un mercado real
    picks = [m for m in mercados_completos if m.get("mercado") and m.get("mercado") != "IA_ANALYSIS"]
    if not picks:
        return None

    vips = [m for m in picks if m.get("es_vip") and isinstance(m.get("ev_pct"), (int, float))]
    if vips:
        return max(vips, key=lambda m: m["ev_pct"])

    positivos = [m for m in picks if isinstance(m.get("ev_pct"), (int, float)) and m["ev_pct"] > 0]
    if positivos:
        return max(positivos, key=lambda m: m["ev_pct"])

    return picks[0]


def _parse_over_code(code: str) -> float | None:
    """
    Extrae la línea numérica de códigos over/under.
    Acepta: 'over_2.5', 'over25', 'under_3.0', 'under35', 'over_3', etc.
    """
    # Extraer todo lo que haya después de over_ / under_ / over / under
    m = re.search(r"(?:over|under)[_]?(\d+\.?\d*)", code)
    if not m:
        return None
    raw = m.group(1)
    try:
        val = float(raw)
        # "25" → 2.5, "35" → 3.5 (convención Podium de 2 dígitos sin punto)
        if val >= 10 and "." not in raw:
            val = val / 10
        return val
    except ValueError:
        return None


def _parse_spread_line(code: str) -> float | None:
    """
    Extrae la línea numérica de códigos spread/handicap.
    Acepta: 'spread_local_0.5', 'spread_visitante_-1.5', etc.
    """
    m = re.search(r"spread_(?:local|visitante)_(-?\d+\.?\d*)", code)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def evaluate_pick(mercado_code: str, home_goals: int, away_goals: int) -> str | None:
    """
    Retorna 'win', 'loss', 'push', o None si el mercado no está soportado.

    Mercados soportados:
      1X2   : 1x2_local | 1x2_empate | 1x2_visitante
      O/U   : over_2.5  | under_3.0  | over25 | under35 (etc.)
      Spread: spread_local_N | spread_visitante_N  (Asian Handicap)
      BTTS  : btts_yes | btts_no
    """
    if not mercado_code:
        return None

    code = mercado_code.lower().strip()
    total = home_goals + away_goals

    # ── 1X2 ──────────────────────────────────────────────────────────────────
    if code == "1x2_local":
        return "win" if home_goals > away_goals else "loss"
    if code == "1x2_empate":
        return "win" if home_goals == away_goals else "loss"
    if code == "1x2_visitante":
        return "win" if away_goals > home_goals else "loss"

    # ── Over / Under ──────────────────────────────────────────────────────────
    if code.startswith("over"):
        line = _parse_over_code(code)
        if line is None:
            return None
        if total == line:
            return "push"
        return "win" if total > line else "loss"

    if code.startswith("under"):
        line = _parse_over_code(code)
        if line is None:
            return None
        if total == line:
            return "push"
        return "win" if total < line else "loss"

    # ── Asian Handicap (spread) ───────────────────────────────────────────────
    if code.startswith("spread_local"):
        line = _parse_spread_line(code)
        if line is None:
            return None
        # local + line vs visitante
        adjusted = home_goals + line - away_goals
        if adjusted > 0:
            return "win"
        if adjusted == 0:
            return "push"
        return "loss"

    if code.startswith("spread_visitante"):
        line = _parse_spread_line(code)
        if line is None:
            return None
        # visitante + abs(line) vs local (line stored as negative for give)
        adjusted = away_goals - line - home_goals
        if adjusted > 0:
            return "win"
        if adjusted == 0:
            return "push"
        return "loss"

    # ── BTTS ─────────────────────────────────────────────────────────────────
    if code == "btts_yes":
        return "win" if home_goals > 0 and away_goals > 0 else "loss"
    if code == "btts_no":
        return "win" if home_goals == 0 or away_goals == 0 else "loss"

    return None  # mercado no soportado


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 52)
    print("  PODIUM 360 - RESULT UPDATER (ROI AUTO-CALIFICADOR)")
    print("=" * 52)

    if not all([SUPABASE_URL, SUPABASE_KEY, FD_KEY]):
        print("[FAIL] Faltan credenciales en .env (SUPABASE_URL, SUPABASE_KEY, FOOTBALL_DATA_KEY)")
        return

    pending = get_pending_matches()
    if not pending:
        print("[INFO] No hay partidos pendientes en historical_results. Nada que actualizar.")
        return

    print(f"[INFO] {len(pending)} partido(s) con status_win_loss='pending'.\n")

    updated = skipped = unsupported = 0

    for row in pending:
        row_id  = row["id"]
        home    = normalize_team_name(row.get("home_team", ""))
        away    = normalize_team_name(row.get("away_team", ""))
        date_s  = row.get("match_date", "")

        print(f"→ {home} vs {away} ({date_s})")

        # 1. Buscar en Football-Data
        fd_match = find_fd_match(home, away, date_s)
        if not fd_match:
            print(f"  [SKIP] No encontrado en Football-Data.")
            skipped += 1
            continue

        # 2. Verificar que esté finalizado
        fd_status = fd_match.get("status", "")
        if fd_status not in ("FINISHED", "AWARDED"):
            print(f"  [SKIP] Estado FD: {fd_status}. Partido aún no terminado.")
            skipped += 1
            continue

        # 3. Extraer score
        full_time = fd_match.get("score", {}).get("fullTime", {})
        hg = full_time.get("home")
        ag = full_time.get("away")
        if hg is None or ag is None:
            print(f"  [SKIP] Score null en Football-Data.")
            skipped += 1
            continue

        actual_result = f"{hg}-{ag}"

        # 4. Determinar pick a evaluar (VIP > mayor EV+ > primero)
        best_pick = get_best_pick(row.get("mercados_completos"))
        mercado_code = best_pick.get("mercado") if best_pick else None

        # 5. Evaluar resultado
        win_loss = evaluate_pick(mercado_code, hg, ag)
        if win_loss is None:
            print(f"  [SKIP] Mercado no soportado: '{mercado_code}'")
            unsupported += 1
            continue

        # 6. Actualizar Supabase
        if update_match_result(row_id, actual_result, win_loss):
            ev_str = f" (EV {best_pick.get('ev_pct', '?')}%)" if best_pick else ""
            print(f"  [OK] {actual_result} → {win_loss.upper()} | pick: {mercado_code}{ev_str}")
            updated += 1
        else:
            skipped += 1

    print()
    print("─" * 52)
    print(f"  Actualizados : {updated}")
    print(f"  Saltados     : {skipped}")
    print(f"  Sin soporte  : {unsupported}")
    print("─" * 52)


if __name__ == "__main__":
    main()
