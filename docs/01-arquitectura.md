# Sustentación — Arquitectura

## Decisiones

| Necesidad | Solución |
|---|---|
| Alta concurrencia | API stateless + escalado horizontal |
| Transferencia <2 s | transacción corta; IA desacoplada |
| Protección de Bancs | integración asíncrona/read models/cache |
| Consistencia | PostgreSQL ACID |
| IA no bloqueante | Redis + worker |
| Observabilidad | logs + Prometheus |
| Automatización | Docker Compose + K8s + Terraform |
| Costo MVP | local |

## Flujo

1. Cliente envía transferencia.
2. API valida.
3. PostgreSQL bloquea las cuentas en orden determinista.
4. Se valida saldo y moneda.
5. Se actualizan cuentas y auditoría en una transacción.
6. Se publica un evento para IA.
7. API responde.
8. Worker genera recomendación posteriormente.

## Bancs

Bancs debe permanecer como sistema de registro legado. No conviene consultar el Core directamente desde cada request a gran escala. La arquitectura propuesta utiliza una capa de integración y datos desacoplada, con eventos/CDC cuando las interfaces disponibles lo permitan, además de reconciliación.

### Estrategia de sincronización de saldos

El MVP representa el flujo con el endpoint `POST /api/v1/bancs/events`, que
valida y normaliza un evento legado y lo guarda en `audit_events`. Este evento
no modifica saldos: su responsabilidad es demostrar la recepción, trazabilidad
y auditoría del mensaje de Bancs.

En una implementación productiva, la sincronización se separaría en dos flujos:

1. Bancs publica eventos de débito/crédito mediante una interfaz acordada,
   CDC, cola o archivo controlado.
2. El adaptador valida esquema, idempotencia (`legacy_id`), moneda, cuentas y
   fecha; después persiste el evento crudo y el evento canónico.
3. Un procesador aplica los cambios a un modelo operativo desacoplado, usando
   transacciones ACID y una clave de idempotencia.
4. Un proceso de reconciliación compara periódicamente totales, saldos y
   conteos contra Bancs; las diferencias quedan en una cola de excepciones.
5. Las consultas de la aplicación utilizan el modelo local/read model y no
   consultan Bancs repetidamente. Solo las operaciones que requieren
   confirmación del Core siguen el contrato de escritura definido por el banco.

Así se evita saturar el Core con lecturas de pantallas o recomendaciones,
mientras se conserva Bancs como fuente autorizada para conciliación financiera.

## Escalabilidad

Para 10 000 TPS se requerirían pruebas de carga y dimensionamiento reales. El diseño permite múltiples instancias de API, balanceo, pools de DB, cachés/read models, mensajería y workers independientes.

## Seguridad de producción

OIDC/OAuth2, RBAC, TLS/mTLS, gestión de secretos, mínimo privilegio, auditoría, cifrado, escaneo de imágenes/dependencias y protección de datos sensibles.
