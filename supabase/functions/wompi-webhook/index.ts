// Supabase Edge Function: wompi-webhook
// Recibe eventos de Wompi y activa el plan PRO en user_profiles automáticamente.
// URL: https://ssvnixnqczpvpiomgrje.supabase.co/functions/v1/wompi-webhook

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
)

// Accede a un valor anidado usando notación de punto: "transaction.id" → obj.transaction.id
function getNestedValue(obj: Record<string, unknown>, path: string): string {
  const value = path.split('.').reduce((current: unknown, key) => {
    if (current && typeof current === 'object') return (current as Record<string, unknown>)[key]
    return undefined
  }, obj)
  return value !== undefined && value !== null ? String(value) : ''
}

// Verifica el checksum de integridad de Wompi
// SHA256(prop1_value + prop2_value + ... + WOMPI_INTEGRITY_SECRET)
async function verifyIntegrity(
  eventData: Record<string, unknown>,
  signature: { checksum: string; properties: string[] },
  secret: string
): Promise<boolean> {
  if (!signature?.checksum || !Array.isArray(signature.properties)) return false

  const concatenated =
    signature.properties.map((prop) => getNestedValue(eventData, prop)).join('') + secret

  const hashBuffer = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(concatenated)
  )
  const hashHex = Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')

  return hashHex === signature.checksum
}

Deno.serve(async (req) => {
  // Wompi solo envía POST
  if (req.method !== 'POST') {
    return new Response('Method Not Allowed', { status: 405 })
  }

  let body: Record<string, unknown>
  try {
    body = await req.json()
  } catch {
    return new Response('Invalid JSON', { status: 400 })
  }

  const integritySecret = Deno.env.get('WOMPI_INTEGRITY_SECRET')
  if (!integritySecret) {
    console.error('WOMPI_INTEGRITY_SECRET no configurado')
    return new Response('Internal Server Error', { status: 500 })
  }

  // Verificar firma de integridad
  const signature = body.signature as { checksum: string; properties: string[] } | undefined
  if (!signature) {
    console.error('Payload sin signature — rechazado')
    return new Response('Missing signature', { status: 400 })
  }

  const isValid = await verifyIntegrity(body.data as Record<string, unknown>, signature, integritySecret)
  if (!isValid) {
    console.error('Firma de integridad inválida — posible request falso')
    return new Response('Invalid signature', { status: 401 })
  }

  const event = body.event as string
  const transaction = (body.data as Record<string, unknown>)?.transaction as Record<string, unknown> | undefined

  console.log(`Evento Wompi: ${event} | status: ${transaction?.status}`)

  // Solo procesar transacciones aprobadas
  if (event === 'transaction.updated' && transaction?.status === 'APPROVED') {
    const reference = transaction.reference as string | undefined

    if (!reference) {
      console.error('Transacción APPROVED sin reference — no se puede identificar usuario')
      return new Response(JSON.stringify({ received: true }), {
        headers: { 'Content-Type': 'application/json' },
      })
    }

    // El reference es el email del usuario (enviado por upgradeToPro())
    const email = decodeURIComponent(reference)
    console.log(`Activando PRO para: ${email}`)

    const { error } = await supabase
      .from('user_profiles')
      .update({
        plan:                'pro',
        subscription_status: 'active',
        updated_at:          new Date().toISOString(),
      })
      .eq('email', email)

    if (error) {
      console.error(`Error actualizando user_profiles para ${email}:`, error)
    } else {
      console.log(`Plan PRO activado correctamente para ${email}`)
    }
  }

  // Siempre responder 200 para que Wompi no reintente
  return new Response(JSON.stringify({ received: true }), {
    headers: { 'Content-Type': 'application/json' },
  })
})
