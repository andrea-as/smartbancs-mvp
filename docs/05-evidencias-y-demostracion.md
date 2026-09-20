# Evidencias y demostración

## Prerrequisitos

- Docker Desktop iniciado.
- Git instalado.
- Puertos libres 8000, 8001, 5432, 6379 y 9090.

## Ejecución reproducible

Desde la raíz del repositorio:

```powershell
docker compose up --build -d
```

Verificación:

```powershell
docker compose ps
curl.exe http://localhost:8000/health
```

Detención:

```powershell
docker compose down
```

## Guion de video demostrativo

El video debe durar aproximadamente tres minutos y mostrar:

1. `docker compose up --build -d` y los servicios saludables.
2. El dashboard en `http://localhost:8000/`.
3. Una transferencia, por ejemplo `ACC-1003 -> ACC-1004`, por `10 USD`,
   mostrando `COMPLETED`.
4. La consulta de recomendaciones de `ACC-1003`, explicando que el trabajo
   se procesa por Redis sin bloquear la transferencia.
5. Un evento Bancs con monto y cuentas editables, mostrando que se acepta y
   que se normaliza en PostgreSQL.
6. El endpoint `/synthetic/transfer` y `/metrics`.
7. Swagger en `/docs`, mostrando los contratos de transferencia y Bancs.
8. La ejecución del ETL y el archivo `etl/data/clean_transactions.csv`.

No se deben mostrar contraseñas, tokens ni datos personales reales.

## Material de presentación para cuatro minutos

### Minuto 1 — Problema y arquitectura

Explicar API stateless, PostgreSQL como fuente transaccional, Redis como cola,
worker de IA y la capa de integración desacoplada de Bancs.

### Minuto 2 — Demostración funcional

Mostrar transferencia, respuesta menor a dos segundos en el entorno de prueba,
recomendación asíncrona y evento Bancs normalizado.

### Minuto 3 — Operación y observabilidad

Mostrar logs JSON con `request_id` y `transaction_id`, métricas de volumen,
latencia, errores, trabajos IA y journey sintético.

### Minuto 4 — Incidente y decisiones

Explicar diagnóstico de timeouts/deadlocks, contención inmediata, locks en
orden determinista, reconciliación con Bancs y límites del benchmark local.

## Datos de prueba utilizados

Las cuentas demo están definidas en `db/init.sql`:

| Cuenta | Saldo inicial USD |
|---|---:|
| ACC-1001 | 1000 |
| ACC-1002 | 500 |
| ACC-1003 | 750 |
| ACC-1004 | 1200 |
| ACC-1005 | 300 |
| ACC-1006 | 900 |
| ACC-1007 | 1500 |
| ACC-1008 | 425 |
| ACC-1009 | 680 |
| ACC-1010 | 2500 |

El lote crudo del ETL está en `etl/data/raw_transactions.csv` y la salida
limpia en `etl/data/clean_transactions.csv`.

Ejemplo de evento Bancs:

```json
{
  "legacy_id": "B-DEMO-001",
  "source_account": "ACC-1003",
  "destination_account": "ACC-1004",
  "amount": "75.50",
  "currency": "USD",
  "event_time": "2026-09-16T15:00:00Z"
}
```

## Evidencias que deben adjuntarse al entregar

- Enlace al repositorio público o compartido con permisos de revisión.
- Video demostrativo.
- Presentación o PDF basado en el guion anterior.
- Capturas o resultados de pruebas.
- Este documento y la declaración de uso de IA.

El video y la presentación son artefactos de la entrega; no se deben guardar
en el repositorio si contienen datos sensibles o hacen crecer innecesariamente
el repositorio. Pueden enlazarse desde el correo o desde el README.
