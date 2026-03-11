import datetime
import os

# Diccionario Maestro de Normalización
MAESTRO_ALIASES = {
    # PSG
    "PSG": "Paris Saint Germain",
    "PARIS SAINT-GERMAIN": "Paris Saint Germain",
    "PARIS SG": "Paris Saint Germain",
    "PARIS SAINT GERMAIN": "Paris Saint Germain",
    
    # Man City
    "MAN CITY": "Manchester City",
    "MANCHESTER CITY": "Manchester City",
    
    # Man Utd
    "MAN UTD": "Manchester United",
    "MANCHESTER UTD": "Manchester United",
    "MANCHESTER UNITED": "Manchester United",
    
    # Athletic
    "ATHLETIC": "Athletic Club",
    "ATHLETIC BILBAO": "Athletic Club",
    "ATHLETIC CLUB": "Athletic Club",
    
    # Bodø
    "BODO/GLIMT": "Bodø/Glimt",
    "BODO / GLIMT": "Bodø/Glimt",
    "BODO GLIMT": "Bodø/Glimt",
    
    # Dortmund
    "BVB": "Borussia Dortmund",
    "DORTMUND": "Borussia Dortmund",
    "BORUSSIA DORTMUND": "Borussia Dortmund",
    
    # Chelsea
    "CHELSEA": "Chelsea",
    "CHELSEA FC": "Chelsea",
    
    # Spurs
    "SPURS": "Tottenham Hotspur",
    "TOTTENHAM HOTSPUR": "Tottenham Hotspur",
    
    # Atletico
    "ATLETI": "Atletico Madrid",
    "ATLÉTICO DE MADRID": "Atletico Madrid",
    "ATLETICO DE MADRID": "Atletico Madrid",
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
