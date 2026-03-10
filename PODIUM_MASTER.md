## PODIUM_MASTER — Contexto + Plan del SaaS

> **Propósito de este archivo:** Unificar en un solo documento el contexto de producto y la hoja de ruta técnica de Podium como **SaaS independiente propiedad de Juan Diego**. Aquí se definen la visión, arquitectura, módulos Python clave (`model_engine.py`, `data_fetcher.py`), flujos de trabajo y el plan de trabajo actual (Landing Page) con la evolución hacia un **método híbrido de análisis**.

---

## 1. Visión del producto (SaaS Podium)

**Qué es Podium:**
- Un **SaaS y Motor de Datos Analíticos para apuestas deportivas**, operado por Juan Diego.
- Produce **Insights Masivos de Partidos**, con cálculo automatizado de Expected Value (+EV) mediante recolección de datos multilibro por Python y análisis narrativo sintetizado por IA.
- Se integra de forma natural con canales de Telegram u otras plataformas de terceros, pero **la tecnología, prompts, lógica y scripts son 100% propiedad de Juan Diego**.

**Para quién es:**
- **Operadores de canales de apuestas deportivas** (ej. canales de Telegram en LATAM).
- **Afiliados de casas de apuestas** que necesitan contenido profesional para mejorar conversión y retención.
- **Tipsters y marcas personales** que quieren elevar la calidad de su contenido sin contratar un equipo de analistas.

**Problema que resuelve:**
- Reemplaza equipos de 6+ personas por una operación **en gran parte automatizada** apoyada en IA y scripts Python.
- Entrega análisis con **datos verificables y cálculo matemático de valor esperado**, en lugar de “tips” improvisados.
- Genera un **portfolio medible de resultados** y un histórico de aciertos gracias al tracking en base de datos.

**Modelo de negocio (visión SaaS):**
- Podium se ofrece como:
  - **Herramienta interna de Juan Diego** para operar sus propios canales.
  - **SaaS B2B ligero**: acceso al sistema a cambio de una tarifa mensual + posible variable ligada a rendimiento, siempre manteniendo la propiedad total del stack en manos de Juan Diego.
- Independiente de cualquier inversor o socio específico. Podium se conecta a **cualquier casa de apuestas o canal** según los acuerdos comerciales que Juan Diego decida.

---

## 2. Arquitectura técnica de alto nivel

**Componentes principales:**

- **Capa de IA (Claude / LLM):**
  - Orquestación narrativa opcional.
  - Generación de JSON con insights, validación cualitativa y empaque lógico (Explicar POR QUÉ un EV arrojó un +3%).

- **Capa Python (backend data-first):**
  - `data_fetcher.py` — módulo de recopilación de datos (RapidAPI, The Odds API).
  - `model_engine.py` — motor matemático de análisis, cálculo Poisson y cruce de EV%.
  - Archivos JSON en `/Pronosticos/` que sirven como API para la DB.

- **Base de datos (Supabase — PostgreSQL):**
  - Tabla `public.partidos` para registrar cada partido, predicción matemática e insights narrativos.

- **Capa de Presentación (Frontend / Dashboard futuro):**
  - Lector de base de datos que consumirá el EV% de `model_engine.py` y el JSON narrativo de la IA.
  - La UI dibujará la data, en lugar de renderizarse mediante el LLM.

- **Distribución:**
  - Envío al SaaS o a Dashboards.
  - Integración vía API con canales de Telegram si se desea crear la gráfica en el servidor, separada de la redacción.

**Regla de diseño global:**
- Todo lo que se construye debe ser:
  - **Escalable vía Scripts** (el LLM no renderiza CSS ni estructuras complejas).
  - **Propiedad intelectual de Juan Diego** (prompts, Python, esquemas de BD).

---

## 3. Módulos Python clave

### 3.1 `data_fetcher.py`

**Rol:** Módulo responsable de obtener datos deportivos de forma estructurada y en el **orden de prioridad definido**.

**Responsabilidades:**
- Implementar funciones que llamen, en este orden:
  1. `fetch_sports_data` (SportRadar u origen equivalente integrado en Claude)  
     - Standings, scores, fixtures, stats básicas y avanzadas si están disponibles.
  2. `web_search`  
     - Cuotas, noticias de lesiones/sanciones, probabilidad de mercado, estadísticas contextuales.
  3. RapidAPI (ej. API-Football)  
     - H2H detallado, lesiones con detalle médico, xG y stats avanzadas.

- Unificar la respuesta en estructuras Python claras (p.ej. dataclasses o diccionarios normalizados) para que `model_engine.py` no tenga que preocuparse por el origen del dato.

- Aplicar la regla cardinal de datos:
  - **Si un dato no se encuentra en ninguna fuente → `"No disponible"`**.
  - Nunca inventar estadísticas ni lesiones.

- Incluir métricas sobre consumo de API (especialmente RapidAPI) para poder reportar:
  - Nº de llamadas realizadas por tarjeta.
  - Consumo estimado diario disponible.

### 3.2 `model_engine.py`

**Rol:** Motor de análisis y generación de tarjetas. Orquesta los datos de `data_fetcher.py`, calcula +EV, decide qué mercados recomendar y construye el HTML final.

**Responsabilidades:**
- Recibir como input la definición del partido:
  - Local, Visitante, Liga, Fecha, hora, posibles parámetros de versión (FREE/VIP) y usuario opcional para watermark.

- Consumir los datos normalizados de `data_fetcher.py` y:
  - Calcular probabilidades reales por mercado (1X2, goles, BTTS, etc.).
  - Aplicar la fórmula de EV:
    - Probabilidad implícita \(= 1 / \text{cuota decimal} \times 100\)
    - EV% \(= (\text{Prob\_real%} - \text{Prob\_implícita%}) / \text{Prob\_implícita%} \times 100\)
  - Evaluar al menos estos mercados:
    1. 1X2 (local / empate / visitante)
    2. BTTS Sí (ambos anotan)
    3. Más de 2.5 goles
    4. Más de 3.5 goles
    5. Asian Handicap (cuando haya cuotas)
    6. Double Chance (cuando tenga sentido)

- Aplicar la regla de negocio crítica:
  - Solo recomendar mercados con **EV ≥ +3%**.
  - Si ningún mercado supera el umbral → mensaje estándar:  
    **"DATOS INSUFICIENTES PARA UNA RECOMENDACIÓN SÓLIDA"**.

- Construir la estructura de datos:
  - Generar el listado final (`top_3_picks`)
  - Empacar en formato JSON (`/Pronosticos/LOCAL_VISIT_DD_MM_YY.json`)
  - Entregar diagnóstico global para auditoría.

---

## 4. Base de datos y tracking (Supabase)

**Tabla principal:** `public.partidos`

Campos clave (resumen):
```text
equipo_local, equipo_visitante, liga, jornada,
fecha_partido, hora_utc, estadio,
pos_local, pts_local, pos_visitante, pts_visitante,
prob_local, prob_empate, prob_visitante,
mercado_ev, cuota_ev, ev_porcentaje, ev_recomendado,
version_generada,
resultado_local, resultado_visitante, prediccion_acertada,
created_at, updated_at
```

**Flujo de uso:**
- **INSERT al generar tarjeta:**  
  Cada vez que se crea una tarjeta (FREE o VIP) se inserta un registro con:
  - Probabilidades y mercados evaluados.
  - Mercado EV recomendado (si lo hay).
  - Versión generada (FREE/VIP).

- **UPDATE post-partido:**  
  Una vez jugado el partido:
  ```sql
  UPDATE public.partidos
  SET resultado_local = [goles_local],
      resultado_visitante = [goles_visitante],
      prediccion_acertada = [true/false],
      updated_at = now()
  WHERE id = [id_del_partido];
  ```

- **Tracking de acierto:**  
  Consultas que calculen:
  - % de predicciones acertadas por periodo.
  - EV medio de los mercados recomendados.
  - Rendimiento por liga/competición.

---

## 5. Flujo de trabajo extremo a extremo

**Paso 1 — Recopilación Masiva (`data_fetcher.py`):**
1. Automatizado para iterar sobre ligas mediante SportsRadar / TheOddsAPI y RapidAPI. Extrae todo tipo de estadísticas en diccionario Python.

**Paso 2 — Análisis Computacional (`model_engine.py`):**
1. Cruce matemático entre Datos Predictivos (Elo, xG, Poisson) y Cuotas Actuales Multi-Libro.
2. Identificación del Top 3 de Mercados de cada jornada garantizando > 0 EV.
3. Exportación automatizada de resultados en `/Pronosticos/`.

**Paso 3 — Análisis Narrativo (Capa LLM / Claude):**
1. Se alimenta al LLM de forma Opcional un partido que haya marcado EV alto en el motor de Python.
2. El LLM actúa como redactor experto (`PROMPT-MAESTRO-PODIUM-v2.2.md`), devolviendo `InsightsPayload` estructurado como JSON, aportando validación y "Color".

**Paso 4 — Registro en Supabase:**
- INSERT en `public.partidos` consolidando el JSON de modelo de Python y (opcionalmente) los Insights.

**Paso 5 — Post-partido:**
- UPDATE con resultados reales y flag `prediccion_acertada` usando un script periódico.

---

## 6. Diseño Visual (SaaS Dashboard & Generación Opcional)

Si bien la inteligencia ahora reside en Python y el LLM responde en JSON, la plataforma SaaS final dibujará el contenido priorizando la siguiente estética a lo largo de Landing Pages y Dashboards:

- **Dark Mode obligatorio**: fondo oscuro para maximizar contraste (`#0b0d1c`).
- **Verde neón** (`#25d466`) para EV positivo.
- **Tipografías**: Títulos en *Bebas Neue*, Cuerpo en *Barlow Condensed*.

(La migración de la interfaz se consolidará cuando la capa web Frontend del SaaS reemplace por completo las antiguas "tarjetas Telegram html" que se encuentran en el repositorio por motivos en archivo).

---

## 8. Estructura del proyecto (archivos)

```text
podium/
├── PODIUM_MASTER.md                  ← Este archivo (contexto + plan unificado)
├── PLAN.md                           ← Versión histórica de la hoja de ruta
├── PODIUM_CONTEXTO_PROYECTO.md       ← Versión histórica de contexto
│
├── templates/                        ← Plantillas HTML base (1080px, dark mode)
│   ├── VIP-PNG-template.html
│   ├── VIP-interactive-template.html
│   ├── FREE-PNG-template.html
│   └── assets/                       ← Escudos, iconos, etc.
│
├── output/                           ← Tarjetas generadas (HTML para screenshot)
│   ├── ARSENAL-LIVERPOOL-VIP-PNG.html
│   ├── ARSENAL-LIVERPOOL-VIP.html
│   ├── ARSENAL-LIVERPOOL-FREE-PNG.html
│   └── ...
│
├── portfolio/                        ← Tarjetas y resultados para demo/ventas
│   ├── tarjetas/
│   └── resultados/
│
├── database/
│   ├── schema.sql                    ← Esquema de la tabla `partidos`
│   ├── queries/                      ← Consultas de tasa de acierto, etc.
│   └── migrations/
│
├── backend/
│   ├── data_fetcher.py               ← Módulo Python de recopilación de datos
│   ├── model_engine.py               ← Motor Python de análisis y generación
│   └── utils/                        ← Scripts auxiliares (p.ej. CLI, helpers)
│
└── dashboard/                        ← (Futuro) panel web de seguimiento
    └── README.md
```

---

## 9. Plan de trabajo actual y roadmap

### 9.1 Objetivo actual — Landing Page del SaaS Podium

**Objetivo:** Diseñar y construir una **Landing Page** que presente Podium como un **SaaS de análisis de apuestas deportivas** propiedad de Juan Diego, con foco en:
- Explicar claramente:
  - Qué es Podium.
  - Cómo funciona el método de análisis (datos + EV + IA).
  - Qué resultados y beneficios ofrece a operadores/afiliados.
- Mostrar ejemplos reales de tarjetas (FREE y VIP).
- Recoger leads/contacto (formulario, WhatsApp, Telegram, email).
- Mantener coherencia visual con las tarjetas:
  - **Dark Mode**
  - Acentos en **verde neón** y dorado
  - Tipografías cercanas a Bebas Neue / Barlow Condensed para branding unificado.

**Tareas concretas (fase Landing Page):**
1. Definir estructura de la página:
   - Hero principal (promesa + CTA).
   - Sección “Cómo funciona”.
   - Sección “Ejemplos de tarjetas” (gallery).
   - Sección “Resultados y métricas” (cuando haya datos).
   - Sección “Para quién es”.
   - FAQ y contacto.
2. Redactar copys en español orientados a operadores/afiliados.
3. Trasladar las reglas de diseño (dark mode, verde neón, 1080px como referencia visual) al layout web.
4. Implementar la Landing en la tecnología elegida (HTML estático / framework ligero) manteniendo simplicidad.

### 9.2 Objetivo futuro — Método híbrido de análisis

**Definición (visión):**  
Evolucionar desde un enfoque puramente basado en datos + IA a un **método híbrido** que:
- Combine:
  - Datos estructurados (stats, xG, H2H, lesiones).
  - Modelos de probabilidad basados en reglas.
  - Ajustes manuales/humanos cuando se detecten patrones no capturados por los datos (ej. cambios de entrenador, contexto motivacional).
- Retroalimente el sistema:
  - Usar los resultados históricos en Supabase para ajustar umbrales, pesos de variables y criterios de recomendación.

**Pasos de trabajo (alto nivel):**
1. Extraer dataset histórico desde `public.partidos` con:
   - Probabilidades estimadas.
   - Cuotas, EV calculado.
   - Resultado real.
   - Aciertos y errores.
2. Analizar patrones:
   - Mercados donde el modelo funciona mejor.
   - Ligas donde el rendimiento sea distinto.
   - Situaciones donde se sobreestima o subestima el riesgo.
3. Definir reglas híbridas:
   - Ajustes por liga/competición.
   - Reglas sobre rachas extremas, derbis, fases finales de torneo, etc.
4. Integrar estas reglas en `model_engine.py` de forma parametrizable para poder iterar sin romper el sistema.

### 9.3 Otras fases del roadmap

**Fase estable del motor de tarjetas (parcialmente completada):**
- Plantillas HTML 1080px (FREE, VIP-PNG, VIP interactiva).
- Flujo de generación y registro en Supabase.
- Portfolio inicial de 5–10 partidos reales con resultados.

**Fase dashboard (cuando haga sentido):**
- Web simple conectada a Supabase:
  - Lista de partidos, predicciones, resultados, % acierto.
  - Vistas por liga, periodo, tipo de mercado.

**Fase automatización:**
- Publicación semiautomatizada o automatizada de tarjetas en canales.
- Integración con la Landing Page para transformar leads en usuarios VIP.

---

## 10. Instrucciones para trabajar con Podium (Claude Code / scripts)

1. **Siempre tratar a Podium como un SaaS independiente propiedad de Juan Diego.**  
   Ningún diseño, decisión técnica ni texto debe implicar dependencia de un jefe o inversor.

2. **Para generar tarjetas:**
   - Seguir el flujo completo:
     - `data_fetcher.py` → `model_engine.py` → HTML → Supabase → reporte.

3. **Sobre los datos:**
   - Usar siempre fuentes verificables.
   - Si falta un dato → `"No disponible"`.
   - Nunca inventar lesiones, cuotas o estadísticas.

4. **Sobre el EV:**
   - Solo recomendar mercados con EV ≥ +3%.
   - Si no hay EV positivo aceptable → escribir explícitamente que no hay recomendación sólida.

5. **Sobre el HTML:**
   - Mantener:
     - Ancho 1080px.
     - Dark Mode.
     - Verde neón como color de énfasis.
   - Nunca exponer nombres de fuentes, endpoints, claves ni lógica interna en el HTML.
   - Nunca usar formato de cuotas americano (+150 / -110).

6. **Sobre la Landing Page:**
   - Comunicar Podium como SaaS, no solo como un canal de Telegram.
   - Alinear branding con las tarjetas (dark + verde neón).
   - Destacar la existencia de un método de análisis basado en datos y en evolución hacia un enfoque híbrido.

7. **Propiedad intelectual:**
   - Prompts, código Python, HTML, estructura de BD y procesos son propiedad de Juan Diego.
   - Cualquier uso con terceros se hace bajo licenciamiento o acuerdo comercial, sin ceder el control del sistema.

---

*Versión: 1.0 — Marzo 2026*  
*Estado: SaaS en desarrollo — Objetivo actual: Landing Page + diseño del método híbrido de análisis a futuro*

