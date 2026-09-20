# Evidencia de plataformas Tata

| Competencia | Evidencia local sin costo | Equivalencia productiva |
|---|---|---|
| Kubernetes/OpenShift | `k8s/` incluye Deployments, Services, HPA, probes, recursos y Route | OpenShift aplica los mismos objetos y añade Route/Operators |
| Terraform/IaC | `terraform/` crea red y contenedores Docker locales | Sustituir provider Docker por Azure/AWS/GCP/OpenShift |
| Ansible | `ansible/site.yml` valida y levanta Compose | Provisionamiento repetible de hosts Linux |
| T-SQL | `sqlserver/t-sql-schema.sql` | SQL Server/Bancs; el MVP ejecutable usa PostgreSQL |
| VMware | `docs/vmware-runbook.md` | VM Linux con Docker sobre ESXi/vCenter |
| Bash/PowerShell | `scripts/*.ps1` y comandos reproducibles | Automatización de operación y CI/CD |
| CI/CD | `.github/workflows/ci.yml` | Build, validación, escaneo y publicación de imágenes |
| Trazas | OpenTelemetry con exporter de consola local | Collector + Jaeger/Tempo en producción |
| Experiencia digital | `/synthetic/transfer` y métricas Prometheus | Synthetics desde una ubicación externa |
