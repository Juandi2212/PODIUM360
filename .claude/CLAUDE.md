# CLAUDE.md — Valior v2.0 (SaaS Vision + Freemium Architecture)

Este es el documento maestro del repositorio. Léelo completo antes de cualquier acción.

---

## Misión del Proyecto

**Valior** es un SaaS de análisis de Valor Esperado (EV) en apuestas deportivas.
Utiliza modelos matemáticos propios (Poisson + Elo + xG) y narrativa generada por IA (Gemini 2.5 Flash) para auditar mercados de fútbol europeo — mostrando al usuario si las cuotas de una casa de apuestas están balanceadas o no respecto a la probabilidad real calculada por el modelo.

**Propósito central:** No es un generador de señales ciegas. Es una herramienta de auditoría de mercado que empodera al usuario con metodología matemática transparente. Los "Pronósticos VIP" son simplemente los mercados con EV más alto del día — curados automáticamente por el modelo, no por criterio editorial.

**Diferencial competitivo:** A diferencia de los canales de Telegram que venden pronósticos sin metodología verificable, Valior muestra el trabajo matemático detrás de cada análisis y mantiene un historial público de ROI verificable.

---

## Modelo de Negocio — Freemium

### Plan Gratuito
- Acceso a 2–3 partidos por día (los de menor EV del `daily_board`)
- Solo mercado 1X2
- Sin narrativa IA (solo números crudos)
- Sin acceso a `vip_signals`
- Sin historial de ROI

### Plan Pago (~$5–8 USD/mes, precio Latam)
- Todos los partidos del día (todas las ligas disponibles)
- Todos los mercados: 1X2, Over/Under, BTTS, Double Chance, Asian Handicap
- Narrativa Triple Ángulo generada por Gemini 2.5 Flash
- Pronósticos VIP del día (mercados con EV ≥ 5%)
- Historial completo con ROI verificable

### Estrategia de adquisición
- Canal TikTok (~15K seguidores): contenido educativo sobre EV y value betting
- Canales Telegram (~15K seguidores): preview diario con 1 análisis gratuito
- Conversión orgánica hacia plan pago desde ambos canales
- **Regla:** No invertir en APIs de pago hasta tener tracción real de usuarios.
  Las fuentes actuales (gratuitas) son suficientes para lanzar y validar.

---

## Hoja de Ruta SaaS

### Fase 1 — MVP Web (COMPLETADO ✅)
- [x] Arquitectura Frontend Vanilla JS (sin frameworks complejos) + Supabase Auth
- [x] Landing page pública (`web/index.html`) con llamada a la acción
- [x] Portal de Login/Registro (`web/auth.html`) con Auth Guard
- [x] Dashboard SaaS Privado (`web/dashboard.html`)
- [x] Tablas de análisis `daily_board` y `vip_signals` cargando en Real-Time en el DOM
- [x] Deploy en Vercel exitoso en `valior.vercel.app`
- [x] Landing page migrada a React/Vite/Tailwind v4 (23-Mar-2026)
- [x] Auth page rediseñada con dark theme split-screen (24-Mar-2026)
- [ ] **NEXT →** Rediseñar dashboard.html (generar con Google AI Studio, integrar lógica Supabase existente)
- [ ] **NEXT →** Integración Stripe: checkout, webhooks, tabla `user_profiles`, condicional freemium/pago

### Fase 2 — Credibilidad
- [ ] Tab "Historial" público con ROI acumulado (historical_results)
- [ ] Badge de track record en landing page
- [ ] Automatización del pipeline en servidor (no correr desde máquina local)

### Fase 3 — Expansión de mercados (cuando haya tracción)
- [ ] Integrar API-Football ($9.99/mes) para corners, tarjetas, stats avanzadas
- [ ] Ampliar modelo a mercados de corners y tarjetas
- [ ] Considerar app móvil (React Native)

---

## Stack Técnico

```
Frontend Landing → React 19, Vite 6, Tailwind CSS v4 (Carpeta `frontend/`) (operativo ✅)
Frontend Auth/Dash → HTML5, Vanilla JS, Tailwind CSS (Carpeta `web/` → copiado a `frontend/public/`) (operativo ✅)
Backend/DB       → Supabase (operativo ✅)
Auth             → Supabase Auth (operativo ✅)
Pagos            → Stripe — por integrar (Próximo hito)
Deploy           → Vercel (conectado ✅)
Pipeline         → Python local (operativo ✅) — migrar a servidor en Fase 2
IA narrativa     → Gemini 2.5 Flash (operativo ✅)
```

---

## Estado Actual (18 de Marzo de 2026) — TODOS LOS MÓDULOS OPERATIVOS ✅

### Última jornada operativa:
- **Migración Frontend Completada (24-Mar-2026):**
  - Landing page migrada de HTML estático a React 19/Vite 6/Tailwind v4 (carpeta `frontend/`). Diseño generado con Google AI Studio.
  - Auth page (`auth.html`) rediseñada completamente: split-screen dark theme, grid de fondo, glow verde, testimonial. Lógica Supabase Auth intacta.
  - `vercel.json` actualizado: build apunta a `frontend/dist`, `auth.html` y `dashboard.html` servidos desde `frontend/public/`.
  - Carpeta `web/` preservada como fallback. Ningún archivo Python modificado.
  - Tag de backup: `backup-pre-react-landing` (commit `c51a68f`). Copia física en `Desktop\VALIOR-BACKUP-23MAR`.
- **PENDIENTE — Dashboard (`dashboard.html`):** Necesita rediseño visual para alinear con el nuevo look (dark theme, `#00ff66`, tipografía mono). La lógica de Supabase (renderBoardCard, renderVipCard, modales, etc.) debe mantenerse intacta. Generar diseño con Google AI Studio y luego integrar.
- **PENDIENTE — Integración Stripe:** Implementar checkout y webhooks para el plan PRO ($9.99/mes). Requiere crear `user_profiles` en Supabase, agregar variables de entorno de Stripe, y condicionar el acceso freemium/pago en el dashboard.
- **Deploy SaaS Completado (23-Mar-2026):** Se desplegó exitosamente el Frontend en Vercel (`valior.vercel.app`). El proyecto ya no depende de scripts locales para ver la UI. La Landing Page es pública, y el Dashboard está protegido por Supabase Auth.
- **Configuración de Seguridad en Vercel:** Se implementó `vercel.json` con cabeceras `Cache-Control`, `X-Frame-Options` (DENY), y `X-Content-Type-Options` (nosniff) para prevención de ataques.
- **Schema maestro ejecutado:** `migrations/schema_maestro.sql` sincroniza las 3 tablas de Supabase. Políticas RLS de lectura anónima activadas temporalmente, pendientes de restricción a `authenticated`.
- **ROI reconciliado (18-Mar-2026):** 26 picks totales, 10W/16L, +18.48 unidades, **ROI global +71.1%**
- **model_engine.py v2.0:** Forma reciente + H2H integrados al modelo matemático (Paso C.5)
- DC markets activos; arquitectura pick-level completamente alineada
- Nomenclatura de mercados de totales completamente normalizada (v1.9)
- **dashboard_live.html v2.1:** Rediseño completo de cards (renderBoardCard) + VIP agrupadas por partido (17-Mar-2026)
- **Auto-detección de ligas domésticas (18-Mar-2026):** `test_runner.py` ahora consulta PL, SA, PD, BL1, FL1 vía Football-Data API antes de correr el pipeline. Los partidos encontrados se escriben automáticamente en `partidos_manuales.json` (sobreescribe la jornada anterior). Respeta el rate limit con delays de 7s entre llamadas. Ya no se requiere entrada manual para ligas domésticas.
- **Scripts maestros creados (18-Mar-2026):** `master_morning.py` (test_runner → supabase_sync) y `master_night.py` (result_updater) como puntos únicos de entrada para la operación diaria.
- **Gap de calificación nocturna eliminado (18-Mar-2026):** `result_updater.py` ahora califica picks pendientes en `vip_signals` (picks del día actual) además de `historical_results` (picks archivados). Columnas `status_win_loss` y `actual_result` agregadas a `vip_signals` via migration. Los 7 picks VIP de la jornada UCL 18/03 fueron calificados la misma noche.

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
         → Archiva picks VIP finalizados de vip_signals en historical_results (ANTES del purge)
         → Lee daily_report, llama a Gemini 2.5 Flash (Triple Ángulo)
         → time.sleep(12) entre cada llamada a Gemini (respeta rate limit free tier)
         → Sube datos a Supabase (daily_board + vip_signals)
   [NOTA: partidos_manuales.json se vacía automáticamente al final de cada ejecución
    de test_runner.py vía fetch_and_save_domestic_matches() — no requiere limpieza manual]

5. python result_updater.py
         → Consulta historical_results (solo status_win_loss='pending')
         → Lee columna mercado directamente (arquitectura pick-level)
         → Obtiene scores de API-Football (caché en memoria por fecha)
         → Actualiza: actual_result + status_win_loss

6. El Frontend (alojado en Vercel) lee las tablas automáticamente y el usuario final puede consumirlo desde `valior.vercel.app`.
```

---

## Arquitectura de Módulos

### `data_fetcher.py` — Ingesta de Datos
- **Fuentes:** ClubElo (Elo), Fotmob (xG season avg), Football-Data.org (fixtures/standings/forma), The Odds API (cuotas 1X2/OU/BTTS)
- **Caché local:** `database/api_cache.json` (TTL 24h, actualmente ~44MB)
- **Ligas soportadas:** Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Champions League, Eredivisie, Primeira Liga
- **Captura de totales (v1.9):** Todas las líneas disponibles de la API se capturan sin filtro en `mejores_cuotas_extra.totals`. Clave generada: `f"{name}_{pt}".lower()` → `over_1.5`, `under_1.5`, `over_2.5`, `under_2.5`, `over_3.5`, etc.
- **`mejor_cuota["over_2.5"]`** se mantiene en sync con `mejores_cuotas_extra.totals["over_2.5"]` (ambos establecidos desde la API; la clave `over25` fue eliminada en v1.9).
- **Output:** `partido_data.json`

### `utils/naming.py` — FUENTE DE VERDAD DE NOMBRES ⚠️
- Diccionario `MAESTRO_ALIASES` (~70+ equipos): alias → nombre canónico
- `normalize_team_name()` → lookup O(1) por clave UPPERCASE
- `fuzzy_match()` → substring matching bidireccional entre APIs
- `log_naming_error()` → registra errores en `naming_errors.log`
- **CRÍTICO:** Todos los módulos (`data_fetcher`, `model_engine`, `supabase_sync`, `result_updater`) importan desde aquí. Si hay un nuevo equipo que no se cruza, agrégalo aquí.
- **Aliases añadidos en v1.3 (EL Round of 16):** Bologna, Real Betis, Stuttgart, Celta Vigo, Panathinaikos, Ferencvaros, Braga, Genk, Freiburg, Nottingham Forest, Midtjylland
- **Fix v2.1 (18-Mar-2026):** Agregado `"ATLÉTICO MADRID"` (acento sin "de") — The Odds API devuelve esta variante. Sin este alias, la fuzzy match falla y el partido queda sin cuotas, H2H, forma visitante y xG. **Lección:** cuando un partido nuevo falla en cuotas, revisar `naming_errors.log` primero — probablemente es un alias faltante.

### `model_engine.py` — Motor Predictivo (Pasos A→H) — v2.0
- **A:** Elo + ventaja local (+60)
- **B:** xG rolling con decay 0.85 (N=8 partidos)
- **C:** Lambdas Poisson normalizados con corrección Elo
- **C.5:** Ajuste de lambdas por forma reciente + H2H (v2.0)
- **D:** Matriz Poisson 7×7
- **E:** Probabilidades 1X2, Over/Under (0.5→6.5), Asian Handicap (-3.5→+3.5)
- **F:** Blend modelo(45%) + Pinnacle(55%) para 1X2 y Over 2.5
- **F.5:** Mercados de Doble Oportunidad sintéticos (`dc_1x`, `dc_x2`, `dc_12`)
- **G:** EV% por mercado — todos los totales fluyen por el loop de `extra["totals"]`; no hay duplicación
- **H:** Regla de Oro: EV ≥ 3%, Consenso ≥ 2/3, Divergencia ≤ 8pp → VIP si EV ≥ 5%
- **Value Matrix:** Exporta el 100% de mercados (positivos y negativos)
- **Output:** `model_output.json` + archivos en `Pronosticos/`

#### Paso C.5 — Forma reciente + H2H (v2.0)

**Problema resuelto:** `data_fetcher.py` obtenía forma y H2H pero `model_engine.py` los ignoraba — solo Gemini los usaba en narrativa. Ahora el modelo matemático los integra como multiplicadores sobre lambdas.

**`_form_to_multiplier(forma)`:**
- Input: `["W","L","D","W","W"]` (más reciente primero)
- Pesos: W=3, D=1, L=0 con decay `FORM_DECAY=0.80` por partido
- Rango multiplicador: ~0.925 a ~1.075 (`FORM_WEIGHT=0.15`)
- `forma=None` → retorna 1.0 (sin cambio)

**`_h2h_adjustments(h2h)`:**
- Input: `{"victorias_local": N, "empates": N, "victorias_visitante": N}`
- Empates cuentan como 0.5 victoria para cada lado
- Mínimo `H2H_MIN_GAMES=2` partidos para aplicar
- Rango multiplicador: ~0.95 a ~1.05 (`H2H_WEIGHT=0.10`)
- `h2h=None` o muestra insuficiente → retorna (1.0, 1.0)

**Integración:** Se aplican **después** de `paso_c_lambdas()`, **antes** de `paso_d_matrix()`:
```python
lam_local  *= form_adj_l * h2h_adj_l
lam_visit  *= form_adj_v * h2h_adj_v
```

**Diagnóstico:** `diagnostico_global` exporta `form_adj_local`, `form_adj_visitante`, `h2h_adj_local`, `h2h_adj_visitante` para transparencia.

#### Nomenclatura de mercados de totales — NORMALIZADA v1.9 ⚠️
La clave `over25` (legacy) fue **eliminada completamente**. Formato canónico en todo el pipeline:

| Línea | Código Over | Código Under |
|-------|-------------|--------------|
| 1.5 goles | `over_1.5` | `under_1.5` |
| 2.5 goles | `over_2.5` | `under_2.5` |
| 3.5 goles | `over_3.5` | `under_3.5` |

- `result_updater.py` acepta tanto el formato normalizado como el legacy `over25` vía regex `_parse_over_code()` (retrocompatibilidad con picks del 12-Mar-2026 en `historical_results`).
- `tracker_engine.py` acepta `("over_2.5", "over25")` para la misma retrocompatibilidad.

#### `paso_g_ev` — flujo de totales (v1.9):
- `over_2.5` ya **no está** en la lista hardcoded de `markets`. Fluye junto a `over_1.5`, `under_1.5`, `over_3.5`, etc. a través del loop `for tm, tc in extra["totals"].items()`.
- Condición de inclusión: `tm in p_final` (garantizado porque `paso_e` computa todas las líneas 0.5→6.5).
- Solo se calcula EV si la API devolvió una cuota para esa línea.

#### `run_model()` — garantía de presencia de línea 1.5 (v1.9):
- Tras construir `processed_all_markets`, se inyectan `over_1.5` y `under_1.5` si no están presentes (probabilidad del modelo Poisson disponible pero sin cuota API).
- Estos registros tienen `ev_pct: null`, `cuota: null`, `bookie: "Modelo puro"` y `p_modelo_ext` con la probabilidad directa.
- El dashboard los muestra con "sin cuota API" en lugar de ocultar la línea.

#### CLI print — Value Matrix (v1.9):
- Líneas mostradas: `over_1.5`, `under_1.5`, `over_2.5`, `over_3.5`, `under_3.5`
- `over_1.5`/`under_1.5`: se muestran **siempre** aunque no haya cuota API (columna cuota = `N/D`)
- Resto de totales: se omiten si no hay cuota API disponible

#### Paso F.5 — Double Chance (DC) detalle:
- **Constante:** `DC_MIN_COMPONENT = 0.20` — ambas componentes deben tener ≥ 20% (blended) para que se emita el mercado
- **Tres variantes:** `dc_1x` (local+empate), `dc_x2` (empate+visitante), `dc_12` (local+visitante)
- **Probabilidad blended:** suma de las dos componentes de `p_final`
- **Cuota sintética:** `1 / (p_pinnacle_comp1 + p_pinnacle_comp2)` derivada de Pinnacle no-vig; si no hay Pinnacle, el mercado DC no se emite
- **Divergencia:** `fair_pinnacle[dc_code] * 100 - p_modelo[dc_code]` (mismo criterio que 1X2)
- **Consenso DC en `_elo_favors`:** dc_1x si p_elo ≥ 0.40; dc_x2 si p_elo ≤ 0.60; dc_12 si |p_elo−0.5| > 0.10
- **Consenso DC en `_xg_favors`:** dc_1x si lam_l ≥ lam_v×0.80; dc_x2 si lam_v ≥ lam_l×0.80; dc_12 si |lam_l−lam_v| > 0.30
- **Consenso DC en `_poisson_favors`:** dc_1x si (local+empate) > 60%; dc_x2 si (visit+empate) > 60%; dc_12 si (local+visit) > 70%

#### Over/Under 1.5 — detalle (activo desde v1.8, robusto desde v1.9):
- **VIP-elegible:** `over_1.5` y `under_1.5` están en `OUTCOME_MAP` de `paso_h` y pueden pasar la Regla de Oro
- **Probabilidad:** modelo puro (sin blend Pinnacle); cuota de `m_extra["totals"]` si disponible desde The Odds API
- **Merge en `run_model()`:** cuotas de `over_1.5`/`under_1.5` se inyectan en `mejor_cuota` antes de `paso_h`
- **Consenso en `_xg_favors`:** over_1.5 si suma λ > 1.5; under_1.5 si suma λ < 1.5
- **Consenso en `_poisson_favors`:** over_1.5 si P > 70%; under_1.5 si P > 30%
- **Consenso en `_elo_favors`:** siempre False (Elo no aplica a totales)
- **Dashboard:** humanizados como "Más de 1.5 Goles" / "Menos de 1.5 Goles"
- **`result_updater.py`:** soportado vía `_parse_over_code()` sin cambios adicionales

### `supabase_sync.py` — Backend + IA — v2.0
- Lee `database/daily_report_DD_MM_YY.json`
- Filtra "partidos fantasma" (sin `hora_utc` ni `all_markets`)
- Construye **Match ID único:** `YYYYMMDD_Local_Visitante` (evita duplicados en `daily_board`)
- **VIP ID:** `YYYYMMDD_Local_Visitante_mercado` (pick-level, en `vip_signals`)
- Calcula `status`: `active` (partido futuro) o `finished` (partido pasado)
- Llama a **Gemini 2.5 Flash** → genera `angulo_matematico`, `angulo_tendencia`, `angulo_contexto`
- **`time.sleep(12)` entre cada llamada a Gemini (v1.9):** evita el error HTTP 429 del free tier (límite: 5 req/min). Con 9 partidos el sync tarda ~2 min extra pero garantiza análisis completo.
- **MOMENTUM_DATA injection (v2.0):** Inyecta forma, h2h y diagnostico_global dentro del JSONB existente `mercados_completos` como un registro especial con `mercado: "MOMENTUM_DATA"`. Esto evita migraciones de esquema en Supabase:
  ```python
  mercados_completos.append({
      "mercado": "MOMENTUM_DATA",
      "forma": forma_data,
      "h2h": h2h_data,
      "diagnostico_global": diag_global,
  })
  ```
- **`archive_finished_matches(url, key)` — v1.8 CORREGIDO:**
  - Lee `vip_signals?status=finished` (no `daily_board`)
  - Usa el `id` de `vip_signals` directamente (ya es pick-level)
  - Extrae `mercado` del campo `angulo_matematico` via regex `[Mercado: X]`
  - Añade `archived_at` con timestamp UTC
  - Deja `mercados_completos` como null (no requerido para evaluación)
- **PURGE total** de `daily_board` + `vip_signals` → luego UPSERT con datos frescos
- **Tablas Supabase:** `daily_board` (jornada activa) + `vip_signals` (picks profundos) + `historical_results` (archivo ROI permanente)

### `result_updater.py` — ROI Auto-Calificador — v1.9
- **Propósito:** Cierra el loop de ROI calificando picks pendientes en **dos tablas en orden**:
  1. **`vip_signals`** — picks del día actual (picks VIP activos, recién subidos por `supabase_sync.py`)
  2. **`historical_results`** — picks archivados de días anteriores
  - Esto elimina el gap de 24h que existía antes: los picks de hoy se califican la misma noche, sin esperar a que `supabase_sync.py` los archive al día siguiente.
- **Lógica compartida:** `_process_rows(rows, update_fn)` — función reutilizable que recibe filas de cualquier tabla y un `update_fn` específico por tabla. La calificación (API-Football + `evaluate_pick()`) es idéntica para ambas.
- **Query mínimo:** `vip_signals` selecciona `id,home_team,away_team,mercado` (sin `match_date` — fecha se extrae del ID). `historical_results` mantiene `match_date` como campo adicional.
- **Mercado directo:** Lee `row.get("mercado")` directamente del registro (arquitectura pick-level). No usa `get_best_pick()` ni `mercados_completos`.
- **Caché en memoria:** Agrupa llamadas a API-Football por fecha (1 llamada por día, no por partido).
- **Mercados soportados para evaluación:**

  | Código | Lógica |
  |--------|--------|
  | `1x2_local` | Win si home > away |
  | `1x2_empate` | Win si home == away |
  | `1x2_visitante` | Win si away > home |
  | `over_2.5`, `over25` (legacy), `under_3.0` | Totales vía `_parse_over_code()` regex |
  | `over_1.5`, `under_1.5` | Totales línea 1.5 |
  | `over_3.5`, `under_3.5` | Totales línea 3.5 |
  | `spread_local_N`, `spread_visitante_N` | Asian Handicap (push si línea exacta) |
  | `btts_yes`, `btts_no` | Ambos marcan |
  | `dc_1x` | Win si home_goals ≥ away_goals (local gana o empata) |
  | `dc_x2` | Win si away_goals ≥ home_goals (visitante gana o empata) |
  | `dc_12` | Win si home_goals ≠ away_goals (cualquier equipo gana, no empate) |

- **Valores de salida:** `win`, `loss`, `push`, `pending` (sin tocar si partido no encontrado o no terminado).
- **PATCH quirúrgico:** Solo actualiza `actual_result` y `status_win_loss`.
- **Dependencias:** `SUPABASE_URL`, `SUPABASE_KEY`, `API_FOOTBALL_KEY` (del `.env`)

### Carpeta `web/` — Frontend SaaS Producción (Vercel)
- Stack: HTML5 + Tailwind CSS (CDN) + Vanilla JS + Supabase JS Client
- **`index.html`**: Landing page pública. Carta de ventas.
- **`auth.html`**: Portal de Login y Creación de Cuentas (integrado con `supabase.auth.signInWithPassword` y `signUp`).
- **`dashboard.html`**: Terminal SaaS Privada. Dos tabs: Jornada General y Pronósticos VIP.
- **Seguridad**: `dashboard.html` usa un Auth Guard que detecta si no hay sesión (`getSession()`) y expulsa al usuario devolviéndolo a `auth.html`.
- **Config compartida**: Credenciales extraídas a `js/config.js` (`SUPABASE_ANON_KEY` y `SUPABASE_URL`).
- Modal de detalle: Triple Ángulo + Momentum + Value Matrix completa por partido

#### `renderBoardCard(item)` — rediseño v2.1
Tarjeta compacta de la Jornada General. Jerarquía visual en 5 filas:
1. **Fila liga + pills:** nombre de liga (truncado) a la izquierda; a la derecha pill `xG ±N.N` (verde/rojo/muted según signo) y pill `IA` (gold, solo si el partido tiene análisis Gemini inyectado como `IA_ANALYSIS` en `mercados_completos`)
2. **Fila equipos:** local y visitante en `font-display` xl uppercase, separados por "vs" en muted
3. **Barra 1X2:** barra thin (`h-1.5`) dividida en 3 segmentos verde/muted/rojo con porcentajes Poisson del modelo debajo en `font-mono`
4. **Fila "Mejor EV":** busca el mercado con mayor `ev_pct` en `mercados_completos` (excluye `MOMENTUM_DATA` e `IA_ANALYSIS`); muestra etiqueta abreviada del mercado + badge EV con borde coloreado (verde si ≥ 5%, gold si menor)
5. **Fila Forma:** dots 2×2 px por resultado (verde=W, gold=D, rojo=L) para local y visitante, con abreviatura de 3 letras del nombre del equipo; se oculta si no hay `MOMENTUM_DATA`
- **CTA footer:** "Triple ángulo + matrices" si tiene IA, "Ver matrices de valor" si no
- Al hacer clic → abre `openMatchModal(matchKey)`

#### `renderVipCard(picks)` — agrupación por partido v2.1
Recibe un **array de picks** del mismo partido (no un item individual). Renderiza una card por partido.
- **Header:** badge "VIP Signal" (gold sobre negro) + nombre del partido en `font-display` 3xl
- **Lista de picks:** top 3 ordenados por `ev_pct` descendente. Cada fila:
  - Mercado humanizado (`getHumanizedMarket`) | cuota | badge EV con borde (verde ≥ 5%, gold <5%)
- **Accordion "Ver análisis IA ▾":** colapsado por defecto; usa el primer pick con narrativa no-pending como fuente de los tres ángulos. Si **todos** los picks del partido tienen texto pending (`'Análisis IA Pendiente'` o `'[PENDING_IA_GENERATION]'`) → no se muestra el accordion, solo el indicador pulsante "Análisis en proceso"
- Colores del diseño: borde `podium-gold/30`, fondo `from-[#0f1428] via-[#050716] to-black`, glow superior gold/10

#### `groupVipByMatch(items)` — helper de agrupación v2.1
Agrupa el array plano de `vip_signals` (un registro por pick) en sub-arrays por partido (`home_team + away_team`). Preserva el orden de llegada. Llamada en `fetchData()` antes de `.map(renderVipCard)`:
```js
groupVipByMatch(vipActiveData).map(renderVipCard).join('')
groupVipByMatch(vipFinishedData).map(renderVipCard).join('')
```
**Antes (v2.0):** `vipData.map(renderVipCard)` — una card por pick → mismo partido repetido N veces
**Ahora (v2.1):** `groupVipByMatch(vipData).map(renderVipCard)` — una card por partido con todos sus picks

#### Funciones helper de UI compartidas
- **`getEvColorClass(ev)`:** `text-podium-red` (<1%) · `text-podium-gold` (1–4.99%) · `text-podium-green font-bold` (≥5%)
- **`renderFormDots(formaArr)`:** círculos `h-2 w-2 rounded-full` verde/gold/rojo; `title` con texto del resultado
- **`renderFormRow(label, formaArr)`:** fila con label + dots + contador `NW ND NL`
- **`formatAdj(val)`:** formatea multiplicadores del modelo (ej: `1.05` → `+5.0%` en verde)
- **`getHumanizedMarket(mercado, home, away)`:** mapea códigos internos a texto legible; los DC incluyen nombre de equipo dinámico

#### Sección Momentum en tarjetas (v2.0, vigente)
- Extrae `MOMENTUM_DATA` de `mercados_completos` JSONB via `extractMomentum()`
- Muestra dots de forma compacta en la Fila 5 de `renderBoardCard`

#### Sección Momentum en modal de detalle (v2.0, vigente)
- Bloque "Forma Reciente": dots + porcentaje de ajuste al modelo (`form_adj_local/visitante`)
- Bloque "Historial Directo (H2H)": contadores W-D-L + impacto porcentual (`h2h_adj_*`)
- Ubicado entre el Triple Ángulo y las Value Matrices

#### Humanización de mercados `getHumanizedMarket()` (v1.9, vigente)
- `over_1.5` → "Más de 1.5 Goles" · `under_1.5` → "Menos de 1.5 Goles"
- `over_2.5` → "Más de 2.5 Goles" · `under_2.5` → "Menos de 2.5 Goles"
- `over_3.5` → "Más de 3.5 Goles" · `under_3.5` → "Menos de 3.5 Goles"
- `dc_x2` → "Doble Oportunidad: Empate o {away}", etc.

#### Robustez y edge cases (v1.9, vigente)
- Sección Totals vacía → muestra "Línea no disponible"
- Sección Spreads vacía → se oculta completamente
- Filas sin cuota API → "sin cuota API" en cursiva; usa `p_modelo_ext` para Prob Modelo
- **`buildTable()`:** usa `p_modelo_ext` del JSON para probabilidad directa (sin reverse-engineering)

### `test_runner.py` — Orquestador de Validación — v2.0
- Niveles 1–5: smoke test, caché, EV trigger, tracker, generación de reporte diario
- Busca partidos de **Champions League** (`CL`) y **Europa League** (`EL`) vía Football-Data API
- **Passthrough de forma/h2h (v2.0):** Pasa `forma`, `h2h` y `diagnostico_global` del output del modelo al `daily_report`, para que `supabase_sync.py` pueda inyectarlos en `mercados_completos`
- **`load_manual_matches()`** → Lee `partidos_manuales.json` como fuente adicional/fallback
- **Deduplicación automática:** matches de API tienen prioridad; los manuales se agregan solo si no están ya en la respuesta de la API
- **`partidos_manuales.json`** → Archivo editable en raíz del proyecto. Formato: `[{"local": "X", "visitante": "Y", "liga": "Z"}]`
  - Úsalo para ligas que Football-Data no escanea automáticamente (PL, Serie A, LaLiga, BL, etc.)
  - **Vaciar antes de cada jornada nueva** para evitar procesar partidos de jornadas pasadas
  - **Jornada 18/03/2026:** contiene Braga vs Ferencvaros (UEL). Vaciar antes de la próxima jornada.

### `master_morning.py` y `master_night.py` — Scripts Maestros (18-Mar-2026)

Orquestadores de ejecución diaria. Usan `subprocess.run()` con `capture_output=False` para que los logs de cada script se vean en tiempo real. Muestran timestamp `HH:MM:SS` al inicio de cada paso y resumen de tiempos al finalizar. Si cualquier paso falla (exit code ≠ 0), detienen la ejecución inmediatamente.

**`master_morning.py`** — correr en la mañana antes de que empiecen los partidos:
```
python master_morning.py
  Paso 1/2: test_runner.py    (auto-detecta partidos, corre pipeline, genera daily_report)
  Paso 2/2: supabase_sync.py  (sube a Supabase, llama a Gemini)
```

**`master_night.py`** — correr después de las 22:00 cuando todos los partidos ya terminaron:
```
python master_night.py
  Paso 1/1: result_updater.py  (califica picks en vip_signals y historical_results)
```

### `migrations/schema_maestro.sql` — Schema Maestro de Supabase ⚠️
- **Define las 3 tablas completas:** `daily_board` (11 cols), `vip_signals` (12 cols), `historical_results` (20 cols)
- Usa `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ADD COLUMN IF NOT EXISTS` → idempotente
- Incluye políticas RLS: anon read para `daily_board`/`vip_signals`, service_role para `historical_results`
- **Ya ejecutado** en producción (18-Mar-2026)
- **REGLA:** Antes de cada jornada, si el pipeline falla con errores de columna inexistente, re-ejecutar este script en Supabase SQL Editor. Es seguro correrlo múltiples veces.

### `migrations/create_historical_results.sql` — DDL legacy
- Script original de creación de `historical_results`. Superado por `schema_maestro.sql`.
- **Ya ejecutado** en producción (12-Mar-2026).

### `insert_historical_12_03_26.py` — Script de Archivado Manual (UEL R16)
- Script **one-shot** para archivar los 12 picks VIP de la jornada del 12-Mar-2026.
- **Ya ejecutado.** Sirve como plantilla para futuros archivados manuales de emergencia.
- **Nota:** Los picks de esta jornada usan el código legacy `over25` en su `id` y columna `mercado`. `result_updater.py` los califica correctamente vía regex.

---

## Variables de Entorno (`.env`)

```
SUPABASE_URL=https://ssvnixnqczpvpiomgrje.supabase.co
SUPABASE_KEY=<service_role_key>
SUPABASE_ANON_KEY=<publishable_key>  ← usada por dashboard HTML frontend
GOOGLE_API_KEY=<gemini_2.5_flash>
ODDS_API_KEY=<the-odds-api.com>
API_FOOTBALL_KEY=<api-football.com>
FOOTBALL_DATA_KEY=<football-data.org>  ← legacy, ya no se usa en result_updater
```

### Variables a añadir en Fase 1 (Next.js):
```
NEXT_PUBLIC_SUPABASE_URL=https://ssvnixnqczpvpiomgrje.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon_key>
STRIPE_SECRET_KEY=<stripe_secret>
STRIPE_WEBHOOK_SECRET=<stripe_webhook>
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=<stripe_publishable>
```

---

## Esquema de Supabase (v2.0)

| Tabla | Propósito | Acceso dashboard JS |
|-------|-----------|-------------------|
| `daily_board` | Jornada activa (se purga en cada sync) | ✅ anon read |
| `vip_signals` | Picks EV ≥ 5% de la jornada activa | ✅ anon read |
| `historical_results` | Archivo permanente de picks finalizados + ROI | ❌ solo service_role |

### Columnas a añadir en Supabase para Fase 1 (usuarios y membresías):
```sql
-- Tabla de perfiles de usuario (vinculada a Supabase Auth)
CREATE TABLE user_profiles (
  id UUID REFERENCES auth.users PRIMARY KEY,
  email TEXT,
  plan TEXT DEFAULT 'free',         -- 'free' | 'paid'
  stripe_customer_id TEXT,
  subscription_status TEXT,         -- 'active' | 'canceled' | 'past_due'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS: usuarios solo leen su propio perfil
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
```

### `daily_board` — patrón MOMENTUM_DATA (v2.0)
La columna `mercados_completos` (JSONB) ahora incluye un registro especial con `mercado: "MOMENTUM_DATA"` que contiene `forma`, `h2h` y `diagnostico_global`. El dashboard JS lo extrae con `extractMomentum()` para renderizar la sección de Momentum en tarjetas y modal. Este patrón evita migraciones de esquema — los datos viajan dentro del JSONB existente.

### `vip_signals` — columnas de resultado (v1.9) ✅
- `mercado` TEXT — creada via `schema_maestro.sql` (18-Mar-2026)
- `status_win_loss` TEXT DEFAULT `'pending'` — agregada via migration (18-Mar-2026)
- `actual_result` TEXT — agregada via migration (18-Mar-2026)

`supabase_sync.py` escribe `mercado` directamente en cada upsert. `result_updater.py` actualiza `status_win_loss` y `actual_result` cada noche vía `master_night.py`.

### `historical_results` — arquitectura pick-level (v1.6+)

**Cada fila representa UN pick VIP, no un partido.** El ID es el mismo que en `vip_signals`.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | TEXT PK | `YYYYMMDD_Local_Visitante_mercado` (ej: `2026-03-12_Stuttgart_Porto_1x2_visitante`) |
| `home_team` | TEXT | Equipo local |
| `away_team` | TEXT | Equipo visitante |
| `competition` | TEXT | Liga/torneo |
| `match_date` | DATE | Fecha del partido |
| `mercado` | TEXT | Mercado del pick (`1x2_local`, `dc_x2`, `over_1.5`, `over_2.5`, etc.) |
| `cuota` | FLOAT | Cuota al momento del pick |
| `ev_pct` | FLOAT | EV% calculado por el modelo |
| `actual_result` | TEXT | Score final ej. `"2-1"`. Llenado por `result_updater.py` o manualmente. |
| `status_win_loss` | TEXT | `'win'` · `'loss'` · `'push'` · `'void'` · `'pending'` (default) |
| `mercados_completos` | JSONB | Contexto opcional (null en registros archivados desde v1.8) |
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

| Fecha | Competición | Picks | W | L | Profit | ROI |
|-------|-------------|------:|--:|--:|-------:|----:|
| 2026-03-12 | UEL R16 1ª ida | 12 | 3 | 9 | +3.05u | +25.4% |
| 2026-03-15 | Serie A + PL | 6 | 2 | 4 | +7.50u | +125.0% |
| 2026-03-16 | UCL | 1 | 1 | 0 | +0.56u | +56.0% |
| 2026-03-17 | UCL QF ida | 7 | 4 | 3 | +7.37u | +105.3% |
| **TOTAL** | | **26** | **10** | **16** | **+18.48u** | **+71.1%** |

---

## Problemas Conocidos

| Problema | Impacto | Solución |
|----------|---------|----------|
| ~~Columna `mercado` falta en `vip_signals`~~ | ~~RESUELTO 18-Mar-2026~~ | `schema_maestro.sql` la incluye |
| ~~Naming: Atlético Madrid sin alias con acento~~ | ~~RESUELTO 18-Mar-2026~~ | Alias `"ATLÉTICO MADRID"` agregado a `naming.py` |
| Football-Data API no retorna partidos EL/CL (tier insuficiente) | `result_updater.py` ya migrado a API-Football; Football-Data solo se usa en `data_fetcher.py` para fixtures/standings | Migración completada para resultados; evaluar migrar data_fetcher también |
| Partidos UEL de bajo perfil sin cobertura en The Odds API | Ej: Braga vs Ferencvaros (18-Mar) — solo Elo disponible, sin cuotas ni xG | No se puede resolver con naming; es limitación de cobertura API. Marcar visualmente en dashboard. |
| ~~`partidos_manuales.json` requiere mantenimiento manual~~ | ~~RESUELTO 18-Mar-2026~~ | `fetch_and_save_domestic_matches()` sobreescribe el archivo en cada ejecución de `test_runner.py` |
| ~~`test_runner.py` solo escanea CL y EL automáticamente~~ | ~~RESUELTO 18-Mar-2026~~ | Ahora consulta PL, SA, PD, BL1, FL1 vía Football-Data API con delays de 7s |
| `result_updater.py` no califica mercados Asian Handicap complejos | Picks AH complejos quedan `pending` indefinidamente | Implementar `void` y lógica AH avanzada (`-1`, `-2`) |
| DC markets no se emiten si Pinnacle no está disponible para el partido | Sin cuota sintética de referencia, el EV no se puede calcular | Implementar fallback con margen estimado (ej: 4%) cuando Pinnacle no retorna cuotas |
| `over_1.5`/`under_1.5` usan probabilidad modelo puro (sin blend Pinnacle) | EV ligeramente menos preciso que mercados 1X2 | Extender `paso_f_blend()` para blendear O/U 1.5 cuando cuota disponible |
| Picks del 12-Mar-2026 en `historical_results` usan código legacy `over25` | No afecta calificación (regex lo maneja); pero rompe consistencia del historial | Ejecutar `UPDATE historical_results SET mercado='over_2.5' WHERE mercado='over25'` en Supabase |
| Sin corners/tarjetas/stats avanzadas en el modelo | Mercados de corners y tarjetas no disponibles | Integrar API-Football cuando haya tracción de usuarios pagos |
| Gemini free tier rate limit (~50 req/día, 5 req/min) | Con jornadas de 9+ partidos, algunas narrativas quedan vacías si la cuota diaria se agota | Re-ejecutar `supabase_sync.py` cuando la cuota se renueve; considerar API key de pago en Fase 2 |
| MOMENTUM_DATA embebido en `mercados_completos` JSONB | Patrón de embeber datos estructurados en campo JSONB existente — funcional pero no ideal a largo plazo | Migrar a columnas dedicadas (`forma`, `h2h`, `diagnostico_global`) en `daily_board` cuando se haga el port a Next.js |
| H2H requiere mínimo 2 partidos para aplicar ajuste | Partidos de fase nueva (ej: UCL QF) con 0-1 H2H no reciben ajuste | Comportamiento correcto — muestra insuficiente no debe sesgar el modelo |

---

## Subcarpetas de Contexto Adicional

- **`.claude/rules/`** → Convenciones de desarrollo y políticas
- **`.claude/workflows/`** → Flujos de datos detallados
- **`.claude/docs/`** → Algoritmos matemáticos (ver `hybrid_model.md`)
- **`.claude/agents/`** → Roles: `math_engineer.md`, `narrative_insights.md`

---

## Reglas de Desarrollo — CRÍTICAS ⚠️

1. **No romper el pipeline Python.** Cualquier cambio en Next.js o Supabase que afecte las tablas `daily_board`, `vip_signals` o `historical_results` debe ser retrocompatible con los scripts Python existentes.
2. **No invertir en APIs de pago** hasta tener usuarios pagos reales. Las fuentes actuales (gratuitas) son suficientes para Fase 1.
3. **El dashboard HTML sigue funcionando** durante toda la Fase 1. Es el fallback operativo.
4. **Supabase es la única fuente de verdad** entre el pipeline Python y el frontend Next.js. No duplicar lógica de negocio en el frontend.
5. **Freemium se implementa en el frontend** (RLS de Supabase + verificación de plan en Next.js). El pipeline Python no sabe nada de planes — sigue subiendo todos los datos.

---

## Frontend React — Landing Page (23-Mar-2026)

La landing page de VALIOR (`web/index.html`) fue reemplazada por una app React/Vite/Tailwind v4 ubicada en `frontend/`.

### Stack frontend (landing):
- React 19 + TypeScript
- Vite 6 (bundler)
- Tailwind CSS v4 (via @tailwindcss/vite plugin)
- Motion (Framer Motion) para animaciones
- Recharts para gráfico de ROI
- Lucide React para iconos

### Ubicación: `frontend/`

### Instalación: `npm install --legacy-peer-deps` (obligatorio por peer deps de lucide-react)

### Build: `npm run build` → genera `frontend/dist/`

### Convivencia con web/:
- `web/auth.html` y `web/dashboard.html` se copian a `frontend/public/` para que Vercel los sirva
- `web/` se mantiene como fallback pero ya no es servido directamente por Vercel
- Si se modifica auth.html o dashboard.html en web/, hay que re-copiar a frontend/public/

### Auth page rediseñada (24-Mar-2026):
- Split-screen: formulario a la izquierda, propuesta de valor a la derecha (oculta en móvil)
- Dark theme consistente con landing: `#050505` fondo, `#00ff66` acentos, tipografía Inter + JetBrains Mono
- Grid de fondo con mask gradient, glow verde central, testimonial en panel derecho
- Lógica Supabase Auth completa: `signInWithPassword`, `signUp`, detección de sesión, redirect a dashboard
- Botón "Continuar con Google" (placeholder visual — requiere configurar OAuth provider en Supabase)
- Archivo fuente: `web/auth.html` (se copia a `frontend/public/auth.html`)

### Regla Crítica #6:
No modificar `frontend/src/App.tsx` ni `web/auth.html` sin confirmación explícita del usuario. Estos archivos contienen diseños aprobados manualmente (generados con Google AI Studio).
