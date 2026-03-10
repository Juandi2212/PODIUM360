# PROJECT ARCHITECTURE REPORT
## Podium VIP Cards Generator
**Generated:** 2026-03-06 | **Analyzer:** Claude Sonnet 4.6

---

## 1. PROJECT STRUCTURE

```
CLAUDE DL/
├── CLAUDE.md                              → Project instructions loaded into every Claude session
├── PLAN.md                                → Technical roadmap and business scope
├── PODIUM_CONTEXTO_PROYECTO.md           → Full business context, content split rules, workflow
│
├── Prompts/
│   └── PROMPT-MAESTRO-PODIUM-v2.2.md    → MASTER SYSTEM PROMPT (core engine, 414 lines)
│
├── output/                                → Analisis and prediction json files generated
├── Pronosticos/                           → Automated JSON outputs containing EV mathematical calculations from Python model engine. 
├── Pruebas Tarjetas/                      → (LEGACY) Old HTML cards
├── templates/                             → (LEGACY) HTML files (No longer actively populated by LLM)
│
├── database/
│   ├── schema.sql                        → PostgreSQL table definition (122 lines)
│   ├── queries/tasa-acierto.sql          → 6 accuracy-tracking queries (102 lines)
│   └── migrations/                       → Empty (no version-controlled migrations yet)
│
├── portfolio/
│   ├── tarjetas/                         → Empty (future: best demo cards for investors)
│   └── resultados/                       → Empty (future: post-match result screenshots)
│
├── dashboard/
│   └── README.md                         → Placeholder (dashboard deferred to Phase 2)
│
├── docs/                                  → Empty
├── output/                                → Empty (intended for production cards)
│
└── .claude/
    └── settings.local.json               → MCP permissions, pre-approved WebFetch domains
```

### Role Summary

| Component | Role |
|---|---|
| `CLAUDE.md` | Auto-loaded project config; sets data order, EV rules, hard constraints |
| `PROMPT-MAESTRO-PODIUM-v2.2.md` | LLM Inference constraint for Data-Analysis mapping |
| `data_fetcher.py` | Data fetching Engine |
| `model_engine.py` | Python Script processing mathematical structures based on Odds and Data |
| `Pronosticos/` | Current output location for Python models. |
| `database/schema.sql` | Defines the `public.partidos` table in Supabase PostgreSQL |
| `database/queries/` | Analysis queries for prediction accuracy tracking and investor reporting |
| `settings.local.json` | Controls which MCP tools and web domains Claude can access |

---

## 2. DATA PIPELINE

There are **no scripts**. All data collection is performed by Claude at generation time, following a strict priority sequence defined in the master prompt.

### Data Sources & Sequence

```
Priority  Source                  Tool                    Cost        Use Case
────────  ──────────────────────  ──────────────────────  ──────────  ────────────────────────────────────
1         SportRadar              fetch_sports_data (MCP)  Free        Standings, scores, fixtures
2         Web search              web_search (MCP)         Free        Injuries, news, odds, BTTS, corners
3         The Odds API            WebFetch / HTTP GET      3 credits   Multi-bookmaker structured odds
4         RapidAPI                WebFetch / HTTP GET      4–5 calls   H2H history, xG, detailed injuries
```

### The Odds API Call Pattern

```
Step A (free):   GET /v4/sports/{sport_key}/events          → verify event exists
Step B (paid):   GET /v4/sports/{sport_key}/events/{id}/odds?markets=h2h,totals,spreads&regions=eu&oddsFormat=decimal
```
Key: `TU_CLAVE_AQUI` | Budget: ~3 credits/card | Header `x-requests-remaining` checked after each call.

### Web Search Queries (executed every card generation)

```
"[Local] vs [Visitante] team news injuries [month] [year]"
"[Local] vs [Visitante] odds [month] [year]"
"[Local] vs [Visitante] prediction probability [month] [year]"
```
Priority sources: Sports Mole, BBC Sport, Last Word On Football, Oddschecker, OddsPortal.

### Where Data Handling Lives

| Task | Where |
|---|---|
| Data fetching | `data_fetcher.py` Python Script |
| Math Engine | `model_engine.py` Python Script |
| Data Analytics | LLM (Prompt Maestro) processing `model_engine.py` json and constructing `InsightsPayload` |
| Data parsing | Inside Claude's context using Prompt Maestro |
| Data storage | Supabase `public.partidos` via INSERT after generation |
| Data retrieval | `tasa-acierto.sql` queries run manually by operator |

---

## 3. STATISTICAL CALCULATIONS

**All calculations happen inside the LLM (Claude), at prompt time.** There are no external scripts, no Python, no JavaScript that performs math.

### xG

- Source: fetched from RapidAPI (advanced stats endpoint) or web_search
- Processing: Claude reads the raw xG values and uses them as reasons in the +EV block
- No independent calculation — Claude uses the figure as-is from the source

### Probability Estimates (1X2)

- Source: aggregated from web_search results (Dimers, Sports Mole, forebet, etc.) and/or The Odds API implied probabilities
- Processing: Claude synthesizes multiple source probabilities into a single estimate
- Location: Entirely inside LLM inference; no formula is applied outside the prompt

### EV (Expected Value) — VIP only

Defined in both `CLAUDE.md` and `PROMPT-MAESTRO-PODIUM-v2.2.md`:

```
Prob. implícita = 1 / cuota_decimal × 100
EV% = (Prob_real% − Prob_implícita%) / Prob_implícita% × 100
```

**Fair value (when Pinnacle available):**
```
Prob_implícita_raw = 1 / cuota_Pinnacle
Suma_raws = Prob_local_raw + Prob_empate_raw + Prob_visitante_raw
Prob_fair = Prob_implícita_raw / Suma_raws × 100
```

- Markets evaluated: 1X2, Over/Under 2.5, Over/Under 3.5, BTTS, Asian Handicap, Corners O/U, Double Chance
- Threshold: EV ≥ +3% to recommend; otherwise outputs `"DATOS INSUFICIENTES PARA UNA RECOMENDACIÓN SÓLIDA"`
- Location: **LLM prompt only** — formula is stated in the prompt, Claude performs the arithmetic

### BTTS (Both Teams To Score)

- Source: web_search (footystats.org, sofascore.com, etc.)
- Calculation: Claude reports raw percentages found in search results (no derivation)
- Required: Every VIP card

### Corners

- Source: web_search (average corners by team from stats sites)
- Calculation: Claude reports averages and derives an O/U recommendation from them
- Required: Every VIP card

### Calculation Location Summary

| Metric | Script | LLM Prompt | Notes |
|---|---|---|---|
| 1X2 Probabilities | ✗ | ✓ | Aggregated from multiple sources in context |
| EV% | ✗ | ✓ | Formula defined in prompt, computed by LLM |
| BTTS % | ✗ | ✓ | Raw values from search; no derivation |
| Corners avg | ✗ | ✓ | Raw values from search; no derivation |
| xG | ✗ | ✓ | Passed through from RapidAPI, not computed |
| Implied probability | ✗ | ✓ | `1/odd × 100`, computed by LLM |
| Fair value (Pinnacle) | ✗ | ✓ | Vig removal, computed by LLM |

---

## 4. LLM USAGE

Claude is the **only** processing engine. There is no preprocessing, no microservices, no scheduled jobs. Every generation is a single Claude conversation.

### LLM Touchpoints

#### 4.1 Data Collection Orchestration
- **File:** `PROMPT-MAESTRO-PODIUM-v2.2.md` → PASO 1
- **Purpose:** Claude decides which APIs to call, in what order, and assembles raw data into its context
- **Prompt structure:**
  - 5 required web searches with exact query strings
  - 2-step Odds API call (events check → odds fetch)
  - RapidAPI calls for H2H, injuries, xG
  - Explicit fallback: write `"No disponible"` for missing data

#### 4.2 Probability Synthesis
- **File:** `PROMPT-MAESTRO-PODIUM-v2.2.md` → PASO 1 + PASO 2
- **Purpose:** Claude reads multiple conflicting probability estimates from different sources and synthesizes a single probability for each outcome
- **Prompt structure:** Implicit — no explicit formula, relies on LLM judgment to average/weight sources

#### 4.3 EV Calculation
- **File:** `PROMPT-MAESTRO-PODIUM-v2.2.md` → PASO 2
- **Purpose:** Apply the EV formula to all 7 markets and select the best one
- **Prompt structure:** Formula spelled out in prose; Claude performs arithmetic and selects market with highest EV ≥ +3%

#### 4.4 HTML Generation
- **File:** `PROMPT-MAESTRO-PODIUM-v2.2.md` → PASO 3
- **Purpose:** Generate the complete HTML card from scratch (or populate a template)
- **Prompt structure:** Full design spec (1080px, dark theme, inline CSS, forbidden elements, watermark CSS, mandatory blocks) — Claude writes the entire HTML in its response

#### 4.5 Supabase INSERT Construction
- **File:** `PROMPT-MAESTRO-PODIUM-v2.2.md` → PASO 4
- **Purpose:** Construct the exact SQL INSERT statement with all extracted values
- **Prompt structure:** Full INSERT template with column list; Claude fills in values from the generated card

#### 4.6 Delivery Summary
- **File:** `PROMPT-MAESTRO-PODIUM-v2.2.md` → PASO 5
- **Purpose:** Compose delivery message with API consumption report
- **Prompt structure:** Order: data summary → API credits used → HTML file(s) → Supabase confirmation

### Token Load Per Generation

Each VIP card generation requires Claude to hold in context simultaneously:
- The full master prompt (~414 lines / ~6,000 tokens)
- SportRadar data (standings, scores)
- 5+ web search result pages
- The Odds API JSON response
- RapidAPI JSON responses (multiple calls)
- The EV calculation working
- The complete 700-line HTML output

**Estimated tokens per VIP card:** 15,000–35,000 tokens depending on search result verbosity.

---

## 5. PIPELINE ARCHITECTURE (DATA-FIRST)

```
[PASO 1] DATA COLLECTION
│
└─ data_fetcher.py (Automated)
     ├─ SportRadar (standings, scores)
     ├─ The Odds API (structured odds)
     └─ RapidAPI (H2H, xG, detailed injuries)
         │
         ▼
[PASO 2] EV CALCULATION AND MARKET FILTERING
│
└─ model_engine.py (Automated)
     ├─ Synthesize 1X2 probabilities via Poisson vs Odds.
     ├─ Filter all markets with EV ≥ 0%
     └─ Export TOP 3 markets to Pronosticos/[MATCH].json
         │
         ▼
[PASO 3] NARRATIVE INSIGHTS GENERATION (LLM - Claude)
│
└─ Prompt Maestro
     ├─ Read Python output json variables.
     ├─ Inject human-like context, reasoning, and real world variables (Injuries context vs Odds context)
     └─ Return strict 'InsightsPayload' JSON.
         │
         ▼
[PASO 4] DATABASE REGISTRATION AND EXPORT
│
└─ Subabase / Dashboard
     ├─ Inject Mathematical models + LLM Insights into public.partidos
     └─ Display on Vue / React Web Frontend Panel.
```

---

## 6. HTML GENERATION (DEPRECATED)

The legacy architecture required Claude to generate 1080px HTML files directly within the LLM inference. This has been deprecated in favor of JSON-only payloads generated via Data Flow and Mathematical Engine (`model_engine.py`) and subsequent LLM reasoning. Future User Interface renderings belong strictly to the UI level (Vue/React Dashboards).

---

## 7. TOKEN USAGE HOTSPOTS

Ranked by token impact:

### Hotspot 1 — HTML Generation (~8,000–15,000 tokens)
**Why:** Claude writes 600–900 lines of HTML + inline CSS from scratch every card. The VIP template alone is 37KB. This is the single largest token consumer in the output.

### Hotspot 2 — Web Search Results (~5,000–12,000 tokens)
**Why:** 5 mandatory web searches return full page content. Sports news pages are verbose. All of this is passed into Claude's context to be read, synthesized, and then discarded after the card is generated. No caching layer exists.

### Hotspot 3 — Master Prompt (~6,000 tokens)
**Why:** `PROMPT-MAESTRO-PODIUM-v2.2.md` is 414 lines of dense instructions. This is loaded into context on every card generation regardless of card type (VIP or FREE). Many VIP-specific sections are read even when generating FREE cards.

### Hotspot 4 — API JSON Responses (~2,000–4,000 tokens)
**Why:** The Odds API returns multi-bookmaker JSON across 3 markets. RapidAPI returns multiple structured payloads (H2H, injuries, stats). These are passed into context verbatim.

### Hotspot 5 — EV Calculation Chain (~1,000–2,000 tokens)
**Why:** Claude evaluates 7 markets, computing EV for each, and narrates the reasoning. This is verbose by design to ensure accuracy, but all intermediate reasoning stays in the output.

### Hotspot 6 — Supabase INSERT Construction (~500 tokens)
**Why:** The full INSERT statement template is re-read and re-populated every generation.

### Token Budget Estimate per VIP Card

| Component | Estimated Tokens |
|---|---|
| Master prompt (input) | ~6,000 |
| Data fetching context (input) | ~8,000–18,000 |
| EV calculation reasoning (output) | ~1,000–2,000 |
| HTML generation (output) | ~8,000–15,000 |
| SQL + delivery summary (output) | ~500–800 |
| **Total per card** | **~23,500–41,800 tokens** |

---

## 8. IMPROVEMENT OPPORTUNITIES

### 8.1 Move HTML Rendering Out of LLM — Highest Impact

**Current:** Claude writes 600–900 lines of HTML from scratch on every card.
**Problem:** This is the single largest token consumer and source of inconsistency.
**Solution:** Build a real template renderer.

```
Option A: Node.js + Handlebars/Mustache
  - Input: JSON data object from Claude
  - Output: HTML file via template render
  - Savings: ~8,000–15,000 output tokens per card

Option B: Python + Jinja2
  - Same concept, simpler dependency tree
  - Claude outputs a structured JSON payload only
  - A script renders the HTML from the template

Option C: Inline JS in HTML (minimal)
  - Template with <script> that reads a data JSON file
  - Claude writes ONLY the JSON; browser renders the HTML
```

**Implementation path:**
1. Convert `VIP-PNG-template.html` into a Handlebars/Jinja2 template with `{{variable}}` slots
2. Define a JSON schema for card data (`card-schema.json`)
3. Claude outputs only the JSON payload (~800–1,200 tokens)
4. Script renders HTML from template + JSON

### 8.2 Move EV Calculations to a Script — Medium Impact

**Current:** Claude computes EV%, implied probability, and vig removal in prose inside the LLM.
**Problem:** Arithmetic errors possible; verbose reasoning consumes tokens.
**Solution:** A small Python/JS function handles all math.

```python
def calculate_ev(prob_real: float, cuota: float) -> float:
    prob_implicita = (1 / cuota) * 100
    return (prob_real - prob_implicita) / prob_implicita * 100

def remove_vig(odds: list[float]) -> list[float]:
    raws = [1/o for o in odds]
    total = sum(raws)
    return [r / total for r in raws]
```

Claude provides the raw odds and probability estimates; the script computes EV and returns only the result. This eliminates 500–1,000 tokens of LLM arithmetic per card.

### 8.3 Split the Master Prompt by Card Type — Medium Impact

**Current:** One 414-line prompt is loaded for every card type (VIP or FREE).
**Problem:** FREE cards load all VIP-specific instructions (EV, BTTS, corners, watermark) they will never use.
**Solution:** Two smaller prompts.

```
PROMPT-FREE-v1.md    (~150 lines) → only FREE-specific instructions
PROMPT-VIP-v1.md     (~280 lines) → only VIP-specific instructions
PROMPT-SHARED-v1.md  (~80 lines)  → data collection order (shared base)
```

Estimated savings: ~1,500–3,000 input tokens per FREE card generation.

### 8.4 Cache Web Search Results — Medium Impact

**Current:** Every card generation runs 5 fresh web searches, even if the same match was researched minutes ago.
**Problem:** Redundant token consumption; same injury reports re-read multiple times.
**Solution:** Save web search output to a local file (`search-cache/{match-id}.json`) and skip re-fetching if cache is less than N hours old.

### 8.5 Preprocess Odds API JSON Before Injecting to Context — Low-Medium Impact

**Current:** Full multi-bookmaker JSON (often 3,000–5,000 tokens) is passed raw into Claude's context.
**Problem:** Claude must scan through irrelevant bookmakers to find the relevant odds.
**Solution:** A lightweight preprocessing script extracts only the needed fields before the data reaches Claude.

```python
def extract_odds(raw_json, bookmakers=["pinnacle", "bet365", "unibet"]):
    return {
        "h2h": {bk: ... for bk in bookmakers},
        "totals": {bk: ... for bk in bookmakers},
        "spreads": {bk: ... for bk in bookmakers}
    }
```

Estimated reduction: 1,500–3,000 input tokens per VIP card.

### 8.6 Structured Data Schema for Claude Output

**Current:** Claude produces the HTML card + SQL INSERT + delivery summary in one unstructured response.
**Solution:** Define a strict JSON output schema that Claude populates. Downstream scripts handle rendering and SQL construction.

```json
{
  "match": { "local": "...", "visitante": "...", "liga": "...", "fecha": "..." },
  "probabilities": { "local": 45.2, "empate": 28.1, "visitante": 26.7 },
  "ev": { "market": "Over 2.5", "odds": 1.85, "ev_pct": 4.2, "reasons": [...] },
  "btts": { "pct_home": 62, "pct_away": 55, "combined": 58, "odds_yes": 1.72 },
  "corners": { "avg_home": 5.8, "avg_away": 4.9, "line": 10.5, "odds_over": 1.90 },
  "injuries": [{ "team": "local", "player": "...", "severity": "red", "detail": "..." }],
  "h2h": [...]
}
```

This separates concerns: Claude is responsible for data synthesis and analysis; scripts are responsible for rendering.

### 8.7 Add a Database-Backed Match Cache

**Current:** Each card generation starts with zero knowledge of previously generated matches.
**Solution:** Query Supabase before starting data collection. If the match already exists in `partidos`, skip re-fetching and only run new queries.

### 8.8 Centralize API Key Management

**Current:** The Odds API key (`TU_CLAVE_AQUI`) is hardcoded in `CLAUDE.md`, `PROMPT-MAESTRO-PODIUM-v2.2.md`, and project context documents.
**Risk:** Exposed in all documentation files in plaintext.
**Solution:** Move to an environment variable or a `.env` file excluded from version control. Reference it as `$ODDS_API_KEY` in the prompt.

### 8.9 Implement a Pre-Generation Checklist Script

**Current:** Claude decides whether to call The Odds API based on reading the prompt instructions.
**Problem:** Credits are consumed even when the event doesn't exist or the match is outside the API's coverage.
**Solution:** A lightweight script checks `/events` first and returns a boolean before the full generation starts — keeping this logic outside the LLM.

### Improvement Priority Matrix

| Improvement | Token Savings | Effort | Priority |
|---|---|---|---|
| 8.1 Template renderer (remove HTML from LLM) | ~8,000–15,000/card | Medium | **HIGH** |
| 8.3 Split prompt by card type | ~1,500–3,000/FREE card | Low | **HIGH** |
| 8.2 Move EV math to script | ~500–1,000/card | Low | **MEDIUM** |
| 8.5 Preprocess Odds API JSON | ~1,500–3,000/VIP card | Low | **MEDIUM** |
| 8.4 Cache web search results | ~5,000–10,000 (on repeat) | Medium | **MEDIUM** |
| 8.6 Structured JSON output schema | Architectural | High | **MEDIUM** |
| 8.8 Centralize API key management | Security (not tokens) | Low | **HIGH** |
| 8.7 Database-backed match cache | ~15,000+ on repeats | Medium | **LOW** |
| 8.9 Pre-generation checklist script | Prevents wasted runs | Low | **MEDIUM** |

---

## APPENDIX: HARD CONSTRAINTS REFERENCE

| Rule | Source |
|---|---|
| Odds format: decimal ONLY | CLAUDE.md + PROMPT |
| No source names in HTML | CLAUDE.md + PROMPT |
| No predicted lineups | CLAUDE.md + PROMPT |
| No invented data | CLAUDE.md + PROMPT |
| BTTS + Corners: mandatory in every VIP | CLAUDE.md + PROMPT |
| EV threshold: ≥ +3% | CLAUDE.md + PROMPT |
| Watermark: VIP only, never FREE | CLAUDE.md + PROMPT |
| Always report API consumption | CLAUDE.md + PROMPT |
| Output path: `Pruebas Tarjetas/` | CLAUDE.md |
| Naming: `[LOCAL]-[VISIT]-VIP.html` | CLAUDE.md |

---

*End of Report — Podium VIP Cards Generator v2.2*
