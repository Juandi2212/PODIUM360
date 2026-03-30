// Supabase Edge Function: stripe-webhook
// Recibe eventos de Stripe y actualiza user_profiles en Supabase.
// URL de este endpoint: https://ssvnixnqczpvpiomgrje.supabase.co/functions/v1/stripe-webhook

import Stripe from 'https://esm.sh/stripe@14?target=deno'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const stripe = new Stripe(Deno.env.get('STRIPE_SECRET_KEY')!, {
  apiVersion: '2024-04-10',
  httpClient: Stripe.createFetchHttpClient(),
})

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
)

Deno.serve(async (req) => {
  const signature = req.headers.get('stripe-signature')
  if (!signature) {
    return new Response('Missing stripe-signature header', { status: 400 })
  }

  const body = await req.text()

  // Verificar firma del webhook (previene requests falsos)
  let event: Stripe.Event
  try {
    event = await stripe.webhooks.constructEventAsync(
      body,
      signature,
      Deno.env.get('STRIPE_WEBHOOK_SECRET')!
    )
  } catch (err) {
    console.error('Webhook signature verification failed:', err.message)
    return new Response(`Webhook Error: ${err.message}`, { status: 400 })
  }

  console.log(`Evento recibido: ${event.type}`)

  try {
    switch (event.type) {

      // ── Pago completado → activar plan PRO ──────────────────────────────
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.CheckoutSession
        const uid = session.metadata?.supabase_uid

        if (!uid) {
          console.error('checkout.session.completed: supabase_uid no encontrado en metadata')
          break
        }

        const { error } = await supabase.from('user_profiles').upsert({
          id:                     uid,
          plan:                   'pro',
          stripe_subscription_id: session.subscription as string,
          subscription_status:    'active',
          updated_at:             new Date().toISOString(),
        })

        if (error) console.error('Error actualizando user_profiles (checkout):', error)
        else console.log(`Plan PRO activado para user: ${uid}`)
        break
      }

      // ── Suscripción actualizada ─────────────────────────────────────────
      case 'customer.subscription.updated': {
        const sub = event.data.object as Stripe.Subscription
        const uid = sub.metadata?.supabase_uid

        if (!uid) break

        const status = sub.status // 'active' | 'past_due' | 'canceled' | etc.
        const plan   = status === 'active' ? 'pro' : 'free'

        await supabase.from('user_profiles').update({
          plan,
          subscription_status: status,
          updated_at:          new Date().toISOString(),
        }).eq('id', uid)

        console.log(`Suscripción actualizada para ${uid}: ${status}`)
        break
      }

      // ── Suscripción cancelada → bajar a free ────────────────────────────
      case 'customer.subscription.deleted': {
        const sub = event.data.object as Stripe.Subscription
        const uid = sub.metadata?.supabase_uid

        if (!uid) break

        await supabase.from('user_profiles').update({
          plan:                'free',
          subscription_status: 'canceled',
          updated_at:          new Date().toISOString(),
        }).eq('id', uid)

        console.log(`Plan bajado a free para user: ${uid}`)
        break
      }

      // ── Pago fallido → marcar past_due ─────────────────────────────────
      case 'invoice.payment_failed': {
        const invoice    = event.data.object as Stripe.Invoice
        const customerId = invoice.customer as string

        const { data: profile } = await supabase
          .from('user_profiles')
          .select('id')
          .eq('stripe_customer_id', customerId)
          .single()

        if (profile) {
          await supabase.from('user_profiles').update({
            subscription_status: 'past_due',
            updated_at:          new Date().toISOString(),
          }).eq('id', profile.id)

          console.log(`Pago fallido para customer: ${customerId}`)
        }
        break
      }

      default:
        console.log(`Evento no manejado: ${event.type}`)
    }

  } catch (err) {
    console.error('Error procesando webhook:', err.message)
    return new Response(`Handler Error: ${err.message}`, { status: 500 })
  }

  return new Response(JSON.stringify({ received: true }), {
    headers: { 'Content-Type': 'application/json' },
  })
})
