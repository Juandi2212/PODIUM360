-- ══════════════════════════════════════════════════════════════════════════
-- MIGRACIÓN: Tabla user_profiles — Valior Freemium/PRO
-- Ejecutar en: Supabase Dashboard → SQL Editor
-- ══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.user_profiles (
  id                     UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  email                  TEXT,
  plan                   TEXT DEFAULT 'free',             -- 'free' | 'pro'
  stripe_customer_id     TEXT UNIQUE,
  stripe_subscription_id TEXT,
  subscription_status    TEXT DEFAULT 'inactive',         -- 'active' | 'canceled' | 'past_due' | 'inactive'
  created_at             TIMESTAMPTZ DEFAULT NOW(),
  updated_at             TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Usuarios solo leen/actualizan su propio perfil
CREATE POLICY "users_read_own_profile"
  ON public.user_profiles
  FOR SELECT TO authenticated
  USING (auth.uid() = id);

-- Service role escribe todo (webhooks de Stripe)
CREATE POLICY "service_role_all"
  ON public.user_profiles
  FOR ALL TO service_role
  USING (true);

-- Trigger: actualiza updated_at automáticamente
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_updated_at ON public.user_profiles;
CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON public.user_profiles
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Trigger: crea perfil vacío cuando un usuario se registra
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.user_profiles (id, email)
  VALUES (NEW.id, NEW.email)
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
