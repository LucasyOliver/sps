---
versao: 1.0.0
data_editorial: 2026-11-12
tipo: prd_deploy_e_operacao
projeto: SPS (Sistema Para Salões)
estado: aguardando_revisao_prd
modulo_pai: "prd_do_projeto.md"
---

# PRD — Guia de Deploy em VPS Ubuntu (Docker Swarm) e Operação — SPS

## 1. Diretrizes de Governança de Deploy e Operação

- **Execução Exclusiva pelo Desenvolvedor:** Nenhum comando de provisionamento em VPS, publicação de imagem em registry (`{{registry_imagem}}`), criação de secrets reais ou execução de `docker stack deploy` é realizado automaticamente pela IA.
- **Zero Git/GitHub em Scripts (`scripts/deploy.sh`):** Nenhum script de automação pode conter comandos `git` ou `gh` (diretos ou indiretos). O deploy opera sobre a imagem Docker já construída e publicada pelo desenvolvedor.
- **Parâmetros de Produção Pendentes (`a_definir`):** Nos comandos abaixo, substitua `{{dominio_principal}}` (ex.: `sps.seudominio.com.br`), `{{registry_imagem}}` (ex.: `ghcr.io/seu_usuario/sps`) e `{{endereco_swarm}}` pelos valores reais antes da execução em homologação/produção.

---

## 2. Passo 1: Preparação da VPS Ubuntu, Firewall e Docker Swarm

Todos os comandos abaixo são executados pelo desenvolvedor na VPS Ubuntu (`22.04 LTS` ou `24.04 LTS`):

```bash
# 1. Atualizar pacotes básicos e configurar firewall (UFW)
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y ca-certificates curl gnupg ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# 2. Instalar Docker Engine e Docker Compose Plugin pela documentação oficial
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 3. Inicializar o Docker Swarm no IP privado/principal do nó
docker swarm init --advertise-addr {{endereco_swarm}}
```

---

## 3. Passo 2: Redes Overlay e Matriz de Isolamento de Rede

O SPS utiliza três redes overlay com responsabilidades distintas:
- `traefik_public` (`external: true`): ingresso HTTP/HTTPS entre Traefik e `sps_app`.
- `sps_internal` (`internal: true`): tráfego isolado entre `sps_app`, `sps_worker`, `sps_beat`, `sps_postgres`, `sps_rabbitmq` e `sps_redis` (sem saída externa nem portas publicadas no host).
- `sps_egress`: saída controlada para internet atribuída apenas a `traefik`, `sps_app` e `sps_worker` (para envio de e-mail SMTP, ACME DNS-01 Cloudflare e chamadas à API de LLM).

```bash
# Criar a rede externa de ingresso antes do primeiro deploy
docker network create --driver overlay traefik_public
```

| Serviço da Stack | `traefik_public` | `sps_internal` (`internal: true`) | `sps_egress` | Porta Publicada na VPS |
|---|---|---|---|---|
| `traefik` | Sim | Não | Sim (ACME/Cloudflare) | `80:80`, `443:443` |
| `app` (Django/Gunicorn) | Sim | Sim | Sim (SMTP/LLM) | Nenhuma (via Traefik) |
| `postgres` | Não | Sim | Não | Nenhuma |
| `rabbitmq` | Não | Sim | Não | Nenhuma |
| `redis` | Não | Sim | Não | Nenhuma |
| `celery_worker` | Não | Sim | Sim (SMTP/LLM) | Nenhuma |
| `celery_beat` | Não | Sim | Não | Nenhuma |

---

## 4. Passo 3: Token Cloudflare DNS-01 e Criação de Docker Secrets

1. No painel da Cloudflare, acesse **My Profile $\rightarrow$ API Tokens $\rightarrow$ Create Token**:
   - Permissão 1: `Zone - Zone - Read`
   - Permissão 2: `Zone - DNS - Edit`
   - Zone Resources: `Include - Specific zone - {{dominio_principal}}`
2. Crie os Docker Secrets no nó manager do Swarm (sem salvar os valores em arquivos `.env` versionados):

```bash
# Criar os Docker Secrets de produção (substituir pelos segredos reais no terminal seguro)
printf '%s' 'SEU_TOKEN_CLOUDFLARE_AQUI' | docker secret create CLOUDFLARE_DNS_API_TOKEN -
printf '%s' 'SUA_DJANGO_SECRET_KEY_AQUI' | docker secret create SPS_DJANGO_SECRET_KEY -
printf '%s' 'SENHA_FORTE_POSTGRES_AQUI'  | docker secret create SPS_POSTGRES_PASSWORD -
printf '%s' 'SENHA_FORTE_RABBITMQ_AQUI'  | docker secret create SPS_RABBITMQ_PASSWORD -
printf '%s' 'SUA_CHAVE_API_LLM_AQUI'     | docker secret create SPS_LLM_API_KEY -
docker secret ls
```

---

## 5. Passo 4: Configuração de `.env.prod` e Proxy/HTTPS no Django

Em `/opt/sps/.env.prod` (permissão `chmod 600`, fora do controle de versão), defina apenas variáveis não-secretas e os caminhos `*_FILE` lidos por `environ.FileAwareEnv()` no `core/settings.py`:

```ini
DEBUG=False
TIME_ZONE=America/Sao_Paulo
LANGUAGE_CODE=pt-br
ALLOWED_HOSTS={{dominio_principal}},.{{dominio_principal}},localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://{{dominio_principal}},https://*.{{dominio_principal}}

# Caminhos de Docker Secrets lidos pelo FileAwareEnv do Django
SECRET_KEY_FILE=/run/secrets/SPS_DJANGO_SECRET_KEY
POSTGRES_DB=sps_prod
POSTGRES_USER=sps_user
POSTGRES_PASSWORD_FILE=/run/secrets/SPS_POSTGRES_PASSWORD
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

RABBITMQ_DEFAULT_USER=sps_mq
RABBITMQ_DEFAULT_PASS_FILE=/run/secrets/SPS_RABBITMQ_PASSWORD
REDIS_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Configuracao de proxy reverso e healthcheck no core/settings.py
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# SECURE_SSL_REDIRECT = True
# SECURE_REDIRECT_EXEMPT = [r'^healthz/$', r'^readyz/$']

# Parametros do Assistente de IA (a_definir quando ativado)
LLM_MODEL=a_definir
LLM_API_KEY_FILE=/run/secrets/SPS_LLM_API_KEY
```

---

## 6. Passo 5: Especificação de Referência do `docker-stack.yml`

```yaml
version: '3.8'

networks:
  traefik_public:
    external: true
  sps_internal:
    driver: overlay
    internal: true
  sps_egress:
    driver: overlay

volumes:
  postgres_data:
  rabbitmq_data:
  redis_data:
  media_data:
  traefik_certs:

secrets:
  CLOUDFLARE_DNS_API_TOKEN:
    external: true
  SPS_DJANGO_SECRET_KEY:
    external: true
  SPS_POSTGRES_PASSWORD:
    external: true
  SPS_RABBITMQ_PASSWORD:
    external: true
  SPS_LLM_API_KEY:
    external: true

services:
  traefik:
    image: traefik:v3.1
    command:
      - '--providers.swarm.endpoint=unix:///var/run/docker.sock'
      - '--providers.swarm.exposedbydefault=false'
      - '--providers.swarm.network=traefik_public'
      - '--entrypoints.web.address=:80'
      - '--entrypoints.web.http.redirections.entrypoint.to=websecure'
      - '--entrypoints.web.http.redirections.entrypoint.scheme=https'
      - '--entrypoints.websecure.address=:443'
      - '--entrypoints.websecure.forwardedHeaders.trustedIPs=127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16'
      - '--certificatesresolvers.cloudflare.acme.dnschallenge=true'
      - '--certificatesresolvers.cloudflare.acme.dnschallenge.provider=cloudflare'
      - '--certificatesresolvers.cloudflare.acme.email=admin@{{dominio_principal}}'
      - '--certificatesresolvers.cloudflare.acme.storage=/letsencrypt/acme.json'
    ports:
      - '80:80'
      - '443:443'
    environment:
      - CF_DNS_API_TOKEN_FILE=/run/secrets/CLOUDFLARE_DNS_API_TOKEN
    secrets:
      - CLOUDFLARE_DNS_API_TOKEN
    volumes:
      - '/var/run/docker.sock:/var/run/docker.sock:ro'
      - 'traefik_certs:/letsencrypt'
    networks:
      - traefik_public
      - sps_egress
    deploy:
      placement:
        constraints: [node.role == manager]
      restart_policy:
        condition: on-failure

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: sps_prod
      POSTGRES_USER: sps_user
      POSTGRES_PASSWORD_FILE: /run/secrets/SPS_POSTGRES_PASSWORD
    secrets:
      - SPS_POSTGRES_PASSWORD
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - sps_internal
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U sps_user -d sps_prod']
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      restart_policy:
        condition: on-failure

  redis:
    image: redis:7-alpine
    command: ['redis-server', '--appendonly', 'yes']
    volumes:
      - redis_data:/data
    networks:
      - sps_internal
    healthcheck:
      test: ['CMD', 'redis-cli', 'ping']
      interval: 10s
      timeout: 5s
      retries: 5

  rabbitmq:
    image: rabbitmq:3.13-alpine
    env_file: /opt/sps/.env.prod
    secrets:
      - SPS_RABBITMQ_PASSWORD
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    networks:
      - sps_internal
    healthcheck:
      test: ['CMD', 'rabbitmq-diagnostics', '-q', 'ping']
      interval: 15s
      timeout: 10s
      retries: 5

  app:
    image: {{registry_imagem}}:{{tag_release}}
    command: ['sh', '-c', 'python manage.py wait_for_db && gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60']
    env_file: /opt/sps/.env.prod
    secrets:
      - SPS_DJANGO_SECRET_KEY
      - SPS_POSTGRES_PASSWORD
      - SPS_RABBITMQ_PASSWORD
      - SPS_LLM_API_KEY
    volumes:
      - media_data:/app/media
    networks:
      - traefik_public
      - sps_internal
      - sps_egress
    healthcheck:
      test: ['CMD-SHELL', 'python -c "import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8000/healthz/\")"']
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 20s
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
      restart_policy:
        condition: on-failure
      labels:
        - 'traefik.enable=true'
        - 'traefik.http.routers.sps.rule=Host(`{{dominio_principal}}`) || HostRegexp(`^.+\\.{{dominio_principal}}$`)'
        - 'traefik.http.routers.sps.entrypoints=websecure'
        - 'traefik.http.routers.sps.tls=true'
        - 'traefik.http.routers.sps.tls.certresolver=cloudflare'
        - 'traefik.http.routers.sps.tls.domains[0].main={{dominio_principal}}'
        - 'traefik.http.routers.sps.tls.domains[0].sans=*.{{dominio_principal}}'
        - 'traefik.http.services.sps.loadbalancer.server.port=8000'

  celery_worker:
    image: {{registry_imagem}}:{{tag_release}}
    command: ['sh', '-c', 'python -m celery -A core worker -l info --concurrency=2']
    env_file: /opt/sps/.env.prod
    secrets:
      - SPS_DJANGO_SECRET_KEY
      - SPS_POSTGRES_PASSWORD
      - SPS_RABBITMQ_PASSWORD
      - SPS_LLM_API_KEY
    volumes:
      - media_data:/app/media
    networks:
      - sps_internal
      - sps_egress
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure

  celery_beat:
    image: {{registry_imagem}}:{{tag_release}}
    command: ['sh', '-c', 'python -m celery -A core beat -l info']
    env_file: /opt/sps/.env.prod
    secrets:
      - SPS_DJANGO_SECRET_KEY
      - SPS_POSTGRES_PASSWORD
      - SPS_RABBITMQ_PASSWORD
    networks:
      - sps_internal
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
```

---

## 7. Estratégia de Staticfiles, Migrations, `scripts/deploy.sh` e Backup/Restore

1. **Staticfiles e Migrations:**
   - O `collectstatic --noinput` é executado durante o build da imagem Docker (`Dockerfile`) e servido com `WhiteNoise`, evitando condição de corrida em volume compartilhado.
   - `celery_worker` e `celery_beat` **nunca** executam `migrate` nem `collectstatic`.
   - As migrations são aplicadas de forma serializada em job único antes de atualizar as réplicas do `app` no `scripts/deploy.sh`.
2. **Contrato do `scripts/deploy.sh` (Execução pelo Usuário, Zero Git/GH):**
   - Valida que o Docker Swarm está ativo, que a rede `traefik_public` e os 5 Docker Secrets existem e que a variável `IMAGE_TAG` foi informada.
   - Faz `docker pull` da imagem autenticada pelo usuário, executa um container efêmero na rede `sps_internal` para `python manage.py wait_for_db && python manage.py migrate --noinput`, realiza `docker stack deploy --with-registry-auth -c docker-stack.yml sps` e valida `/healthz/` e `/readyz/`.
3. **Verificação do Certificado Wildcard e Smoke Check:**
   - Inspecionar logs do Traefik (`docker service logs sps_traefik`) e validar o certificado emitido com `openssl s_client -connect {{dominio_principal}}:443 -servername {{dominio_principal}} </dev/null 2>/dev/null | openssl x509 -noout -text | grep -A1 "Subject Alternative Name"`.
4. **Backup e Restauração (`RNF-004` — `RPO <= 24h`, `RTO <= 2h`):**
   - Cron diário na VPS executando `pg_dump -Fc` do container PostgreSQL e arquivo compactado de `media_data`, com retenção de 14 dias e teste periódico de restauração (`pg_restore`) em banco de verificação conforme runbook operacional.
