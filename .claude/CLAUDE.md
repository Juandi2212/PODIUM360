# CLAUDE.md: Podium VIP Cards (SaaS Predictivo) 

Este es el documento maestro de este repositorio para los asistentes de IA. Este proyecto es un sistema avanzado de análisis predictivo para apuestas deportivas estructurado como Software as a Service (SaaS).

## Project Overview

El sistema ha evolucionado de ser un simple generador de HTML basado en prompts hacia un robusto motor matemático en Python (`model_engine.py`). 

Calcula probabilidades reales utilizando un enfoque híbrido (ratings Elo, xG con decaimiento exponencial, distribución de Poisson) y los compara contra las cuotas más eficientes del mercado (ej. Pinnacle) para encontrar Valor Esperado (EV).

## Estructura de Agentes y Roles

Para trabajar en este proyecto, la IA y los desarrolladores deben revisar las subcarpetas específicas dentro de `.claude/` según la tarea:

- **`/rules/`**: Contiene convenciones de desarrollo estrictas, políticas de obsolescencia de prompts viejos y lineamientos de protección de datos. (Ej: `core_guidelines.md`).
- **`/workflows/`**: Explica el flujo de datos principal y ejecución del pipeline predictivo del sistema (de inputs a outputs _ALERT). (Ej: `prediction_pipeline.md`).
- **`/docs/`**: Contiene la explicación profunda de nuestros algoritmos y pasos matemáticos paso a paso. Consulta `hybrid_model.md` para entender cómo opera el núcleo del código de modelado.
- **`/agents/`**: Perfiles con instrucciones de rol. Se asume el rol de experto matemático (`math_engineer.md`) al manipular el motor interno, o el de narración técnica (`narrative_insights.md`) para procesar los triggers estadísticos.
