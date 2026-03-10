# Auditoría CTO — Podium SaaS · Pre-lanzamiento a producción

**Fecha:** Marzo 2026  
**Alcance:** `data_fetcher.py`, `model_engine.py`, `index.html`, `PODIUM_MASTER.md`  
**Objetivo:** Identificar fallos y mejoras críticas antes del lanzamiento.

---

## 1. Manejo de errores y edge cases

### 1.1 Nivel CRÍTICO

| # | Riesgo | Ubicación | Descripción |
|---|--------|-----------|-------------|
| **C1** | **model_engine falla si `xg["local"]` o `xg["visitante"]` es `None`** | `model_engine.py` líneas 450-453 | `run_model()` hace `xg["local"].get("atk")` y `xg["visitante"].get("def")`. Si `data_fetcher` devuelve `"local": null` o `"visitante": null` (equipo no resuelto en Fotmob), se produce **AttributeError: 'NoneType' object has no attribute 'get'** y el pipeline se rompe. |
| **C2** | **print_report asume estructura fija de `data_in`** | `model_engine.py` líneas 416-418, 599, 602 | Si `run_model()` no se ejecutó (solo se leyó JSON), o el JSON tiene otra forma, `data_in["odds"]["mejor_cuota"]` puede generar **KeyError**. Además `print_report(data, output)` usa `data_in["odds"]` sin comprobar si existe; si `data_fetcher` falló y no escribió `odds`, el reporte explota. |
| **C3** | **Partido suspendido o no listado** | `data_fetcher.py` | No hay detección de estado del partido (SCHEDULED / POSTPONED / CANCELLED). Si Football-Data o The Odds API dejan de listar el evento, el script sigue generando `partido_data.json` con datos incompletos y el usuario no recibe un mensaje claro de “partido no disponible o suspendido”. |

**Sugerencias exactas:**

- **C1:** En `run_model()`, antes de usar `xg["local"]` y `xg["visitante"]`, normalizar:  
  `xg_local = xg.get("local") or {}` y `xg_visitante = xg.get("visitante") or {}`, y usar `xg_local.get("atk")`, etc. Mantener el fallback actual a `liga_avg/2` cuando los valores sean `None`, pero evitar acceder a atributos de `None`.
- **C2:** En `print_report()`, obtener odds con `data_in.get("odds") or {}` y `mc = (data_in.get("odds") or {}).get("mejor_cuota") or {}`. Comprobar que `data_in` tenga las claves `partido`, `elo` antes de usarlas; si faltan, imprimir un mensaje tipo “Datos de entrada incompletos” y salir sin acceder a claves anidadas.
- **C3:** En `fetch_all()`, después de obtener fixture y odds, comprobar si el partido existe en la respuesta de The Odds API. Si no hay evento coincidente, escribir en `partido_data.json` un campo `"partido_no_disponible": true` y un mensaje en consola. En el orquestador (o en un script que llame a `model_engine`), comprobar ese flag y no ejecutar el modelo ni generar tarjeta; devolver mensaje explícito al usuario.

---

### 1.2 Nivel MEDIO

| # | Riesgo | Ubicación | Descripción |
|---|--------|-----------|-------------|
| **M1** | **Cambio de esquema en APIs externas** | `data_fetcher.py` | Fotmob: `resp.json()["TopLists"][0]["StatList"]` — si la API devuelve `TopLists: []` o cambia la estructura, **IndexError** o **KeyError**. Football-Data: `standings_list[0]["table"]` y `entry["team"]["name"]` — mismo riesgo. No hay validación de estructura antes de acceder. |
| **M2** | **API caída o timeout** | `data_fetcher.py` `_get()` | Los errores se acumulan en `_errors` y se imprime el resumen al final, pero **el script sigue adelante** con datos parciales. Si ClubElo o Football-Data fallan, Elo o standings quedan en `None`; `model_engine` solo valida Elo (raise) y asume que el resto puede ser null. No hay decisión explícita de “abortar si faltan fuentes críticas” ni reintentos. |
| **M3** | **The Odds API devuelve lista vacía o sin Pinnacle** | `data_fetcher.py` `fetch_odds()` | Si `events` está vacía o el partido no está listado, `target` es `None` y se hace `_errors.append(...)` y se retorna `None`. El output queda con `odds.pinnacle` y `mejor_cuota` en null. `model_engine` ya tiene fallback (solo modelo, sin blend), pero **no se informa al usuario** de que las cuotas no están disponibles y el EV se calcula solo con probabilidades del modelo. |
| **M4** | **División por cero o lambda extremos** | `model_engine.py` `paso_c_lambdas` | Si `liga_avg_goals` es 0 (o no viene y el default 2.5 se sobrescribe por error), `xg_avg = liga_avg / 2` es 0 y hay **división por cero** en `atk_l_idx = xg_atk_local / xg_avg`. No hay clamp de `liga_avg` a un mínimo seguro (p. ej. 2.0). |

**Sugerencias exactas:**

- **M1:** En cada función que parsea JSON de una API, usar accesos seguros: p. ej. `(resp.json() or {}).get("TopLists") or []` y comprobar `if not stat_list: continue` antes de iterar. Para Football-Data, comprobar `if not table: return empty_standings, None, ...` y usar `.get("team", {}).get("name")` con defaults. Documentar la versión/contrato de API asumido o añadir un comentario con la URL de documentación.
- **M2:** Introducir una política clara: p. ej. “fuentes críticas” = Elo + al menos una de (xG, Football-Data standings). Si tras los fetches las críticas fallan, no escribir `partido_data.json` y salir con `sys.exit(1)` y mensaje “Datos insuficientes para generar análisis”. Opcional: 1–2 reintentos con backoff solo para requests que fallaron por timeout o 5xx.
- **M3:** En `fetch_all()`, cuando `fetch_odds()` retorna `None`, imprimir en consola una línea explícita: “The Odds API: partido no encontrado o sin cuotas — el modelo usará solo probabilidades propias.” Incluir en `partido_data.json` un campo `"odds_disponibles": false` para que cualquier consumidor (incl. model_engine o un futuro orquestador) pueda decidir si mostrar advertencia en la tarjeta.
- **M4:** En `run_model()`, antes de llamar a `paso_c_lambdas`, hacer `liga_avg = max(2.0, liga_avg)` (o constante `LIGA_AVG_MIN = 2.0`). Así se evita división por cero y valores de lambda absurdos.

---

### 1.3 Nivel BAJO

| # | Riesgo | Ubicación | Descripción |
|---|--------|-----------|-------------|
| **B1** | **Forma (form) con partidos sin resultado** | `data_fetcher.py` `fetch_form_fdorg()` | Se asume `m["score"]["fullTime"]["home"]` y `["away"]` presentes; si la API devuelve `null` en algún partido, ya se hace `if hs is None or as_ is None: continue`. Si todos son null, `forma` queda vacía y se retorna `None`. Aceptable; solo asegurarse de que el consumidor no espere siempre una lista de 5. |
| **B2** | **Nombres de equipos con caracteres especiales** | `data_fetcher.py` | `_fuzzy` y diccionarios de alias cubren muchas variantes; ligas o equipos nuevos pueden no matchear. No hay normalización Unicode (NFD/NFC). Riesgo bajo si el input lo controla el operador. |
| **B3** | **model_engine no valida tipo de partido_data.json** | `model_engine.py` | Si el archivo está corrupto o es un array en vez de objeto, `json.load` puede devolver list y `data["partido"]` falla. Un try/except en `main()` que capture `KeyError`/`TypeError` y devuelva “partido_data.json inválido” mejora la experiencia. |

**Sugerencias exactas:**

- **B1:** Dejar como está; en la documentación indicar que `forma.local` / `forma.visitante` pueden ser `null` cuando no hay partidos finalizados con resultado.
- **B2:** Opcional: normalizar nombres con `unicodedata.normalize("NFC", s)` antes de búsquedas; ampliar alias cuando se incorporen nuevas ligas.
- **B3:** En `main()` de `model_engine.py`, además de `FileNotFoundError`, capturar `(KeyError, TypeError, json.JSONDecodeError)` al leer o al acceder `data["partido"]`, e imprimir mensaje claro antes de `sys.exit(1)`.

---

## 2. Rendimiento y rate limits

### 2.1 Nivel CRÍTICO

| # | Riesgo | Ubicación | Descripción |
|---|--------|-----------|-------------|
| **R1** | **The Odds API consume créditos por request** | `data_fetcher.py` `fetch_odds()` | Cada ejecución de `fetch_all()` hace **1 llamada** a `/v4/sports/{sport_key}/odds` (markets h2h + totals). Según documentación típica, eso consume créditos (p. ej. 1 por request en plan free). Si se automatiza una tarjeta por partido y se lanzan 20 partidos/día, son 20 requests/día. Si en el futuro se llama al endpoint por cada partido por separado (p. ej. eventos por ID), el consumo puede multiplicarse. **No hay caché** de odds para el mismo evento en la misma ejecución ni entre ejecuciones. |
| **R2** | **Sin control de cuotas restantes antes de llamar** | `data_fetcher.py` | Se leen los headers `x-requests-remaining` y `x-requests-used` **después** del request. Si el plan tiene 500 requests/mes y se agotan a mitad de mes, las siguientes llamadas fallan (429 o similar) y esa ejecución no genera tarjeta. No hay comprobación previa ni cola de trabajos para no superar el límite. |

**Sugerencias exactas:**

- **R1:** Documentar en PODIUM_MASTER o en un README del backend: “Una tarjeta = 1 request a The Odds API (fetch de odds por liga)”. Si el producto evoluciona a “N partidos por liga”, usar **un solo** request por liga y matchear local/visitante en memoria para no hacer N requests. Mantener el diseño actual de “una ejecución = un partido” para no gastar de más.
- **R2:** Después de recibir la respuesta de The Odds API, comprobar `remaining = resp.headers.get("x-requests-remaining")`. Si existe y es convertible a int y `int(remaining) < 5`, imprimir advertencia: “Quedan pocas peticiones este mes; considera limitar ejecuciones.” No llamar a la API en bucle sin leer este header en entornos automatizados.

---

### 2.2 Nivel MEDIO

| # | Riesgo | Ubicación | Descripción |
|---|--------|-----------|-------------|
| **R3** | **Football-Data.org: 10 req/min en plan free** | `data_fetcher.py` | En una sola ejecución se hacen varias llamadas: standings, team matches (forma) x2, league matches (avg goals), y posiblemente más para fixture y H2H. Si se acelera el uso (varios partidos seguidos o scripts en paralelo), se puede superar 10 req/min y recibir **429**. No hay `time.sleep()` ni cola entre llamadas a la misma API. |
| **R4** | **Fotmob: sin límite documentado pero sin control** | `data_fetcher.py` | Fotmob no exige API key; el CDN y el API pueden tener límites por IP. Un uso muy intensivo podría provocar bloqueos temporales. El caché in-memory `_FOTMOB_CDN_CACHE` reduce llamadas en la misma ejecución para la misma liga/temporada, lo cual es correcto. |

**Sugerencias exactas:**

- **R3:** Entre llamadas a `_fdorg()` (o dentro de `_fdorg`), añadir `time.sleep(6)` (o 60/10 = 6 segundos) para no superar 10 req/min en plan free. Alternativamente, centralizar todas las llamadas a Football-Data en un helper que lleve un timestamp de la última petición y duerma si hace falta.
- **R4:** Mantener el caché actual; si en producción se detectan 403/429 de Fotmob, añadir un retry con backoff y un sleep mínimo (p. ej. 1 s) entre requests al mismo host.

---

### 2.3 Nivel BAJO

| # | Riesgo | Ubicación | Descripción |
|---|--------|-----------|-------------|
| **R5** | **ClubElo sin key y sin rate limit** | `data_fetcher.py` | Dos llamadas por partido (local + visitante). Riesgo bajo; si el sitio cambia o bloquea, el fallback es Elo = None y model_engine ya exige Elo, por lo que el flujo falla de forma controlada. |

---

## 3. Seguridad y despliegue

### 3.1 Nivel CRÍTICO

| # | Riesgo | Ubicación | Descripción |
|---|--------|-----------|-------------|
| **S1** | **Clave API real en .env.example** | `.env.example` | El archivo contiene **ODDS_API_KEY=TU_CLAVE_AQUI**. Si este archivo se sube a un repositorio público o se comparte, la clave queda expuesta. El manual (CLAUDE.md) también menciona esa clave; cualquier persona con acceso al repo puede consumir la cuota del titular. |
| **S2** | **index.html: formulario sin backend** | `index.html` | El CTA usa `<form action="mailto:" method="get">`. Los datos no se envían a ningún servidor propio; se abre el cliente de correo. Para producción SaaS, hace falta un endpoint que reciba el formulario (p. ej. Supabase Edge Function, Formspree, o backend propio), validar y almacenar en BD o enviar email, y no exponer direcciones de correo en el HTML. |

**Sugerencias exactas:**

- **S1:** En `.env.example`, reemplazar la clave real por un placeholder: `ODDS_API_KEY=your_odds_api_key_here`. En CLAUDE.md (o en la documentación que cite la clave), eliminar la clave o sustituirla por “configurar ODDS_API_KEY en .env”. Rotar la clave actual en the-odds-api.com si el .env.example o CLAUDE.md han sido compartidos o versionados.
- **S2:** Definir un flujo de contacto para producción: (1) formulario POST a una URL (Supabase, Vercel serverless, o servicio de formularios), (2) validación de campos, (3) guardado en tabla `leads` o envío por email. Mantener `index.html` estático pero cambiar `action` y `method` y, si se usa JS, enviar por fetch para evitar depender de mailto.

---

### 3.2 Nivel MEDIO

| # | Riesgo | Ubicación | Descripción |
|---|--------|-----------|-------------|
| **S3** | **Dependencias no fijadas para model_engine** | `model_engine.py` / proyecto | `model_engine.py` solo usa stdlib (`json`, `math`, `sys`). No aparece en `requirements.txt` porque no necesita paquetes extra. `data_fetcher.py` sí usa `requests` y `python-dotenv`. **beautifulsoup4** está en requirements pero no se usa en el código actual; puede ser resto de una versión anterior. Si se despliega en un servidor, instalar solo lo necesario evita conflictos. |
| **S4** | **Rutas de archivos fijas en CWD** | `data_fetcher.py`, `model_engine.py` | `OUTPUT_FILE = "partido_data.json"` y `INPUT_FILE = "partido_data.json"`, `OUTPUT_FILE = "model_output.json"`. Si el proceso se ejecuta desde otro directorio (cron, systemd, Docker), los archivos se crean/leen en el directorio de trabajo actual. No hay variable de entorno ni argumento para definir el directorio de datos. |
| **S5** | **Sin healthcheck ni versión de API** | Backend | Para producción, no hay un endpoint tipo `/health` ni cabecera de versión. Útil para despliegue en Docker/Kubernetes o detrás de un load balancer, y para saber qué versión está desplegada. |

**Sugerencias exactas:**

- **S3:** Revisar `requirements.txt`: quitar `beautifulsoup4` si no se usa, o dejarlo con comentario “# opcional para futuras extracciones”. Incluir en el mismo archivo todas las dependencias del proyecto (p. ej. `requests`, `python-dotenv`) y documentar que `model_engine` no requiere instalación extra.
- **S4:** Introducir variables de entorno opcionales, p. ej. `PODIUM_DATA_DIR` o `PODIUM_OUTPUT_DIR`, por defecto el directorio actual. En `data_fetcher` y `model_engine`, construir `INPUT_FILE`/`OUTPUT_FILE` como `os.path.join(os.getenv("PODIUM_DATA_DIR", "."), "partido_data.json")` (y análogo para `model_output.json`). Documentar en README o PODIUM_MASTER.
- **S5:** Si se expone un mini servidor (Flask/FastAPI) para ejecutar el pipeline, añadir ruta `GET /health` que devuelva 200 y un JSON `{"status": "ok", "version": "1.0"}`. Incluir la versión en el docstring o en una constante `__version__` en cada script.

---

### 3.3 Nivel BAJO

| # | Riesgo | Ubicación | Descripción |
|---|--------|-----------|-------------|
| **S6** | **index.html: recursos externos** | `index.html` | Google Fonts y Tailwind CDN se cargan desde terceros. Si esos servicios caen, la landing se ve degradada. Riesgo bajo; para entornos de máxima disponibilidad se pueden self-hostear fuentes y Tailwind. |
| **S7** | **Logs y errores en consola** | `data_fetcher.py` | `_errors` es una lista global; los mensajes se imprimen al final. En producción, convendría enviar estos errores a un logger (logging) con nivel ERROR y, opcionalmente, a un servicio de monitoreo, en lugar de solo print. |

**Sugerencias exactas:**

- **S6:** Opcional: descargar Bebas Neue y Barlow Condensed y servir desde el mismo dominio; compilar Tailwind y servir el CSS estático.
- **S7:** Sustituir o complementar `_errors.append(...)` con `logging.error(...)` y configurar `logging` para que en producción escriba a archivo o a stdout en formato JSON para un agregador de logs.

---

## 4. Resumen ejecutivo

| Nivel   | Cantidad | Acción prioritaria |
|---------|----------|--------------------|
| Crítico | 6        | Corregir antes de cualquier lanzamiento: C1, C2, C3, R1/R2 (documentar y advertir), S1, S2. |
| Medio   | 8        | Planificar para la primera iteración post-lanzamiento: M1–M4, R3–R4, S3–S5. |
| Bajo    | 5        | Mejoras de robustez y operación: B1–B3, R5, S6–S7. |

**Recomendación:** No subir a producción con código que pueda lanzar `AttributeError` o `KeyError` ante datos incompletos (C1, C2). Corregir C1 y C2 con los cambios indicados; a continuación, eliminar la clave real de .env.example y de documentación (S1) y definir el flujo de contacto de la landing (S2). Después de eso, el sistema es desplegable con un flujo manual (ejecutar data_fetcher + model_engine desde un directorio controlado y servir index.html estático), documentando límites de APIs (R1, R2) y añadiendo `requirements.txt` y variables de entorno para rutas (S3, S4) en la misma iteración.

---

*Documento generado a partir de auditoría de `data_fetcher.py`, `model_engine.py`, `index.html` y `PODIUM_MASTER.md`.*
