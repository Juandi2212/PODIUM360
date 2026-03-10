-- ============================================================
-- PODIUM VIP — Queries de seguimiento
-- Archivo: queries/tasa-acierto.sql
-- ============================================================

-- ── 1. TASA DE ACIERTO GLOBAL ───────────────────────────────────
SELECT
  COUNT(*) FILTER (WHERE prediccion_acertada IS NOT NULL) AS partidos_con_resultado,
  COUNT(*) FILTER (WHERE prediccion_acertada = TRUE)      AS acertados,
  COUNT(*) FILTER (WHERE prediccion_acertada = FALSE)     AS fallados,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE prediccion_acertada = TRUE)
    / NULLIF(COUNT(*) FILTER (WHERE prediccion_acertada IS NOT NULL), 0),
    1
  ) AS tasa_acierto_pct
FROM public.partidos
WHERE ev_recomendado = TRUE;

-- ── 2. TASA DE ACIERTO POR LIGA ─────────────────────────────────
SELECT
  liga,
  COUNT(*) FILTER (WHERE prediccion_acertada IS NOT NULL) AS partidos,
  COUNT(*) FILTER (WHERE prediccion_acertada = TRUE)      AS acertados,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE prediccion_acertada = TRUE)
    / NULLIF(COUNT(*) FILTER (WHERE prediccion_acertada IS NOT NULL), 0),
    1
  ) AS tasa_pct
FROM public.partidos
WHERE ev_recomendado = TRUE
GROUP BY liga
ORDER BY tasa_pct DESC;

-- ── 3. TASA DE ACIERTO POR MERCADO ──────────────────────────────
SELECT
  mercado_ev,
  COUNT(*) FILTER (WHERE prediccion_acertada IS NOT NULL) AS veces_recomendado,
  COUNT(*) FILTER (WHERE prediccion_acertada = TRUE)      AS acertados,
  ROUND(AVG(ev_porcentaje), 1)                            AS ev_promedio_pct,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE prediccion_acertada = TRUE)
    / NULLIF(COUNT(*) FILTER (WHERE prediccion_acertada IS NOT NULL), 0),
    1
  ) AS tasa_pct
FROM public.partidos
WHERE ev_recomendado = TRUE
GROUP BY mercado_ev
ORDER BY tasa_pct DESC;

-- ── 4. ÚLTIMOS 10 PARTIDOS (para portfolio) ─────────────────────
SELECT
  fecha_partido,
  equipo_local || ' vs ' || equipo_visitante AS partido,
  liga,
  mercado_ev,
  cuota_ev,
  ev_porcentaje,
  CASE
    WHEN resultado_local IS NULL THEN '—'
    ELSE resultado_local::TEXT || '-' || resultado_visitante::TEXT
  END AS resultado,
  CASE
    WHEN prediccion_acertada IS NULL THEN 'Pendiente'
    WHEN prediccion_acertada = TRUE  THEN '✅ Acertó'
    ELSE '❌ Falló'
  END AS resultado_prediccion
FROM public.partidos
WHERE ev_recomendado = TRUE
ORDER BY fecha_partido DESC
LIMIT 10;

-- ── 5. PARTIDOS PENDIENTES DE RESULTADO ─────────────────────────
SELECT
  id,
  fecha_partido,
  equipo_local || ' vs ' || equipo_visitante AS partido,
  liga,
  mercado_ev,
  cuota_ev
FROM public.partidos
WHERE
  ev_recomendado = TRUE
  AND prediccion_acertada IS NULL
  AND fecha_partido < CURRENT_DATE
ORDER BY fecha_partido ASC;

-- ── 6. RESUMEN SEMANAL (para presentar a Wick) ──────────────────
SELECT
  DATE_TRUNC('week', fecha_partido)::DATE AS semana,
  COUNT(*)                                AS tarjetas_generadas,
  COUNT(*) FILTER (WHERE ev_recomendado = TRUE AND prediccion_acertada = TRUE)  AS ev_acertados,
  COUNT(*) FILTER (WHERE ev_recomendado = TRUE AND prediccion_acertada = FALSE) AS ev_fallados,
  COUNT(*) FILTER (WHERE ev_recomendado = TRUE AND prediccion_acertada IS NULL) AS ev_pendientes,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE ev_recomendado = TRUE AND prediccion_acertada = TRUE)
    / NULLIF(COUNT(*) FILTER (WHERE ev_recomendado = TRUE AND prediccion_acertada IS NOT NULL), 0),
    1
  ) AS tasa_acierto_semana_pct
FROM public.partidos
GROUP BY DATE_TRUNC('week', fecha_partido)
ORDER BY semana DESC
LIMIT 8;
