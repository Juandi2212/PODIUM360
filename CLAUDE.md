# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Podium VIP Cards Generator** — A Claude AI-driven workflow that generates HTML sports betting analysis cards for distribution via Telegram. There is no traditional backend server; Claude itself is the engine. The master system prompt lives in `Prompts/PROMPT-MAESTRO-PODIUM-v2.2.md` and is configured once as project instructions in Claude.

## Triggering the Workflow

```
Genera tarjeta VIP: Arsenal vs Liverpool, Premier League, 15/03/2026
Genera tarjeta FREE: Arsenal vs Liverpool, Premier League, 15/03/2026
Genera tarjeta AMBAS: Arsenal vs Liverpool, Premier League, 15/03/2026
```

If no version is specified, generate **VIP** by default. Optionally include a username for a personalized watermark:
```
Genera tarjeta VIP para @CarlosBet99: Arsenal vs Liverpool, Premier League, 15/03/2026
```

## Data Collection Order (always respect this sequence)

1. **fetch_sports_data (SportRadar)** — standings, scores, fixtures. No usage limit.
2. **web_search** — injuries, news, prediction probabilities, BTTS stats, corners stats. No usage limit.
3. **The Odds API** — structured multi-bookmaker odds (h2h, totals, spreads). Check free events endpoint first; only call odds if event exists. ~3 credits per VIP card. Key: `TU_CLAVE_AQUI`.
4. **RapidAPI** — H2H history, detailed injuries, advanced stats (xG). ~100 calls/day (~4–5 per card ≈ 20 cards/day max).
5. If a data point is not found in any source → write `"No disponible"`. Never invent data.

**BTTS and Corners are mandatory sections in every VIP card**, regardless of data source used.

## Output Files

Generated HTML files are saved in `Pruebas Tarjetas/` following this naming convention:
- FREE: `[LOCAL]-[VISIT]-FREE.html`
- VIP: `[LOCAL]-[VISIT]-VIP.html`

## Card Architecture

Cards are single-file HTML (1080px fixed width, dynamic height) with all CSS inline in `<head>`. No external JS. Only external dependency is Google Fonts (`Bebas Neue` for headlines, `Barlow Condensed` for body).

**FREE vs VIP content split:**
- FREE: header, 1X2 probability bar, last-5 form badges, basic standings, footer CTA.
- VIP: everything above + odds (decimal only), detailed H2H, injuries with severity codes (🔴/🟠/🟡), **BTTS block**, **Corners block**, EV block (with best bookmaker noted), diagonal watermark overlay.

## EV Calculation (VIP only)

```
Prob. implícita = 1 / cuota_decimal × 100
EV% = (Prob_real% − Prob_implícita%) / Prob_implícita% × 100
```

Only recommend a market if EV > +3%. If no market clears +3%, output: `"DATOS INSUFICIENTES PARA UNA RECOMENDACIÓN SÓLIDA"`. Never inflate probabilities to force a positive EV.

## Watermark (VIP only)

CSS overlay with `position:absolute; inset:0; z-index:9999`. Text `PODIUM VIP · EXCLUSIVO` rotated −35°, opacity 6.5%. Parent `.card` must have `position:relative`. Never apply to FREE cards.

## Database (Supabase — PostgreSQL)

After generating the HTML, execute an INSERT into `public.partidos`. After the match concludes, run an UPDATE with the actual score and prediction accuracy flag. See `Prompts/PROMPT-MAESTRO-PODIUM-v2.2.md` → **PASO 4** for the exact SQL templates.

Key columns: `equipo_local/visitante`, `liga`, `prob_local/empate/visitante`, `mercado_ev`, `cuota_ev`, `ev_porcentaje`, `ev_recomendado`, `version_generada`, `resultado_local/visitante`, `prediccion_acertada`.

## Hard Rules

- Odds format: **decimal only** — never American (+150/−110).
- HTML must never expose source names (SportRadar, Dimers, Sports Mole, etc.), API endpoints, or internal logic.
- No predicted lineups (XI) — clubs publish them ~1 hour before kickoff.
- Always report both API consumptions on delivery: The Odds API credits used + remaining, and RapidAPI call count.
