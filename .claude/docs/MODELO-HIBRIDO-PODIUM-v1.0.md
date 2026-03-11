# Manual de Lógica Predictiva — Modelo Híbrido Podium v1.0

---

## PARTE 1 — Fortalezas y debilidades por modelo y mercado

| Modelo | Brilla en | Falla en | Por qué |
|---|---|---|---|
| **Poisson** | Over/Under, BTTS, Total goles | 1X2 directo, partidos atípicos | Modela bien volumen de goles pero asume independencia entre equipos |
| **xG** | Forma reciente, equipos con mala puntería | Muestras pequeñas (<5 partidos) | Captura calidad real de ocasiones, no suerte en conversión |
| **Elo** | 1X2, fuerza relativa largo plazo | Copas, cambios de entrenador, equipos en transformación | Rating histórico lento en reflejar cambios estructurales |
| **Market Calibration** | Todos los mercados como validador | No detecta value por sí solo | Es el consenso del mercado, no una predicción independiente |

---

## PARTE 2 — Lógica de integración: cómo se alimentan entre sí

El modelo no es un promedio simple. Es una cadena donde cada componente refina al anterior.

### Cadena de cálculo

**Paso A — Elo establece la base de fuerza relativa**

```
P_elo_local = 1 / (1 + 10^((Elo_visitante - Elo_local - 60) / 400))

El +60 es el ajuste estándar de ventaja de local en fútbol.
```

Este valor no se usa directamente como probabilidad final. Se convierte en un factor de ajuste de fuerza:

```
factor_elo = log(P_elo_local / (1 - P_elo_local))
```

**Paso B — xG construye los lambdas de Poisson**

En lugar de usar goles reales históricos para estimar los parámetros de Poisson, usamos xG de los últimos N partidos con decay exponencial para que los partidos recientes pesen más:

```
xG_atk_local   = Σ(xG_generados_local[i] × 0.85^i) / Σ(0.85^i)
xG_def_local   = Σ(xG_concedidos_local[i] × 0.85^i) / Σ(0.85^i)
xG_atk_visit   = igual para visitante
xG_def_visit   = igual para visitante

donde i = 0 es el partido más reciente, i = 1 el anterior, etc.
N recomendado = 8 partidos. Mínimo aceptable = 5.
```

**Paso C — Elo corrige los lambdas de Poisson**

Los xG absolutos deben convertirse en índices relativos al promedio de la liga antes de multiplicar. De lo contrario el lambda resultante se infla de forma irreal (prediciendo 4-5 goles por partido con demasiada frecuencia).

```
xG_atk_local_idx  = xG_atk_local  / xG_avg_liga
xG_def_visit_idx  = xG_def_visit  / xG_avg_liga
xG_atk_visit_idx  = xG_atk_visit  / xG_avg_liga
xG_def_local_idx  = xG_def_local  / xG_avg_liga

λ_local = xG_atk_local_idx × xG_def_visit_idx × liga_avg_goals × e^(0.3 × factor_elo)
λ_visit = xG_atk_visit_idx × xG_def_local_idx × liga_avg_goals × e^(-0.3 × factor_elo)
```

Ejemplo con valores reales:
```
xG_atk_local = 2.1,  xG_def_visit = 1.8,  xG_avg_liga = 1.35

Sin normalizar:  λ_local = 2.1 × 1.8 × 1.35 = 5.1  ← incorrecto
Con normalizar:  λ_local = 1.56 × 1.33 × 1.35 = 2.8 ← correcto
```

El exponente 0.3 es el peso de Elo sobre Poisson. Suaviza la influencia para evitar que una diferencia grande de Elo distorsione los lambdas.

**Paso D — Poisson genera la matriz de marcadores**

```
P(i, j) = (e^-λ_local × λ_local^i / i!) × (e^-λ_visit × λ_visit^j / j!)

para i, j ∈ {0, 1, 2, 3, 4, 5, 6+}
```

De esta matriz se derivan todas las probabilidades de mercado:

```
P_modelo_local   = Σ P(i,j) donde i > j
P_modelo_empate  = Σ P(i,j) donde i = j
P_modelo_visit   = Σ P(i,j) donde i < j
P_over25         = Σ P(i,j) donde i+j > 2
P_btts           = Σ P(i,j) donde i > 0 AND j > 0
```

**Paso E — Market Calibration como capa final**

Las probabilidades del modelo se combinan con las fair odds de Pinnacle:

```
P_fair_pinnacle = prob Pinnacle sin vig

P_final = (w_modelo × P_modelo) + (w_market × P_fair_pinnacle)
```

Los pesos por mercado son:

```
1X2:        w_modelo = 0.45,  w_market = 0.55
Over/Under: w_modelo = 0.55,  w_market = 0.45
BTTS:       w_modelo = 0.60,  w_market = 0.40
Corners:    w_modelo = 0.25,  w_market = 0.75
```

Corners tiene peso de mercado alto porque el modelo Poisson no tiene componente de corners. El mercado sabe más que el modelo en ese caso.

---

## PARTE 3 — Protocolo de decisión cuando modelo y mercado divergen

### Jerarquía de decisión

```
CASO 1 — Modelo y mercado coinciden (diferencia < 3%)
  → No hay edge. No recomendar.
  → El mercado ya incorporó la información que el modelo detecta.

CASO 2 — Modelo supera al mercado (P_modelo > P_fair + umbral)
  → Edge potencial detectado.
  → Calcular EV con la mejor cuota disponible entre todos los bookmakers.
  → Recomendar solo si EV > +3%.

CASO 3 — Mercado supera al modelo (P_fair > P_modelo significativamente)
  → El mercado sabe algo que el modelo no captura.
  → Señal de alerta: puede haber información no pública (lesión no anunciada,
    alineación táctica, clima extremo).
  → NO recomendar en contra del mercado. Marcar como "revisar manualmente".

CASO 4 — Modelo y mercado divergen fuertemente (> 10%)
  → Revisar calidad de datos antes de cualquier decisión.
  → Divergencia extrema casi siempre indica dato corrupto o partido especial
    (final de copa, partido de ida con ventaja, etc.).
```

### Fórmula de EV final

```
Prob_fair    = P_final (resultado del blend modelo + mercado)
Mejor_cuota  = max(cuotas disponibles en todos los bookmakers para ese mercado)
Prob_bookie  = 1 / Mejor_cuota

EV% = (Prob_fair - Prob_bookie) / Prob_bookie × 100

Recomendar si EV% > +3%
```

---

## PARTE 4 — Escenarios donde modificar o ignorar un modelo

### Ignorar o reducir Elo

```
CONDICIÓN                          ACCIÓN
─────────────────────────────────────────────────────────
Copa nacional (eliminatoria)       Reducir peso Elo a 0.15
Cambio de entrenador < 5 partidos  Reducir peso Elo a 0.20
Equipo recién ascendido            Inicializar Elo en media de liga
Más de 60 días sin jugar           Aplicar decay: Elo × 0.95
```

### Ignorar o reducir xG

```
CONDICIÓN                          ACCIÓN
─────────────────────────────────────────────────────────
Menos de 5 partidos disponibles    Usar solo goles reales como fallback
Datos xG no disponibles para liga  Sustituir con ratio goles/partido × liga_avg
Equipo con cambio táctico radical  Reiniciar ventana rolling desde partido 0
```

### Señales de contexto que el modelo no captura (ajuste manual)

```
SEÑAL                              AJUSTE RECOMENDADO
─────────────────────────────────────────────────────────
Titular indiscutible baja          λ_atk del equipo × 0.85
Portero titular baja               λ_def del equipo × 1.15
Partido entre semana (fatiga)      λ_def ambos equipos × 1.05
Motivación asimétrica alta         Factor manual ±0.05 en P_final
```

---

## PARTE 5 — Matriz de mercados

| Mercado | Modelos activos | Peso Elo | Peso xG | Peso Poisson | Peso Market |
|---|---|---|---|---|---|
| **1X2 local** | Todos | 0.25 | 0.20 | 0.20 | 0.35 |
| **1X2 empate** | Poisson + Market | 0.10 | 0.15 | 0.35 | 0.40 |
| **1X2 visitante** | Todos | 0.25 | 0.20 | 0.20 | 0.35 |
| **Over 2.5** | xG + Poisson + Market | 0.05 | 0.30 | 0.30 | 0.35 |
| **Under 2.5** | xG + Poisson + Market | 0.05 | 0.30 | 0.30 | 0.35 |
| **BTTS Sí** | xG + Poisson + Market | 0.05 | 0.35 | 0.25 | 0.35 |
| **BTTS No** | Poisson + Market | 0.05 | 0.25 | 0.35 | 0.35 |
| **Corners O/U** | Market dominante | 0.00 | 0.05 | 0.20 | 0.75 |
| **Asian Handicap** | Elo + Market | 0.30 | 0.15 | 0.15 | 0.40 |

---

## PARTE 6 — Regla de Oro Podium

Un pick se marca como VIP si cumple **los tres criterios simultáneamente**:

```
CRITERIO 1 — EV positivo confirmado
  EV% > +3% calculado con P_final vs mejor cuota disponible

CRITERIO 2 — Consenso de modelo
  Al menos dos de los tres modelos estadísticos (Elo, xG, Poisson)
  apuntan en la misma dirección que la recomendación

CRITERIO 3 — Mercado no contradice fuertemente
  P_fair_pinnacle no supera a P_modelo en más de 8 puntos porcentuales
  Si el mercado contradice fuertemente → descartar aunque el EV sea positivo
```

### En pseudocódigo para Claude Code

```python
def es_pick_vip(ev_pct, consenso_modelos, divergencia_mercado):
    if ev_pct <= 3.0:
        return False, "EV insuficiente"
    if consenso_modelos < 2:
        return False, "Modelos no alineados"
    if divergencia_mercado > 8.0:
        return False, "Mercado contradice el modelo"
    return True, "PICK VIP CONFIRMADO"
```

---

## PARTE 7 — Resumen ejecutivo para Claude Code

```
INPUT:
  xG últimos 8 partidos (con decay 0.85)
  Elo actual de ambos equipos
  Odds Pinnacle (para fair value)
  Odds mejores bookmakers (para mejor cuota)
  Liga avg goals (para normalizar lambdas)

PASO 1: Calcular factor_elo desde ratings actuales
PASO 2: Calcular λ_local y λ_visit con xG corregido por Elo
PASO 3: Generar matriz Poisson P(i,j) para marcadores 0-0 a 6-6
PASO 4: Derivar P_modelo para cada mercado desde la matriz
PASO 5: Blend P_modelo con P_fair_pinnacle según pesos por mercado
PASO 6: Calcular EV% para cada mercado con mejor cuota disponible
PASO 7: Aplicar Regla de Oro → marcar picks VIP

OUTPUT:
  JSON con probabilidades por mercado
  EV% por mercado
  Picks VIP confirmados con razones
```

---

*Modelo Híbrido Podium v1.0 — Documento interno confidencial*
