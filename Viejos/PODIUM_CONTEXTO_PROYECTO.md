# PODIUM — Documento de Contexto del Proyecto

> **Propósito de este archivo:** Servir como contexto completo para Claude Code. Incluye el objetivo del proyecto, la propuesta de valor, todas las decisiones de diseño, arquitectura técnica, flujos de trabajo y reglas de negocio.

---

## 1. QUÉ ES PODIUM

**Podium** es un canal VIP de apuestas deportivas en Telegram que genera tarjetas de análisis pre-partido con datos reales y cálculo de Expected Value (+EV). El producto se diferencia por ofrecer análisis basado en datos verificables, no en "corazonadas" o predicciones inventadas.

### Propuesta de valor
- Tarjetas visuales premium (HTML → PNG) optimizadas para Telegram
- Datos reales de múltiples fuentes verificadas (SportRadar, web scraping, APIs)
- Cálculo matemático de +EV para identificar apuestas con valor real
- Dos niveles de contenido: FREE (anzuelo) y VIP (análisis completo post-depósito)
- Honestidad: si no hay valor, se dice claramente — nunca se fuerza una recomendación

---

## 2. ARQUITECTURA TÉCNICA

### Stack principal
- **Claude (AI):** Motor de análisis, recopilación de datos y generación de HTML
- **Supabase:** Base de datos para registro de partidos, predicciones y seguimiento de aciertos
- **Telegram:** Canal de distribución final (las tarjetas se envían como imágenes PNG)
- **HTML estático:** Formato de las tarjetas (1080px de ancho, optimizado para screenshot)

### Fuentes de datos (en orden de prioridad)

| Prioridad | Fuente | Límite | Datos que provee |
|-----------|--------|--------|------------------|
| 1 | `fetch_sports_data` (SportRadar) | Sin límite | Standings, scores, fixtures, stats de partido |
| 2 | `web_search` | Sin límite | Cuotas, noticias de bajas, probabilidades de modelos |
| 3 | API RapidAPI | ~100 llamadas/día | H2H detallado, lesiones con detalle médico, xG y stats avanzadas |

**Regla cardinal:** Solo incluir datos que vengan de una fuente verificable. Si no se encuentra → "No disponible". NUNCA inventar.

### Base de datos (Supabase)

Tabla principal: `public.partidos`

```
equipo_local, equipo_visitante, liga, jornada,
fecha_partido, hora_utc, estadio,
pos_local, pts_local, pos_visitante, pts_visitante,
prob_local, prob_empate, prob_visitante,
mercado_ev, cuota_ev, ev_porcentaje, ev_recomendado,
version_generada,
resultado_local, resultado_visitante, prediccion_acertada,
created_at, updated_at
```

Después de cada partido se actualiza con el resultado real y si la predicción acertó.

---

## 3. FLUJO DE TRABAJO COMPLETO

Cuando el usuario escribe `Genera tarjeta [datos del partido]`:

### Paso 1 — Recopilar datos reales
```
1. fetch_sports_data → standings + scores (gratis, sin límite)
2. web_search → cuotas + noticias + probabilidades (gratis, sin límite)
3. API RapidAPI → H2H + lesiones detalladas + stats avanzadas (limitado)
4. Si un dato no aparece en ninguna fuente → "No disponible"
```

### Paso 2 — Calcular +EV (solo VIP)
```
Prob. implícita cuota = 1 / cuota decimal × 100
EV = (Prob. real % - Prob. implícita %) / Prob. implícita % × 100
```

Mercados a evaluar siempre:
1. Victoria local / Empate / Victoria visitante (1X2)
2. BTTS Sí (ambos anotan)
3. Más de 2.5 goles
4. Más de 3.5 goles
5. Asian Handicap (si hay cuota)
6. Double Chance (si hay valor)

**EV mínimo aceptable: +3%.** Si ningún mercado lo supera → "DATOS INSUFICIENTES PARA UNA RECOMENDACIÓN SÓLIDA"

### Paso 3 — Generar HTML
Se generan hasta 3 archivos según la versión:
- `[LOCAL]-[VISIT]-FREE-PNG.html` — versión gratuita
- `[LOCAL]-[VISIT]-VIP.html` — versión interactiva con tabs (uso interno)
- `[LOCAL]-[VISIT]-VIP-PNG.html` — versión flat para screenshot/Telegram

### Paso 4 — Registrar en Supabase
INSERT del partido con todos los datos recopilados.

### Paso 5 — Entregar
1. Resumen de datos encontrados
2. Consumo de API reportado
3. Archivos HTML
4. Confirmación de registro en Supabase

---

## 4. DISEÑO DE LAS TARJETAS

### Especificaciones base
```css
/* Dimensiones */
html, body { width: 1080px; background: #0b0d1c; }
.card { width: 1080px; }

/* Tipografía */
Títulos: Bebas Neue (Google Fonts)
Cuerpo: Barlow Condensed (Google Fonts)

/* Paleta de colores */
--bg: #0b0d1c;
--card: #141828;
--border: #1e2340;
--gold: #f5bc2f;
--green: #25d466;
--red: #f04444;
--orange: #fb8c3a;
--yellow: #f5c518;
--text: #e8eef8;
--muted: #8090b0;
```

**Colores de equipos:** Siempre usar los colores reales del equipo (primario y secundario).

### Versión PNG (para Telegram) — Reglas clave
- ❌ Sin JavaScript, sin animaciones CSS, sin tabs navegables
- ❌ Sin listado de últimos 5 partidos por equipo (consume espacio)
- ✅ Todo el contenido visible de corrido (no interactivo)
- ✅ Barras con anchos fijos inline
- ✅ Divisores de sección con título dorado (📊 ESTADÍSTICAS, 💰 CUOTAS, 🚨 BAJAS)
- ✅ Marca de agua VIP incluida
- ✅ Bajas en formato compacto (grilla 2 columnas, emoji semáforo + nombre + motivo)
- **Objetivo:** Lo más corto posible verticalmente. Menos scroll = más calidad en Telegram.

### Versión Interactiva (VIP interno)
- Tabs navegables: STATS · CUOTAS 💰 · BAJAS 🚨
- Animaciones JS y barras animadas
- Archivo de trabajo, NUNCA se comparte con usuarios

### Marca de agua VIP
```css
.watermark { position: absolute; inset: 0; z-index: 9999; pointer-events: none; }
.wm-text { font-family: 'Bebas Neue'; font-size: 44px; letter-spacing: 6px;
  color: rgba(255,255,255,.065); transform: rotate(-35deg); }
```
- Texto por defecto: `PODIUM VIP · EXCLUSIVO`
- Si el usuario especifica @username: alternar entre `@username` y `PODIUM VIP`
- NUNCA se aplica a versión FREE

---

## 5. CONTENIDO POR NIVEL

### 🔓 FREE (anzuelo — datos públicos)
1. Header del partido (liga, fecha, hora, equipos, posiciones)
2. Barra de probabilidades 1X2 (solo porcentajes, sin cuotas)
3. Forma reciente últimos 5 partidos (badges G/E/P)
4. Clasificación básica (posición, puntos, V/E/D)
5. Footer con CTA hacia VIP

**Excluye:** cuotas, EV, predicción, bajas detalladas, H2H, mercados de goles, razones de predicción.

**Footer FREE:**
```
📊 PODIUM | 🔒 DESBLOQUEA EL ANÁLISIS COMPLETO
Regístrate y deposita para acceder a predicciones con valor real
```

### 🔑 VIP (valor real — post-depósito)
1. Header completo con estadio y badges
2. Barra de probabilidades 1X2
3. Tabs/secciones: STATS · CUOTAS · BAJAS
4. Forma reciente con resultados específicos
5. Clasificación detallada (posición, puntos, V/E/D, rachas, xG si disponible)
6. H2H histórico con barras visuales y stats clave
7. Cuotas 1X2 + mercados de goles + otros mercados
8. Bajas completas con semáforo (🔴 baja · 🟠 suspendido · 🟡 duda)
9. Bloque +EV completo (mercado, cuota, barra de EV, cálculo, 4-5 razones)
10. Footer VIP con disclaimer legal

**Footer VIP:**
```
📊 PODIUM VIP | ⭐ ANÁLISIS VIP
EV calculado sobre modelos estadísticos. Las apuestas conllevan riesgo real. Solo +18.
```

---

## 6. REGLAS DE NEGOCIO IMPORTANTES

### Sobre los datos
- Solo datos verificables de fuentes reales
- NUNCA lenguaje absoluto: "gol garantizado", "dominará", "sin duda"
- SÍ permitido: "buena estadística goleadora", "historial favorable", "domina el H2H con X victorias"
- Cuotas SIEMPRE en formato decimal (2.50), NUNCA americano (+150)

### Sobre la recomendación
- Solo recomendar mercados con EV ≥ +3%
- Si no hay valor real → decirlo claramente, no forzar una recomendación
- Cada razón debe ser rastreable a un dato real del Paso 1

### Sobre el HTML
- ❌ NUNCA mostrar nombres de fuentes (Sports Mole, SportRadar, Dimers, etc.)
- ❌ NUNCA sección "Fuentes verificadas" ni similar
- ❌ NUNCA claves API, URLs de endpoints o datos técnicos en el HTML
- ❌ NUNCA comentarios en el código que revelen fuentes o lógica interna
- ❌ NUNCA alineaciones predichas (los equipos las publican 1h antes)
- ❌ NUNCA cuotas en formato americano

### Sobre el consumo de API
- Estimación por tarjeta: 4-5 llamadas a RapidAPI
- Capacidad diaria: ~20 tarjetas con plan gratuito
- Siempre reportar consumo de API al entregar
- Usar herramientas de Claude ANTES que RapidAPI para conservar llamadas

### Versión por defecto
Si el usuario no especifica versión → generar **VIP**.

---

## 7. PLANTILLA HTML DE REFERENCIA

El archivo `PARTIDOS_PLANTILLA.html` contiene una tarjeta de ejemplo (Bournemouth vs Brentford) con el diseño base a 420px. Las tarjetas de producción usan 1080px de ancho.

Estructura de la plantilla:
1. **Banner** — Liga + fecha/hora
2. **Matchup** — Escudos + nombres + posiciones + VS
3. **Barra de probabilidad** — 1X2 con porcentajes
4. **H2H** — Barras horizontales con victorias/empates/derrotas
5. **Goals Grid** — 4 cards (goles local, goles visitante, promedio, BTTS%)
6. **Predicción** — Mercado recomendado + cuota + nota
7. **Footer** — Marca + disclaimer

---

## 8. NOMENCLATURA DE ARCHIVOS

```
[LOCAL]-[VISITANTE]-FREE-PNG.html    → Versión gratuita (para screenshot)
[LOCAL]-[VISITANTE]-VIP.html         → Versión interactiva (uso interno)
[LOCAL]-[VISITANTE]-VIP-PNG.html     → Versión VIP flat (para screenshot/Telegram)
```

Ejemplo: `ARSENAL-LIVERPOOL-VIP-PNG.html`

---

## 9. TRIGGER DE GENERACIÓN

El usuario activa la generación escribiendo:
```
Genera tarjeta [VERSIÓN opcional] [para @username opcional]: [Local] vs [Visitante], [Liga], [Fecha]
```

Ejemplos:
```
Genera tarjeta: Arsenal vs Liverpool, Premier League, 15/03/2026
Genera tarjeta VIP para @CarlosBet99: Arsenal vs Liverpool, Premier League, 15/03/2026
Genera tarjeta FREE: Real Madrid vs Barcelona, La Liga, 22/03/2026
```

---

## 10. POST-PARTIDO: ACTUALIZACIÓN DE RESULTADOS

Después de que el partido se juegue, actualizar en Supabase:
```sql
UPDATE public.partidos
SET resultado_local = [goles], resultado_visitante = [goles],
    prediccion_acertada = [true/false],
    updated_at = now()
WHERE id = [id_del_partido];
```

Esto permite llevar tracking de la tasa de acierto del sistema.

---

## 11. INSTRUCCIONES PARA CLAUDE CODE

Cuando trabajes con este proyecto en Claude Code:

1. **Para generar una tarjeta:** Sigue el flujo completo (datos → EV → HTML → Supabase → entrega)
2. **Para editar el diseño:** La plantilla base está en `PARTIDOS_PLANTILLA.html`, pero las tarjetas de producción son 1080px
3. **Para consultar la BD:** El proyecto usa Supabase con la tabla `public.partidos`
4. **Prioridad de fuentes:** Siempre usar `fetch_sports_data` y `web_search` antes que APIs externas limitadas
5. **Si falta un dato:** Poner "No disponible", nunca inventar
6. **Si no hay EV positivo:** Decirlo honestamente, no forzar recomendaciones

---

## 12. PROPUESTA ESTRATÉGICA PRESENTADA AL JEFE (WICK)

> **Contexto:** Esta es la propuesta formal que se le presentó al jefe/socio (Wick) para justificar la nueva infraestructura. El objetivo era convencerlo de invertir en este sistema para eliminar un balance negativo de -$15,000 en la operación de afiliados de 1XBET. Este texto es clave para que Claude Code pueda analizarlo, proponer mejoras en redacción, estructura, estrategia o negociación.

### 12.1 El problema que se busca resolver

La operación de afiliados tiene un balance negativo de -$15,000. Las causas identificadas son: dependencia de compra de tráfico, canales de Telegram estancados, contenido vacío que mata el engagement, y gestión sin datos reales del comportamiento de los usuarios/apostadores.

### 12.2 Los 4 pilares de la propuesta

**Pilar 1 — Estrategia de Social Media (Atracción orgánica de bajo costo)**
- Dejar de depender solo de compra de tráfico o grupos de Telegram estancados
- Usar TikTok, Instagram y Reels como "mina de oro" por sus algoritmos de recomendación
- Crecimiento sin inversión en publicidad: cada video viral es una entrada gratuita al funnel de ventas (cuentas de soporte en Telegram)
- Innovación con AI: Avatares virtuales de IA y formatos split-screen (highlights del partido + analista). Más barato y rápido que un presentador real. Es el formato que el algoritmo de TikTok premia para aparecer en el "For You"

**Pilar 2 — Panel de Expertos y Contenido Enriquecido (Retención)**
- Cada pronóstico será un reporte técnico profesional, no solo un link
- Tarjetas visuales con análisis y gráficos que respaldan los picks (esto es lo que Podium genera)
- Esto crea crecimiento orgánico por "boca a boca" — NADIE en LATAM lo está haciendo actualmente
- Identidad de marca por país: cada canal (Colombia, México, Brasil) con estilo visual y tono propios para crear comunidad real

**Pilar 3 — VIP Monitor y Auditoría de Datos (Control)**
- Monitoreo científico del comportamiento de depósitos y actividad de usuarios
- Necesidad de acceso al backend de 1XBET o reportes semanales para ejecutar estrategias reales
- Tácticas de retención proactiva: si una "Ballena" (apostador de alto volumen) deja de apostar, se aplican tácticas inmediatas
- Pasar de "gestión basada en esperanza" a gestión basada en datos para limpiar la deuda de -$15,000

**Pilar 4 — Ventaja competitiva**
- Mientras otros afiliados envían mensajes de texto simples que la gente ignora, Podium tiene una plataforma que genera videos atractivos, analiza tendencias y gestiona clientes automáticamente
- Simple para Wick: no necesita aprender la tecnología, el operador maneja la máquina
- Vital para escalar: es la única forma de escalar a 5-10 países sin aumentar costos operativos

### 12.3 Puntos de negociación planteados

**Sobre costos y carga de trabajo:**
- Se necesita definir la densidad de trabajo (videos por semana, canales a gestionar)
- Se requiere un presupuesto mensual fijo para cubrir operación técnica, licencias de software AI y tiempo dedicado
- Se propone discutir un bono de éxito después, pero primero definir una tarifa base operativa
- Pregunta abierta al jefe: ¿cuál es el presupuesto mensual disponible para esta nueva infraestructura?

**Sobre el dashboard (interfaz):**
- Es el "Centro de Comando" que integra todas las herramientas de AI, datos de mercado y automatización de Telegram
- 1XBET sigue siendo la plataforma principal donde se genera el dinero, pero el sistema de Podium es el motor que lleva usuarios allí
- La operación se ve como una corporación profesional, lo cual genera la confianza necesaria para depósitos más altos

**Sobre el acceso a datos del backend:**
- Estrategias data-driven requieren analizar los números reales de los jugadores
- Opción propuesta: acceso "Read-Only" o reportes semanales en Excel
- Esto permite aplicar tácticas de retención a las "Ballenas" para que nunca dejen de apostar

### 12.4 Notas para análisis futuro

Cuando se pida a Claude Code analizar esta propuesta, considerar:
- **Fortalezas:** ¿Qué argumentos son más convincentes y por qué?
- **Debilidades:** ¿Qué puntos son vagos, carecen de números concretos o podrían generar objeciones?
- **Tono de negociación:** ¿El tono es adecuado para la relación con Wick? ¿Es demasiado agresivo, demasiado pasivo, o balanceado?
- **Estructura:** ¿La propuesta fluye lógicamente? ¿Debería reordenarse?
- **Números faltantes:** ¿Qué métricas concretas (ROI proyectado, timeline, KPIs) harían la propuesta más sólida?
- **Riesgos no mencionados:** ¿Qué riesgos debería haber anticipado?
- **Alternativas de pricing:** ¿Cómo estructurar mejor la negociación de la tarifa base vs bono de éxito?

---

*Última actualización: Marzo 2026*
*Proyecto: Podium VIP — Canal de apuestas deportivas en Telegram*
