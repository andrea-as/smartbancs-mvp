# Paquete de evidencia reproducible

Este directorio contiene resultados que pueden regenerarse desde el código.
Las capturas, el video y la presentación final deben agregarse o enlazarse
antes de enviar el correo de finalización.

## Archivos

- `benchmark-results.json`: resultados medidos del entorno local documentados
  en el README; no representan capacidad productiva de 10 000 TPS.
- `etl-quality-report.txt`: salida esperada del ETL con el dataset incluido.

## Regenerar

```powershell
python etl/transform_transactions.py
$env:TOTAL_REQUESTS = "100"
$env:CONCURRENCY = "20"
python tests/load_test.py
```

No se incluyen secretos, datos personales ni credenciales.
