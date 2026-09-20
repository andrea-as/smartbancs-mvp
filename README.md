# SmartBancs App — MVP Técnico

MVP para el reto de Arquitectura, Desarrollo Práctico, Operación e IA.

## Arquitectura

```text
Cliente
   |
   v
FastAPI -----> PostgreSQL
   |
   +----> Redis Queue ----> AI Service
                |
                +----> recomendaciones

Prometheus <---- API + AI
Logs JSON -----> stdout / Docker logs
```

El MVP corre completamente en local y no requiere cuentas cloud ni servicios de pago.

## Stack

- Python + FastAPI
- PostgreSQL 16
- Redis 7
- Prometheus
- Docker Compose
- Kubernetes (manifiestos de referencia)
- Terraform (IaC de referencia)
- Ansible + PowerShell para automatización reproducible
- GitHub Actions
- pandas para ETL
- OpenTelemetry para trazas distribuidas

## Requisitos

Docker Desktop y Git.

## Ejecución

```bash
docker compose up --build
```

Endpoints:
- Dashboard en español: http://localhost:8000/
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Métricas: http://localhost:8000/metrics
- Experiencia digital sintética: http://localhost:8000/synthetic/transfer
- AI: http://localhost:8001/health
- Prometheus: http://localhost:9090

El dashboard muestra automáticamente el listado de cuentas demo con sus
saldos actuales y un resumen legible de métricas. `/metrics` se conserva como
el endpoint técnico en formato Prometheus para scraping y diagnóstico.

## Transferencia

```bash
curl -X POST http://localhost:8000/api/v1/transfers \
  -H "Content-Type: application/json" \
  -d "{\"source_account\":\"ACC-1001\",\"destination_account\":\"ACC-1002\",\"amount\":100,\"currency\":\"USD\"}"
```

Después:

```bash
curl http://localhost:8000/api/v1/accounts/ACC-1001
curl http://localhost:8000/api/v1/recommendations/ACC-1001
```

La transferencia se confirma sin esperar a la IA. La IA trabaja mediante Redis en segundo plano.
Si Redis está temporalmente indisponible, la transferencia no se revierte:
queda registrada en PostgreSQL y el log/métrica `smartbancs_ai_queue_errors_total`
permite alertar y reprocesar el evento mediante un outbox en una evolución productiva.

## Integración práctica con Bancs

El adaptador recibe el formato legado, limpia identificadores/montos/moneda,
normaliza la fecha y persiste el evento canónico para auditoría:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/bancs/events `
  -H "Content-Type: application/json" `
  -d "{\"legacy_id\":\"B-001\",\"source_account\":\" acc-1001 \",\"destination_account\":\"acc-1002\",\"amount\":\"25.50\",\"currency\":\"usd\",\"event_time\":\"2026-09-16T09:00:00Z\"}"
```

La operación es desacoplada del Core: Bancs entrega eventos al adaptador y no
recibe consultas por cada recomendación o pantalla de usuario.

## ETL

```bash
pip install pandas
python etl/transform_transactions.py
```

El script limpia nulos, fechas, montos, mayúsculas, duplicados y genera indicadores de calidad.

## Concurrencia

Las dos cuentas involucradas se bloquean con `SELECT ... FOR UPDATE` dentro de una transacción ACID. Los IDs se ordenan antes del bloqueo para reducir el riesgo de deadlocks.

El código registra errores de base de datos y deadlocks y devuelve un error transitorio al cliente.

## Observabilidad

La API genera logs JSON con `request_id`, endpoint, duración, estado y `transaction_id`. Prometheus recopila:

- requests;
- latencia;
- transferencias;
- errores de DB;
- trabajos de IA.
- fallos de publicación en la cola de IA.
- trazas OpenTelemetry exportadas a consola en el MVP;
- journey sintético de transferencia para disponibilidad y experiencia digital.
- reglas de alerta de SLO en `observability/alerts.yml`.
- correlación `request_id`/`transaction_id` entre API y worker IA, con reintentos
  y cola de mensajes fallidos (DLQ).

## Escenario de 10 000 TPS

La prueba se parametriza para ejecutar el escenario objetivo:

```powershell
$env:TOTAL_REQUESTS = "10000"
$env:CONCURRENCY = "1000"
python tests/load_test.py
```

El resultado reporta `observed_rps`, errores y duración. El número de 10.000
TPS solo puede certificarse en infraestructura dimensionada para ello; un
laptop no es una evidencia válida de capacidad productiva. El MVP demuestra
el camino de medición y la arquitectura: API stateless, escalamiento
horizontal, balanceador, pool de conexiones, caché/read models y mensajería.
El benchmark también reporta `p95_s`, `under_2s` y permite verificar el SLO de
transferencias menor a dos segundos:

```powershell
if ((python tests/load_test.py | Select-String "p95_s") -match '"p95_s": ([0-9.]+)') {
  Write-Host "Revisar p95 contra el SLO de 2 segundos"
}
```

### Resultado medido en el equipo de desarrollo

- Prueba controlada: 100 solicitudes, concurrencia 20, 100/100 exitosas.
- `p95_s`: 1.1713 segundos.
- `under_2s`: 100.
- Errores: 0.
- Escenario agresivo: 10.000 solicitudes y concurrencia 1.000.
- Resultado: 81.1 RPS observados, 83/10.000 exitosas, p95 de 27.2492 segundos.
- Escenario controlado: 10.000 solicitudes y concurrencia 20.
- Resultado: 96.82 RPS observados, 10.000/10.000 exitosas, p95 de 0.9709
  segundos y 9.929 solicitudes bajo dos segundos.

El segundo resultado demuestra que el laptop y la configuración local no
certifican 10.000 TPS. Es una evidencia útil de saturación: antes de afirmar
capacidad hay que escalar API, ajustar el pool de PostgreSQL y ejecutar la
prueba distribuida desde varios generadores de carga.

## Kubernetes / OpenShift

`k8s/` contiene API, IA, PostgreSQL, Redis, HPA, probes, recursos, Secret de
ejemplo y un `Route` de OpenShift. Para una demo:

```bash
kubectl apply -f k8s/
```

El almacenamiento `emptyDir` es deliberadamente de laboratorio; producción
debe usar PersistentVolume/operador administrado.

## IaC y operación

```bash
terraform -chdir=terraform init
terraform -chdir=terraform apply
ansible-playbook ansible/site.yml
```

Terraform crea una red y Redis local mediante Docker. Ansible valida y arranca
Compose. En Windows se pueden usar `scripts/start.ps1`, `scripts/stop.ps1` y
`scripts/smoke-test.ps1`. La matriz de equivalencias de Tata está en
`docs/platform-matrix.md`, incluyendo T-SQL y VMware.

## Post-mortem

El diseño contempla diagnóstico de locks, sesiones activas, latencia, timeouts, acciones de contención y análisis de causa raíz. Ver `docs/03-incidente-postmortem.md`.

## Entregables del reto

- Arquitectura, sincronización con Bancs y decisiones: `docs/01-arquitectura.md`.
- Datos, ETL, ciclo de vida, drift y recursos de IA: `docs/02-datos-ia.md`.
- Incidente, diagnóstico, contención y post-mortem: `docs/03-incidente-postmortem.md`.
- Declaración obligatoria de uso de IA: `docs/04-declaracion-uso-ia.md`.
- Guion de video, presentación, datos de prueba y checklist de evidencias:
  `docs/05-evidencias-y-demostracion.md`.
- Evidencias reproducibles de ETL y pruebas de carga: `evidence/`.

### Matriz de cumplimiento

| Requisito | Evidencia |
|---|---|
| API REST y transferencia | `services/api/app/main.py`, `POST /api/v1/transfers` |
| DDL/DML y concurrencia | `db/init.sql`, locks `FOR UPDATE` en orden determinista |
| Levantamiento con un comando | `docker-compose.yml`, `docker compose up --build -d` |
| Integración y sincronización Bancs | `services/api/app/bancs.py`, `docs/01-arquitectura.md` |
| ETL y calidad de datos | `etl/transform_transactions.py`, `etl/data/`, `evidence/etl-quality-report.txt` |
| IA independiente y no bloqueante | `services/ai/app/main.py`, Redis, reintentos y DLQ |
| Ciclo de vida, drift y recursos | `docs/02-datos-ia.md` |
| Logs, métricas y trazabilidad | `services/api/app/main.py`, `observability/`, `request_id` y `transaction_id` |
| Incidente y post-mortem | `docs/03-incidente-postmortem.md` |
| Declaración de uso de IA | `docs/04-declaracion-uso-ia.md` |
| Video, presentación y datos de prueba | `docs/05-evidencias-y-demostracion.md`, `evidence/` |

El repositorio contiene el código, la configuración reproducible y los datos de
prueba del MVP. El video y la presentación final deben adjuntarse o enlazarse
en la entrega según las instrucciones recibidas, sin incluir secretos ni datos
personales.

## Seguridad

El MVP usa credenciales de desarrollo únicamente. En producción: IAM/OIDC, secretos gestionados, TLS/mTLS, RBAC, mínimo privilegio, auditoría, cifrado, escaneo de dependencias/imágenes y controles de datos sensibles.

## Nota

La IA del MVP es determinista para evitar costos de APIs externas. En producción puede sustituirse por un modelo real manteniendo el mismo contrato asíncrono.
