# Product Marketing Context — Valior

Lee este archivo antes de ejecutar cualquier tarea de marketing.
No asumas nada que no esté aquí. Si hay conflicto con instrucciones genéricas de una skill, este archivo tiene prioridad.

---

## Qué es Valior

Valior es una herramienta de auditoría de mercados de apuestas deportivas basada en Valor Esperado (EV).

Usa modelos matemáticos propios (Poisson + Elo + xG + forma reciente + H2H) para calcular la probabilidad real de cada resultado en fútbol europeo, y la compara contra las cuotas de las casas de apuestas. El output es un análisis que le dice al usuario si una cuota está sobrevalorada o no — con el trabajo matemático visible, no una señal ciega.

**No es un canal de pronósticos.** Es una herramienta de auditoría. La distinción es el núcleo del diferencial.

**Nota sobre el nombre:** El proyecto se llamaba internamente "Podium 360" durante el desarrollo. El nombre público y comercial es **Valior**. Usar siempre Valior en cualquier pieza de marketing, copy o comunicación externa.

---

## Modelo de negocio

**Plan Gratuito:**
- 2–3 partidos por día (los de menor EV del día)
- Solo mercado 1X2
- Sin narrativa IA, sin historial de ROI
- Sin acceso a señales VIP

**Plan Pago (~$5–8 USD/mes):**
- Todos los partidos del día (todas las ligas disponibles)
- Todos los mercados: 1X2, Over/Under, BTTS, Double Chance, Asian Handicap
- Narrativa Triple Ángulo generada por IA (Gemini 2.5 Flash)
- Pronósticos VIP del día: mercados con EV ≥ 5% curados automáticamente por el modelo
- Historial completo con ROI verificable y público

---

## Usuario objetivo

**Perfil principal (el que convierte a pago):**
Apostador recreativo, hombre, 22–38 años, hispanohablante (Colombia y Latam). Ya sigue uno o varios canales de Telegram de pronósticos. Apuesta con frecuencia en plataformas como Bet365, Betplay, Codere o Wplay. No conoce el concepto de EV formalmente, pero ha perdido dinero siguiendo señales que "sonaban seguras". Tiene poder adquisitivo para $5–8 USD/mes si percibe valor real.

**Lo que este usuario busca:**
No busca una fórmula mágica. Busca una razón para confiar — algo que le explique por qué una apuesta tiene sentido, no solo que "el tipster dice que sí".

**Lo que este usuario NO es:**
- Un trader deportivo profesional con bankroll estructurado
- Alguien nuevo en apuestas (no sabe qué es EV y necesita mucha educación)
- Un matemático o analista de datos

---

## Objeción principal a resolver

**"No entiendo qué es EV ni por qué importa."**

Esta es la barrera de entrada más frecuente. El usuario llega condicionado por años de canales que solo dicen "tip seguro ✅" sin explicar nada. Podium 360 tiene que hacer dos cosas a la vez: explicar EV de forma simple sin perder credibilidad técnica, y demostrar que esa transparencia es exactamente el diferencial.

**Cómo resolverlo en el copy:**
- Nunca mencionar EV sin una frase de contexto inmediata. Ejemplo: "EV (Valor Esperado): qué tan desajustada está la cuota respecto a la probabilidad real del partido."
- Usar analogías concretas antes que fórmulas. El usuario entiende "la casa siempre gana porque cobra de más" — partir de ahí.
- Mostrar el número del modelo junto a la cuota real. Ver la diferencia es más persuasivo que explicarla.

---

## Diferencial competitivo

| Canal de señales típico | Valior |
|------------------------|--------|
| "Tip seguro, confía en mí" | Probabilidad calculada por modelo propio |
| Sin historial verificable | ROI histórico público, pick por pick |
| Criterio editorial opaco | Curación automática por EV ≥ 5% |
| Solo el resultado | Metodología visible en cada análisis |

**El argumento central:** Cualquier canal puede acertar. Solo Valior muestra por qué acertó — y eso es lo que permite aprender y verificar.

---

## Tono y voz

**Neutro y profesional — como una herramienta, no un gurú.**

- Habla como un analista, no como un influencer de apuestas
- Sin emojis de fuego, sin "🔥 tip bomba", sin lenguaje de hype
- Sin promesas de ganancia. Nunca "vas a ganar", siempre "el modelo identifica valor"
- Precisión antes que emoción: datos, porcentajes, comparaciones
- Accesible: términos técnicos siempre acompañados de su explicación en la misma frase
- Primera persona del producto cuando sea necesario: "Valior calcula...", no "nosotros creemos..."

**Frases que SÍ funcionan:**
- "El modelo detectó un EV de +7.3% en este mercado."
- "La cuota ofrecida está 6 puntos por encima de la probabilidad calculada."
- "Historial público. Cada pick, cada resultado, cada cifra verificable."

**Frases que NO usar jamás:**
- "Tip del día 🔥"
- "Pronóstico seguro"
- "Mi experto dice que..."
- "No te lo pierdas"
- "Gana dinero apostando"

---

## Canales de adquisición actuales

- **TikTok (~15K seguidores):** Contenido educativo sobre EV y value betting. El usuario llega aquí primero — no conoce el producto, conoce el concepto.
- **Telegram (~15K seguidores):** Preview diario con 1 análisis gratuito. Aquí el usuario ya tiene contacto con el producto — es el canal de conversión más directo.

**Flujo típico:** TikTok educa → Telegram muestra el producto → web convierte a pago.

---

## Lo que Valior nunca promete

- Rentabilidad garantizada
- Porcentaje de aciertos fijo
- "El mejor tipster"
- Resultados pasados como garantía de resultados futuros

Si una skill sugiere copy que roce cualquiera de estos puntos, descártalo. El proyecto opera en un espacio regulado y la credibilidad a largo plazo depende de no sobre-prometer.

---

## Stack y contexto técnico relevante para marketing

- El dashboard muestra análisis en tiempo real conectado a Supabase
- La narrativa de cada partido es generada por IA (Gemini 2.5 Flash) — esto es un feature destacable: no es copy genérico, es análisis contextualizado partido a partido
- El historial de ROI es público y verificable — úsalo como prueba social, no como promesa
- Precio en USD pero público Latam: mencionar siempre equivalencia en moneda local cuando sea relevante (ej: "menos de 25,000 COP al mes")
