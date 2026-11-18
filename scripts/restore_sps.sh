#!/usr/bin/env bash
# ==========================================================================
# SPS (Sistema Para Salões) — Script de Restauração (RNF-004: RTO <= 2h)
# ==========================================================================
set -euo pipefail

DUMP_FILE="${1:-}"
MEDIA_ARCHIVE="${2:-}"

if [[ -z "${DUMP_FILE}" || ! -f "${DUMP_FILE}" ]]; then
  echo "Uso: ./scripts/restore_sps.sh /caminho/sps_db_YYYYMMDD.dump [/caminho/sps_media_YYYYMMDD.tar.gz]"
  exit 1
fi

PG_CONTAINER="$(docker ps --filter "name=sps_postgres" --format "{{.ID}}" | head -n 1)"
if [[ -z "${PG_CONTAINER}" ]]; then
  echo "[ERRO] Container do PostgreSQL (sps_postgres) não encontrado."
  exit 1
fi

echo "[1/2] Restaurando banco de dados a partir de ${DUMP_FILE}..."
cat "${DUMP_FILE}" | docker exec -i "${PG_CONTAINER}" pg_restore -U sps_user -d sps_prod --clean --if-exists --no-owner

if [[ -n "${MEDIA_ARCHIVE}" && -f "${MEDIA_ARCHIVE}" ]]; then
  echo "[2/2] Restaurando volume de mídia a partir de ${MEDIA_ARCHIVE}..."
  docker run --rm \
    -v sps_media_data:/media \
    -v "$(dirname "${MEDIA_ARCHIVE}"):/backup:ro" \
    alpine:3.20 \
    tar -xzf "/backup/$(basename "${MEDIA_ARCHIVE}")" -C /media
fi

echo "[OK] Restauração concluída. Execute 'python manage.py check' e valide /readyz/."
