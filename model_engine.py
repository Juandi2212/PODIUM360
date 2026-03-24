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
    "over_2.5": {"modelo": 0.55, "market": 0.45},
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
P_MIN_VIP      = 35.0   # Regla de Oro: prob mínima del modelo para VIP (%)
                        # Evita "value traps": picks con EV alto pero probabilidad
                        # baja que no tienen sentido futbolístico real

# ── Form & H2H adjustment weights ────────────────────────────────────────────
FORM_WEIGHT    = 0.15   # Max ±7.5% lambda shift from recent form
FORM_DECAY     = 0.80   # Decay per match (most recent = weight 1.0)
H2H_WEIGHT     = 0.10   # Max ±5% lambda shift from H2H record
H2H_MIN_GAMES  = 2      # Minimum H2H matches to apply adjustment


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
# PASO C.5 — Form & H2H lambda adjustments
# ══════════════════════════════════════════════════════════════════════════════
def _form_to_multiplier(forma: list | None) -> float:
    """
    Convert a recent-form list (e.g. ["W","L","D","W","W"]) into a lambda multiplier.
    Most recent match is index 0 (highest weight via FORM_DECAY).

    Returns 1.0 if forma is None/empty (no change to lambda).
    Multiplier range: ~0.925 to ~1.075 with FORM_WEIGHT=0.15.
    """
    if not forma:
        return 1.0

    pts_map = {"W": 3, "D": 1, "L": 0}
    weights = [FORM_DECAY ** i for i in range(len(forma))]
    total_w = sum(weights)
    if total_w == 0:
        return 1.0

    pts = sum(pts_map.get(r.upper(), 0) * w for r, w in zip(forma, weights))
    max_pts = 3 * total_w  # perfect form (all W)

    form_ratio = pts / max_pts  # 0.0 (all L) to 1.0 (all W)
    return 1.0 + FORM_WEIGHT * (form_ratio - 0.5)


def _h2h_adjustments(h2h: dict | None) -> tuple[float, float]:
    """
    Convert H2H record into (adj_local, adj_visit) lambda multipliers.

    h2h format: {"victorias_local": N, "empates": N, "victorias_visitante": N}
    Draws count as 0.5 wins for each side.
    Minimum H2H_MIN_GAMES required to apply adjustment.

    Returns (1.0, 1.0) if h2h is None or insufficient sample.
    Multiplier range: ~0.95 to ~1.05 with H2H_WEIGHT=0.10.
    """
    if not h2h:
        return 1.0, 1.0

    wins_l = h2h.get("victorias_local", 0) or 0
    draws  = h2h.get("empates", 0) or 0
    wins_v = h2h.get("victorias_visitante", 0) or 0
    total  = wins_l + draws + wins_v

    if total < H2H_MIN_GAMES:
        return 1.0, 1.0

    # Each side's H2H "score": full credit for wins, half for draws
    ratio_l = (wins_l + 0.5 * draws) / total  # 0.0 to 1.0
    ratio_v = (wins_v + 0.5 * draws) / total

    adj_l = 1.0 + H2H_WEIGHT * (ratio_l - 0.5)
    adj_v = 1.0 + H2H_WEIGHT * (ratio_v - 0.5)

    return adj_l, adj_v


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
def paso_e_extended_market_probs(matrix: list[list[float]]) -> dict:
    """
    P_local   = Σ P(i,j)  where i > j
    P_empate  = Σ P(i,j)  where i = j
    P_visit   = Σ P(i,j)  where i < j
    P_over25  = Σ P(i,j)  where i + j > 2
    P_btts    = Σ P(i,j)  where i > 0 AND j > 0
    Extended to include all Over/Under totals (0.5 to 6.5) and Asian Handicaps (-3.5 to +3.5).
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

    extended = {
        "local":    round(p_local  * 100, 2),
        "empate":   round(p_empate * 100, 2),
        "visitante":round(p_visit  * 100, 2),
        "over_2.5": round(p_over25 * 100, 2),
        "btts":     round(p_btts   * 100, 2),
    }

    # Totals extended — single matrix sweep accumulates all lines at once (was 12 sweeps)
    total_lines  = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.5]
    spread_lines = [-3.5, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    p_over_acc   = {pt: 0.0 for pt in total_lines}
    p_under_acc  = {pt: 0.0 for pt in total_lines}
    p_hw_acc     = {pt: 0.0 for pt in spread_lines}
    p_hl_acc     = {pt: 0.0 for pt in spread_lines}
    p_aw_acc     = {pt: 0.0 for pt in spread_lines}
    p_al_acc     = {pt: 0.0 for pt in spread_lines}

    for i in range(n):
        for j in range(n):
            p   = matrix[i][j]
            s   = i + j
            diff = i - j
            for pt in total_lines:
                if s > pt:   p_over_acc[pt]  += p
                elif s < pt: p_under_acc[pt] += p
            for pt in spread_lines:
                d  = diff + pt
                dv = -diff + pt
                if d  > 0:   p_hw_acc[pt] += p
                elif d  < 0: p_hl_acc[pt] += p
                if dv > 0:   p_aw_acc[pt] += p
                elif dv < 0: p_al_acc[pt] += p

    # Push money returned → normalise over non-push outcomes
    for pt in total_lines:
        denom = p_over_acc[pt] + p_under_acc[pt]
        if denom > 0:
            extended[f"over_{pt}"]  = round(p_over_acc[pt]  / denom * 100, 2)
            extended[f"under_{pt}"] = round(p_under_acc[pt] / denom * 100, 2)
        else:
            extended[f"over_{pt}"]  = 0
            extended[f"under_{pt}"] = 0

    for pt in spread_lines:
        dh = p_hw_acc[pt] + p_hl_acc[pt]
        da = p_aw_acc[pt] + p_al_acc[pt]
        extended[f"spread_local_{pt}"]    = round(p_hw_acc[pt] / dh * 100, 2) if dh > 0 else 0
        extended[f"spread_visitante_{pt}"] = round(p_aw_acc[pt] / da * 100, 2) if da > 0 else 0

    return extended


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
    fair_over = _fair_single(mejor_cuota.get("over_2.5"))
    if fair_over:
        p_over = (WEIGHTS["over_2.5"]["modelo"] * (p_modelo["over_2.5"] / 100) +
                  WEIGHTS["over_2.5"]["market"] * fair_over)
    else:
        p_over = p_modelo["over_2.5"] / 100

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
        "over_2.5": round(p_over            * 100, 2),
        "btts":     round(p_btts            * 100, 2),
    }
    
    # Merge additional extended markets (pure model without pinnacle blend)
    for k, v in p_modelo.items():
        if k not in p_final:
            p_final[k] = v

    return p_final, odds_blend, fair_pin


# ══════════════════════════════════════════════════════════════════════════════
# PASO F.5 — Double Chance synthetic markets
# ══════════════════════════════════════════════════════════════════════════════
DC_MIN_COMPONENT = 0.20  # Cada componente debe tener ≥ 20% de probabilidad (blended)

def _compute_dc_markets(
    p_modelo: dict,
    p_final: dict,
    fair_pinnacle: dict | None,
    mejor_cuota: dict,
) -> None:
    """
    Inyecta mercados de Doble Oportunidad (dc_1x, dc_x2, dc_12) en los dicts
    existentes. Solo se agregan si ambas componentes cumplen DC_MIN_COMPONENT.

    - p_modelo y p_final usan escala 0–100
    - fair_pinnacle usa escala 0–1
    - mejor_cuota recibe las cuotas sintéticas derivadas de Pinnacle no-vig
    """
    # Probabilidades blended (fracción)
    p_h = p_final.get("local",     0) / 100
    p_d = p_final.get("empate",    0) / 100
    p_a = p_final.get("visitante", 0) / 100

    # Probabilidades modelo Poisson (fracción)
    m_h = p_modelo.get("local",     0) / 100
    m_d = p_modelo.get("empate",    0) / 100
    m_a = p_modelo.get("visitante", 0) / 100

    combos = {
        "dc_1x": (p_h, p_d, m_h, m_d),
        "dc_x2": (p_d, p_a, m_d, m_a),
        "dc_12": (p_h, p_a, m_h, m_a),
    }

    for code, (c1_blend, c2_blend, c1_mod, c2_mod) in combos.items():
        # Filtro de componentes mínimas
        if c1_blend < DC_MIN_COMPONENT or c2_blend < DC_MIN_COMPONENT:
            continue

        p_blend_dc = c1_blend + c2_blend
        p_model_dc = c1_mod  + c2_mod

        # Agregar a p_final y p_modelo (escala 0–100)
        p_final[code]  = round(p_blend_dc * 100, 2)
        p_modelo[code] = round(p_model_dc * 100, 2)

        # Cuota sintética de mercado: derivada de Pinnacle no-vig
        if fair_pinnacle:
            keys = {
                "dc_1x": ("local",  "empate"),
                "dc_x2": ("empate", "visitante"),
                "dc_12": ("local",  "visitante"),
            }[code]
            p_pinn_dc = fair_pinnacle.get(keys[0], 0) + fair_pinnacle.get(keys[1], 0)
            if p_pinn_dc > 0:
                # Almacenar en fair_pinnacle para el cálculo de divergencia en paso_h
                fair_pinnacle[code] = p_pinn_dc
                # Cuota justa (sin margen) como referencia de mercado
                mejor_cuota[code] = round(1 / p_pinn_dc, 3)


# ══════════════════════════════════════════════════════════════════════════════
# PASO G — EV% per market
# ══════════════════════════════════════════════════════════════════════════════
def paso_g_ev(p_final: dict, mejor_cuota: dict, extra: dict) -> dict:
    """
    EV% = (P_final − 1/cuota) / (1/cuota) × 100

    Where P_final is the blended probability and cuota is the best
    available bookmaker odd for that market.
    """
    markets = [
        ("1x2_local",    p_final.get("local",0), mejor_cuota.get("local")),
        ("1x2_empate",   p_final.get("empate",0), mejor_cuota.get("empate")),
        ("1x2_visitante",p_final.get("visitante",0), mejor_cuota.get("visitante")),
        ("btts",         p_final.get("btts",0), mejor_cuota.get("btts")),
    ]
    # over_2.5, over_1.5, under_1.5, over_3.5, etc. all flow via the extra totals loop below
    
    for tm, tc in (extra.get("totals", {})).items():
        if tm in p_final:
            markets.append((tm, p_final[tm], tc))
            
    for sm, sc in (extra.get("spreads", {})).items():
        if sm in p_final:
            markets.append((sm, p_final[sm], sc))

    # Double Chance (sintéticos, solo si fueron generados por _compute_dc_markets)
    for dc_code in ("dc_1x", "dc_x2", "dc_12"):
        if dc_code in p_final:
            markets.append((dc_code, p_final[dc_code], mejor_cuota.get(dc_code)))

    ev = {}
    for name, prob_fair_pct, cuota in markets:
        prob_fair = prob_fair_pct / 100
        if cuota and cuota > 1 and prob_fair > 0.01:
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
    # Double Chance
    if outcome == "dc_1x":
        return p_elo_local >= 0.40   # local no es el gran perdedor
    if outcome == "dc_x2":
        return p_elo_local <= 0.60   # visitante no es el gran perdedor
    if outcome == "dc_12":
        return abs(p_elo_local - 0.5) > 0.10  # hay favorito claro → el empate es improbable
    return False  # Elo not applicable to Over/BTTS (weight 0.05 in manual)


def _xg_favors(lam_local: float, lam_visit: float, outcome: str) -> bool:
    """Does xG (expressed via lambdas) support this outcome?"""
    if outcome == "1x2_local":
        return lam_local > lam_visit
    if outcome == "1x2_visitante":
        return lam_visit > lam_local
    if outcome == "over_2.5":
        return (lam_local + lam_visit) > 2.5
    if outcome == "over_1.5":
        return (lam_local + lam_visit) > 1.5
    if outcome == "under_1.5":
        return (lam_local + lam_visit) < 1.5
    if outcome == "btts":
        return lam_local > 0.65 and lam_visit > 0.65
    # Double Chance
    if outcome == "dc_1x":
        return lam_local >= lam_visit * 0.80   # local no está muy por debajo en xG
    if outcome == "dc_x2":
        return lam_visit >= lam_local * 0.80   # visitante no está muy por debajo en xG
    if outcome == "dc_12":
        return abs(lam_local - lam_visit) > 0.30  # hay diferencia clara → el empate es menos probable
    return False


def _poisson_favors(p_modelo: dict, outcome: str) -> bool:
    """Does the Poisson matrix probability support this outcome?"""
    if outcome == "1x2_local":
        return p_modelo["local"] > p_modelo["visitante"] and p_modelo["local"] > 40
    if outcome == "1x2_visitante":
        return p_modelo["visitante"] > p_modelo["local"] and p_modelo["visitante"] > 40
    if outcome == "over_2.5":
        return p_modelo["over_2.5"] > 52
    if outcome == "over_1.5":
        return p_modelo.get("over_1.5", 0) > 70
    if outcome == "under_1.5":
        return p_modelo.get("under_1.5", 0) > 30
    if outcome == "btts":
        return p_modelo["btts"] > 52
    # Double Chance
    if outcome == "dc_1x":
        return p_modelo.get("local", 0) + p_modelo.get("empate", 0) > 60
    if outcome == "dc_x2":
        return p_modelo.get("visitante", 0) + p_modelo.get("empate", 0) > 60
    if outcome == "dc_12":
        return p_modelo.get("local", 0) + p_modelo.get("visitante", 0) > 70
    return False


def _regla_de_oro(ev_pct: float, consenso: int, divergencia: float,
                  p_modelo_pct: float = 100.0) -> tuple[bool, str]:
    """
    Cuatro criterios simultáneos (Manual Parte 6):
      1. EV% > +3%
      2. consenso_modelos >= 2  (al menos 2 de 3 modelos alineados)
      3. divergencia = P_fair_pinnacle − P_modelo ≤ +8pp
         (si el mercado supera al modelo en más de 8pp → el mercado sabe algo)
      4. P_modelo ≥ P_MIN_VIP  (evita value traps: EV alto con prob baja)
    """
    if p_modelo_pct < P_MIN_VIP:
        return False, f"Probabilidad insuficiente ({p_modelo_pct:.1f}% < {P_MIN_VIP:.0f}%)"
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
) -> tuple[list[dict], list[dict]]:
    """
    Evaluate every market and return the top 3 picks (highest EV, >0).
    Mark as VIP if they pass all three Regla de Oro criteria.
    """
    # outcome → (p_final key, p_modelo key, mejor_cuota key)
    OUTCOME_MAP = {
        "1x2_local":    ("local",    "local",     "local"),
        "1x2_visitante":("visitante","visitante",  "visitante"),
        "over_2.5":     ("over_2.5", "over_2.5",  "over_2.5"),
        "over_1.5":     ("over_1.5", "over_1.5",  "over_1.5"),
        "under_1.5":    ("under_1.5","under_1.5", "under_1.5"),
        "btts":         ("btts",     "btts",      "btts"),
        "dc_1x":        ("dc_1x",   "dc_1x",     "dc_1x"),
        "dc_x2":        ("dc_x2",   "dc_x2",     "dc_x2"),
        "dc_12":        ("dc_12",   "dc_12",     "dc_12"),
    }

    candidates = []  # dicts of picks

    for outcome, (fk, mk, ck) in OUTCOME_MAP.items():
        ev = ev_por_mercado.get(outcome)
        if ev is None:
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

        # Probabilidad del modelo para este mercado (para filtro P_MIN_VIP)
        p_modelo_pct = p_modelo.get(mk, 0) or 0
        is_vip, razon = _regla_de_oro(ev, consenso, divergencia, p_modelo_pct)
        
        # Cuota mínima rentable (+3% EV): cuota_minima = 1.03 / (P_final / 100)
        p_val = p_final.get(fk)
        cuota_minima = round(1.03 / (p_val / 100), 2) if p_val and p_val > 0 else None

        candidates.append({
            "ev":         ev,
            "mercado":    outcome,
            "cuota":      mejor_cuota.get(ck) if ck else None, # Might not be available since ck is just best guess
            "ev_pct":     round(ev, 2),
            "es_vip":     is_vip,
            "razon_rechazo": "" if is_vip else razon,
            "_consenso":  consenso,
            "_divergencia": round(divergencia, 2),
            "cuota_minima": cuota_minima,
            "p_modelo_ext": p_final.get(fk)
        })

    # Add extra markets to all_markets
    extra_candidates = []
    for extr_market, extr_ev in ev_por_mercado.items():
        if extr_market not in OUTCOME_MAP and extr_ev is not None:
            c_val = None # We didn't keep track of cuota here securely except inside ev loop, but we can reconstruct it from JSON
            
            p_val = p_final.get(extr_market)
            ext_cuota_min = round(1.03 / (p_val / 100), 2) if p_val and p_val > 0 else None
            
            extra_candidates.append({
                "ev": extr_ev,
                "mercado": extr_market,
                "cuota": None,  # Will inject later right away
                "ev_pct": round(extr_ev, 2),
                "es_vip": False,
                "razon_rechazo": "Mercado Secundario",
                "_consenso": 0,
                "_divergencia": 0.0,
                "cuota_minima": ext_cuota_min,
                "p_modelo_ext": p_val
            })
            
    all_combined = candidates + extra_candidates

    # Sort descending by EV
    candidates.sort(key=lambda x: x["ev"], reverse=True)
    valid_picks = [c for c in candidates if c["ev"] > 0]
    return valid_picks[:3], all_combined


# ══════════════════════════════════════════════════════════════════════════════
# Diccionario Maestro de Normalización
# ══════════════════════════════════════════════════════════════════════════════
from utils.naming import normalize_team_name

# ══════════════════════════════════════════════════════════════════════════════
# Main engine
# ══════════════════════════════════════════════════════════════════════════════
def _validate_input(data: dict) -> None:
    """Raise ValueError with a clear message if critical fields are missing."""
    required = ["partido", "elo"]
    for field in required:
        if field not in data or data[field] is None:
            raise ValueError(f"partido_data.json missing required field: '{field}'")
    partido = data["partido"]
    for sub in ("local", "visitante"):
        if not partido.get(sub):
            raise ValueError(f"partido_data.json missing partido.{sub}")


def _impute_elo(elo_l, elo_v):
    """Return (elo_l, elo_v, elo_fallback) with sensible defaults when data is absent."""
    if not elo_l and not elo_v:
        return 1500.0, 1500.0, True
    if not elo_l:
        return (1500.0 if not elo_v else elo_v - 50.0), elo_v, True
    if not elo_v:
        return elo_l, (1500.0 if not elo_l else elo_l - 50.0), True
    return float(elo_l), float(elo_v), False


def _process_market_outputs(top_3_picks, all_markets, m_extra, p_final):
    """
    Convert raw paso_h output into the cleaned processed_picks and
    processed_all_markets lists used by the JSON output.
    Also injects over_1.5 / under_1.5 entries when no cuota API was found.
    """
    def _get_extra_cuota(mk):
        if mk.startswith("over_") or mk.startswith("under_"):
            return m_extra.get("totals", {}).get(mk)
        if mk.startswith("spread_"):
            return m_extra.get("spreads", {}).get(mk)
        return None

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
                "divergencia_mercado": div_merc,
            },
        })

    processed_all_markets = []
    for m in all_markets:
        consenso_mod = m.pop("_consenso", 0)
        div_merc     = m.pop("_divergencia", 0.0)
        m.pop("ev", None)
        if m["cuota"] is None:
            m["cuota"] = _get_extra_cuota(m["mercado"])
        processed_all_markets.append({
            **m,
            "bookie": "Best available",
            "diagnostico_interno": {
                "consenso_modelos": consenso_mod,
                "divergencia_mercado": div_merc,
            },
        })

    # Always show over_1.5 / under_1.5 even without a bookie quote
    existing = {m["mercado"] for m in processed_all_markets}
    for ou_key in ("over_1.5", "under_1.5"):
        if ou_key not in existing:
            prob = p_final.get(ou_key)
            if prob is not None:
                processed_all_markets.append({
                    "mercado":   ou_key,
                    "cuota":     m_extra.get("totals", {}).get(ou_key),
                    "ev_pct":    None,
                    "es_vip":    False,
                    "razon_rechazo":  "Sin cuota API",
                    "cuota_minima":   None,
                    "p_modelo_ext":   round(prob, 2),
                    "bookie":    "Modelo puro",
                    "diagnostico_interno": {"consenso_modelos": 0, "divergencia_mercado": 0.0},
                })

    return processed_picks, processed_all_markets


def run_model(data: dict) -> dict:
    _validate_input(data)
    partido      = data["partido"]
    
    # Aplicar normalización
    if "local" in partido:
        partido["local"] = normalize_team_name(partido["local"])
    if "visitante" in partido:
        partido["visitante"] = normalize_team_name(partido["visitante"])
        
    elo          = data["elo"]
    xg           = data.get("xg") or {}
    liga_avg     = data.get("liga_avg_goals") or 2.5
    odds         = data.get("odds", {})
    pinnacle     = odds.get("pinnacle", {}) or {}
    mejor_cuota  = odds.get("mejor_cuota", {}) or {}
    m_extra      = odds.get("mejores_cuotas_extra", {}) or {}

    # ── A. Elo ────────────────────────────────────────────────────────────────
    elo_l, elo_v, elo_fallback = _impute_elo(elo.get("local"), elo.get("visitante"))

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
    # Prevent division by zero and extreme lambdas (Fix M4)
    liga_avg_safe = max(2.0, liga_avg)
    
    lam_local, lam_visit = paso_c_lambdas(
        xg_atk_local, xg_def_local,
        xg_atk_visit, xg_def_visit,
        liga_avg_safe, factor_elo,
    )

    # ── C.5 Form & H2H adjustments on lambdas ─────────────────────────────────
    forma_data = data.get("forma") or {}
    h2h_data   = data.get("h2h")

    form_adj_l = _form_to_multiplier(forma_data.get("local"))
    form_adj_v = _form_to_multiplier(forma_data.get("visitante"))
    h2h_adj_l, h2h_adj_v = _h2h_adjustments(h2h_data)

    lam_local  *= form_adj_l * h2h_adj_l
    lam_visit  *= form_adj_v * h2h_adj_v

    # ── D. Poisson matrix ─────────────────────────────────────────────────────
    matrix = paso_d_matrix(lam_local, lam_visit)

    # ── E. Market probs from matrix ───────────────────────────────────────────
    p_modelo = paso_e_extended_market_probs(matrix)

    # ── F. Blend modelo + Pinnacle ────────────────────────────────────────────
    p_final, odds_blend, fair_pinnacle = paso_f_blend(p_modelo, pinnacle, mejor_cuota)

    # ── F.5 Double Chance synthetic markets ───────────────────────────────────
    _compute_dc_markets(p_modelo, p_final, fair_pinnacle, mejor_cuota)

    # ── G. EV per market ──────────────────────────────────────────────────────
    ev_por_mercado = paso_g_ev(p_final, mejor_cuota, m_extra)

    # Merge over/under 1.5 cuotas en mejor_cuota para que paso_h pueda hacer el lookup
    for _ou in ("over_1.5", "under_1.5"):
        if _ou not in mejor_cuota:
            _tc = m_extra.get("totals", {}).get(_ou)
            if _tc:
                mejor_cuota[_ou] = _tc

    top_3_picks, all_markets = paso_h_regla_de_oro(
        ev_por_mercado, p_modelo, p_final, fair_pinnacle,
        p_elo_local, lam_local, lam_visit, mejor_cuota,
    )

    processed_picks, processed_all_markets = _process_market_outputs(
        top_3_picks, all_markets, m_extra, p_final
    )

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
        "estado_mercado": "Oportunidad Detectada" if any(p.get("ev_pct", 0) >= 5.0 for p in processed_picks) else "Mercado Eficiente",
        "all_markets": processed_all_markets
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
            "form_adj_local":      round(form_adj_l, 4),
            "form_adj_visitante":  round(form_adj_v, 4),
            "h2h_adj_local":       round(h2h_adj_l, 4),
            "h2h_adj_visitante":   round(h2h_adj_v, 4),
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
    if not elo_fallback and elo.get("local") is not None and elo.get("visitante") is not None:
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

    # ── Report Generation ─────────────────────────────────────────────────────
    print(f"\n{'═'*56}")
    print(f"  PODIUM — VIP Report")
    print(f"  {L} vs {V}")
    print(f"{'═'*56}")

    if data_in.get("partido_no_disponible", False):
        print(f"\n  [!] PARTIDO NO DISPONIBLE: No se encontraron cuotas ni datos de calendarización.")
        print(f"  El análisis no continuará para evitar predicciones falsas.")
        return

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
    mc = (data_in.get("odds") or {}).get("mejor_cuota") or {}

    print(f"\n  EXPECTED VALUE  (umbral VIP: EV > +{EV_MIN:.0f}%)")
    print(f"    {'Mercado':<24} {'Cuota':>6}  {'EV%':>8}")
    print(f"    {line('-')[:42]}")
    m_extra_pr = (data_in.get("odds") or {}).get("mejores_cuotas_extra", {}) or {}
    mc_map = {
        "1x2_local":    ("local",     mc.get("local")),
        "1x2_empate":   ("empate",    mc.get("empate")),
        "1x2_visitante":("visitante", mc.get("visitante")),
        "over_2.5":     ("over_2.5",  mc.get("over_2.5")),
        "over_1.5":     ("over_1.5",  m_extra_pr.get("totals", {}).get("over_1.5")),
        "under_1.5":    ("under_1.5", m_extra_pr.get("totals", {}).get("under_1.5")),
        "over_3.5":     ("over_3.5",  m_extra_pr.get("totals", {}).get("over_3.5")),
        "under_3.5":    ("under_3.5", m_extra_pr.get("totals", {}).get("under_3.5")),
        "btts":         ("btts",      mc.get("btts")),
    }
    label_map = {
        "1x2_local":    f"1  {L}",
        "1x2_empate":   "X  Empate",
        "1x2_visitante":f"2  {V}",
        "over_1.5":     "Over 1.5 goles",
        "under_1.5":    "Under 1.5 goles",
        "over_2.5":     "Over 2.5 goles",
        "over_3.5":     "Over 3.5 goles",
        "under_3.5":    "Under 3.5 goles",
        "btts":         "Ambos marcan (BTTS)",
    }
    for key in ["1x2_local","1x2_empate","1x2_visitante","over_1.5","under_1.5","over_2.5","over_3.5","under_3.5","btts"]:
        ev_val  = ev.get(key)
        cuota_v = mc_map[key][1]
        label   = label_map[key]
        if cuota_v is None and key not in {"over_1.5", "under_1.5"}:
            continue  # No mostrar líneas extra sin cuota (1.5 siempre se muestra)
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
            
        # Basic validation
        if not isinstance(data, dict):
            raise TypeError(f"El archivo JSON debe contener un objeto, no {type(data).__name__}")
        if not data.get("partido"):
            raise KeyError("Falta el objeto 'partido' en el JSON de entrada")
            
        # Optional: Inject some mock better odds to ensure something fires if best aren't provided
        # This is strictly to ensure the format holds. (Not strictly needed since pipeline provides this).
    except FileNotFoundError:
        print(f"Error: '{INPUT_FILE}' no encontrado. Ejecuta data_fetcher.py primero.")
        sys.exit(1)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Error: '{INPUT_FILE}' es inválido o está corrupto: {e}")
        sys.exit(1)

    output = run_model(data)

    # Format output file name variables
    local_name = data["partido"].get("local", "Local").replace(" ", "")[:3].upper()
    visitante_name = data["partido"].get("visitante", "Visitante").replace(" ", "")[:3].upper()
    date_str = datetime.now().strftime("%d_%m_%y")

    # ── Save Standard Output ──────────────────────────────────────────────────
    std_output = {
        "partido": data.get("partido"),
        "forma": data.get("forma"),
        "h2h": data.get("h2h"),
        **output
    }
    std_filename = os.path.join(OUTPUT_DIR, f"{local_name}_{visitante_name}_{date_str}.json")
    with open(std_filename, "w", encoding="utf-8") as f:
        json.dump(std_output, f, ensure_ascii=False, indent=2)
    print(f"  [OK] Resultados del modelo guardados en: {std_filename}")

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
