---
description: Flujo de trabajo principal para la predicción de partidos y generación de picks VIP
---

# Flujo de Trabajo: Generación de Predicciones y Picks VIP

El sistema sigue estos pasos para procesar la información:

1. **Obtención de Datos**: 
   - Script: `data_fetcher.py`.
   - Acción: Obtiene datos del partido y los guarda en `partido_data.json` (Elo, xG rodado, medias de la liga, cuotas).

2. **Procesamiento del Motor (Model Engine)**:
   - Script: `model_engine.py`.
   - Acción: Ejecuta el pipeline matemático completo (ver `docs/hybrid_model.md` para detalles de los pasos algorítmicos).
   - Validación: Aplica la "Regla de Oro Podium". Las selecciones deben cumplir:
     - EV > +3.0%
     - Consenso de modelos >= 2 (Elo, xG, Poisson alineados)
     - Divergencia de mercado <= 8.0 pp

3. **Salidas y Triggers**:
   - Acción: Guarda resultados estándar en formato JSON en `Pronosticos/` (ej: `[LOCAL]_[VISIT]_[FECHA].json`).
   - Alertas Especiales: Si hay picks de EV >= +5.0%, genera `[...]_ALERT.json`.
   - Siguiente paso: Este archivo alerta es el trigger para la "Capa IA (Insights Narrativos)".
