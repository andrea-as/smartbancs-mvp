# Ejecución sobre VMware (sin licencia en el MVP)

1. Crear una VM Linux pequeña en ESXi/vCenter (2 vCPU, 4 GB RAM, 20 GB disco).
2. Instalar Docker Engine y Compose Plugin.
3. Clonar el repositorio en la VM.
4. Ejecutar `pwsh ./scripts/start.ps1` o `docker compose up --build -d`.
5. Publicar únicamente el reverse proxy por la red definida; PostgreSQL y Redis permanecen privados.
6. Configurar snapshot solo antes de cambios controlados, no como mecanismo de backup.

La virtualización no se simula dentro del laptop: este runbook demuestra la operación
esperada y separa la capa VMware de la carga de contenedores.
