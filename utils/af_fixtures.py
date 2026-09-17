"""
utils/af_fixtures.py — Mapeo y matching de nombres de equipo → API-Football
============================================================================
Fuente de verdad para traducir nuestros nombres canónicos (utils.naming) al
formato exacto que devuelve API-Football, y para encontrar un fixture dado
un par de equipos dentro de una lista ya obtenida de la API.

Usado por:
  - result_updater.py        (calificación de resultados finales)
  - data_fetcher.py           (comparación de fuerza — reemplazo de ClubElo)

Cada llamador mantiene su propia estrategia de fetch/caché HTTP (result_updater.py
usa caché en memoria por corrida; data_fetcher.py usa el caché persistente en
database/api_cache.json). Este módulo solo resuelve el matching, sin I/O.

Ejecuta `python result_updater.py --debug YYYY-MM-DD` para ver los nombres
exactos que devuelve AF y añadir aquí los que no coincidan.
  Clave   = normalize_team_name(nombre en Supabase)
  Valor   = nombre tal como aparece en la columna "AF (raw)" del debug
"""

from utils.naming import normalize_team_name

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


def af_team_names(fixture: dict) -> tuple[str, str]:
    """Extrae y normaliza los nombres de equipos de un fixture de API-Football."""
    home_raw = fixture.get("teams", {}).get("home", {}).get("name", "")
    away_raw = fixture.get("teams", {}).get("away", {}).get("name", "")
    return normalize_team_name(home_raw), normalize_team_name(away_raw)


def apply_af_map(name: str) -> str:
    """Traduce nuestro nombre canónico al equivalente en API-Football."""
    return AF_NAME_MAP.get(name, name)


def match_af_fixture(fixtures: list, home: str, away: str) -> dict | None:
    """
    Busca, dentro de una lista de fixtures ya obtenida de API-Football,
    el que corresponde a (home, away).
      Paso 1: coincidencia exacta tras aplicar AF_NAME_MAP.
      Paso 2: subcadena bidireccional (maneja abreviaciones y sufijos).
    """
    home_mapped = apply_af_map(home)
    away_mapped = apply_af_map(away)

    for f in fixtures:
        af_home, af_away = af_team_names(f)
        if af_home == home_mapped and af_away == away_mapped:
            return f

    home_u, away_u = home_mapped.upper(), away_mapped.upper()
    for f in fixtures:
        af_home, af_away = af_team_names(f)
        af_home_u, af_away_u = af_home.upper(), af_away.upper()
        home_ok = home_u in af_home_u or af_home_u in home_u
        away_ok = away_u in af_away_u or af_away_u in away_u
        if home_ok and away_ok:
            return f

    return None
