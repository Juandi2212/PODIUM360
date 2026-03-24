-- ══════════════════════════════════════════════════════════════════════════
-- MIGRACIÓN DE SEGURIDAD 1 (RESTRICTED RLS)
-- Propósito: Bloquear a usuarios anónimos de descargar la BD entera vía API.
-- Ejecutar en el SQL Editor de Supabase.
-- ══════════════════════════════════════════════════════════════════════════

-- 1. Eliminar las políticas abiertas y riesgosas (USING true)
DROP POLICY IF EXISTS anon_read_daily_board ON public.daily_board;
DROP POLICY IF EXISTS anon_read_vip_signals ON public.vip_signals;

-- 2. Crear nuevas políticas exigiendo que el usuario tenga un token autenticado JWT
CREATE POLICY auth_read_daily_board 
  ON public.daily_board 
  FOR SELECT 
  TO authenticated 
  USING (true);

CREATE POLICY auth_read_vip_signals 
  ON public.vip_signals 
  FOR SELECT 
  TO authenticated 
  USING (true);
