# CLAUDE.md — Podium 360 v1.6 (ROI Pick-Level + UEL R16 Archivado)

Este es el documento maestro del repositorio. Léelo completo antes de cualquier acción.

---

## Misión del Proyecto

**Podium 360** es un SaaS de análisis de Valor Esperado (EV) en apuestas deportivas.
Utiliza modelos matemáticos propios (Poisson + Elo + xG) y narrativa generada por IA (Gemini 2.5 Flash) para auditar el mercado 1X2 de fútbol europeo.

---

## Estado Actual (12 de Marzo de 2026) — TODOS LOS MÓDULOS OPERATIVOS ✅

### Pipeline completo (en orden de ejecución):

```
1. python data_fetcher.py "Local" "Visitante" "Liga"
         → partido_data.json

2. python model_engine.py
         → Pronosticos/LOCAL_vs_VISITANTE_DD_MM_YY.json
         → Pronosticos/LOCAL_vs_VISITANTE_DD_MM_YY_ALERT.json  (si EV ≥ 5%)

3. python test_runner.py
         → Corre pipeline para partidos CL + EL (API) y manuales (partidos_manuales.json)
         → Genera database/daily_report_DD_MM_YY.json

4. python supabase_sync.py
         → Archiva picks VIP finalizados en historical_results (ANTES del purge)  ⚠️ ver nota v1.6
         → Lee daily_report, llama a Gemini 2.5 Flash (Triple Ángulo)
         → Sube datos a Supabase (daily_board + vip_signals)

5. python result_updater.py
         → Consulta historical_results (solo status_win_loss='pending')
         → Obtiene scores de Football-Data.org (caché en memoria por fecha)
         → Actualiza: actual_result + status_win_loss  ⚠️ ver nota v1.6

6. Abrir: landing page/dashboard.html  (conecta a Supabase vía JS)
```

---

## Arquitectura de Módulos

### `data_fetcher.py` — Ingesta de Datos
- **Fuentes:** ClubElo (Elo), Fotmob (xG season avg), Football-Data.org (fixtures/standings/forma), The Odds API (cuotas 1X2/OU/BTTS)
- **Caché local:** `database/api_cache.json` (TTL 24h, actualmente ~44MB)
- **Ligas soportadas:** Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Champions League, Eredivisie, Primeira Liga
- **Output:** `partido_data.json`

### `utils/naming.py` — FUENTE DE VERDAD DE NOMBRES ⚠️
- Diccionario `MAESTRO_ALIASES` (~70+ equipos): alias → nombre canónico
- `normalize_team_name()` → lookup O(1) por clave UPPERCASE
- `fuzzy_match()` → substring matching bidireccional entre APIs
- `log_naming_error()` → registra errores en `naming_errors.log`
- **CRÍTICO:** Todos los módulos (`data_fetcher`, `model_engine`, `supabase_sync`, `result_updater`) importan desde aquí. Si hay un nuevo equipo que no se cruza, agrégalo aquí.
- **Aliases añadidos en v1.3 (EL Round of 16):** Bologna, Real Betis, Stuttgart, Celta Vigo, Panathinaikos, Ferencvaros, Braga, Genk, Freiburg, Nottingham Forest, Midtjylland

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
- **⚠️ Inconsistencia de nomenclatura conocida:** algunos mercados O/U se emiten como `over25` (sin guion bajo ni decimal) en lugar de `over_2.5`. `result_updater.py` ya maneja ambas notaciones.

### `supabase_sync.py` — Backend + IA
- Lee `database/daily_report_DD_MM_YY.json`
- Filtra "partidos fantasma" (sin `hora_utc` ni `all_markets`)
- Construye **Match ID único:** `YYYYMMDD_Local_Visitante` (evita duplicados en `daily_board`)
- Calcula `status`: `active` (partido futuro) o `finished` (partido pasado)
- Llama a **Gemini 2.5 Flash** → genera `angulo_matematico`, `angulo_tendencia`, `angulo_contexto`
- **`archive_finished_matches(url, key)`**: antes del PURGE, consulta `daily_board` por `status=finished` y hace upsert en `historical_results`.
- **⚠️ PENDIENTE v1.6:** `archive_finished_matches()` aún genera IDs match-level (`YYYYMMDD_Local_Visitante`). Debe migrarse a IDs pick-level (`YYYYMMDD_Local_Visitante_mercado`) para alinearse con la nueva arquitectura de `historical_results`.
- **PURGE total** de `daily_board` + `vip_signals` → luego UPSERT con datos frescos
- **Tablas Supabase:** `daily_board` (jornada activa) + `vip_signals` (picks profundos) + `historical_results` (archivo ROI permanente)

### `result_updater.py` — ROI Auto-Calificador
- **Propósito:** Cierra el loop de ROI calificando automáticamente los picks archivados en `historical_results`.
- **Query mínimo:** Solo lee `id, home_team, away_team, match_date, mercados_completos` donde `status_win_loss = 'pending'`.
- **Caché en memoria:** Agrupa llamadas a Football-Data por fecha (1 llamada por día, no por partido).
- **⚠️ PENDIENTE v1.6:** `result_updater.py` fue diseñado para IDs match-level y selecciona el pick de mayor EV de `mercados_completos`. Con la nueva arquitectura pick-level, debe leer la columna `mercado` directamente del registro y evaluar ese mercado específico.
- **Mercados soportados para evaluación:**

  | Código | Lógica |
  |--------|--------|
  | `1x2_local` | Win si home > away |
  | `1x2_empate` | Win si home == away |
  | `1x2_visitante` | Win si away > home |
  | `over_2.5`, `over25`, `under_3.0` | Totales (ambas notaciones) |
  | `spread_local_N`, `spread_visitante_N` | Asian Handicap (push si línea exacta) |
  | `btts_yes`, `btts_no` | Ambos marcan |

- **Valores de salida:** `win`, `loss`, `push`, `pending` (sin tocar si partido no encontrado o no terminado).
- **PATCH quirúrgico:** Solo actualiza `actual_result` y `status_win_loss`.
- **Dependencias:** `SUPABASE_URL`, `SUPABASE_KEY`, `FOOTBALL_DATA_KEY` (del `.env`)

### `landing page/dashboard.html` — Frontend
- Stack: HTML5 + Tailwind CSS (CDN) + Vanilla JS + Supabase JS Client
- Dos tabs: **Jornada General** (todas las tarjetas) y **Pronósticos VIP** (picks con EV ≥ 5%)
- Cada tab tiene sub-secciones: **Activos** vs **Historial**
- Semaforización: 🔴 EV < 1% · 🟡 1–4.99% · 🟢 EV ≥ 5%
- Modal de detalle: Triple Ángulo + Value Matrix completa por partido
- Mercados humanizados: `1x2_local` → "Victoria Arsenal", etc.

### `test_runner.py` — Orquestador de Validación
- Niveles 1–5: smoke test, caché, EV trigger, tracker, generación de reporte diario
- Busca partidos de **Champions League** (`CL`) y **Europa League** (`EL`) vía Football-Data API
- **`load_manual_matches()`** → Lee `partidos_manuales.json` como fuente adicional/fallback
- **Deduplicación automática:** matches de API tienen prioridad; los manuales se agregan solo si no están ya en la respuesta de la API
- **`partidos_manuales.json`** → Archivo editable en raíz del proyecto. Formato: `[{"local": "X", "visitante": "Y", "liga": "Z"}]`
  - Úsalo cuando Football-Data no retorne partidos EL/CL (ej: tier API insuficiente, partidos con fecha incorrecta)
  - **Vaciar antes de cada jornada nueva** para evitar procesar partidos de jornadas pasadas

### `migrations/create_historical_results.sql` — DDL Supabase
- Script de creación de la tabla `historical_results` con todas sus columnas.
- Incluye `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` para migraciones incrementales.
- **Ya ejecutado** en producción (12-Mar-2026).

### `insert_historical_12_03_26.py` — Script de Archivado Manual (UEL R16)
- Script **one-shot** para archivar los 12 picks VIP de la jornada del 12-Mar-2026.
- **Ya ejecutado.** Sirve como plantilla para futuros archivados manuales de emergencia.

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

## Esquema de Supabase (v1.6)

| Tabla | Propósito | Acceso dashboard JS |
|-------|-----------|-------------------|
| `daily_board` | Jornada activa (se purga en cada sync) | ✅ anon read |
| `vip_signals` | Picks EV ≥ 5% de la jornada activa | ✅ anon read |
| `historical_results` | Archivo permanente de picks finalizados + ROI | ❌ solo service_role |

### `historical_results` — arquitectura pick-level (v1.6) ⚠️

**Cada fila representa UN pick VIP, no un partido.** El ID es el mismo que en `vip_signals`.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | TEXT PK | `YYYYMMDD_Local_Visitante_mercado` (ej: `2026-03-12_Stuttgart_Porto_1x2_visitante`) |
| `home_team` | TEXT | Equipo local |
| `away_team` | TEXT | Equipo visitante |
| `competition` | TEXT | Liga/torneo |
| `match_date` | DATE | Fecha del partido |
| `mercado` | TEXT | Mercado del pick (`1x2_local`, `over25`, etc.) |
| `cuota` | FLOAT | Cuota al momento del pick |
| `ev_pct` | FLOAT | EV% calculado por el modelo |
| `actual_result` | TEXT | Score final ej. `"2-1"`. Llenado por `result_updater.py` o manualmente. |
| `status_win_loss` | TEXT | `'win'` · `'loss'` · `'push'` · `'void'` · `'pending'` (default) |
| `mercados_completos` | JSONB | Array completo de mercados del partido (contexto) |
| `archived_at` | TIMESTAMPTZ | Timestamp de archivado |

**Para actualizar resultados manualmente (override):**
```sql
UPDATE historical_results
SET actual_result = '2-1', status_win_loss = 'win'
WHERE id = '2026-03-12_Stuttgart_Porto_1x2_visitante';
```

**Query ROI acumulado:**
```sql
SELECT
  COUNT(*) FILTER (WHERE status_win_loss = 'win')  AS wins,
  COUNT(*) FILTER (WHERE status_win_loss = 'loss') AS losses,
  SUM(CASE WHEN status_win_loss = 'win'  THEN cuota - 1
           WHEN status_win_loss = 'loss' THEN -1
           ELSE 0 END)                              AS profit_units
FROM historical_results
WHERE status_win_loss IN ('win', 'loss');
```

### Historial de jornadas archivadas

| Fecha | Competición | Picks | W | L | ROI |
|-------|-------------|------:|--:|--:|----:|
| 2026-03-12 | UEL R16 1ª ida | 12 | 3 | 9 | +33.75% |

---

## Problemas Conocidos

| Problema | Impacto | Solución |
|----------|---------|----------|
| `archive_finished_matches()` en `supabase_sync.py` genera IDs match-level | Desalineado con arquitectura pick-level de `historical_results` v1.6 | Refactorizar para iterar sobre `vip_signals` y generar IDs `YYYYMMDD_Local_Visitante_mercado` |
| `result_updater.py` selecciona el pick de mayor EV de `mercados_completos` | Con IDs pick-level, debe leer la columna `mercado` del registro directamente | Actualizar lógica de selección de mercado en `result_updater.py` |
| Football-Data API no retorna partidos EL/CL (tier insuficiente) | `result_updater.py` no puede calificar partidos EL automáticamente; requiere archivado manual | Integrar fuente alternativa (ej: API-Football) o upgrade de tier |
| `partidos_manuales.json` requiere mantenimiento manual | Si no se vacía, el pipeline corre con datos de jornadas pasadas | Vaciar o actualizar antes de cada jornada nueva |
| `test_runner.py` solo escanea CL y EL | Otras ligas (LaLiga, BL, etc.) no se procesan automáticamente | Extender `get_upcoming_matches()` con nuevos competition codes |
| Inconsistencia de nomenclatura O/U en `model_engine.py` | `over25` emitido sin guion bajo junto a `over_2.5` | `result_updater.py` ya lo maneja; pendiente normalizar en `model_engine.py` |
| `result_updater.py` no califica mercados Asian Handicap complejos | Picks AH complejos quedan `pending` indefinidamente | Implementar `void` y lógica AH avanzada (`-1`, `-2`) |
| `mercado` embedded en `angulo_matematico` de `vip_signals` | Parsing con regex en dashboard | Workaround funcional, baja prioridad |

---

## Subcarpetas de Contexto Adicional

- **`.claude/rules/`** → Convenciones de desarrollo y políticas
- **`.claude/workflows/`** → Flujos de datos detallados
- **`.claude/docs/`** → Algoritmos matemáticos (ver `hybrid_model.md`)
- **`.claude/agents/`** → Roles: `math_engineer.md`, `narrative_insights.md`
