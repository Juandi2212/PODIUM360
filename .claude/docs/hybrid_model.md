# Modelo Híbrido Podium v1.0

Este documento detalla la lógica interna de `model_engine.py`.

El motor matemático procesa los datos (por ejemplo de `partido_data.json`) a través de los siguientes pasos para encontrar el valor esperado (EV):

- **Paso A**: Cálculo de Elo (probabilidades base y factor ajustado por ventaja de localía).
- **Paso B**: Cálculo de Expected Goals (xG) rodado con una tasa de decaimiento (decay) de 0.85. Incorpora fallbacks robustos al promedio de la liga si faltan datos de alguno de los equipos.
- **Paso C**: Cálculo de parámetros $\lambda$ (Lambdas) normalizando el xG con corrección de las métricas Elo obtenidas.
- **Paso D**: Generación de Matriz de Poisson 7x7 (resultados de 0-0 hasta 6-6) con los lambdas.
- **Paso E**: Derivación de probabilidades teóricas del mercado (1X2, Over 2.5, Ambos Marcan / BTTS) a partir de la matriz 7x7.
- **Paso F**: Mezcla (Blend) de las probabilidades generadas por el modelo con las cuotas justas obtenidas del mercado (ej: Pinnacle sin overround/vig), que son balanceadas mediante pesos configurados.
- **Paso G**: Cálculo final del Valor Esperado (EV%) frente a las mejores cuotas disponibles reportadas por las bookies comerciales.
- **Paso H**: Validación de la **Regla de Oro Podium**. Un pick se marca como de alto valor ("VIP") sólo si cumple todos los 3 requisitos simultáneos:
  1. **EV > +3.0%**
  2. **Consenso de modelos $\ge$ 2** (Alineación teórica positiva de al menos dos de los vectores principales: Elo, xG y Poisson).
  3. **Divergencia de mercado $\le$ 8.0 pp** (el mercado no contradice de forma muy agresiva a lo que el modelo indica).
