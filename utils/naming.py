import datetime
import os

# Diccionario Maestro de Normalización
# Cada variante conocida (Odds API, Football-Data, Fotmob, test_runner) → nombre canónico
MAESTRO_ALIASES = {
    # PSG
    "PSG": "Paris Saint Germain",
    "PARIS SAINT-GERMAIN": "Paris Saint Germain",
    "PARIS SG": "Paris Saint Germain",
    "PARIS SAINT GERMAIN": "Paris Saint Germain",
    "PARIS S-G": "Paris Saint Germain",
    
    # Manchester City
    "MAN CITY": "Manchester City",
    "MANCHESTER CITY": "Manchester City",
    "MAN. CITY": "Manchester City",
    
    # Manchester United
    "MAN UTD": "Manchester United",
    "MANCHESTER UTD": "Manchester United",
    "MANCHESTER UNITED": "Manchester United",
    "MAN. UNITED": "Manchester United",
    "MAN UNITED": "Manchester United",
    
    # Athletic
    "ATHLETIC": "Athletic Club",
    "ATHLETIC BILBAO": "Athletic Club",
    "ATHLETIC CLUB": "Athletic Club",
    
    # Bodø/Glimt
    "BODO/GLIMT": "Bodø/Glimt",
    "BODO / GLIMT": "Bodø/Glimt",
    "BODO GLIMT": "Bodø/Glimt",
    "BODØ/GLIMT": "Bodø/Glimt",
    
    # Borussia Dortmund
    "BVB": "Borussia Dortmund",
    "DORTMUND": "Borussia Dortmund",
    "BORUSSIA DORTMUND": "Borussia Dortmund",
    
    # Chelsea
    "CHELSEA": "Chelsea",
    "CHELSEA FC": "Chelsea",
    
    # Tottenham
    "SPURS": "Tottenham Hotspur",
    "TOTTENHAM HOTSPUR": "Tottenham Hotspur",
    "TOTTENHAM": "Tottenham Hotspur",
    
    # Atletico Madrid
    "ATLETI": "Atletico Madrid",
    "ATLÉTICO DE MADRID": "Atletico Madrid",
    "ATLETICO DE MADRID": "Atletico Madrid",
    "ATLETICO MADRID": "Atletico Madrid",
    "ATL. MADRID": "Atletico Madrid",
    "ATL MADRID": "Atletico Madrid",

    # Bayern Munich
    "BAYERN": "Bayern Munich",
    "BAYERN MUNICH": "Bayern Munich",
    "BAYERN MUNCHEN": "Bayern Munich",
    "BAYERN MÜNCHEN": "Bayern Munich",
    "FC BAYERN": "Bayern Munich",
    "FC BAYERN MUNICH": "Bayern Munich",
    "FC BAYERN MÜNCHEN": "Bayern Munich",
    
    # Bayer Leverkusen
    "LEVERKUSEN": "Bayer Leverkusen",
    "BAYER LEVERKUSEN": "Bayer Leverkusen",
    "B. LEVERKUSEN": "Bayer Leverkusen",
    "BAYER 04 LEVERKUSEN": "Bayer Leverkusen",
    
    # Real Madrid
    "REAL MADRID": "Real Madrid",
    "REAL MADRID CF": "Real Madrid",
    "R. MADRID": "Real Madrid",
    
    # Barcelona
    "BARCELONA": "Barcelona",
    "FC BARCELONA": "Barcelona",
    "BARCA": "Barcelona",
    "BARÇA": "Barcelona",
    
    # Inter Milan
    "INTER": "Inter Milan",
    "INTER MILAN": "Inter Milan",
    "INTERNAZIONALE": "Inter Milan",
    "FC INTERNAZIONALE": "Inter Milan",
    
    # AC Milan
    "MILAN": "AC Milan",
    "AC MILAN": "AC Milan",
    
    # AS Roma
    "ROMA": "AS Roma",
    "AS ROMA": "AS Roma",
    
    # SS Lazio
    "LAZIO": "SS Lazio",
    "SS LAZIO": "SS Lazio",
    
    # Napoli
    "NAPOLI": "Napoli",
    "SSC NAPOLI": "Napoli",
    
    # Juventus
    "JUVENTUS": "Juventus",
    "JUVE": "Juventus",
    
    # Arsenal
    "ARSENAL": "Arsenal",
    "ARSENAL FC": "Arsenal",
    
    # Liverpool
    "LIVERPOOL": "Liverpool",
    "LIVERPOOL FC": "Liverpool",
    
    # RB Leipzig
    "RB LEIPZIG": "RB Leipzig",
    "LEIPZIG": "RB Leipzig",
    "RASENBALLSPORT LEIPZIG": "RB Leipzig",
    
    # Sporting CP
    "SPORTING CP": "Sporting CP",
    "SPORTING": "Sporting CP",
    "SPORTING LISBON": "Sporting CP",
    "SPORTING LISBOA": "Sporting CP",
    
    # Porto
    "PORTO": "Porto",
    "FC PORTO": "Porto",
    
    # Benfica
    "BENFICA": "Benfica",
    "SL BENFICA": "Benfica",
    
    # Sevilla
    "SEVILLA": "Sevilla",
    "SEVILLA FC": "Sevilla",
    
    # Villarreal
    "VILLARREAL": "Villarreal",
    "VILLARREAL CF": "Villarreal",
    
    # Monaco
    "MONACO": "Monaco",
    "AS MONACO": "Monaco",
    
    # Marseille
    "MARSEILLE": "Marseille",
    "OLYMPIQUE DE MARSEILLE": "Marseille",
    "OLYMPIQUE MARSEILLE": "Marseille",
    "OM": "Marseille",
    
    # Lyon
    "LYON": "Lyon",
    "OLYMPIQUE LYONNAIS": "Lyon",
    "OL LYON": "Lyon",
    
    # Newcastle
    "NEWCASTLE": "Newcastle United",
    "NEWCASTLE UNITED": "Newcastle United",
    "NEWCASTLE UTD": "Newcastle United",
    
    # West Ham
    "WEST HAM": "West Ham United",
    "WEST HAM UNITED": "West Ham United",
    
    # Aston Villa
    "ASTON VILLA": "Aston Villa",
    
    # Wolves
    "WOLVES": "Wolverhampton",
    "WOLVERHAMPTON WANDERERS": "Wolverhampton",
    "WOLVERHAMPTON": "Wolverhampton",
    
    # Brighton
    "BRIGHTON": "Brighton",
    "BRIGHTON & HOVE ALBION": "Brighton",
    "BRIGHTON AND HOVE ALBION": "Brighton",
    
    # Feyenoord
    "FEYENOORD": "Feyenoord",
    
    # Ajax
    "AJAX": "Ajax",
    "AFC AJAX": "Ajax",
    
    # PSV
    "PSV": "PSV Eindhoven",
    "PSV EINDHOVEN": "PSV Eindhoven",
    
    # Atalanta
    "ATALANTA": "Atalanta",
    "ATALANTA BC": "Atalanta",
    
    # Galatasaray
    "GALATASARAY": "Galatasaray",
    "GALATASARAY SK": "Galatasaray",
    
    # Lille
    "LILLE": "Lille",
    "LOSC LILLE": "Lille",
    "LOSC": "Lille",
    
    # Brest
    "BREST": "Brest",
    "STADE BRESTOIS": "Brest",

    # Bologna
    "BOLOGNA": "Bologna",
    "BOLOGNA FC": "Bologna",
    "FC BOLOGNA": "Bologna",

    # Real Betis
    "BETIS": "Real Betis",
    "REAL BETIS": "Real Betis",
    "R. BETIS": "Real Betis",
    "REAL BETIS BALOMPIÉ": "Real Betis",

    # VfB Stuttgart
    "STUTTGART": "Stuttgart",
    "VFB STUTTGART": "Stuttgart",

    # Celta Vigo
    "CELTA": "Celta Vigo",
    "CELTA VIGO": "Celta Vigo",
    "RC CELTA": "Celta Vigo",
    "RC CELTA DE VIGO": "Celta Vigo",

    # Panathinaikos
    "PANATHINAIKOS": "Panathinaikos",
    "PANATHINAIKOS FC": "Panathinaikos",

    # Ferencvaros
    "FERENCVAROS": "Ferencvaros",
    "FERENCVAROSI TC": "Ferencvaros",
    "FERENCVÁROS": "Ferencvaros",
    "FTC": "Ferencvaros",

    # SC Braga
    "BRAGA": "Braga",
    "SC BRAGA": "Braga",
    "SPORTING DE BRAGA": "Braga",

    # KRC Genk
    "GENK": "Genk",
    "KRC GENK": "Genk",

    # SC Freiburg
    "FREIBURG": "Freiburg",
    "SC FREIBURG": "Freiburg",

    # Nottingham Forest
    "NOTTINGHAM FOREST": "Nottingham Forest",
    "NOTTM FOREST": "Nottingham Forest",
    "FOREST": "Nottingham Forest",

    # FC Midtjylland
    "MIDTJYLLAND": "Midtjylland",
    "FC MIDTJYLLAND": "Midtjylland",
}

def normalize_team_name(name: str) -> str:
    """Normaliza los nombres de los equipos para la Matriz y para APIs."""
    if not name:
        return ""
    clean_name = name.strip()
    return MAESTRO_ALIASES.get(clean_name.upper(), clean_name)

def fuzzy_match(api_name: str, model_name: str) -> bool:
    """
    Compara dos nombres usando normalización y búsqueda laxa (ignorando guiones).
    """
    norm_api = normalize_team_name(api_name).lower().replace("-", " ")
    norm_mod = normalize_team_name(model_name).lower().replace("-", " ")
    
    if norm_api in norm_mod or norm_mod in norm_api:
        return True
    
    # Búsqueda laxa literal
    raw_api = api_name.lower().strip().replace("-", " ")
    raw_mod = model_name.lower().strip().replace("-", " ")
    if raw_api in raw_mod or raw_mod in raw_api:
        return True

    return False

def log_naming_error(api_source: str, missing_name: str):
    """
    Registra el error en naming_errors.log.
    """
    log_path = "naming_errors.log"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] Error de cruce: [{api_source}] No se encontró el equipo [{missing_name}]\n"
    
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg)
    except Exception as e:
        print(f"No se pudo escribir en el log de nombres: {e}")
