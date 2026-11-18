#!/usr/bin/env bash
# ==========================================================================
# SPS (Sistema Para Salões) — Script de Deploy Serializado no Docker Swarm
# Governança: Executado exclusivamente pelo desenvolvedor na VPS Ubuntu.
# Zero comandos de Git/GitHub (atua sobre a imagem já publicada no registry).
# ==========================================================================
set -euo pipefail

STACK_NAME="${STACK_NAME:-sps}"
ENV_FILE="${ENV_FILE:-/opt/sps/.env.prod}"
STACK_FILE="${STACK_FILE:-/opt/sps/docker-stack.yml}"
IMAGE_REPO="${IMAGE_REPO:-}"
IMAGE_TAG="${IMAGE_TAG:-}"

if [[ -z "${IMAGE_REPO}" || -z "${IMAGE_TAG}" ]]; then
  echo "[ERRO] Defina IMAGE_REPO e IMAGE_TAG antes de executar (ex.: IMAGE_REPO=ghcr.io/usuario/sps IMAGE_TAG=1.0.0 ./scripts/deploy.sh)."
  exit 1
fi

FULL_IMAGE="${IMAGE_REPO}:${IMAGE_TAG}"

echo "[1/6] Verificando estado do Docker Swarm e rede traefik_public..."
docker info --format '{{.Swarm.LocalNodeState}}' | grep -q "active" || {
  echo "[ERRO] Docker Swarm não está ativo neste nó."
  exit 1
}
docker network inspect traefik_public >/dev/null 2>&1 || {
  echo "[ERRO] Rede overlay 'traefik_public' não encontrada. Crie com: docker network create --driver overlay traefik_public"
  exit 1
}

echo "[2/6] Verificando presença dos 5 Docker Secrets obrigatórios..."
for SECRET_NAME in CLOUDFLARE_DNS_API_TOKEN SPS_DJANGO_SECRET_KEY SPS_POSTGRES_PASSWORD SPS_RABBITMQ_PASSWORD SPS_LLM_API_KEY; do
  docker secret inspect "${SECRET_NAME}" >/dev/null 2>&1 || {
    echo "[ERRO] Docker Secret obrigatório ausente: ${SECRET_NAME}"
    exit 1
  }
done

echo "[3/6] Baixando imagem ${FULL_IMAGE}..."
docker pull "${FULL_IMAGE}"

echo "[4/6] Aplicando stack de infraestrutura e serviços (${STACK_NAME})..."
docker stack deploy --with-registry-auth -c "${STACK_FILE}" "${STACK_NAME}"

echo "[5/6] Executando migrations de forma serializada em container único na rede interna..."
INTERNAL_NET="${STACK_NAME}_sps_internal"
docker run --rm \
  --network "${INTERNAL_NET}" \
  --env-file "${ENV_FILE}" \
  "${FULL_IMAGE}" \
  sh -c "python manage.py wait_for_db --timeout 60 && python manage.py migrate --noinput"

echo "[6/6] Atualizando serviço ${STACK_NAME}_app para ${FULL_IMAGE}..."
docker service update --with-registry-auth --image "${FULL_IMAGE}" "${STACK_NAME}_app"
docker service update --with-registry-auth --image "${FULL_IMAGE}" "${STACK_NAME}_celery_worker"
docker service update --with-registry-auth --image "${FULL_IMAGE}" "${STACK_NAME}_celery_beat"

echo "[OK] Deploy concluído. Verifique os serviços com: docker stack ps ${STACK_NAME}"
