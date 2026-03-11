# Reglas y Contexto del Desarrollo

- **Stack Tecnológico**: Predominantemente Python sin backend web tradicional expuesto al cliente directamente.
- **Obsoletización**: Ignorar por completo cualquier instrucción antigua relacionada a "generar tarjetas HTML manualmente con Claude" o el uso de "PROMPT-MAESTRO-PODIUM-v2.2.md". El sistema es ahora puramente algorítmico y emite JSON.
- **Manejo de Datos**: El script debe mantener las protecciones anti-errores (fallbacks de 1500 Elo, promedios de temporada en caso de falta de xG individual). Nunca forzar datos inventados ni sobreestimar probabilidades.
