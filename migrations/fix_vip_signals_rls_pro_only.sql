-- Fix #2: Proteger vip_signals con RLS — solo usuarios PRO pueden leer
-- Ejecutar en: Supabase Dashboard → SQL Editor
-- Fecha: 2026-05-11

-- 1. Eliminar la política permisiva que permitía acceso anónimo
DROP POLICY IF EXISTS anon_read_vip_signals ON public.vip_signals;
DROP POLICY IF EXISTS "anon_read_vip_signals" ON public.vip_signals;

-- 2. Crear política que solo permite lectura a usuarios autenticados con plan='pro'
CREATE POLICY pro_read_vip_signals ON public.vip_signals
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE user_profiles.id = auth.uid()
      AND user_profiles.plan = 'pro'
    )
  );

-- Verificación: ejecutar estas queries para confirmar el estado de las políticas
-- SELECT policyname, cmd, roles, qual FROM pg_policies WHERE tablename = 'vip_signals';
-- La única fila debe ser: pro_read_vip_signals | SELECT | {authenticated} | (EXISTS (...))
