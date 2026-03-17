#!/usr/bin/env python3
"""
result_updater.py — Podium 360 · ROI Auto-Updater
===================================================
Consulta historical_results (solo status_win_loss='pending'),
obtiene el score final de API-Football y actualiza win/loss/push.

Uso:
    python result_updater.py                 # modo normal
    python result_updater.py --debug DATE    # muestra nombres reales de AF para una fecha
                                             # DATE formato YYYY-MM-DD, ej: 2026-03-15
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from utils.naming import normalize_team_name

MANUAL_MATCHES_PATH = Path(__file__).parent / "partidos_manuales.json"

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
AF_KEY       = os.getenv("API_FOOTBALL_KEY")
AF_BASE      = "https://v3.football.api-sports.io"

# ──────────────────────────────────────────────────────────────────────────────
# Mapeo de nombres: nuestro nombre canónico → nombre que devuelve API-Football
# ──────────────────────────────────────────────────────────────────────────────
# Ejecuta `python result_updater.py --debug YYYY-MM-DD` para ver los nombres
# exactos que devuelve AF y añadir aquí los que no coincidan.
# Clave   = normalize_team_name(nombre en Supabase)
# Valor   = nombre tal como aparece en la columna "AF (raw)" del debug
# ──────────────────────────────────────────────────────────────────────────────
AF_NAME_MAP: dict[str, str] = {
    # ── Serie A ───────────────────────────────────────────────────────────────
    "SS Lazio":                 "Lazio",
    "SSC Napoli":               "Napoli",
    "Inter Milan":              "Inter",
    "Hellas Verona":            "Hellas Verona",
    # ── Premier League ────────────────────────────────────────────────────────
    "Tottenham Hotspur":        "Tottenham",
    "Manchester United":        "Manchester Utd",
    "West Ham United":          "West Ham",
    "Newcastle United":         "Newcastle",
    "Wolverhampton":            "Wolves",
    "Leicester City":           "Leicester",
    "Ipswich Town":             "Ipswich",
    "Brighton":                 "Brighton",
    # ── La Liga ───────────────────────────────────────────────────────────────
    "Atletico Madrid":          "Atletico Madrid",
    "Celta Vigo":               "Celta Vigo",
    "Leganes":                  "Leganes",
    "Alaves":                   "Alaves",
    "Rayo Vallecano":           "Rayo Vallecano",
    # ── Bundesliga ────────────────────────────────────────────────────────────
    "Borussia Dortmund":        "Dortmund",
    "Eintracht Frankfurt":      "Frankfurt",
    "Borussia Monchengladbach": "M'gladbach",
    "Bayer Leverkusen":         "Leverkusen",
    "Hoffenheim":               "Hoffenheim",
    "Werder Bremen":            "Werder Bremen",
    "Union Berlin":             "Union Berlin",
    "Heidenheim":               "Heidenheim",
    "St. Pauli":                "St. Pauli",
    "Holstein Kiel":            "Kiel",
    # ── Ligue 1 ───────────────────────────────────────────────────────────────
    "Paris Saint-Germain":      "Paris Saint Germain",
    "Marseille":                "Marseille",
    "Lyon":                     "Lyon",
    "Rennes":                   "Rennes",
    "Havre":                    "Le Havre",
    "Saint-Etienne":            "Saint-Etienne",
    # ── Champions / Europa League ─────────────────────────────────────────────
    "Ajax":                     "Ajax",
    "Feyenoord":                "Feyenoord",
    "PSV":                      "PSV Eindhoven",
    "Club Brugge":              "Club Brugge",
    "Galatasaray":              "Galatasaray",
    "Fenerbahce":               "Fenerbahce",
    "Besiktas":                 "Besiktas",
    "Ferencvaros":              "Ferencvaros",
    "Panathinaikos":            "Panathinaikos",
}

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
    cols = "id,home_team,away_team,match_date,mercado"
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
# API-Football helpers (con caché en memoria por fecha)
# ──────────────────────────────────────────────────────────────────────────────
# Estructura de respuesta relevante:
#   response[i].fixture.status.short  → "FT" | "AET" | "PEN" | "AWD" | "NS" …
#   response[i].teams.home.name       → nombre del equipo local
#   response[i].teams.away.name       → nombre del equipo visitante
#   response[i].goals.home            → goles local (int o null si no empezó)
#   response[i].goals.away            → goles visitante
#   response[i].league.name           → nombre de la liga
# ──────────────────────────────────────────────────────────────────────────────

AF_FINISHED_STATUSES = {"FT", "AET", "PEN", "AWD", "WO"}

_af_cache: dict[str, list] = {}  # "YYYY-MM-DD" → [fixture_objects]


def _af_headers() -> dict:
    return {"x-apisports-key": AF_KEY}


def _get_fixtures_on_date(date_str: str) -> list:
    """
    Carga todos los fixtures de API-Football para una fecha (caché en memoria).
    Un solo request trae todos los partidos del día sin filtro de liga.
    """
    if date_str in _af_cache:
        return _af_cache[date_str]

    url = f"{AF_BASE}/fixtures"
    params = {"date": date_str}
    try:
        resp = requests.get(url, headers=_af_headers(), params=params, timeout=15)
        if resp.status_code == 200:
            body = resp.json()
            # API-Football devuelve errores de autenticación dentro del cuerpo con status 200
            errors = body.get("errors", {})
            if errors:
                print(f"  [AF] Error de API: {errors}")
                fixtures = []
            else:
                fixtures = body.get("response", [])
                print(f"  [AF] {len(fixtures)} fixture(s) encontrado(s) para {date_str}")
        elif resp.status_code == 429:
            print(f"  [AF] Rate limit alcanzado para {date_str}. Reintenta más tarde.")
            fixtures = []
        else:
            print(f"  [AF] HTTP {resp.status_code} para {date_str}: {resp.text[:120]}")
            fixtures = []
    except Exception as e:
        print(f"  [AF] Error de red para {date_str}: {e}")
        fixtures = []

    _af_cache[date_str] = fixtures
    return fixtures


def _af_team_names(fixture: dict) -> tuple[str, str]:
    """Extrae y normaliza los nombres de equipos de un fixture de AF."""
    home_raw = fixture.get("teams", {}).get("home", {}).get("name", "")
    away_raw = fixture.get("teams", {}).get("away", {}).get("name", "")
    return normalize_team_name(home_raw), normalize_team_name(away_raw)


def _apply_af_map(name: str) -> str:
    """Traduce nuestro nombre canónico al equivalente en API-Football."""
    return AF_NAME_MAP.get(name, name)


def find_af_fixture(home: str, away: str, date_str: str) -> dict | None:
    """
    Busca un fixture por nombre normalizado en la respuesta de AF.
    Pasos:
      1. Match exacto tras aplicar AF_NAME_MAP a nuestros nombres.
      2. Coincidencia por subcadena bidireccional (fallback).
    """
    fixtures = _get_fixtures_on_date(date_str)

    home_mapped = _apply_af_map(home)
    away_mapped = _apply_af_map(away)

    # Paso 1 — coincidencia exacta
    for f in fixtures:
        af_home, af_away = _af_team_names(f)
        if af_home == home_mapped and af_away == away_mapped:
            return f

    # Paso 2 — subcadena bidireccional (maneja abreviaciones y sufijos)
    home_u = home_mapped.upper()
    away_u = away_mapped.upper()
    for f in fixtures:
        af_home, af_away = _af_team_names(f)
        af_home_u = af_home.upper()
        af_away_u = af_away.upper()
        home_ok = home_u in af_home_u or af_home_u in home_u
        away_ok = away_u in af_away_u or af_away_u in away_u
        if home_ok and away_ok:
            return f

    return None


def debug_af_names(date_str: str) -> None:
    """
    Modo debug: imprime todos los nombres de equipos que devuelve API-Football
    para una fecha dada, junto con su versión normalizada. Úsalo para identificar
    discrepancias y actualizar AF_NAME_MAP.

    Uso: python result_updater.py --debug 2026-03-15
    """
    print("=" * 70)
    print(f"  DEBUG — Fixtures de API-Football para {date_str}")
    print("=" * 70)

    fixtures = _get_fixtures_on_date(date_str)
    if not fixtures:
        print("  [WARN] Sin fixtures para esta fecha (o error de API).")
        return

    print(f"  {len(fixtures)} fixture(s) encontrado(s):\n")
    print(f"  {'Liga':<30} {'AF (raw)':<32} {'Normalizado':<28} Estado")
    print("  " + "-" * 100)

    for f in sorted(fixtures, key=lambda x: x.get("league", {}).get("name", "")):
        league  = f.get("league", {}).get("name", "?")
        status  = f.get("fixture", {}).get("status", {}).get("short", "?")
        for side in ("home", "away"):
            raw  = f.get("teams", {}).get(side, {}).get("name", "?")
            norm = normalize_team_name(raw)
            in_map = AF_NAME_MAP.get(norm)
            map_str = f"  ← map OK" if in_map else ""
            print(f"  {league:<30} {raw:<32} {norm:<28} {status}{map_str}")

    print()
    print("  Para corregir un mismatch, añade a AF_NAME_MAP:")
    print('  "Tu nombre canónico (Supabase)": "Nombre AF (raw) de arriba",')
    print("=" * 70)


# ──────────────────────────────────────────────────────────────────────────────
# Lógica de pick y evaluación
# ──────────────────────────────────────────────────────────────────────────────


def _parse_over_code(code: str) -> float | None:
    """
    Extrae la línea numérica de códigos over/under.
    Acepta: 'over_2.5', 'over_1.5', 'under_3.0', 'over25' (legacy), etc.
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

    # ── Double Chance ─────────────────────────────────────────────────────────
    if code == "dc_1x":
        return "win" if home_goals >= away_goals else "loss"   # local gana o empata
    if code == "dc_x2":
        return "win" if away_goals >= home_goals else "loss"   # visitante gana o empata
    if code == "dc_12":
        return "win" if home_goals != away_goals else "loss"   # cualquier equipo gana (no empate)

    return None  # mercado no soportado


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    # ── Modo debug ────────────────────────────────────────────────────────────
    if len(sys.argv) >= 3 and sys.argv[1] == "--debug":
        if not AF_KEY:
            print("[FAIL] API_FOOTBALL_KEY no encontrado en .env")
            return
        debug_af_names(sys.argv[2])
        return

    print("=" * 52)
    print("  PODIUM 360 - RESULT UPDATER (ROI AUTO-CALIFICADOR)")
    print("=" * 52)

    if not all([SUPABASE_URL, SUPABASE_KEY, AF_KEY]):
        print("[FAIL] Faltan credenciales en .env (SUPABASE_URL, SUPABASE_KEY, API_FOOTBALL_KEY)")
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
        date_s  = row.get("match_date", "") or ""

        # El ID siempre empieza con la fecha real del partido en formato YYYY-MM-DD
        # (ej: "2026-03-12_Stuttgart_Porto_1x2_visitante").  Si match_date tiene un año
        # distinto (error de inserción), usamos la fecha del ID como fuente de verdad.
        id_date = row_id[:10] if len(row_id) >= 10 and row_id[4] == '-' else ""
        if id_date and (len(date_s) < 4 or date_s[:4] != id_date[:4]):
            print(f"  [WARN] match_date='{date_s}' tiene año incorrecto — "
                  f"usando fecha del ID: '{id_date}'")
            date_s = id_date

        home_mapped = _apply_af_map(home)
        away_mapped = _apply_af_map(away)
        map_note = ""
        if home_mapped != home or away_mapped != away:
            map_note = f" (mapeado: {home_mapped} vs {away_mapped})"
        print(f"→ {home} vs {away} ({date_s}){map_note}")

        # 1. Buscar en API-Football
        fixture = find_af_fixture(home, away, date_s)
        if not fixture:
            # Mostrar nombres disponibles ese día para facilitar el debug
            available = _get_fixtures_on_date(date_s)
            if available:
                print(f"  [SKIP] No encontrado en API-Football.")
                print(f"  [DEBUG] Fixtures disponibles en AF ese día:")
                for f in available:
                    af_h = normalize_team_name(f.get("teams",{}).get("home",{}).get("name","?"))
                    af_a = normalize_team_name(f.get("teams",{}).get("away",{}).get("name","?"))
                    st   = f.get("fixture",{}).get("status",{}).get("short","?")
                    print(f"          • {af_h} vs {af_a}  [{st}]")
            else:
                print(f"  [SKIP] No encontrado en API-Football.")
            skipped += 1
            continue

        # 2. Verificar que esté finalizado
        af_status = fixture.get("fixture", {}).get("status", {}).get("short", "")
        if af_status not in AF_FINISHED_STATUSES:
            print(f"  [SKIP] Estado AF: '{af_status}'. Partido aún no terminado.")
            skipped += 1
            continue

        # 3. Extraer score (goals.home/away es el marcador final de 90 min;
        #    para AET/PEN usamos score.fulltime que refleja los 90 min regulares)
        goals = fixture.get("goals", {})
        hg = goals.get("home")
        ag = goals.get("away")
        if hg is None or ag is None:
            print(f"  [SKIP] Score null en API-Football.")
            skipped += 1
            continue

        actual_result = f"{hg}-{ag}"

        # 4. Leer mercado directamente del registro (arquitectura pick-level)
        mercado_code = row.get("mercado")

        # 5. Evaluar resultado
        win_loss = evaluate_pick(mercado_code, hg, ag)
        if win_loss is None:
            print(f"  [SKIP] Mercado no soportado: '{mercado_code}'")
            unsupported += 1
            continue

        # 6. Actualizar Supabase
        if update_match_result(row_id, actual_result, win_loss):
            print(f"  [OK] {actual_result} → {win_loss.upper()} | pick: {mercado_code}")
            updated += 1
        else:
            skipped += 1

    print()
    print("─" * 52)
    print(f"  Actualizados : {updated}")
    print(f"  Saltados     : {skipped}")
    print(f"  Sin soporte  : {unsupported}")
    print("─" * 52)

    check_and_clear_manual_matches()


# ──────────────────────────────────────────────────────────────────────────────
# Verificación y limpieza automática de partidos_manuales.json
# ──────────────────────────────────────────────────────────────────────────────

def check_and_clear_manual_matches():
    """
    Tras actualizar resultados, verifica si todos los partidos en
    partidos_manuales.json ya tienen sus picks resueltos en Supabase
    (status_win_loss != 'pending'). Si es así, vacía el archivo.

    Un partido se considera "pendiente" solo si existe al menos un pick
    en historical_results con status_win_loss='pending' para esos equipos.
    Si un partido no generó señales VIP (no está en historical_results),
    se considera resuelto.
    """
    # Leer partidos_manuales.json
    try:
        with open(MANUAL_MATCHES_PATH, "r", encoding="utf-8") as f:
            manual = json.load(f)
    except FileNotFoundError:
        return
    except json.JSONDecodeError:
        print("  [WARN] partidos_manuales.json tiene formato inválido. No se modificará.")
        return

    if not manual:
        return  # ya está vacío

    print()
    print("─" * 52)
    print("  VERIFICACIÓN DE PARTIDOS MANUALES")
    print("─" * 52)

    # Obtener todos los picks aún pendientes en Supabase
    pending_rows = get_pending_matches()

    # Construir set de pares (local_norm, visitante_norm) con picks pending
    pending_pairs = set()
    for row in pending_rows:
        h = normalize_team_name(row.get("home_team", ""))
        a = normalize_team_name(row.get("away_team", ""))
        pending_pairs.add((h, a))

    # Clasificar cada partido manual
    still_pending = []
    for match in manual:
        local_norm = normalize_team_name(match.get("local", ""))
        visit_norm = normalize_team_name(match.get("visitante", ""))
        if (local_norm, visit_norm) in pending_pairs:
            still_pending.append(match)

    if not still_pending:
        with open(MANUAL_MATCHES_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)
        print("  [OK] Todos los partidos procesados.")
        print("  [OK] partidos_manuales.json vaciado automáticamente.")
    else:
        print(f"  [INFO] {len(still_pending)} partido(s) con picks aún pendientes:")
        for m in still_pending:
            print(f"    • {m['local']} vs {m['visitante']} ({m.get('liga', '?')})")
        print("  [INFO] partidos_manuales.json no modificado.")

    print("─" * 52)


if __name__ == "__main__":
    main()
