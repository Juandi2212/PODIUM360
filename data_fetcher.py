#!/usr/bin/env python3
"""
data_fetcher.py — Podium VIP Cards · Data Ingestion Script v1.2
================================================================
Sources (in strict order):
  1. ClubElo.com        — Elo ratings                  (free, no key)
  2. Fotmob             — xG attack/defense season avg  (free, JSON API)
  3. Football-Data.org  — fixtures/standings/form/H2H   (key required)
  4. Football-Data.org  — league avg goals               (same key)
  5. The Odds API       — odds 1X2/O-U/BTTS/corners     (key required)

Usage:
    python data_fetcher.py "Arsenal" "Liverpool" "Premier League"

Output:
    partido_data.json  in the project root
"""

import sys
import os
import json
import time
import re
import csv
import io

import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Force UTF-8 output on Windows consoles (CP1252 safe)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY")  # football-data.org
ODDS_API_KEY      = os.getenv("ODDS_API_KEY")        # the-odds-api.com
# ClubElo and Understat: free, no key

# ── Base URLs ─────────────────────────────────────────────────────────────────
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"
ODDS_API_BASE      = "https://api.the-odds-api.com/v4"
CLUBELO_BASE       = "http://api.clubelo.com"
FOTMOB_BASE        = "https://www.fotmob.com"
FOTMOB_CDN         = "https://data.fotmob.com/stats"
OUTPUT_FILE        = "partido_data.json"
CACHE_FILE         = "database/api_cache.json"

# ── Sistema de Caché Local ────────────────────────────────────────────────────
class CacheManager:
    def __init__(self, cache_file=CACHE_FILE):
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_cache(self):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def get(self, key):
        if key in self.cache:
            entry = self.cache[key]
            if time.time() < entry["expires_at"]:
                return entry["data"]
            else:
                del self.cache[key] # Limpiar expirados
                self._save_cache()
        return None

    def set(self, key, data, ttl_seconds):
        self.cache[key] = {
            "expires_at": time.time() + ttl_seconds,
            "data": data
        }
        self._save_cache()

cache_db = CacheManager()

# Fotmob Mobile User-Agent (their API is not behind Cloudflare)
FOTMOB_UA = (
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/90.0.4430.91 Mobile Safari/537.36"
)

# Fotmob league IDs  (used for dynamic team-ID resolution via standings)
FOTMOB_LEAGUE_IDS = {
    "Premier League":   47,
    "La Liga":          87,
    "Bundesliga":       54,
    "Serie A":          55,
    "Ligue 1":          53,
    "Champions League": 42,
    "Europa League":    73,
    "Eredivisie":       57,
    "Primeira Liga":    61,
}

# Fotmob team IDs  (fallback when league standings lookup fails or liga not mapped)
# IDs verified from /api/leagues standings — 2025-26 season
FOTMOB_TEAM_IDS = {
    # Premier League
    "Arsenal":                  9825,
    "Liverpool":                8650,
    "Manchester City":          8456,
    "Manchester United":        10260,
    "Chelsea":                  8455,
    "Tottenham":                8586,
    "Tottenham Hotspur":        8586,
    "Newcastle":                10261,
    "Newcastle United":         10261,
    "Aston Villa":              10252,
    "Brighton":                 10204,
    "Brighton & Hove Albion":   10204,
    "Fulham":                   9879,
    "Brentford":                9937,
    "West Ham":                 8654,
    "West Ham United":          8654,
    "Everton":                  8668,
    "Crystal Palace":           9826,
    "Wolves":                   8602,
    "Wolverhampton Wanderers":  8602,
    "Wolverhampton":            8602,
    "Nottingham Forest":        10203,
    "Sunderland":               8472,
    "Bournemouth":              8678,
    "AFC Bournemouth":          8678,
    "Leeds":                    8463,
    "Leeds United":             8463,
    "Burnley":                  8191,
    # La Liga
    "Real Madrid":              8633,
    "Barcelona":                8634,
    "FC Barcelona":             8634,
    "Atletico Madrid":          9906,
    "Atletico de Madrid":       9906,
    "Villarreal":               10205,
    "Real Betis":               8603,
    "Real Sociedad":            8560,
    "Athletic Club":            8315,
    "Athletic Bilbao":          8315,
    "Sevilla":                  8302,
    "Valencia":                 10267,
    "Celta Vigo":               9910,
    "Osasuna":                  8371,
    "Girona":                   7732,
    "Getafe":                   8305,
    "Rayo Vallecano":           8370,
    "Espanyol":                 8558,
    "Mallorca":                 8661,
    # Bundesliga
    "Bayern Munich":            9823,
    "Bayern":                   9823,
    "Bayern Munchen":           9823,
    "Borussia Dortmund":        9789,
    "Dortmund":                 9789,
    "RB Leipzig":               178475,
    "Bayer Leverkusen":         8178,
    "Leverkusen":               8178,
    "Eintracht Frankfurt":      9810,
    "Frankfurt":                9810,
    "VfB Stuttgart":            10269,
    "Stuttgart":                10269,
    "Freiburg":                 8358,
    "Augsburg":                 8406,
    "Wolfsburg":                8721,
    "Werder Bremen":            8697,
    "Union Berlin":             8149,
    "Borussia Monchengladbach": 9788,
    "Gladbach":                 9788,
    "Hoffenheim":               8226,
    "St. Pauli":                8152,
    # Serie A
    "Juventus":                 9885,
    "AC Milan":                 8564,
    "Milan":                    8564,
    "Inter Milan":              8636,
    "Internazionale":           8636,
    "Inter":                    8636,
    "AS Roma":                  8686,
    "Roma":                     8686,
    "Lazio":                    8543,
    "SS Lazio":                 8543,
    "Napoli":                   9875,
    "Atalanta":                 8524,
    "Bologna":                  9857,
    "Fiorentina":               8535,
    "Torino":                   9804,
    "Genoa":                    10233,
    "Udinese":                  8600,
    "Cagliari":                 8529,
    "Lecce":                    9888,
    "Como":                     10171,
    # Ligue 1
    "Paris Saint-Germain":      9847,
    "PSG":                      9847,
    "Marseille":                8592,
    "Olympique de Marseille":   8592,
    "Lyon":                     9748,
    "Olympique Lyonnais":       9748,
    "Monaco":                   9829,
    "Lille":                    8639,
    "Nice":                     9831,
    "Rennes":                   9851,
    "Lens":                     8588,
    "Brest":                    8521,
    # Eredivisie / Primeira Liga
    "PSV":                      8640,
    "PSV Eindhoven":            8640,
    "Feyenoord":                10235,
    "Ajax":                     8631,
    "Porto":                    9773,
    "FC Porto":                 9773,
    "Sporting CP":              9768,
    "Benfica":                  9772,
    "SL Benfica":               9772,
    # Europa League — extra clubs not in domestic league lists above
    "Panathinaikos":            8261,
    "Ferencvaros":              9920,
    "Braga":                    9816,
    "SC Braga":                 9816,
    "Genk":                     8005,
    "KRC Genk":                 8005,
    "Midtjylland":              8398,
    "FC Midtjylland":           8398,
    "Real Betis":               8603,
}

# ── Football-Data.org competition codes ───────────────────────────────────────
FDORG_CODES = {
    "Premier League":   "PL",
    "La Liga":          "PD",
    "Bundesliga":       "BL1",
    "Serie A":          "SA",
    "Ligue 1":          "FL1",
    "Champions League": "CL",
    "Europa League":    "EL",
    "Eredivisie":       "DED",
    "Primeira Liga":    "PPL",
    "Championship":     "ELC",
    "Copa del Rey":     "CDR",
    "FA Cup":           "FAC",
    "Liga MX":          "MX1",
}

# ── The Odds API sport keys ───────────────────────────────────────────────────
ODDS_SPORT_KEYS = {
    "Premier League":    "soccer_epl",
    "La Liga":           "soccer_spain_la_liga",
    "Bundesliga":        "soccer_germany_bundesliga",
    "Serie A":           "soccer_italy_serie_a",
    "Ligue 1":           "soccer_france_ligue_one",
    "Champions League":  "soccer_uefa_champs_league",
    "Europa League":     "soccer_uefa_europa_league",
    "Eredivisie":        "soccer_netherlands_eredivisie",
    "Primeira Liga":     "soccer_portugal_primeira_liga",
    "Championship":      "soccer_england_league1",
    "Liga MX":           "soccer_mexico_ligamx",
    "Copa Libertadores": "soccer_conmebol_copa_libertadores",
    "Copa Sudamericana": "soccer_conmebol_copa_sudamericana",
}

# ── ClubElo name aliases (run-together CamelCase) ─────────────────────────────
CLUBELO_ALIASES = {
    "manchester city":         "ManCity",
    "manchester united":       "ManUnited",
    "tottenham hotspur":       "Tottenham",
    "tottenham":               "Tottenham",
    "newcastle united":        "Newcastle",
    "newcastle":               "Newcastle",
    "west ham united":         "WestHam",
    "west ham":                "WestHam",
    "aston villa":             "AstonVilla",
    "nottingham forest":       "Nottingham",
    "paris saint-germain":     "Paris",
    "psg":                     "Paris",
    "atletico madrid":         "Atletico",
    "atlético de madrid":      "Atletico",
    "betis":                   "RealBetis",
    "real betis":              "RealBetis",
    "real sociedad":           "RealSociedad",
    "athletic club":           "Athletic",
    "athletic bilbao":         "Athletic",
    "inter milan":             "Inter",
    "internazionale":          "Inter",
    "ac milan":                "Milan",
    "as roma":                 "Roma",
    "ss lazio":                "Lazio",
    "rb leipzig":              "RasenBallsport",
    "bayer leverkusen":        "Leverkusen",
    "borussia dortmund":       "Dortmund",
    "borussia monchengladbach":"Mgladbach",
    "eintracht frankfurt":     "Frankfurt",
    "vfb stuttgart":           "Stuttgart",
    "psv eindhoven":           "PSV",
    "psv":                     "PSV",
    "olympique lyonnais":      "Lyon",
    "ol lyon":                 "Lyon",
    "olympique de marseille":  "Marseille",
    "sporting cp":             "Sporting",
    "wolverhampton wanderers": "Wolverhampton",
    "wolves":                  "Wolverhampton",
    "leicester city":          "Leicester",
    "crystal palace":          "CrystalPalace",
    "brighton":                "Brighton",
    "brighton & hove albion":  "Brighton",
    "brentford":               "Brentford",
    "fulham":                  "Fulham",
    "ipswich town":            "Ipswich",
    "southampton":             "Southampton",
    "espanyol":                "Espanyol",
    "real oviedo":             "RealOviedo",
}

# ── Understat name aliases ────────────────────────────────────────────────────
UNDERSTAT_ALIASES = {
    "manchester city":         "Manchester_City",
    "manchester united":       "Manchester_United",
    "tottenham hotspur":       "Tottenham",
    "tottenham":               "Tottenham",
    "newcastle united":        "Newcastle_United",
    "newcastle":               "Newcastle_United",
    "west ham united":         "West_Ham",
    "west ham":                "West_Ham",
    "aston villa":             "Aston_Villa",
    "nottingham forest":       "Nottingham_Forest",
    "wolverhampton wanderers": "Wolverhampton_Wanderers",
    "wolves":                  "Wolverhampton_Wanderers",
    "paris saint-germain":     "Paris_Saint_Germain",
    "psg":                     "Paris_Saint_Germain",
    "atletico madrid":         "Atletico_Madrid",
    "atlético de madrid":      "Atletico_Madrid",
    "inter milan":             "Internazionale",
    "internazionale":          "Internazionale",
    "ac milan":                "AC_Milan",
    "as roma":                 "Roma",
    "rb leipzig":              "RB_Leipzig",
    "bayer leverkusen":        "Bayer_Leverkusen",
    "borussia dortmund":       "Borussia_Dortmund",
    "borussia monchengladbach":"Borussia_Monchengladbach",
    "eintracht frankfurt":     "Eintracht_Frankfurt",
    "vfb stuttgart":           "Stuttgart",
    "real madrid":             "Real_Madrid",
    "fc barcelona":            "Barcelona",
    "real betis":              "Real_Betis",
    "real sociedad":           "Real_Sociedad",
    "athletic club":           "Athletic_Club",
    "athletic bilbao":         "Athletic_Club",
    "ss lazio":                "Lazio",
    "olympique lyonnais":      "Lyon",
    "ol lyon":                 "Lyon",
    "olympique de marseille":  "Marseille",
    "sporting cp":             "Sporting_CP",
    "brighton":                "Brighton",
    "brighton & hove albion":  "Brighton",
    "leicester city":          "Leicester",
    "crystal palace":          "Crystal_Palace",
}

# ── Global counters ───────────────────────────────────────────────────────────
_call_count = 0
_errors     = []


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════
def _get(url: str, headers: dict = None, params: dict = None, timeout: int = 15, cache_ttl_seconds: int = 0):
    """Silent GET with Optional Caching. Returns (response_json_dict_or_text, None) or (None, error_str)."""
    global _call_count

    if cache_ttl_seconds > 0:
        cache_key = f"get_{url}_{json.dumps(params, sort_keys=True) if params else ''}"
        cached = cache_db.get(cache_key)
        if cached is not None:
            return cached, None

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        _call_count += 1
        resp.raise_for_status()
        
        # Determine if JSON
        try:
            data = resp.json()
        except (ValueError, json.JSONDecodeError):
            data = resp.text

        if cache_ttl_seconds > 0:
            cache_db.set(cache_key, data, cache_ttl_seconds)

        return data, None
    except requests.exceptions.Timeout:
        err = f"TIMEOUT: {url}"
        _errors.append(err)
        return None, err
    except requests.exceptions.HTTPError as e:
        err = f"HTTP {e.response.status_code}: {url}"
        _errors.append(err)
        return None, err
    except Exception as e:
        err = f"ERROR [{type(e).__name__}]: {url} — {e}"
        _errors.append(err)
        return None, err


from utils.naming import fuzzy_match, log_naming_error

def _fuzzy(a: str, b: str) -> bool:
    return fuzzy_match(a, b)


def _current_season() -> int:
    """Football season start year: Aug–Jul cycle."""
    now = datetime.now()
    return now.year if now.month >= 7 else now.year - 1


def _to_clubelo(name: str) -> str:
    key = name.lower().strip()
    if key in CLUBELO_ALIASES:
        return CLUBELO_ALIASES[key]
    return "".join(w.capitalize() for w in name.split())


def _to_understat(name: str) -> str:
    key = name.lower().strip()
    if key in UNDERSTAT_ALIASES:
        return UNDERSTAT_ALIASES[key]
    return name.strip().replace(" ", "_")


# ══════════════════════════════════════════════════════════════════════════════
# 1. ClubElo  (free, no auth)
# ══════════════════════════════════════════════════════════════════════════════
def fetch_elo(team: str) -> float | None:
    """GET http://api.clubelo.com/{slug} → most recent Elo rating (cache 24h)."""
    slug = _to_clubelo(team)
    data, _ = _get(f"{CLUBELO_BASE}/{slug}", cache_ttl_seconds=86400)
    if not data:
        return None
    try:
        reader = csv.DictReader(io.StringIO(data))
        rows   = [r for r in reader if r.get("Elo")]
        if rows:
            return round(float(rows[-1]["Elo"]), 1)
    except Exception as e:
        _errors.append(f"ClubElo parse error ({team}): {e}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 2. Fotmob — xG data  (free, JSON API — no Cloudflare protection)
#
# FBref (original target) is fully behind Cloudflare BIC; requests returns 403
# on every URL including the homepage. Fotmob's mobile API is accessible and
# provides season-aggregate xG via their public CDN stats endpoint.
#
# Data returned: season-average xG per match repeated 8 times for schema
# compatibility. This represents the team's sustained xG level this season,
# not individual match figures. Enough for Claude's card generation analysis.
# ══════════════════════════════════════════════════════════════════════════════

_FOTMOB_HEADERS = {
    "User-Agent": FOTMOB_UA,
    "Accept":     "application/json",
}

# Module-level cache: (league_id, season_id) → {team_id: {xg, xga, matches}}
# Shared between both team calls so CDN endpoints are hit only once per run.
_FOTMOB_CDN_CACHE: dict = {}


def _fotmob_get(url: str):
    """GET against Fotmob API/CDN with mobile headers (cache 24h)."""
    return _get(url, headers=_FOTMOB_HEADERS, cache_ttl_seconds=86400)


def _fotmob_cdn_stats(league_id: int, season_id: int) -> dict:
    """
    Fetch xG + xGA season totals for all teams from Fotmob CDN.
    """
    cache_key = (league_id, season_id)
    if cache_key in _FOTMOB_CDN_CACHE:
        return _FOTMOB_CDN_CACHE[cache_key]

    base = f"{FOTMOB_CDN}/{league_id}/season/{season_id}"
    result: dict = {}

    for stat_key, field in (
        ("expected_goals_team",          "xg"),
        ("expected_goals_conceded_team", "xga"),
    ):
        data, _ = _fotmob_get(f"{base}/{stat_key}.json")
        if not data:
            continue
        try:
            top_lists = data.get("TopLists")
            if not top_lists:
                continue
            stat_list = top_lists[0].get("StatList")
            if not stat_list:
                continue
            for entry in stat_list:
                tid      = entry.get("TeamId")
                total    = entry.get("StatValue", 0.0)
                matches  = entry.get("MatchesPlayed", 1) or 1
                avg      = round(total / matches, 2)
                if tid not in result:
                    result[tid] = {"xg": None, "xga": None, "mp": matches}
                result[tid][field] = avg
                result[tid]["mp"]  = matches
        except Exception as e:
            _errors.append(f"Fotmob CDN parse error ({stat_key}): {e}")

    _FOTMOB_CDN_CACHE[cache_key] = result
    return result


def _fotmob_resolve_team_ids(local: str, visitante: str, liga: str) -> tuple[int, int] | None:
    """
    Resolve Fotmob team IDs via league standings API — no hardcoded IDs needed.
    GET /api/leagues?id={fotmob_league_id}&season={year} → extract team IDs
    from the current standings table.

    Returns (local_id, visitante_id) or None if the liga isn't mapped or
    either team isn't found in the standings.
    """
    fotmob_lid = FOTMOB_LEAGUE_IDS.get(liga)
    if not fotmob_lid:
        _errors.append(f"Fotmob: no league_id mapped for '{liga}' — using dict fallback")
        return None

    season = _current_season()
    data, _ = _fotmob_get(f"{FOTMOB_BASE}/api/leagues?id={fotmob_lid}&season={season}")
    if not data:
        return None

    try:
        tables = data.get("table", [])
        if not tables:
            return None
        table_obj = tables[0].get("data", {}).get("table", {})
        if not table_obj:
            return None
        rows = table_obj.get("all", [])
    except Exception as e:
        _errors.append(f"Fotmob: standings parse error for '{liga}': {e}")
        return None

    local_id = visitante_id = None
    for row in rows:
        name = row.get("name", "")
        if _fuzzy(name, local):
            local_id = row.get("id")
        elif _fuzzy(name, visitante):
            visitante_id = row.get("id")

    if local_id and visitante_id:
        print(f"      Fotmob: IDs via standings — {local}={local_id}  {visitante}={visitante_id}")
        return local_id, visitante_id

    if not local_id:
        _errors.append(f"Fotmob: '{local}' not found in {liga} standings")
    if not visitante_id:
        _errors.append(f"Fotmob: '{visitante}' not found in {liga} standings")
    return None


def _fotmob_xg_for_team(team_id: int, team_name: str) -> dict | None:
    """
    Given a resolved Fotmob team_id:
      1. GET /api/teams?id={team_id} → primaryLeagueId + primarySeasonId
      2. _fotmob_cdn_stats() → season-average xG/xGA per match  (cached)

    Returns {"atk": [avg_xg]*8, "def": [avg_xga]*8} or None.
    CDN responses are module-level cached so both teams in the same league
    share a single HTTP call per stat file.
    """
    data, _ = _fotmob_get(f"{FOTMOB_BASE}/api/teams?id={team_id}")
    if not data:
        return None

    try:
        league_id = data["stats"]["primaryLeagueId"]
        season_id = data["stats"]["primarySeasonId"]
    except Exception as e:
        _errors.append(f"Fotmob: could not parse league/season for '{team_name}' (id={team_id}): {e}")
        return None

    print(f"      Fotmob [{team_name}] — league={league_id}  season={season_id}")

    stats = _fotmob_cdn_stats(league_id, season_id)
    entry = stats.get(team_id)

    if not entry:
        _errors.append(f"Fotmob: no CDN xG entry for '{team_name}' (id={team_id})")
        return None

    xg_avg  = entry.get("xg")
    xga_avg = entry.get("xga")
    mp      = entry.get("mp", 0)

    if xg_avg is None and xga_avg is None:
        _errors.append(f"Fotmob: xG data missing for '{team_name}'")
        return None

    print(f"      Fotmob [{team_name}] — xG/match={xg_avg}  xGA/match={xga_avg}  ({mp} matches)")

    return {
        "atk": [xg_avg]  * 8 if xg_avg  is not None else None,
        "def": [xga_avg] * 8 if xga_avg is not None else None,
    }


def fetch_xg_fotmob(local: str, visitante: str, liga: str) -> dict:
    """
    Fetches xG data for BOTH teams in three steps:
      1. GET /api/leagues?id={league_id}&season={year} → team IDs from standings
      2. GET /api/teams?id={team_id} per team → primaryLeagueId + primarySeasonId
      3. CDN expected_goals[_conceded]_team.json → season-avg xG/xGA

    Primary resolution: league standings (works for any team, any time).
    Fallback: FOTMOB_TEAM_IDS dict (for cups / unmapped leagues).

    Returns {"local":     {"atk": [...], "def": [...]},
             "visitante": {"atk": [...], "def": [...]}}
    Either value is None if the team or data cannot be resolved.
    """
    result = {"local": None, "visitante": None}

    # ── Step 1: Resolve team IDs via league standings (primary method) ────
    ids = _fotmob_resolve_team_ids(local, visitante, liga)
    if ids:
        local_id, visitante_id = ids
    else:
        # Fallback: static dictionary lookup (cups, unmapped leagues, etc.)
        local_id = FOTMOB_TEAM_IDS.get(local) or next(
            (v for k, v in FOTMOB_TEAM_IDS.items() if _fuzzy(k, local)), None)
        visitante_id = FOTMOB_TEAM_IDS.get(visitante) or next(
            (v for k, v in FOTMOB_TEAM_IDS.items() if _fuzzy(k, visitante)), None)
        if local_id or visitante_id:
            print(f"      Fotmob: IDs via dict fallback — {local}={local_id}  {visitante}={visitante_id}")

    # ── Step 2 & 3: team API + CDN xG per team ────────────────────────────
    if local_id:
        result["local"]     = _fotmob_xg_for_team(local_id,     local)
    else:
        _errors.append(f"Fotmob: could not resolve team_id for '{local}'")

    if visitante_id:
        result["visitante"] = _fotmob_xg_for_team(visitante_id, visitante)
    else:
        _errors.append(f"Fotmob: could not resolve team_id for '{visitante}'")

    return result


# ══════════════════════════════════════════════════════════════════════════════
# 3 & 4. Football-Data.org  (fixtures / standings / form / H2H / avg goals)
# ══════════════════════════════════════════════════════════════════════════════
def _fdorg(endpoint: str, params: dict = None) -> dict | None:
    """Authenticated GET to Football-Data.org. Returns parsed JSON or None (cache 24h)."""
    if not FOOTBALL_DATA_KEY:
        _errors.append("FOOTBALL_DATA_KEY not configured")
        return None
    data, _ = _get(
        f"{FOOTBALL_DATA_BASE}{endpoint}",
        headers={"X-Auth-Token": FOOTBALL_DATA_KEY},
        params=params,
        cache_ttl_seconds=86400 # 24 hrs
    )
    if not data:
        return None
    return data


def fetch_standings_and_ids(local: str, visitante: str, liga: str):
    """
    GET /competitions/{code}/standings
    Returns (standings_dict, local_id, visitante_id, forma_local_str, forma_visitante_str)
    Extracts standings, team IDs, and form strings in a single call.
    """
    empty_standings = {
        "pos_local": None, "pts_local": None,
        "pos_visitante": None, "pts_visitante": None,
    }
    code = FDORG_CODES.get(liga)
    if not code:
        return empty_standings, None, None, None, None

    data = _fdorg(f"/competitions/{code}/standings")
    if not data:
        return empty_standings, None, None, None, None

    # Find the TOTAL standings table
    standings_list = data.get("standings", [])
    table = None
    for s in standings_list:
        if s.get("type") == "TOTAL":
            table = s["table"]
            break
    if table is None and standings_list:
        table = standings_list[0]["table"]
    if not table:
        return empty_standings, None, None, None, None

    out          = dict(empty_standings)
    local_id     = None
    visitante_id = None
    forma_l_str  = None
    forma_v_str  = None

    for entry in table:
        team = entry["team"]
        name = team["name"]
        if _fuzzy(name, local):
            out["pos_local"]  = entry["position"]
            out["pts_local"]  = entry["points"]
            local_id          = team["id"]
        elif _fuzzy(name, visitante):
            out["pos_visitante"]  = entry["position"]
            out["pts_visitante"]  = entry["points"]
            visitante_id          = team["id"]

    return out, local_id, visitante_id, None, None


def _parse_form_string(form_str: str) -> list | None:
    """Convert 'WWDLL' → ['W','W','D','L','L'] (last 5 chars)."""
    if not form_str:
        return None
    cleaned = [c for c in form_str.upper() if c in ("W", "D", "L")]
    return cleaned[-5:] if cleaned else None


def fetch_form_fdorg(team_id: int, liga: str) -> list | None:
    """
    GET /teams/{id}/matches?status=FINISHED&competitions={code}&season={year}
    Calculates last-5 form as ['W','D','L',...] from actual match results.
    Free-tier alternative since standings does not return the form field.
    """
    code = FDORG_CODES.get(liga)
    if not code or not team_id:
        return None

    season = _current_season()
    data   = _fdorg(f"/teams/{team_id}/matches", {
        "status":       "FINISHED",
        "competitions": code,
        "season":       season,
    })
    if not data:
        return None

    # Sort ascending by date and take last 5
    matches = sorted(data.get("matches", []), key=lambda m: m.get("utcDate", ""))[-5:]

    forma = []
    for m in matches:
        home_id = m["homeTeam"]["id"]
        hs      = m["score"]["fullTime"]["home"]
        as_     = m["score"]["fullTime"]["away"]
        if hs is None or as_ is None:
            continue
        if home_id == team_id:
            if hs > as_:   forma.append("W")
            elif hs < as_: forma.append("L")
            else:          forma.append("D")
        else:
            if as_ > hs:   forma.append("W")
            elif as_ < hs: forma.append("L")
            else:          forma.append("D")

    return forma if forma else None


def fetch_upcoming_fixture(local_id: int, visitante_id: int, liga: str) -> dict | None:
    """
    GET /teams/{local_id}/matches?status=SCHEDULED
    Finds the next match between local and visitante.
    """
    if not local_id or not visitante_id:
        return None

    data = _fdorg(f"/teams/{local_id}/matches", {"status": "SCHEDULED", "limit": 30})
    if not data:
        return None

    for m in data.get("matches", []):
        home_id = m["homeTeam"]["id"]
        away_id = m["awayTeam"]["id"]
        if visitante_id in (home_id, away_id):
            venue = (m.get("venue") or
                     m.get("homeTeam", {}).get("venue") or
                     None)
            return {
                "estadio":  venue,
                "hora_utc": m.get("utcDate"),
            }
    return None


def fetch_h2h(local_id: int, local_name: str,
              visitante_id: int, visitante_name: str) -> dict | None:
    """
    GET /teams/{local_id}/matches?status=FINISHED
    Filters for matches against visitante and counts W/D/L.
    """
    if not local_id or not visitante_id:
        return None

    data = _fdorg(f"/teams/{local_id}/matches",
                  {"status": "FINISHED", "limit": 40})
    if not data:
        return None

    wins_local = wins_visitante = empates = 0
    found = 0

    for m in data.get("matches", []):
        home_id = m["homeTeam"]["id"]
        away_id = m["awayTeam"]["id"]

        # Only count H2H meetings
        if not ({home_id, away_id} == {local_id, visitante_id}):
            continue

        hs = m["score"]["fullTime"]["home"]
        as_ = m["score"]["fullTime"]["away"]
        if hs is None or as_ is None:
            continue

        found += 1
        if home_id == local_id:
            if hs > as_:   wins_local += 1
            elif hs < as_: wins_visitante += 1
            else:          empates += 1
        else:
            if as_ > hs:   wins_local += 1
            elif as_ < hs: wins_visitante += 1
            else:          empates += 1

    if found == 0:
        return None

    return {
        "victorias_local":     wins_local,
        "empates":             empates,
        "victorias_visitante": wins_visitante,
    }


def fetch_league_avg_goals(liga: str) -> float | None:
    """
    GET /competitions/{code}/matches?status=FINISHED
    Calculates average goals per match in the current season.
    """
    code = FDORG_CODES.get(liga)
    if not code:
        return None

    season = _current_season()
    data   = _fdorg(f"/competitions/{code}/matches",
                    {"status": "FINISHED", "season": season})
    if not data:
        return None

    try:
        matches = data.get("matches", [])
        scored  = [
            m for m in matches
            if m["score"]["fullTime"]["home"] is not None
        ]
        if not scored:
            return None
        total = sum(
            m["score"]["fullTime"]["home"] + m["score"]["fullTime"]["away"]
            for m in scored
        )
        return round(total / len(scored), 2)
    except Exception as e:
        _errors.append(f"FD.org avg goals parse error: {e}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 5. The Odds API
# ══════════════════════════════════════════════════════════════════════════════
def fetch_odds(local: str, visitante: str, liga: str) -> dict | None:
    """
    Fetches 1X2, Over/Under 2.5, and BTTS markets.
    Returns odds dict with pinnacle, mejor_cuota, and corners skeleton.
    """
    if not ODDS_API_KEY:
        _errors.append("ODDS_API_KEY not configured")
        return None

    sport_key = ODDS_SPORT_KEYS.get(liga)
    if not sport_key:
        _errors.append(f"No Odds API sport_key mapped for: {liga}")
        return None

    data, _ = _get(
        f"{ODDS_API_BASE}/sports/{sport_key}/odds",
        params={
            "apiKey":     ODDS_API_KEY,
            "regions":    "eu",
            "markets":    "h2h,totals,spreads",
            "oddsFormat": "decimal",
        },
        cache_ttl_seconds=3600
    )
    if not data:
        return None

    events = data
    if not isinstance(events, list):
        _errors.append(f"Odds API unexpected response: {events}")
        return None

    # Find matching event
    target = None
    for ev in events:
        if _fuzzy(ev.get("home_team", ""), local) and \
           _fuzzy(ev.get("away_team", ""), visitante):
            target = ev
            break

    if not target:
        _errors.append(f"Odds API: event not found — {local} vs {visitante} in {sport_key}")
        print("\n      [!] The Odds API: partido no encontrado o sin cuotas — el modelo usará solo probabilidades propias.")
        log_naming_error("The Odds API", f"{local} vs {visitante}")
        return None

    home_key = target["home_team"]
    away_key = target["away_team"]

    result = {
        "pinnacle":    {"local": None, "empate": None, "visitante": None},
        "mejor_cuota": {"local": None, "empate": None, "visitante": None,
                        "over_2.5": None, "btts": None},
        "mejores_cuotas_extra": {
            "totals": {},
            "spreads": {},
        },
        "corners":     {"avg_local": None, "avg_visitante": None, "linea": None},
    }

    def _best_extra(category: str, key: str, val):
        if val is not None:
            cur = result["mejores_cuotas_extra"][category].get(key)
            result["mejores_cuotas_extra"][category][key] = round(max(cur or 0.0, val), 3)

    def _best(key: str, val):
        if val is not None:
            cur = result["mejor_cuota"].get(key)
            result["mejor_cuota"][key] = round(max(cur or 0.0, val), 3)

    for bk in target.get("bookmakers", []):
        bk_key = bk.get("key", "")
        for market in bk.get("markets", []):
            mkt      = market["key"]
            outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}

            if mkt == "h2h":
                h = outcomes.get(home_key)
                d = outcomes.get("Draw")
                a = outcomes.get(away_key)
                if bk_key == "pinnacle":
                    result["pinnacle"]["local"]     = h
                    result["pinnacle"]["empate"]    = d
                    result["pinnacle"]["visitante"] = a
                _best("local",     h)
                _best("empate",    d)
                _best("visitante", a)

            elif mkt == "totals":
                for o in market.get("outcomes", []):
                    pt = o.get("point")
                    price = o["price"]
                    if pt is not None:
                        # Extra totals collection
                        key_name = f"{o['name']}_{pt}".lower()
                        _best_extra("totals", key_name, price)
                        # Keep mejor_cuota in sync with extra totals for Over 2.5
                        if pt == 2.5 and o["name"] == "Over":
                            _best("over_2.5", price)

            elif mkt == "spreads":
                for o in market.get("outcomes", []):
                    pt = o.get("point")
                    nm = o.get("name")
                    price = o["price"]
                    if pt is not None:
                        is_home = (nm == home_key)
                        # We label it based on home/away perspective
                        prefix = "local" if is_home else "visitante"
                        key_name = f"spread_{prefix}_{pt}"
                        _best_extra("spreads", key_name, price)

            elif mkt == "btts":
                for o in market.get("outcomes", []):
                    if o["name"] == "Yes":
                        _best("btts", o["price"])

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Orchestrator
# ══════════════════════════════════════════════════════════════════════════════
def fetch_all(local: str, visitante: str, liga: str) -> dict:
    t0     = time.time()
    season = _current_season()

    output = {
        "partido":        {"local": local, "visitante": visitante,
                           "liga": liga, "estadio": None, "hora_utc": None},
        "elo":            {"local": None, "visitante": None},
        "xg": {
            "local":      {"atk": None, "def": None},
            "visitante":  {"atk": None, "def": None},
        },
        "liga_avg_goals": None,
        "standings":      {"pos_local": None, "pts_local": None,
                           "pos_visitante": None, "pts_visitante": None},
        "forma":          {"local": None, "visitante": None},
        "h2h":            {"victorias_local": None, "empates": None,
                           "victorias_visitante": None},
        "bajas":          {"local": None, "visitante": None},
        "odds": {
            "pinnacle":    {"local": None, "empate": None, "visitante": None},
            "mejor_cuota": {"local": None, "empate": None, "visitante": None,
                            "over_2.5": None, "btts": None},
            "corners":     {"avg_local": None, "avg_visitante": None, "linea": None},
        },
        "partido_no_disponible": False,
        "odds_disponibles": True,
    }

    # ── 1. ClubElo ─────────────────────────────────────────────────────────
    print("\n[1/5] ClubElo.com — Elo ratings...")
    elo_l = fetch_elo(local)
    elo_v = fetch_elo(visitante)
    output["elo"]["local"]     = elo_l
    output["elo"]["visitante"] = elo_v
    print(f"      {local}: {elo_l}  |  {visitante}: {elo_v}")

    # ── 2. Fotmob — xG ────────────────────────────────────────────────────
    print(f"[2/5] Fotmob.com — xG data (season {season}-{season+1})...")
    xg_result = fetch_xg_fotmob(local, visitante, liga)
    xg_l = xg_result.get("local")
    xg_v = xg_result.get("visitante")
    if xg_l:
        output["xg"]["local"]     = xg_l
    if xg_v:
        output["xg"]["visitante"] = xg_v
    print(f"      {local}     atk xG : {(xg_l or {}).get('atk')}")
    print(f"      {local}     def xGA: {(xg_l or {}).get('def')}")
    print(f"      {visitante} atk xG : {(xg_v or {}).get('atk')}")
    print(f"      {visitante} def xGA: {(xg_v or {}).get('def')}")

    # ── 3. Football-Data.org — standings, form, fixture, H2H ───────────────
    print("[3/5] Football-Data.org — standings / form / fixture / H2H...")

    standings, local_id, visitante_id, _, _ = \
        fetch_standings_and_ids(local, visitante, liga)
    output["standings"].update(standings)
    print(f"      Standings  : {standings}")
    print(f"      Team IDs   : local={local_id}  visitante={visitante_id}")

    output["forma"]["local"]     = fetch_form_fdorg(local_id,     liga)
    output["forma"]["visitante"] = fetch_form_fdorg(visitante_id, liga)
    print(f"      Forma local: {output['forma']['local']}")
    print(f"      Forma visit: {output['forma']['visitante']}")

    fixture = fetch_upcoming_fixture(local_id, visitante_id, liga)
    if fixture:
        output["partido"]["estadio"]  = fixture["estadio"]
        output["partido"]["hora_utc"] = fixture["hora_utc"]
    print(f"      Fixture    : {fixture}")

    h2h = fetch_h2h(local_id, local, visitante_id, visitante)
    if h2h:
        output["h2h"] = h2h
    print(f"      H2H        : {output['h2h']}")

    # ── 4. Football-Data.org — league avg goals ─────────────────────────────
    print("[4/5] Football-Data.org — league average goals...")
    avg = fetch_league_avg_goals(liga)
    output["liga_avg_goals"] = avg
    print(f"      {liga} avg goals/match: {avg}")

    # ── 5. The Odds API ────────────────────────────────────────────────────
    print("[5/5] The Odds API — odds (1X2 / O-U 2.5 / BTTS)...")
    odds = fetch_odds(local, visitante, liga)
    if odds:
        output["odds"] = odds
    else:
        output["odds_disponibles"] = False
        
    print(f"      Pinnacle   : {output['odds']['pinnacle']}")
    print(f"      Best cuota : {output['odds']['mejor_cuota']}")

    # ── C3 Check for match cancellation/unlisted ───────────────────────────
    if output["partido"].get("hora_utc") is None and not output["odds_disponibles"]:
        print(f"\n      [!] CUIDADO: El partido no se encontró ni en Fixtures ni en The Odds API.")
        output["partido_no_disponible"] = True

    # ── Summary ────────────────────────────────────────────────────────────
    elapsed = round(time.time() - t0, 2)
    print(f"\n{'═'*56}")
    print(f"  API calls : {_call_count}  |  Elapsed: {elapsed}s")
    if _errors:
        print(f"  Silenced errors ({len(_errors)}):")
        for e in _errors:
            print(f"    · {e}")
    print(f"{'═'*56}")

    return output


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
def main():
    if len(sys.argv) < 4:
        print('Usage  : python data_fetcher.py "Local" "Visitante" "Liga"')
        print('Example: python data_fetcher.py "Arsenal" "Liverpool" "Premier League"')
        sys.exit(1)

    local, visitante, liga = sys.argv[1], sys.argv[2], sys.argv[3]

    print(f"\n{'═'*56}")
    print(f"  PODIUM — Data Fetcher v1.2")
    print(f"  {local} vs {visitante}  |  {liga}")
    print(f"{'═'*56}")

    data = fetch_all(local, visitante, liga)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved → {OUTPUT_FILE}")
    print(f"✓ Total API calls: {_call_count}\n")


if __name__ == "__main__":
    main()
