# Incidente crítico — Timeouts y deadlocks

## Indicadores

- p95/p99 de latencia;
- tasa de 5xx;
- timeouts;
- pool de conexiones;
- sesiones esperando locks;
- deadlocks.

## Diagnóstico PostgreSQL

```sql
SELECT pid, usename, state, wait_event_type, wait_event, query,
       now() - query_start AS duration
FROM pg_stat_activity
WHERE state <> 'idle'
ORDER BY query_start;
```

```sql
SELECT locktype, relation::regclass, mode, granted, pid
FROM pg_locks
ORDER BY relation, pid;
```

## Acciones inmediatas

1. Abrir incidente y determinar alcance.
2. Revisar métricas y logs con `request_id`.
3. Identificar query/sesión bloqueante.
4. Reducir tráfico no esencial.
5. Pausar procesos no críticos si compiten por DB.
6. Terminar sesiones bloqueantes únicamente con evidencia y procedimiento autorizado.
7. Ajustar temporalmente pool/timeouts si el diagnóstico lo justifica.
8. Escalar API si el cuello está en la capa de aplicación.
9. Verificar consistencia de transacciones y saldos.
10. Mantener auditoría de las acciones.

No se recomienda matar conexiones indiscriminadamente.

## Prevención

- transacciones cortas;
- orden determinista de locks;
- índices;
- timeouts;
- pool dimensionado;
- reintentos con backoff para errores transitorios;
- idempotencia;
- pruebas de concurrencia/carga;
- alertas de latencia, errores, pool y locks.

## Post-mortem

Documentar línea de tiempo, impacto, detección, causa raíz, factores contribuyentes, queries involucradas, acciones realizadas y acciones correctivas con responsable/fecha. Después se debe ejecutar una prueba que demuestre que la corrección evita la recurrencia.
