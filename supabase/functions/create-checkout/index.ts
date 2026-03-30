// Supabase Edge Function: create-checkout
// Crea una sesión de pago de Stripe y devuelve la URL de checkout.
// Llamada desde el dashboard cuando el usuario hace clic en "Upgrade a PRO".

import Stripe from 'https://esm.sh/stripe@14?target=deno'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

const stripe = new Stripe(Deno.env.get('STRIPE_SECRET_KEY')!, {
  apiVersion: '2024-04-10',
  httpClient: Stripe.createFetchHttpClient(),
})

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
)

Deno.serve(async (req) => {
  // Preflight CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: CORS })
  }

  try {
    // 1. Autenticar usuario via JWT
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) throw new Error('No authorization header')

    const token = authHeader.replace('Bearer ', '')
    const { data: { user }, error: authError } = await supabase.auth.getUser(token)
    if (authError || !user) throw new Error('Usuario no autenticado')

    // 2. Verificar si ya tiene plan PRO
    const { data: profile } = await supabase
      .from('user_profiles')
      .select('stripe_customer_id, plan')
      .eq('id', user.id)
      .single()

    if (profile?.plan === 'pro') {
      return new Response(
        JSON.stringify({ error: 'Ya tienes el plan PRO activo.' }),
        { status: 400, headers: { ...CORS, 'Content-Type': 'application/json' } }
      )
    }

    // 3. Obtener o crear customer en Stripe
    let customerId = profile?.stripe_customer_id

    if (!customerId) {
      const customer = await stripe.customers.create({
        email: user.email,
        metadata: { supabase_uid: user.id },
      })
      customerId = customer.id

      // Guardar el customer_id en user_profiles
      await supabase.from('user_profiles').upsert({
        id: user.id,
        email: user.email,
        stripe_customer_id: customerId,
        plan: 'free',
      })
    }

    // 4. Construir URL base para redirecciones
    const origin = req.headers.get('origin') || 'https://valior.vercel.app'

    // 5. Crear sesión de Stripe Checkout
    const session = await stripe.checkout.sessions.create({
      customer: customerId,
      payment_method_types: ['card'],
      line_items: [{
        price: Deno.env.get('STRIPE_PRICE_ID')!,
        quantity: 1,
      }],
      mode: 'subscription',
      success_url: `${origin}/dashboard.html?checkout=success`,
      cancel_url:  `${origin}/dashboard.html?checkout=canceled`,
      subscription_data: {
        metadata: { supabase_uid: user.id },
      },
      allow_promotion_codes: true,
      locale: 'es',
    })

    return new Response(
      JSON.stringify({ url: session.url }),
      { headers: { ...CORS, 'Content-Type': 'application/json' } }
    )

  } catch (err) {
    console.error('create-checkout error:', err.message)
    return new Response(
      JSON.stringify({ error: err.message }),
      { status: 400, headers: { ...CORS, 'Content-Type': 'application/json' } }
    )
  }
})
