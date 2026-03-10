-- ============================================================
-- PODIUM VIP — Schema de Supabase (PostgreSQL)
-- Tabla: public.partidos
-- ============================================================
-- INSTRUCCIONES:
-- Ejecutar en: Supabase Dashboard → SQL Editor
-- O usar el MCP de Supabase con apply_migration
-- ============================================================

CREATE TABLE IF NOT EXISTS public.partidos (
  -- ── IDENTIFICACIÓN ──────────────────────────────────────
  id                  BIGSERIAL PRIMARY KEY,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- ── DATOS DEL PARTIDO ───────────────────────────────────
  equipo_local        TEXT NOT NULL,
  equipo_visitante    TEXT NOT NULL,
  liga                TEXT NOT NULL,
  jornada             INTEGER,                    -- número de jornada (null si es Copa/UEFA)
  fecha_partido       DATE NOT NULL,
  hora_utc            TIME,                       -- hora en UTC
  estadio             TEXT,

  -- ── CLASIFICACIÓN AL MOMENTO DEL PARTIDO ────────────────
  pos_local           INTEGER,                    -- posición en tabla
  pts_local           INTEGER,                    -- puntos
  pos_visitante       INTEGER,
  pts_visitante       INTEGER,

  -- ── PROBABILIDADES 1X2 (en %) ───────────────────────────
  prob_local          NUMERIC(5,2),               -- ej: 52.40
  prob_empate         NUMERIC(5,2),               -- ej: 23.10
  prob_visitante      NUMERIC(5,2),               -- ej: 24.50

  -- ── MERCADO CON MEJOR EV ────────────────────────────────
  mercado_ev          TEXT,                       -- ej: "Más de 2.5 goles"
  cuota_ev            NUMERIC(6,2),               -- ej: 1.80
  ev_porcentaje       NUMERIC(6,2),               -- ej: 15.60 (puede ser negativo)
  ev_recomendado      BOOLEAN DEFAULT FALSE,      -- TRUE solo si EV >= +3%

  -- ── VERSIÓN GENERADA ────────────────────────────────────
  version_generada    TEXT DEFAULT 'VIP' CHECK (version_generada IN ('FREE', 'VIP', 'AMBAS')),

  -- ── RESULTADO REAL (llenar post-partido) ────────────────
  resultado_local     INTEGER,                    -- goles del equipo local
  resultado_visitante INTEGER,                    -- goles del equipo visitante
  prediccion_acertada BOOLEAN,                    -- TRUE si el mercado recomendado fue correcto

  -- ── OPERACIÓN ────────────────────────────────────────────
  -- NOTA: estas columnas ya existen en la BD real
  api_calls_used      INTEGER DEFAULT 0,          -- llamadas a RapidAPI usadas para esta tarjeta
  notas               TEXT                        -- notas internas del operador
);

-- ── TRIGGER: actualizar updated_at automáticamente ──────────────
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER partidos_updated_at
  BEFORE UPDATE ON public.partidos
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- ── ÍNDICES para queries frecuentes ─────────────────────────────
CREATE INDEX IF NOT EXISTS idx_partidos_fecha       ON public.partidos (fecha_partido DESC);
CREATE INDEX IF NOT EXISTS idx_partidos_liga        ON public.partidos (liga);
CREATE INDEX IF NOT EXISTS idx_partidos_acertada    ON public.partidos (prediccion_acertada);
CREATE INDEX IF NOT EXISTS idx_partidos_version     ON public.partidos (version_generada);

-- ── ROW LEVEL SECURITY ──────────────────────────────────────────
-- Habilitar RLS (recomendado)
ALTER TABLE public.partidos ENABLE ROW LEVEL SECURITY;

-- Policy: solo el operador autenticado puede leer y escribir
-- (Ajustar según los usuarios de Supabase que uses)
CREATE POLICY "Operador puede leer" ON public.partidos
  FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Operador puede insertar" ON public.partidos
  FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Operador puede actualizar" ON public.partidos
  FOR UPDATE USING (auth.role() = 'authenticated');

-- ============================================================
-- TEMPLATES DE INSERT Y UPDATE (copiar y pegar al usar)
-- ============================================================

/*
── INSERT al generar una tarjeta ──────────────────────────────

INSERT INTO public.partidos (
  equipo_local, equipo_visitante, liga, jornada,
  fecha_partido, hora_utc, estadio,
  pos_local, pts_local, pos_visitante, pts_visitante,
  prob_local, prob_empate, prob_visitante,
  mercado_ev, cuota_ev, ev_porcentaje, ev_recomendado,
  version_generada
) VALUES (
  'Arsenal', 'Chelsea', 'Premier League', 30,
  '2026-03-15', '16:30', 'Emirates Stadium',
  2, 58, 6, 44,
  52.40, 23.10, 24.50,
  'Más de 2.5 goles', 1.80, 15.60, TRUE,
  'VIP'
) RETURNING id;

── UPDATE post-partido ────────────────────────────────────────

UPDATE public.partidos
SET
  resultado_local = 3,
  resultado_visitante = 1,
  prediccion_acertada = TRUE   -- el partido tuvo más de 2.5 goles
WHERE id = [id_devuelto_por_insert];

*/
