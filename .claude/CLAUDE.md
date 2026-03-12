# CLAUDE.md — Podium 360 v1.5 (ROI Auto-Calificador)

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
         → Archiva partidos finalizados en historical_results (ANTES del purge)
         → Lee daily_report, llama a Gemini 2.5 Flash (Triple Ángulo)
         → Sube datos a Supabase (daily_board + vip_signals)

5. python result_updater.py                                         ← NUEVO v1.5
         → Consulta historical_results (solo status_win_loss='pending')
         → Obtiene scores de Football-Data.org (caché en memoria por fecha)
         → Evalúa el pick de mayor EV y actualiza: actual_result + status_win_loss

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
- Construye **Match ID único:** `YYYYMMDD_Local_Visitante` (evita duplicados)
- Calcula `status`: `active` (partido futuro) o `finished` (partido pasado)
- Llama a **Gemini 2.5 Flash** → genera `angulo_matematico`, `angulo_tendencia`, `angulo_contexto`
- **`archive_finished_matches(url, key)`** (v1.4): antes del PURGE, consulta `daily_board` por `status=finished` y hace upsert en `historical_results`. No sobreescribe filas ya archivadas (preserva `actual_result` y `status_win_loss` si ya fueron cargados).
- **PURGE total** de `daily_board` + `vip_signals` → luego UPSERT con datos frescos
- **Tablas Supabase:** `daily_board` (jornada activa) + `vip_signals` (picks profundos) + `historical_results` (archivo ROI permanente)

### `result_updater.py` — ROI Auto-Calificador ✨ NUEVO v1.5
- **Propósito:** Cierra el loop de ROI calificando automáticamente los picks archivados en `historical_results`.
- **Query mínimo:** Solo lee `id, home_team, away_team, match_date, mercados_completos` donde `status_win_loss = 'pending'`. No lee filas ya calificadas.
- **Caché en memoria:** Agrupa llamadas a Football-Data por fecha. Si hay N partidos el mismo día, hace 1 sola llamada a la API (no N).
- **Selección del pick a evaluar** (prioridad descendente):
  1. Pick con `es_vip: true` de mayor `ev_pct`
  2. Pick con mayor `ev_pct` positivo
  3. Primer pick de la lista como fallback final
- **Mercados soportados para evaluación:**

  | Código | Lógica |
  |--------|--------|
  | `1x2_local` | Win si home > away |
  | `1x2_empate` | Win si home == away |
  | `1x2_visitante` | Win si away > home |
  | `over_2.5`, `over25`, `under_3.0` | Totales (ambas notaciones) |
  | `spread_local_N`, `spread_visitante_N` | Asian Handicap (push si línea exacta) |
  | `btts_yes`, `btts_no` | Ambos marcan |

- **Valores de salida:** `win`, `loss`, `push` (handicap 0.0 o total exacto), `pending` (sin tocar si partido no encontrado o no terminado).
- **Fuzzy matching:** Intenta match exacto con `normalize_team_name()`; si falla, intenta subcadena bidireccional.
- **PATCH quirúrgico:** Solo actualiza `actual_result` y `status_win_loss`. No toca `mercados_completos`, `ai_analysis` ni ninguna otra columna.
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

## Esquema de Supabase (v1.5)

| Tabla | Propósito | Acceso dashboard JS |
|-------|-----------|-------------------|
| `daily_board` | Jornada activa (se purga en cada sync) | ✅ anon read |
| `vip_signals` | Picks EV ≥ 5% de la jornada activa | ✅ anon read |
| `historical_results` | Archivo permanente de partidos finalizados + ROI | ❌ solo service_role |

### `historical_results` — columnas clave para ROI

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | TEXT PK | `YYYYMMDD_Local_Visitante` |
| `actual_result` | TEXT | Score final ej. `"2-1"`. Llenado por `result_updater.py` o manualmente. |
| `status_win_loss` | TEXT | `'win'` · `'loss'` · `'push'` · `'void'` · `'pending'` (default) |
| `archived_at` | TIMESTAMPTZ | Timestamp de archivado (seteado por `supabase_sync.py`) |
| `mercados_completos` | JSONB | Array de todos los mercados evaluados por el modelo (fuente de verdad para `result_updater`) |

**Para actualizar resultados manualmente (override):**
```sql
UPDATE historical_results
SET actual_result = '2-1', status_win_loss = 'win'
WHERE id = '2026-03-11_Arsenal_Chelsea';
```

---

## Problemas Conocidos

| Problema | Impacto | Solución |
|----------|---------|----------|
| `naming_errors.log` puede tener errores con equipos nuevos | Equipos sin cruzar entre APIs → fallback a nombre raw | Agregar alias a `MAESTRO_ALIASES` en `utils/naming.py` |
| Football-Data API no retorna partidos EL (posible tier) | `get_upcoming_el_matches()` devuelve `[]` silenciosamente | Usar `partidos_manuales.json` como fallback manual |
| `partidos_manuales.json` requiere mantenimiento manual | Si no se actualiza, el pipeline corre con datos de jornadas pasadas | Vaciar o actualizar el archivo antes de cada jornada nueva |
| `test_runner.py` solo escanea CL y EL | Otras ligas (LaLiga, BL, etc.) no se procesan automáticamente | Extender `get_upcoming_matches()` con nuevos competition codes |
| Inconsistencia de nomenclatura O/U en `model_engine.py` | `over25` emitido sin guion bajo ni decimal junto a `over_2.5` | `result_updater.py` ya lo maneja; pendiente normalizar en `model_engine.py` |
| `result_updater.py` no califica mercados Asian Handicap complejos (`void`) | Picks en mercados no soportados quedan `pending` indefinidamente | Implementar `void` para cancelaciones y lógica AH avanzada (ej: `-1`, `-2`) |
| `result_updater.py` depende de Football-Data para encontrar el partido | Si FD no tiene el partido en su base (ej: ligas menores) quedará `pending` | Integrar fuente de resultados alternativa (ej: API-Football) como fallback |
| `mercado` embedded en `angulo_matematico` de `vip_signals` | Parsing con regex en dashboard | Workaround funcional, baja prioridad |

---

## Subcarpetas de Contexto Adicional

- **`.claude/rules/`** → Convenciones de desarrollo y políticas
- **`.claude/workflows/`** → Flujos de datos detallados
- **`.claude/docs/`** → Algoritmos matemáticos (ver `hybrid_model.md`)
- **`.claude/agents/`** → Roles: `math_engineer.md`, `narrative_insights.md`
