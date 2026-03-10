# PLAN.md — Podium v1: Hoja de Ruta Técnica

> **Propósito:** Este documento es la hoja de ruta para Claude Code. Contiene todo lo necesario para construir el sistema Podium v1 sin ambigüedades.

---

## 1. RESUMEN DEL PRODUCTO

**Qué es Podium:**
Un sistema de generación de contenido profesional para canales de apuestas deportivas en Telegram. Produce tarjetas de análisis pre-partido con datos reales, cálculo de Expected Value (+EV), y diseño visual premium. Es operado por una sola persona asistida por IA.

**Para quién es:**
- Usuario final: apostadores deportivos en LATAM (principalmente Colombia, Argentina, México, Perú)
- Cliente/socio: inversores que operan esquemas de afiliados con casas de apuestas (1XBET, Betway)

**Qué problema resuelve:**
- Para el apostador: recibe análisis profesional con datos reales en lugar de "tips" inventados
- Para el operador (tú): reemplaza equipos de 6+ personas por una operación de 1 persona con IA
- Para el inversor: reduce costos operativos drásticamente mientras mejora la calidad del contenido

**Modelo de negocio:**
Canal gratuito (anzuelo con contenido limitado) → el usuario se registra y deposita en la casa de apuestas → obtiene acceso al canal VIP (análisis completo con +EV) → el operador cobra comisión de afiliado por cada depósito + tarifa fija mensual por operar el sistema.

---

## 2. CONTEXTO ESTRATÉGICO (importante para decisiones técnicas)

**Situación actual:**
- Existen 6 marcas con ~47,000 suscriptores totales en canales de Telegram abandonados
- No hay equipos operando ningún canal actualmente
- El operador tiene acceso al canal principal (Podium Colombia, 19,000 suscriptores)
- Hay una negociación en curso con el inversor principal (Wick) — sin acuerdo cerrado aún
- Existe un plan B (Jay, operación en China) y un plan C (operación independiente)

**Decisión de diseño crítica:**
Todo lo que se construya debe ser PORTABLE y propiedad del operador. El sistema no debe depender de ningún inversor específico, canal específico, ni casa de apuestas específica. Se conecta a cualquiera de ellos según el acuerdo que se cierre.

**Lo que NO se comparte antes del acuerdo:**
- La infraestructura técnica (Claude, Supabase, prompts, APIs)
- El dashboard de operaciones
- La lógica de cálculo de +EV
- Cualquier detalle que permita replicar el sistema sin el operador

**Lo que SÍ se puede mostrar antes del acuerdo:**
- El output final: tarjetas VIP terminadas de partidos reales
- Resultados: tasa de acierto de predicciones
- El concepto general: "opero con IA lo que antes hacían 6 personas"

---

## 3. ALCANCE DE LA VERSIÓN 1

### ✅ Lo que INCLUYE la v1

**Bloque A — Motor de Tarjetas (construir ahora, sin depender de nadie)**

| Componente | Descripción | Estado |
|---|---|---|
| Prompt de generación | System prompt completo con reglas de datos, EV, diseño y entrega | ✅ Listo |
| Plantilla HTML base | Diseño a 1080px con paleta oscura, tipografía Bebas Neue / Barlow Condensed | ✅ Listo (420px, adaptar a 1080px) |
| Versión VIP-PNG | HTML flat sin JS, optimizado para screenshot/Telegram, con marca de agua | 🔧 Construir |
| Versión VIP interactiva | HTML con tabs navegables (STATS/CUOTAS/BAJAS), uso interno del operador | 🔧 Construir |
| Versión FREE-PNG | HTML reducido (sin cuotas, sin EV, sin predicción), con CTA a VIP | 🔧 Construir |
| Pipeline de datos | fetch_sports_data → web_search → RapidAPI (en ese orden de prioridad) | ✅ Definido en prompt |
| Cálculo de +EV | Fórmula implementada, umbral mínimo de +3%, 6 mercados evaluados | ✅ Definido en prompt |

**Bloque B — Base de Datos y Tracking (construir ahora)**

| Componente | Descripción | Estado |
|---|---|---|
| Tabla `partidos` en Supabase | Registro de cada partido analizado con datos, predicción y resultado | 🔧 Crear/verificar esquema |
| Flujo de registro | INSERT automático al generar tarjeta | 🔧 Construir |
| Flujo de actualización | UPDATE con resultado real post-partido | 🔧 Construir |
| Vista de tasa de acierto | Query que calcule % de predicciones acertadas por período | 🔧 Construir |

**Bloque C — Portfolio de demostración (construir ahora, es tu herramienta de venta)**

| Componente | Descripción | Estado |
|---|---|---|
| 5-10 tarjetas VIP de partidos reales | Generadas con datos reales de partidos recientes o próximos | 🔧 Generar |
| Registro de aciertos | Los 5-10 partidos registrados en Supabase con resultado real | 🔧 Registrar |
| Resumen de resultados | Documento o imagen que muestre la tasa de acierto del sistema | 🔧 Crear |

> **Por qué el portfolio:** Cuando llegue el momento de negociar (con Wick, Jay, o solo), necesitas poder decir "mira, aquí hay 10 partidos analizados, acerté 7, así se ven las tarjetas." Eso es tangible e irrefutable.

**Bloque D — Dashboard del operador (construir después del acuerdo)**

| Componente | Descripción | Estado |
|---|---|---|
| Web simple con datos de Supabase | Lista de partidos, predicciones, resultados, tasa de acierto | 📋 Fase post-acuerdo |
| Vista de canales activos | Qué canales se operan, cuántos suscriptores, última publicación | 📋 Fase post-acuerdo |
| Vista para el inversor (limitada) | Solo muestra resultados y métricas, NO muestra la tecnología detrás | 📋 Fase post-acuerdo |

### ❌ Lo que NO incluye la v1

| Componente | Por qué se excluye | Cuándo se agrega |
|---|---|---|
| Avatares de IA para TikTok/Reels | Requiere acuerdo cerrado + presupuesto para licencias | Fase 2 |
| Bot de Telegram automatizado | Primero operar manual para validar, después automatizar | Fase 2 |
| Monitor de "Ballenas" | Requiere acceso al backend de 1XBET que aún no se tiene | Fase 2 |
| Consolidación de canales | Requiere acuerdo con Wick sobre qué marcas mantener | Fase 2 |
| Operación en China (Jay) | Estrategia completamente diferente, otro mercado | Fase 3 |
| Multi-idioma (portugués para Brasil) | Primero validar en español | Fase 3 |

---

## 4. STACK TÉCNICO

| Capa | Herramienta | Justificación |
|---|---|---|
| Motor de análisis | Claude (Opus/Sonnet) | Genera tarjetas, recopila datos, calcula EV. Es el cerebro del sistema |
| Datos deportivos (primario) | fetch_sports_data (SportRadar) | Sin límite de uso, standings/scores/stats |
| Datos deportivos (secundario) | web_search | Cuotas, noticias, probabilidades de modelos |
| Datos deportivos (terciario) | RapidAPI | H2H detallado, lesiones, xG. Límite: ~100 calls/día |
| Base de datos | Supabase (PostgreSQL) | Gratis para el volumen actual, ya configurado |
| Formato de tarjetas | HTML estático (1080px) | Se convierte a PNG para Telegram vía screenshot |
| Tipografía | Google Fonts (Bebas Neue + Barlow Condensed) | Gratis, embebidas en el HTML |
| Distribución | Telegram (manual) | El operador publica en los canales. Sin bot por ahora |
| Dashboard (post-acuerdo) | React o HTML + Supabase | Web simple, hosting gratuito en Vercel |
| Control de versiones | Claude Code + archivos locales | El operador trabaja desde Claude Code |

**Costo mensual del stack en v1: $0**
Todo el stack actual es gratuito o está incluido en la suscripción de Claude. El único costo es el tiempo del operador.

---

## 5. ESTRUCTURA DEL PROYECTO

```
podium/
├── PLAN.md                          ← Este archivo (hoja de ruta)
├── PODIUM_CONTEXTO_PROYECTO.md      ← Contexto completo del proyecto
│
├── templates/                       ← Plantillas HTML base
│   ├── VIP-PNG-template.html        ← Template para tarjeta VIP (screenshot)
│   ├── VIP-interactive-template.html← Template para tarjeta VIP (con tabs)
│   ├── FREE-PNG-template.html       ← Template para tarjeta FREE (screenshot)
│   └── assets/                      ← Escudos, iconos si se necesitan
│
├── output/                          ← Tarjetas generadas
│   ├── ARSENAL-LIVERPOOL-VIP-PNG.html
│   ├── ARSENAL-LIVERPOOL-VIP.html
│   ├── ARSENAL-LIVERPOOL-FREE-PNG.html
│   └── ...
│
├── portfolio/                       ← Tarjetas para demostración/venta
│   ├── tarjetas/                    ← Las mejores tarjetas generadas
│   └── resultados/                  ← Screenshots de aciertos
│
├── database/                        ← Scripts y esquemas de Supabase
│   ├── schema.sql                   ← Esquema de la tabla partidos
│   ├── queries/                     ← Queries útiles (tasa de acierto, etc.)
│   └── migrations/                  ← Cambios futuros al esquema
│
├── docs/                            ← Documentación adicional
│   ├── propuesta-wick.md            ← Propuesta original a Wick
│   ├── plan-negocio.md              ← Plan de negocio con números (Bloque C)
│   └── decisiones.md                ← Registro de decisiones tomadas
│
└── dashboard/                       ← (Fase post-acuerdo)
    └── README.md                    ← Placeholder hasta que se construya
```

---

## 6. TAREAS PRIORIZADAS

### 🔴 PRIORIDAD ALTA — Hacer ahora (antes del acuerdo)

**Tarea 1: Finalizar las 3 plantillas HTML a 1080px**
- Adaptar la plantilla actual (420px) al formato de producción (1080px)
- Crear las 3 versiones: VIP-PNG, VIP-interactiva, FREE-PNG
- Aplicar las reglas de diseño del prompt (paleta, tipografía, marca de agua)
- Verificar que la versión PNG se ve bien al hacer screenshot
- Complejidad: Media. Estimación: 1-2 sesiones de trabajo.

**Tarea 2: Generar 5-10 tarjetas de partidos reales (portfolio)**
- Elegir partidos de ligas populares (Premier League, La Liga, Champions)
- Ejecutar el flujo completo: datos → EV → HTML → registro en Supabase
- Verificar los resultados reales después del partido y actualizar Supabase
- Esto construye tu track record y tu herramienta de venta
- Complejidad: Baja (el sistema ya está definido). Estimación: 1 tarjeta por sesión.

**Tarea 3: Verificar y completar el esquema de Supabase**
- Confirmar que la tabla `partidos` tiene todas las columnas necesarias
- Crear la tabla si no existe
- Probar INSERT y UPDATE con datos reales
- Crear query de tasa de acierto
- Complejidad: Baja. Estimación: 1 sesión.

**Tarea 4: Preparar el resumen de resultados**
- Una vez que tengas 5+ partidos con resultado real, generar un resumen visual
- Puede ser una tarjeta especial tipo "Resumen Semanal Podium" o un simple documento
- Esto es lo que le muestras a Wick (o Jay, o a futuros clientes)
- Complejidad: Baja. Estimación: 1 sesión.

### 🟡 PRIORIDAD MEDIA — Hacer cuando haya acuerdo

**Tarea 5: Consolidación de canales**
- Definir con el inversor qué marcas se mantienen y cuáles se migran
- Solicitar acceso de admin a todos los canales necesarios
- Planificar la migración de suscriptores si aplica

**Tarea 6: Construir el dashboard del operador**
- Web simple conectada a Supabase
- Vista de partidos, predicciones, resultados, tasa de acierto
- Vista limitada para el inversor (solo resultados, no tecnología)

**Tarea 7: Definir y documentar la operación diaria**
- Cuántas tarjetas por día, de qué ligas, a qué horas publicar
- Flujo de trabajo diario del operador
- Protocolo de actualización post-partido

### 🟢 PRIORIDAD BAJA — Fase 2+

**Tarea 8:** Estrategia de TikTok/Reels con avatares de IA
**Tarea 9:** Bot de Telegram para automatizar publicación y acceso VIP
**Tarea 10:** Monitor de comportamiento de apostadores ("Ballenas")
**Tarea 11:** Expansión a nuevos países/idiomas
**Tarea 12:** Adaptación para mercado chino (plan B con Jay)

---

## 7. DECISIONES PENDIENTES

| # | Decisión | Depende de | Impacto |
|---|----------|------------|---------|
| 1 | ¿Se consolida todo en "Podium" o se mantienen múltiples marcas? | Acuerdo con Wick | Define cuántas plantillas y tonos de contenido necesitas |
| 2 | ¿Cuál es la tarifa mensual que vas a pedir? | Tu decisión | Define el plan de negocio |
| 3 | ¿Se obtiene acceso al backend de 1XBET? | Negociación con Wick | Habilita o bloquea el monitor de Ballenas |
| 4 | ¿Wick acepta o vas con Jay o solo? | Respuesta de Wick | Cambia el mercado, idioma y estrategia completa |
| 5 | ¿Dominio web para el dashboard? | Tu decisión + presupuesto | Necesario solo cuando se construya el dashboard |
| 6 | ¿Qué ligas cubrir en v1? | Tu decisión | Afecta volumen de trabajo diario y fuentes de datos |

---

## 8. SERVICIOS EXTERNOS NECESARIOS

### Activos ahora (sin costo adicional)
- **Claude (Opus/Sonnet):** suscripción actual cubre generación de tarjetas y análisis
- **Supabase:** plan gratuito suficiente para v1
- **Google Fonts:** gratuito (Bebas Neue, Barlow Condensed)
- **SportRadar (vía fetch_sports_data):** incluido en Claude, sin límite
- **Web search (vía Claude):** incluido, sin límite

### Activos con límite
- **RapidAPI (API-Football):** plan gratuito, ~100 llamadas/día, suficiente para ~20 tarjetas/día

### Necesarios post-acuerdo
- **Vercel o similar:** hosting del dashboard (gratis en tier básico)
- **Dominio web:** ~$12/año si se quiere uno personalizado
- **Herramientas de IA para video (TikTok):** a definir en Fase 2, requiere presupuesto

### NO necesarios en v1
- Servicios de email marketing
- CRM
- Pasarelas de pago
- Servidores dedicados

---

## 9. INSTRUCCIONES PARA CLAUDE CODE

Cuando uses este archivo como contexto en Claude Code:

1. **Lee primero** `PODIUM_CONTEXTO_PROYECTO.md` para entender las reglas de negocio, diseño y generación de tarjetas
2. **Lee este archivo** (`PLAN.md`) para entender qué se está construyendo y en qué orden
3. **Empieza por la Tarea 1** (plantillas HTML) a menos que el operador indique otra cosa
4. **Nunca publiques nada** en canales de Telegram sin confirmación explícita del operador
5. **Todo lo que construyas es propiedad del operador**, no de ningún inversor
6. **Si falta un dato para una tarjeta**, pon "No disponible" — nunca inventes
7. **Reporta siempre** el consumo de llamadas a RapidAPI después de generar una tarjeta

---

*Versión: 1.0 — Marzo 2026*
*Estado: Pre-acuerdo — Construyendo motor y portfolio*
*Siguiente revisión: Cuando se cierre acuerdo con inversor*
