# CLAUDE.md

This file provides guidance to standard AI assistants when working with code in this repository.

## Project Overview

**Podium VIP Cards (SaaS Predictivo)** — Un sistema avanzado de análisis predictivo para apuestas deportivas estructurado como Software as a Service (SaaS). El sistema ha evolucionado de ser un simple generador de HTML basado en prompts hacia un robusto motor matemático en Python (`model_engine.py`). 

Calcula probabilidades reales utilizando un enfoque híbrido (ratings Elo, xG con decaimiento exponencial, distribución de Poisson) y los compara contra las cuotas más eficientes del mercado (ej. Pinnacle) para encontrar Valor Esperado (EV).

## Arquitectura y Flujo de Trabajo

1. **Obtención de Datos**: Los datos del partido se obtienen a través de `data_fetcher.py` y se guardan en el archivo de entrada `partido_data.json` (actualmente incluye Elo, xG rodado, medias de la liga y cuotas).
2. **Motor del Modelo (`model_engine.py`)**: El núcleo matemático del sistema. Procesa `partido_data.json` a través de los pasos del **Modelo Híbrido Podium v1.0**:
   - **Paso A**: Cálculo de Elo (probabilidades base y factor ajustado por ventaja de localía).
   - **Paso B**: Cálculo de Expected Goals (xG) rodado con una tasa de decaimiento (decay) de 0.85. Incorpora fallbacks robustos al promedio de la liga si faltan datos.
   - **Paso C**: Cálculo de parámetros $\lambda$ (Lambdas) normalizando el xG con corrección de las métricas Elo.
   - **Paso D**: Generación de Matriz de Poisson 7x7 (resultados de 0-0 hasta 6-6).
   - **Paso E**: Derivación de probabilidades del mercado (1X2, Over 2.5, Ambos Marcan / BTTS) a partir de la matriz.
   - **Paso F**: Mezcla (Blend) de las probabilidades del modelo con las cuotas justas de Pinnacle (sin overround / vig), balanceadas mediante pesos configurados.
   - **Paso G**: Cálculo del Valor Esperado (EV%) frente a las mejores cuotas disponibles de las bookies.
   - **Paso H**: Validación **Regla de Oro Podium**. Un pick se marca como "VIP" sólo si cumple los 3 requisitos simultáneos:
     1. EV > +3.0%
     2. Consenso de modelos $\ge$ 2 (Alineación entre Elo, xG y Poisson).
     3. Divergencia de mercado $\le$ 8.0 pp (el mercado no contradice agresivamente al modelo).
3. **Salidas y Triggers (SaaS)**:
   - Los resultados estándar se guardan en formato JSON en el directorio `Pronosticos/` (ej: `[LOCAL]_[VISIT]_[FECHA].json`).
   - Si se detectan picks de altísimo valor (EV $\ge$ +5.0%), se dispara la generación de un archivo extra `[...]_ALERT.json`. Este archivo funciona como el **Trigger** que despierta a la "Capa IA (Insights Narrativos)" del SaaS de Podium.

## Reglas y Contexto del Desarrollo

- **Stack Tecnológico**: Predominantemente Python sin backend web tradicional expuesto al cliente directamente.
- **Obsoletización**: Ignorar por completo cualquier instrucción antigua relacionada a "generar tarjetas HTML manualmente con Claude" o el uso de "PROMPT-MAESTRO-PODIUM-v2.2.md". El sistema es ahora puramente algorítmico y emite JSON.
- **Manejo de Datos**: El script debe mantener las protecciones anti-errores (fallbacks de 1500 Elo, promedios de temporada en caso de falta de xG individual). Nunca forzar datos inventados ni sobreestimar probabilidades.
