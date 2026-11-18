#!/usr/bin/env bash
# ==========================================================================
# SPS (Sistema Para Salões) — Script de Backup Diário (RNF-004: RPO <= 24h)
# ==========================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/sps}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "${BACKUP_DIR}"

PG_CONTAINER="$(docker ps --filter "name=sps_postgres" --format "{{.ID}}" | head -n 1)"
if [[ -z "${PG_CONTAINER}" ]]; then
  echo "[ERRO] Container do PostgreSQL (sps_postgres) não encontrado em execução."
  exit 1
fi

echo "[1/3] Gerando dump lógico comprimido do PostgreSQL..."
docker exec "${PG_CONTAINER}" pg_dump -U sps_user -d sps_prod -Fc > "${BACKUP_DIR}/sps_db_${TIMESTAMP}.dump"

echo "[2/3] Compactando volume de mídia (sps_media_data)..."
docker run --rm \
  -v sps_media_data:/media:ro \
  -v "${BACKUP_DIR}:/backup" \
  alpine:3.20 \
  tar -czf "/backup/sps_media_${TIMESTAMP}.tar.gz" -C /media .

echo "[3/3] Removendo arquivos de backup com mais de ${RETENTION_DAYS} dias..."
find "${BACKUP_DIR}" -type f -mtime +"${RETENTION_DAYS}" -delete

echo "[OK] Backup concluído em ${BACKUP_DIR}: sps_db_${TIMESTAMP}.dump e sps_media_${TIMESTAMP}.tar.gz"
