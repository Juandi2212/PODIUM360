-- ══════════════════════════════════════════════════════════════════════════
-- SCHEMA MAESTRO — Valior v2.0
-- Ejecutar en Supabase SQL Editor para sincronizar esquema con el pipeline
-- Seguro de re-ejecutar: usa ADD COLUMN IF NOT EXISTS
-- Fecha: 18/03/2026
-- ══════════════════════════════════════════════════════════════════════════

-- ──────────────────────────────────────────────────────────────────────────
-- TABLA 1: daily_board
-- Escrita por: supabase_sync.py (purge + upsert cada sync)
-- Leída por: dashboard_live.html (anon read)
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.daily_board (
  id                   TEXT PRIMARY KEY,
  match_date           DATE,
  home_team            TEXT,
  away_team            TEXT,
  poisson_1            FLOAT,
  poisson_x            FLOAT,
  poisson_2            FLOAT,
  xg_diff              FLOAT,
  estado_mercado       TEXT,
  mercados_completos   JSONB,
  status               TEXT DEFAULT 'active'
);

-- Columnas que pudieron faltar si la tabla fue creada manualmente
ALTER TABLE public.daily_board ADD COLUMN IF NOT EXISTS match_date         DATE;
ALTER TABLE public.daily_board ADD COLUMN IF NOT EXISTS home_team          TEXT;
ALTER TABLE public.daily_board ADD COLUMN IF NOT EXISTS away_team          TEXT;
ALTER TABLE public.daily_board ADD COLUMN IF NOT EXISTS poisson_1          FLOAT;
ALTER TABLE public.daily_board ADD COLUMN IF NOT EXISTS poisson_x          FLOAT;
ALTER TABLE public.daily_board ADD COLUMN IF NOT EXISTS poisson_2          FLOAT;
ALTER TABLE public.daily_board ADD COLUMN IF NOT EXISTS xg_diff            FLOAT;
ALTER TABLE public.daily_board ADD COLUMN IF NOT EXISTS estado_mercado     TEXT;
ALTER TABLE public.daily_board ADD COLUMN IF NOT EXISTS mercados_completos JSONB;
ALTER TABLE public.daily_board ADD COLUMN IF NOT EXISTS status             TEXT DEFAULT 'active';

-- RLS: lectura anónima
ALTER TABLE public.daily_board ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'daily_board' AND policyname = 'anon_read_daily_board') THEN
    CREATE POLICY anon_read_daily_board ON public.daily_board FOR SELECT USING (true);
  END IF;
END $$;

-- ──────────────────────────────────────────────────────────────────────────
-- TABLA 2: vip_signals
-- Escrita por: supabase_sync.py (purge + upsert cada sync)
-- Leída por: dashboard_live.html (anon read)
-- ──────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.vip_signals (
  id                   TEXT PRIMARY KEY,
  match_date           DATE,
  home_team            TEXT,
  away_team            TEXT,
  mercado              TEXT,
  cuota                FLOAT,
  ev_pct               FLOAT,
  ev_initial           FLOAT,
  angulo_matematico    TEXT,
  angulo_tendencia     TEXT,
  angulo_contexto      TEXT,
  status               TEXT DEFAULT 'active'
);

-- Columnas que pudieron faltar
ALTER TABLE public.vip_signals ADD COLUMN IF NOT EXISTS match_date         DATE;
ALTER TABLE public.vip_signals ADD COLUMN IF NOT EXISTS home_team          TEXT;
ALTER TABLE public.vip_signals ADD COLUMN IF NOT EXISTS away_team          TEXT;
ALTER TABLE public.vip_signals ADD COLUMN IF NOT EXISTS mercado            TEXT;
ALTER TABLE public.vip_signals ADD COLUMN IF NOT EXISTS cuota              FLOAT;
ALTER TABLE public.vip_signals ADD COLUMN IF NOT EXISTS ev_pct             FLOAT;
ALTER TABLE public.vip_signals ADD COLUMN IF NOT EXISTS ev_initial         FLOAT;
ALTER TABLE public.vip_signals ADD COLUMN IF NOT EXISTS angulo_matematico  TEXT;
ALTER TABLE public.vip_signals ADD COLUMN IF NOT EXISTS angulo_tendencia   TEXT;
ALTER TABLE public.vip_signals ADD COLUMN IF NOT EXISTS angulo_contexto    TEXT;
ALTER TABLE public.vip_signals ADD COLUMN IF NOT EXISTS status             TEXT DEFAULT 'active';

-- RLS: lectura anónima
ALTER TABLE public.vip_signals ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'vip_signals' AND policyname = 'anon_read_vip_signals') THEN
    CREATE POLICY anon_read_vip_signals ON public.vip_signals FOR SELECT USING (true);
  END IF;
END $$;

-- ──────────────────────────────────────────────────────────────────────────
-- TABLA 3: historical_results
-- Escrita por: supabase_sync.py (archive) + result_updater.py (PATCH)
-- Leída por: result_updater.py (SELECT pending)
-- ──────────────────────────────────────────────────────────────────────────

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
  mercado              TEXT,
  cuota                FLOAT,
  ev_pct               FLOAT,
  mercados_completos   JSONB,
  ai_analysis          JSONB,
  status               TEXT DEFAULT 'finished',
  actual_result        TEXT,
  status_win_loss      TEXT DEFAULT 'pending',
  archived_at          TIMESTAMPTZ DEFAULT now()
);

-- Columnas críticas que pudieron faltar
ALTER TABLE public.historical_results ADD COLUMN IF NOT EXISTS mercado          TEXT;
ALTER TABLE public.historical_results ADD COLUMN IF NOT EXISTS cuota            FLOAT;
ALTER TABLE public.historical_results ADD COLUMN IF NOT EXISTS ev_pct           FLOAT;
ALTER TABLE public.historical_results ADD COLUMN IF NOT EXISTS actual_result    TEXT;
ALTER TABLE public.historical_results ADD COLUMN IF NOT EXISTS status_win_loss  TEXT DEFAULT 'pending';
ALTER TABLE public.historical_results ADD COLUMN IF NOT EXISTS archived_at      TIMESTAMPTZ DEFAULT now();

-- RLS: solo service_role
ALTER TABLE public.historical_results ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'historical_results' AND policyname = 'service_role_only') THEN
    CREATE POLICY service_role_only ON public.historical_results FOR ALL USING (auth.role() = 'service_role');
  END IF;
END $$;

-- ══════════════════════════════════════════════════════════════════════════
-- FIN — Schema maestro sincronizado con pipeline Python v2.0
-- ══════════════════════════════════════════════════════════════════════════
