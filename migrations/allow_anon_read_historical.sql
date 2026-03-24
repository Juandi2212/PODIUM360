-- ============================================================
-- MIGRACIÓN: Permitir lectura anónima de historical_results
-- ============================================================
-- Ejecutar en: Supabase Dashboard → SQL Editor
-- Propósito: Permitir que el dashboard SaaS (con anon key) 
--            lea las métricas de rendimiento (KPIs, ROI chart).
-- ============================================================

-- Policy para lectura anónima (SELECT) en historical_results
-- Esto es seguro porque solo permite leer, no escribir.
CREATE POLICY "anon_read_historical" ON public.historical_results
  FOR SELECT USING (true);

-- Policy para lectura anónima de daily_board (si no existe)  
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'daily_board' AND policyname = 'anon_read_daily_board'
  ) THEN
    CREATE POLICY "anon_read_daily_board" ON public.daily_board
      FOR SELECT USING (true);
  END IF;
END $$;

-- Policy para lectura anónima de vip_signals (si no existe)
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'vip_signals' AND policyname = 'anon_read_vip_signals'
  ) THEN
    CREATE POLICY "anon_read_vip_signals" ON public.vip_signals
      FOR SELECT USING (true);
  END IF;
END $$;
