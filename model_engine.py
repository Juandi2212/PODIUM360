#!/usr/bin/env python3
"""
model_engine.py — Podium VIP Cards · Predictive Model Engine v1.0
==================================================================
Implements Modelo Híbrido Podium v1.0 (MODELO-HIBRIDO-PODIUM-v1.0.md)

  Paso A: factor_elo  ← Elo ratings (base force with home advantage)
  Paso B: xG rolling  ← decay 0.85, fallback to liga avg if null
  Paso C: λ_local / λ_visit ← xG normalizado × corrección Elo
  Paso D: Poisson matrix P(i,j) 0-0 to 6-6
  Paso E: Market probs (1X2, Over 2.5, BTTS) desde la matriz
  Paso F: Blend modelo + Pinnacle fair odds (pesos por mercado)
  Paso G: EV% por mercado vs mejor cuota disponible
  Paso H: Regla de Oro Podium (3 criterios simultáneos)

Input:  partido_data.json
Output: model_output.json
"""

import sys
import json
import math
import os
from datetime import datetime

# Force UTF-8 on Windows consoles (CP1252 safe)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

INPUT_FILE  = "partido_data.json"
OUTPUT_DIR  = "Pronosticos"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Blend weights (Manual Parte 2) ────────────────────────────────────────────
WEIGHTS = {
    "1x2":    {"modelo": 0.45, "market": 0.55},
    "over25": {"modelo": 0.55, "market": 0.45},
    "btts":   {"modelo": 0.60, "market": 0.40},
}

# ── Model constants ────────────────────────────────────────────────────────────
ELO_HOME_ADV   = 60     # Standard home advantage (Manual Paso A)
ELO_EXP_WEIGHT = 0.3    # Elo influence on Poisson lambdas (Manual Paso C)
DECAY          = 0.85   # xG rolling decay factor (Manual Paso B)
MAX_GOALS      = 7      # Poisson matrix size: 0..6 per team
EV_MIN         = 3.0    # Regla de Oro: EV% threshold
CONSENSUS_MIN  = 2      # Regla de Oro: minimum models aligned
DIVERGENCIA_MAX = 8.0   # Regla de Oro: max market-vs-model divergence (pp)


# ══════════════════════════════════════════════════════════════════════════════
# PASO A — Elo: base probability and log-odds factor
# ══════════════════════════════════════════════════════════════════════════════
def paso_a_elo(elo_local: float, elo_visit: float) -> tuple[float, float]:
    """
    P_elo_local = 1 / (1 + 10^((Elo_visit - Elo_local - 60) / 400))
    factor_elo  = ln(P_elo_local / (1 - P_elo_local))

    Returns (p_elo_local, factor_elo).
    factor_elo > 0 → local stronger;  factor_elo < 0 → visitante stronger.
    """
    exponent    = (elo_visit - elo_local - ELO_HOME_ADV) / 400
    p_elo_local = 1 / (1 + 10 ** exponent)
    # Clamp to avoid log(0)
    p_elo_local = max(0.001, min(0.999, p_elo_local))
    factor_elo  = math.log(p_elo_local / (1 - p_elo_local))
    return p_elo_local, factor_elo


# ══════════════════════════════════════════════════════════════════════════════
# PASO B — xG rolling with exponential decay
# ══════════════════════════════════════════════════════════════════════════════
def paso_b_xg_rolling(values: list | None, decay: float = DECAY) -> float | None:
    """
    xG_weighted = Σ(values[i] × decay^i) / Σ(decay^i)
    where i=0 is the most recent match (Manual: N=8 recommended).
    Returns None if values is None or empty.
    """
    if not values:
        return None
    weights  = [decay ** i for i in range(len(values))]
    total_w  = sum(weights)
    if total_w == 0:
        return None
    return sum(v * w for v, w in zip(values, weights)) / total_w


# ══════════════════════════════════════════════════════════════════════════════
# PASO C — Normalize xG → indices → λ with Elo correction
# ══════════════════════════════════════════════════════════════════════════════
def paso_c_lambdas(
    xg_atk_local: float,
    xg_def_local: float,   # xGA (goals conceded) by local team
    xg_atk_visit: float,
    xg_def_visit: float,   # xGA (goals conceded) by visitante
    liga_avg_goals: float,
    factor_elo: float,
) -> tuple[float, float]:
    """
    xG_avg_liga (per team) = liga_avg_goals / 2

    xG_atk_local_idx = xG_atk_local / xG_avg_liga
    xG_def_visit_idx = xG_def_visit / xG_avg_liga   (visitante's defensive weakness)
    (symmetrically for visitante)

    λ_local = atk_l_idx × def_v_idx × xG_avg × e^(+0.3 × factor_elo)
    λ_visit = atk_v_idx × def_l_idx × xG_avg × e^(−0.3 × factor_elo)

    Per Manual Paso C — normalizing prevents lambda inflation.
    """
    xg_avg    = liga_avg_goals / 2  # per-team average xG per match

    atk_l_idx = xg_atk_local / xg_avg
    def_v_idx = xg_def_visit / xg_avg
    atk_v_idx = xg_atk_visit / xg_avg
    def_l_idx = xg_def_local  / xg_avg

    lam_local = atk_l_idx * def_v_idx * xg_avg * math.exp( ELO_EXP_WEIGHT * factor_elo)
    lam_visit = atk_v_idx * def_l_idx * xg_avg * math.exp(-ELO_EXP_WEIGHT * factor_elo)

    return lam_local, lam_visit


# ══════════════════════════════════════════════════════════════════════════════
# PASO D — Poisson matrix P(i, j)
# ══════════════════════════════════════════════════════════════════════════════
def _poisson_pmf(lam: float, k: int) -> float:
    """Poisson probability mass function: P(X=k | λ)."""
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def paso_d_matrix(lam_local: float, lam_visit: float) -> list[list[float]]:
    """
    Build a MAX_GOALS × MAX_GOALS probability matrix.
    matrix[i][j] = P(local scores i goals, visitante scores j goals).
    Rows/cols index from 0 to MAX_GOALS-1 (i.e., 0 to 6).
    Matrix is renormalized to sum to 1.0 (captures 6+ bucket).
    """
    n = MAX_GOALS
    matrix = [
        [_poisson_pmf(lam_local, i) * _poisson_pmf(lam_visit, j) for j in range(n)]
        for i in range(n)
    ]
    total = sum(matrix[i][j] for i in range(n) for j in range(n))
    if total > 0:
        matrix = [[matrix[i][j] / total for j in range(n)] for i in range(n)]
    return matrix


# ══════════════════════════════════════════════════════════════════════════════
# PASO E — Derive market probabilities from matrix
# ══════════════════════════════════════════════════════════════════════════════
def paso_e_market_probs(matrix: list[list[float]]) -> dict:
    """
    P_local   = Σ P(i,j)  where i > j
    P_empate  = Σ P(i,j)  where i = j
    P_visit   = Σ P(i,j)  where i < j
    P_over25  = Σ P(i,j)  where i + j > 2
    P_btts    = Σ P(i,j)  where i > 0 AND j > 0
    """
    p_local = p_empate = p_visit = 0.0
    p_over25 = p_btts = 0.0
    n = len(matrix)

    for i in range(n):
        for j in range(n):
            p = matrix[i][j]
            if   i > j:  p_local  += p
            elif i == j: p_empate += p
            else:        p_visit  += p
            if i + j > 2:           p_over25 += p
            if i > 0 and j > 0:     p_btts   += p

    return {
        "local":    round(p_local  * 100, 2),
        "empate":   round(p_empate * 100, 2),
        "visitante":round(p_visit  * 100, 2),
        "over25":   round(p_over25 * 100, 2),
        "btts":     round(p_btts   * 100, 2),
    }


# ══════════════════════════════════════════════════════════════════════════════
# PASO F — Remove vig + blend modelo with market
# ══════════════════════════════════════════════════════════════════════════════
def _remove_vig_1x2(odd_l, odd_e, odd_v) -> dict | None:
    """Convert 3-way decimal odds to fair probabilities (remove overround)."""
    if not (odd_l and odd_e and odd_v):
        return None
    raw = {"local": 1/odd_l, "empate": 1/odd_e, "visitante": 1/odd_v}
    total = sum(raw.values())
    return {k: v / total for k, v in raw.items()}


def _fair_single(cuota: float | None) -> float | None:
    """
    Estimate fair probability from a single-sided market cuota.
    Assumes ~5% overround on a 2-way market → divide by 1.05.
    """
    if not cuota or cuota <= 1:
        return None
    return (1 / cuota) / 1.05


def paso_f_blend(p_modelo: dict, pinnacle: dict, mejor_cuota: dict) -> tuple[dict, bool, dict | None]:
    """
    Blend P_modelo with Pinnacle fair odds using per-market weights.

    1X2 weights:    w_modelo=0.45, w_market=0.55
    Over/U weights: w_modelo=0.55, w_market=0.45
    BTTS weights:   w_modelo=0.60, w_market=0.40

    Returns (p_final dict, odds_blend bool, fair_pinnacle dict | None).
    fair_pinnacle is the Pinnacle fair probability dict (raw fractions, not %).
    """
    # ── 1X2 ──────────────────────────────────────────────────────────────────
    fair_pin = _remove_vig_1x2(
        pinnacle.get("local"), pinnacle.get("empate"), pinnacle.get("visitante")
    )
    wm, wk = WEIGHTS["1x2"]["modelo"], WEIGHTS["1x2"]["market"]

    if fair_pin:
        p1x2 = {
            k: wm * (p_modelo[k] / 100) + wk * fair_pin[k]
            for k in ("local", "empate", "visitante")
        }
        odds_blend = True
    else:
        p1x2 = {k: p_modelo[k] / 100 for k in ("local", "empate", "visitante")}
        odds_blend = False

    # ── Over 2.5 ─────────────────────────────────────────────────────────────
    fair_over = _fair_single(mejor_cuota.get("over25"))
    if fair_over:
        p_over = (WEIGHTS["over25"]["modelo"] * (p_modelo["over25"] / 100) +
                  WEIGHTS["over25"]["market"] * fair_over)
    else:
        p_over = p_modelo["over25"] / 100

    # ── BTTS ─────────────────────────────────────────────────────────────────
    fair_btts = _fair_single(mejor_cuota.get("btts"))
    if fair_btts:
        p_btts = (WEIGHTS["btts"]["modelo"] * (p_modelo["btts"] / 100) +
                  WEIGHTS["btts"]["market"] * fair_btts)
    else:
        p_btts = p_modelo["btts"] / 100

    p_final = {
        "local":    round(p1x2["local"]     * 100, 2),
        "empate":   round(p1x2["empate"]    * 100, 2),
        "visitante":round(p1x2["visitante"] * 100, 2),
        "over25":   round(p_over            * 100, 2),
        "btts":     round(p_btts            * 100, 2),
    }
    return p_final, odds_blend, fair_pin


# ══════════════════════════════════════════════════════════════════════════════
# PASO G — EV% per market
# ══════════════════════════════════════════════════════════════════════════════
def paso_g_ev(p_final: dict, mejor_cuota: dict) -> dict:
    """
    EV% = (P_final − 1/cuota) / (1/cuota) × 100

    Where P_final is the blended probability and cuota is the best
    available bookmaker odd for that market.
    """
    markets = [
        ("1x2_local",    p_final["local"]    / 100, mejor_cuota.get("local")),
        ("1x2_empate",   p_final["empate"]   / 100, mejor_cuota.get("empate")),
        ("1x2_visitante",p_final["visitante"]/ 100, mejor_cuota.get("visitante")),
        ("over25",       p_final["over25"]   / 100, mejor_cuota.get("over25")),
        ("btts",         p_final["btts"]     / 100, mejor_cuota.get("btts")),
    ]
    ev = {}
    for name, prob_fair, cuota in markets:
        if cuota and cuota > 1:
            prob_bookie = 1 / cuota
            ev[name] = round((prob_fair - prob_bookie) / prob_bookie * 100, 2)
        else:
            ev[name] = None
    return ev


# ══════════════════════════════════════════════════════════════════════════════
# PASO H — Regla de Oro Podium
# ══════════════════════════════════════════════════════════════════════════════
def _elo_favors(p_elo_local: float, outcome: str) -> bool:
    """Does the Elo model support this outcome?"""
    if outcome == "1x2_local":
        return p_elo_local > 0.5
    if outcome == "1x2_visitante":
        return p_elo_local < 0.5
    if outcome == "1x2_empate":
        return abs(p_elo_local - 0.5) < 0.1
    return False  # Elo not applicable to Over/BTTS (weight 0.05 in manual)


def _xg_favors(lam_local: float, lam_visit: float, outcome: str) -> bool:
    """Does xG (expressed via lambdas) support this outcome?"""
    if outcome == "1x2_local":
        return lam_local > lam_visit
    if outcome == "1x2_visitante":
        return lam_visit > lam_local
    if outcome == "1x2_empate":
        return abs(lam_local - lam_visit) < 0.25
    if outcome == "over25":
        return (lam_local + lam_visit) > 2.5
    if outcome == "btts":
        return lam_local > 0.65 and lam_visit > 0.65
    return False


def _poisson_favors(p_modelo: dict, outcome: str) -> bool:
    """Does the Poisson matrix probability support this outcome?"""
    if outcome == "1x2_local":
        return p_modelo["local"] > p_modelo["visitante"] and p_modelo["local"] > 35
    if outcome == "1x2_visitante":
        return p_modelo["visitante"] > p_modelo["local"] and p_modelo["visitante"] > 35
    if outcome == "1x2_empate":
        return p_modelo["empate"] > 26
    if outcome == "over25":
        return p_modelo["over25"] > 52
    if outcome == "btts":
        return p_modelo["btts"] > 52
    return False


def _regla_de_oro(ev_pct: float, consenso: int, divergencia: float) -> tuple[bool, str]:
    """
    Tres criterios simultáneos (Manual Parte 6):
      1. EV% > +3%
      2. consenso_modelos >= 2  (al menos 2 de 3 modelos alineados)
      3. divergencia = P_fair_pinnacle − P_modelo ≤ +8pp
         (si el mercado supera al modelo en más de 8pp → el mercado sabe algo)
    """
    if ev_pct <= EV_MIN:
        return False, f"EV insuficiente ({ev_pct:.1f}% ≤ {EV_MIN:.0f}%)"
    if consenso < CONSENSUS_MIN:
        return False, f"Modelos no alineados ({consenso}/3)"
    if divergencia > DIVERGENCIA_MAX:
        return False, f"Mercado contradice el modelo ({divergencia:.1f}pp > {DIVERGENCIA_MAX:.0f}pp)"
    return True, "PICK VIP CONFIRMADO"


def paso_h_regla_de_oro(
    ev_por_mercado:  dict,
    p_modelo:        dict,
    p_final:         dict,
    fair_pinnacle:   dict | None,
    p_elo_local:     float,
    lam_local:       float,
    lam_visit:       float,
    mejor_cuota:     dict,
) -> list[dict]:
    """
    Evaluate every market and return the top 3 picks (highest EV, >0).
    Mark as VIP if they pass all three Regla de Oro criteria.
    """
    # outcome → (p_final key, p_modelo key, mejor_cuota key)
    OUTCOME_MAP = {
        "1x2_local":    ("local",    "local",     "local"),
        "1x2_empate":   ("empate",   "empate",    "empate"),
        "1x2_visitante":("visitante","visitante",  "visitante"),
        "over25":       ("over25",   "over25",    "over25"),
        "btts":         ("btts",     "btts",      "btts"),
    }

    candidates = []  # dicts of picks

    for outcome, (fk, mk, ck) in OUTCOME_MAP.items():
        ev = ev_por_mercado.get(outcome)
        if ev is None or ev <= 0:
            continue

        # ── Consenso de modelos ──────────────────────────────────────────────
        c_elo     = _elo_favors(p_elo_local, outcome)
        c_xg      = _xg_favors(lam_local, lam_visit, outcome)
        c_poisson = _poisson_favors(p_modelo, outcome)
        consenso  = int(c_elo) + int(c_xg) + int(c_poisson)

        # ── Divergencia de mercado (signed) ─────────────────────────────────
        if fair_pinnacle and fk in fair_pinnacle:
            divergencia = fair_pinnacle[fk] * 100 - p_modelo[mk]
        else:
            divergencia = 0.0

        is_vip, razon = _regla_de_oro(ev, consenso, divergencia)
        
        # Cuota mínima rentable (+3% EV): cuota_minima = 1.03 / (P_final / 100)
        p_val = p_final.get(fk)
        cuota_minima = round(1.03 / (p_val / 100), 2) if p_val and p_val > 0 else None

        candidates.append({
            "ev":         ev,
            "mercado":    outcome,
            "cuota":      mejor_cuota.get(ck),
            "ev_pct":     round(ev, 2),
            "es_vip":     is_vip,
            "razon_rechazo": "" if is_vip else razon,
            "_consenso":  consenso,
            "_divergencia": round(divergencia, 2),
            "cuota_minima": cuota_minima
        })

    # Sort descending by EV
    candidates.sort(key=lambda x: x["ev"], reverse=True)
    return candidates[:3]


# ══════════════════════════════════════════════════════════════════════════════
# Main engine
# ══════════════════════════════════════════════════════════════════════════════
def run_model(data: dict) -> dict:
    partido      = data["partido"]
    elo          = data["elo"]
    xg           = data.get("xg") or {}
    liga_avg     = data.get("liga_avg_goals") or 2.5
    odds         = data.get("odds", {})
    pinnacle     = odds.get("pinnacle", {}) or {}
    mejor_cuota  = odds.get("mejor_cuota", {}) or {}

    # ── A. Elo ────────────────────────────────────────────────────────────────
    # If Elo data is completely missing, we fall back to a baseline of 1500.
    elo_l = elo.get("local")
    elo_v = elo.get("visitante")

    if not elo_l and not elo_v:
        elo_l, elo_v = 1500.0, 1500.0
    elif not elo_l:
        elo_l = 1500.0 if not elo_v else elo_v - 50.0 # guess local is slightly weaker if missing
    elif not elo_v:
        elo_v = 1500.0 if not elo_l else elo_l - 50.0 # guess visitor is slightly weaker if missing

    # Record if we used fallback Elo
    elo_fallback = not (elo.get("local") and elo.get("visitante"))

    p_elo_local, factor_elo = paso_a_elo(elo_l, elo_v)

    # ── B. xG rolling ─────────────────────────────────────────────────────────
    xg_local     = xg.get("local") or {}
    xg_visitante = xg.get("visitante") or {}
    xg_atk_l_raw = paso_b_xg_rolling(xg_local.get("atk"))
    xg_def_l_raw = paso_b_xg_rolling(xg_local.get("def"))
    xg_atk_v_raw = paso_b_xg_rolling(xg_visitante.get("atk"))
    xg_def_v_raw = paso_b_xg_rolling(xg_visitante.get("def"))

    xg_avg_team = liga_avg / 2   # per-team league average

    if xg_atk_l_raw is not None:
        xg_atk_local = xg_atk_l_raw
        xg_def_local = xg_def_l_raw if xg_def_l_raw is not None else xg_avg_team
        xg_atk_visit = xg_atk_v_raw if xg_atk_v_raw is not None else xg_avg_team
        xg_def_visit = xg_def_v_raw if xg_def_v_raw is not None else xg_avg_team
        # Detect if values are truly different (real rolling) or all the same (season avg)
        atk_vals = xg_local.get("atk") or []
        xg_usado = "rolling_8" if len(set(atk_vals)) > 1 else "fotmob_promedio"
    else:
        # Full fallback — no xG data at all
        xg_atk_local = xg_avg_team
        xg_def_local = xg_avg_team
        xg_atk_visit = xg_avg_team
        xg_def_visit = xg_avg_team
        xg_usado = "fallback_goles"

    # ── C. Lambdas ────────────────────────────────────────────────────────────
    lam_local, lam_visit = paso_c_lambdas(
        xg_atk_local, xg_def_local,
        xg_atk_visit, xg_def_visit,
        liga_avg, factor_elo,
    )

    # ── D. Poisson matrix ─────────────────────────────────────────────────────
    matrix = paso_d_matrix(lam_local, lam_visit)

    # ── E. Market probs from matrix ───────────────────────────────────────────
    p_modelo = paso_e_market_probs(matrix)

    # ── F. Blend modelo + Pinnacle ────────────────────────────────────────────
    p_final, odds_blend, fair_pinnacle = paso_f_blend(p_modelo, pinnacle, mejor_cuota)

    # ── G. EV per market ──────────────────────────────────────────────────────
    ev_por_mercado = paso_g_ev(p_final, mejor_cuota)

    top_3_picks = paso_h_regla_de_oro(
        ev_por_mercado, p_modelo, p_final, fair_pinnacle,
        p_elo_local, lam_local, lam_visit, mejor_cuota,
    )

    # Extract internal diagnostics from picks before saving
    processed_picks = []
    for pick in top_3_picks:
        consenso_mod = pick.pop("_consenso", 0)
        div_merc     = pick.pop("_divergencia", 0.0)
        pick.pop("ev", None)
        processed_picks.append({
            **pick,
            "bookie": "Best available",
            "diagnostico_interno": {
                "consenso_modelos": consenso_mod,
                "divergencia_mercado": div_merc
            }
        })

    # Build fair Pinnacle probability display (%)
    p_mercado = {
        "local":     round(fair_pinnacle["local"]    * 100, 2) if fair_pinnacle else None,
        "empate":    round(fair_pinnacle["empate"]   * 100, 2) if fair_pinnacle else None,
        "visitante": round(fair_pinnacle["visitante"]* 100, 2) if fair_pinnacle else None,
    }

    match_summary = {
        "probabilidades_poisson": {
            "local": p_modelo["local"],
            "empate": p_modelo["empate"],
            "visitante": p_modelo["visitante"]
        },
        "diferencial_xg_rolling": round(xg_atk_local - xg_atk_visit, 3),
        "estado_mercado": "Oportunidad Detectada" if any(p.get("ev_pct", 0) >= 5.0 for p in processed_picks) else "Mercado Eficiente"
    }

    return {
        "match_summary": match_summary,
        "probabilidades_modelo": {
            "local":    p_modelo["local"],
            "empate":   p_modelo["empate"],
            "visitante":p_modelo["visitante"],
        },
        "probabilidades_mercado": p_mercado,
        "probabilidades_finales": {
            "local":    p_final["local"],
            "empate":   p_final["empate"],
            "visitante":p_final["visitante"],
        },
        "lambdas": {
            "local":    round(lam_local, 4),
            "visitante":round(lam_visit, 4),
        },
        "top_3_picks": processed_picks,
        "diagnostico_global": {
            "xg_usado":            xg_usado,
            "odds_blend":          odds_blend,
            "elo_fallback":        elo_fallback,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# Console report
# ══════════════════════════════════════════════════════════════════════════════
def print_report(data_in: dict, out: dict):
    partido = data_in.get("partido") or {}
    elo     = data_in.get("elo") or {}
    L       = partido.get("local") or "Local"
    V       = partido.get("visitante") or "Visitante"
    liga    = partido.get("liga") or "—"
    W       = 60

    def line(char="═"): return char * W

    print(f"\n{line()}")
    print(f"  PODIUM — Modelo Híbrido Predictivo v1.0")
    print(f"  {L} vs {V}  ·  {liga}")
    print(line())

    # ── Elo ──────────────────────────────────────────────────────────────────
    elo_fallback = out.get("diagnostico_global", {}).get("elo_fallback", False)
    if not elo_fallback:
        p_elo = 1 / (1 + 10 ** ((elo["visitante"] - elo["local"] - 60) / 400))
        print(f"\n  ELO")
        print(f"    {L:<22}  {elo['local']:.1f}  →  P(win) = {p_elo*100:.1f}%")
        print(f"    {V:<22}  {elo['visitante']:.1f}  →  P(win) = {(1-p_elo)*100:.1f}%")
        print(f"    Ventaja local (+60 Elo) incluida.")
    else:
        # Re-derive the effective Elo used in the model
        lam_data = out["lambdas"]
        print(f"\n  ELO")
        print(f"    ⚠️ Datos Elo incompletos o no encontrados. Se utilizó Elo fallback de 1500/ajustado.")
        print(f"    Esto degrada parcialmente la fiabilidad del pick final.")

    # ── Lambdas ───────────────────────────────────────────────────────────────
    lam = out["lambdas"]
    print(f"\n  xG ESPERADOS (λ Poisson)")
    print(f"    λ {L:<20}  {lam['local']:.3f} goles/partido")
    print(f"    λ {V:<20}  {lam['visitante']:.3f} goles/partido")
    print(f"    λ total esperado: {lam['local'] + lam['visitante']:.3f}")

    # ── Probability table ─────────────────────────────────────────────────────
    pm  = out["probabilidades_modelo"]
    pmk = out["probabilidades_mercado"]
    pf  = out["probabilidades_finales"]

    print(f"\n  PROBABILIDADES")
    print(f"    {'Resultado':<26} {'Modelo':>7} {'Mercado':>8} {'Final':>7}")
    print(f"    {line('-')[:50]}")
    for k, label in [("local", f"1  {L}"), ("empate", "X  Empate"), ("visitante", f"2  {V}")]:
        m_str  = f"{pm[k]:.1f}%"
        mk_str = f"{pmk[k]:.1f}%" if pmk and pmk.get(k) is not None else "  N/D"
        f_str  = f"{pf[k]:.1f}%"
        print(f"    {label:<26} {m_str:>7} {mk_str:>8} {f_str:>7}")

    # ── EV per market ─────────────────────────────────────────────────────────
    ev = out.get("ev_por_mercado") or {}
    odds_data = data_in.get("odds") or {}
    mc = odds_data.get("mejor_cuota") or {}

    print(f"\n  EXPECTED VALUE  (umbral VIP: EV > +{EV_MIN:.0f}%)")
    print(f"    {'Mercado':<24} {'Cuota':>6}  {'EV%':>8}")
    print(f"    {line('-')[:42]}")
    mc_map = {
        "1x2_local":    ("local",     mc.get("local")),
        "1x2_empate":   ("empate",    mc.get("empate")),
        "1x2_visitante":("visitante", mc.get("visitante")),
        "over25":       ("over25",    mc.get("over25")),
        "btts":         ("btts",      mc.get("btts")),
    }
    label_map = {
        "1x2_local":    f"1  {L}",
        "1x2_empate":   "X  Empate",
        "1x2_visitante":f"2  {V}",
        "over25":       "Over 2.5 goles",
        "btts":         "Ambos marcan (BTTS)",
    }
    for key in ["1x2_local","1x2_empate","1x2_visitante","over25","btts"]:
        ev_val  = ev.get(key)
        cuota_v = mc_map[key][1]
        label   = label_map[key]
        cuota_s = f"{cuota_v:.2f}" if cuota_v else "  N/D"
        if ev_val is not None:
            flag = "  ✓ EV+" if ev_val > EV_MIN else ""
            print(f"    {label:<24} {cuota_s:>6}  {ev_val:>+7.2f}%{flag}")
        else:
            print(f"    {label:<24} {cuota_s:>6}  {'N/D':>8}")

    # ── Pick VIP & Top 3 ──────────────────────────────────────────────────────
    picks = out.get("top_3_picks", [])
    diag_global = out["diagnostico_global"]

    print(f"\n{line()}")
    if picks:
        print(f"  ★  TOP 3 MERCADOS CON +EV  ★\n")
        for i, pick in enumerate(picks, 1):
            vip_flag = "  [VIP] " if pick["es_vip"] else "  "
            print(f"{i}.{vip_flag}{pick['mercado'].upper()} a cuota {pick['cuota']}  →  EV: +{pick['ev_pct']:.2f}%")
            if pick.get("cuota_minima"):
                print(f"      Cuota Mín. (+3% EV): {pick['cuota_minima']}")
            print(f"      Motivo (si no es VIP): {pick['razon_rechazo'] if not pick['es_vip'] else 'OK'}")
            print(f"      Consenso: {pick['diagnostico_interno']['consenso_modelos']}/3  |  Div: {pick['diagnostico_interno']['divergencia_mercado']:+.1f}pp")
            print()
    else:
        print(f"  ✗  Sin mercados con EV > 0% detectados en este partido")

    print(f"\n  DIAGNÓSTICO GLOBAL")
    print(f"    xG fuente           : {diag_global['xg_usado']}")
    print(f"    Blend Pinnacle      : {'Sí' if diag_global['odds_blend'] else 'No — solo modelo'}")
    print(f"{line()}\n")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
def main():
    try:
        with open(INPUT_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: '{INPUT_FILE}' no encontrado. Ejecuta data_fetcher.py primero.")
        sys.exit(1)

    output = run_model(data)

    # Format output file name: LOCAL_VISITANTE_DD_MM_YY.json
    local_name = data["partido"].get("local", "Local").replace(" ", "")[:3].upper()
    visitante_name = data["partido"].get("visitante", "Visitante").replace(" ", "")[:3].upper()
    date_str = datetime.now().strftime("%d_%m_%y")
    output_filename = os.path.join(OUTPUT_DIR, f"{local_name}_{visitante_name}_{date_str}.json")

    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print_report(data, output)
    print(f"  ✓ Guardado → {output_filename}\n")

    # ── Trigger & Alert Logic (SaaS) ──────────────────────────────────────────
    high_value_picks = [p for p in output.get("top_3_picks", []) if p.get("ev_pct", 0) >= 5.0]
    if high_value_picks:
        alert_filename = os.path.join(OUTPUT_DIR, f"{local_name}_{visitante_name}_{date_str}_ALERT.json")
        with open(alert_filename, "w", encoding="utf-8") as f:
            json.dump({
                "alerta": "ALTO VALOR DETECTADO (>=5% EV)",
                "partido": data.get("partido"),
                "match_summary": output.get("match_summary"),
                "picks_valiosos": high_value_picks,
                "timestamp": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        print(f"  [🚨] ALERTA DE ALTO VALOR DETECTADA (>5% EV)")
        print(f"       Archivo Trigger generado: {alert_filename}")
        print(f"       -> Esto debe disparar la Capa IA (Insights Narrativos) de Podium SaaS.\n")


if __name__ == "__main__":
    main()
