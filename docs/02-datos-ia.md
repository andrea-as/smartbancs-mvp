# Sustentación — Datos e IA

## Gobierno y calidad

La fuente transaccional debe conservar registros ACID y trazables. La capa analítica es derivada y debe reconciliarse contra la fuente autorizada.

Controles:
- completitud;
- unicidad;
- validez;
- consistencia;
- exactitud;
- frescura;
- trazabilidad.

El ETL registra filas procesadas, válidas y rechazadas.

## Ciclo de vida del modelo

1. Ingesta de datos autorizados.
2. Validación/versionado del dataset.
3. Train/validation/test.
4. Entrenamiento reproducible.
5. Evaluación.
6. Registro de modelo.
7. Despliegue controlado.
8. Monitoreo de precisión, drift y latencia.
9. Reentrenamiento.
10. Rollback si la versión nueva degrada las métricas acordadas.

En un sistema financiero también deben considerarse privacidad, explicabilidad, sesgo, trazabilidad y controles humanos.

La IA del MVP es determinista para demostrar la integración sin depender de una API externa de pago.

### Drift, precisión y consumo de recursos

En producción se registrarían las características usadas por el modelo, la
distribución de predicciones y las etiquetas reales disponibles posteriormente.
Se compararían ventanas recientes contra el conjunto de referencia mediante
PSI, KS u otra prueba aprobada por el equipo de datos. Un aumento sostenido
del drift activaría revisión, no un reentrenamiento automático sin controles.

La calidad del modelo se vigilaría con precisión, cobertura, tasa de
recomendaciones descartadas, latencia p95, errores y porcentaje de trabajos
reprocesados. Cada versión tendría un conjunto de validación, umbrales de
promoción, despliegue gradual y rollback.

Para controlar costos y capacidad se medirían CPU, memoria, tamaño de lote,
longitud de la cola, concurrencia de workers y tiempo de inferencia. El worker
se escalaría según la profundidad de la cola y se limitarían recursos por
contenedor. El MVP usa reglas deterministas y una espera simulada de 0.5 s;
esto demuestra el contrato asíncrono sin consumir una API externa ni incurrir
en costos de inferencia.
