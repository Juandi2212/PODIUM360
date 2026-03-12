-- Ejecutar UNA VEZ en el SQL Editor de Supabase
-- Dashboard → SQL Editor → New Query → pegar y ejecutar

CREATE TABLE IF NOT EXISTS public.historical_results (
  id                   TEXT PRIMARY KEY,
  match_date           DATE,
  home_team            TEXT,
  away_team            TEXT,
  competition          TEXT,
  hora_utc             TEXT,
  poisson_1            FLOAT,
  poisson_x            FLOAT,
  poisson_2            FLOAT,
  xg_diff              FLOAT,
  estado_mercado       TEXT,
  mercado              TEXT,        -- mercado del pick (1x2_local, over25, etc.)
  cuota                FLOAT,       -- cuota al momento del pick
  ev_pct               FLOAT,       -- EV% calculado por el modelo
  mercados_completos   JSONB,
  ai_analysis          JSONB,
  status               TEXT DEFAULT 'finished',
  actual_result        TEXT,
  status_win_loss      TEXT DEFAULT 'pending',
  archived_at          TIMESTAMPTZ DEFAULT now()
);

-- Si la tabla ya existe, agregar columnas faltantes:
ALTER TABLE public.historical_results ADD COLUMN IF NOT EXISTS mercado   TEXT;
ALTER TABLE public.historical_results ADD COLUMN IF NOT EXISTS cuota     FLOAT;
ALTER TABLE public.historical_results ADD COLUMN IF NOT EXISTS ev_pct    FLOAT;

-- Permisos: solo service_role puede leer/escribir (sin acceso anónimo)
ALTER TABLE public.historical_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_only" ON public.historical_results
  FOR ALL USING (auth.role() = 'service_role');
