-- Migration: Add indexes to historical_results for common query patterns
-- Run once in Supabase SQL Editor.
-- Safe to re-run (IF NOT EXISTS).

-- Index for result_updater.py: WHERE status_win_loss = 'pending'
CREATE INDEX IF NOT EXISTS idx_historical_results_status
    ON public.historical_results (status_win_loss);

-- Index for date-range ROI queries and result_updater grouping by date
CREATE INDEX IF NOT EXISTS idx_historical_results_match_date
    ON public.historical_results (match_date DESC);

-- Index for mercado-specific ROI breakdowns
CREATE INDEX IF NOT EXISTS idx_historical_results_mercado
    ON public.historical_results (mercado);

-- Also ensure mercado column exists in vip_signals (H4 fix)
ALTER TABLE public.vip_signals
    ADD COLUMN IF NOT EXISTS mercado TEXT;

-- Backfill mercado from angulo_matematico for existing rows
UPDATE public.vip_signals
SET mercado = lower(trim(substring(angulo_matematico FROM '\[Mercado:\s*(.+?)\]')))
WHERE mercado IS NULL
  AND angulo_matematico LIKE '%[Mercado:%';
