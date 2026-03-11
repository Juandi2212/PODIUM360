# CLAUDE.md — Podium 360 v1.2 (Handover Ready)

Este es el documento maestro del repositorio. Léelo completo antes de cualquier acción.

---

## Misión del Proyecto

**Podium 360** es un SaaS de análisis de Valor Esperado (EV) en apuestas deportivas.
Utiliza modelos matemáticos propios (Poisson + Elo + xG) y narrativa generada por IA (Gemini 2.5 Flash) para auditar el mercado 1X2 de fútbol europeo.

---

## Estado Actual (11 de Marzo de 2026) — TODOS LOS MÓDULOS OPERATIVOS ✅

### Pipeline completo (en orden de ejecución):

```
1. python data_fetcher.py "Local" "Visitante" "Liga"
         → partido_data.json

2. python model_engine.py
         → Pronosticos/LOCAL_vs_VISITANTE_DD_MM_YY.json
         → Pronosticos/LOCAL_vs_VISITANTE_DD_MM_YY_ALERT.json  (si EV ≥ 5%)

3. python test_runner.py
         → Corre pipeline para TODOS los partidos CL del día
         → Genera database/daily_report_DD_MM_YY.json

4. python supabase_sync.py
         → Lee daily_report, llama a Gemini 2.5 Flash (Triple Ángulo)
         → Sube datos a Supabase (daily_board + vip_signals)

5. Abrir: landing page/dashboard.html  (conecta a Supabase vía JS)
```

---

## Arquitectura de Módulos

### `data_fetcher.py` — Ingesta de Datos
- **Fuentes:** ClubElo (Elo), Fotmob (xG season avg), Football-Data.org (fixtures/standings/forma), The Odds API (cuotas 1X2/OU/BTTS)
- **Caché local:** `database/api_cache.json` (TTL 24h, actualmente ~44MB)
- **Ligas soportadas:** Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Champions League, Eredivisie, Primeira Liga
- **Output:** `partido_data.json`

### `utils/naming.py` — FUENTE DE VERDAD DE NOMBRES ⚠️
- Diccionario `MAESTRO_ALIASES` (~60+ equipos): alias → nombre canónico
- `normalize_team_name()` → lookup O(1) por clave UPPERCASE
- `fuzzy_match()` → substring matching bidireccional entre APIs
- `log_naming_error()` → registra errores en `naming_errors.log`
- **CRÍTICO:** Todos los módulos (`data_fetcher`, `model_engine`, `supabase_sync`) importan desde aquí. Si hay un nuevo equipo que no se cruza, agrégalo aquí.

### `model_engine.py` — Motor Predictivo (Pasos A→H)
- **A:** Elo + ventaja local (+60)
- **B:** xG rolling con decay 0.85 (N=8 partidos)
- **C:** Lambdas Poisson normalizados con corrección Elo
- **D:** Matriz Poisson 7×7
- **E:** Probabilidades 1X2, Over/Under (0.5→6.5), Asian Handicap (-3.5→+3.5)
- **F:** Blend modelo(45%) + Pinnacle(55%) para 1X2
- **G:** EV% por mercado
- **H:** Regla de Oro: EV ≥ 3%, Consenso ≥ 2/3, Divergencia ≤ 8pp → VIP si EV ≥ 5%
- **Value Matrix:** Exporta el 100% de mercados (positivos y negativos)
- **Output:** `model_output.json` + archivos en `Pronosticos/`

### `supabase_sync.py` — Backend + IA
- Lee `database/daily_report_DD_MM_YY.json`
- Filtra "partidos fantasma" (sin `hora_utc` ni `all_markets`)
- Construye **Match ID único:** `YYYYMMDD_Local_Visitante` (evita duplicados)
- Calcula `status`: `active` (partido futuro) o `finished` (partido pasado)
- Llama a **Gemini 2.5 Flash** → genera `angulo_matematico`, `angulo_tendencia`, `angulo_contexto`
- **PURGE total** antes de cada sync → luego UPSERT en Supabase
- **Tablas Supabase:** `daily_board` (radiografía general) + `vip_signals` (picks profundos)

### `landing page/dashboard.html` — Frontend
- Stack: HTML5 + Tailwind CSS (CDN) + Vanilla JS + Supabase JS Client
- Dos tabs: **Jornada General** (todas las tarjetas) y **Pronósticos VIP** (picks con EV ≥ 5%)
- Cada tab tiene sub-secciones: **Activos** vs **Historial**
- Semaforización: 🔴 EV < 1% · 🟡 1–4.99% · 🟢 EV ≥ 5%
- Modal de detalle: Triple Ángulo + Value Matrix completa por partido
- Mercados humanizados: `1x2_local` → "Victoria Arsenal", etc.

### `test_runner.py` — Orquestador de Validación
- Niveles 1–5: smoke test, caché, EV trigger, tracker, generación de reporte diario
- ⚠️ Solo busca partidos de **Champions League** por defecto

---

## Variables de Entorno (`.env`)

```
SUPABASE_URL=https://ssvnixnqczpvpiomgrje.supabase.co
SUPABASE_KEY=<service_role_key>
GOOGLE_API_KEY=<gemini_2.5_flash>
ODDS_API_KEY=<the-odds-api.com>
FOOTBALL_DATA_KEY=<football-data.org>
```

---

## Problemas Conocidos

| Problema | Impacto | Solución |
|----------|---------|----------|
| `naming_errors.log` tiene errores | Equipos sin cruzar entre APIs | Agregar alias a `MAESTRO_ALIASES` en `utils/naming.py` |
| `test_runner.py` solo escanea CL | Otras ligas no se procesan automáticamente | Extender `get_upcoming_cl_matches()` |
| PURGE total en cada sync | No hay historial acumulativo en Supabase | Por diseño actual; aceptable para v1.2 |
| `mercado` embedded en `angulo_matematico` | Parsing con regex en dashboard | Workaround funcional, baja prioridad |

---

## Subcarpetas de Contexto Adicional

- **`.claude/rules/`** → Convenciones de desarrollo y políticas
- **`.claude/workflows/`** → Flujos de datos detallados
- **`.claude/docs/`** → Algoritmos matemáticos (ver `hybrid_model.md`)
- **`.claude/agents/`** → Roles: `math_engineer.md`, `narrative_insights.md`
