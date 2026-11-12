---
versao: 1.0.0
data_editorial: 2026-11-12
tipo: evidencias_de_sprint
projeto: SPS (Sistema Para Salões)
sprint: Sprint 01
estado: concluida_aguardando_acao_git_do_usuario
---

# Evidências de Execução e Revisão — Sprint 01 — SPS (Sistema Para Salões)

## 1. Identificação da Entrega

- **Sprint:** `Sprint 01 — Fundação Técnica, Usuário Customizado (AUTH_USER_MODEL) e Tenant (Salon)`
- **Versão do PRD de referência:** `1.0.0` (aprovada pelo desenvolvedor em `2026-11-12`)
- **Solicitação explícita do desenvolvedor:** *"Aprovo o PRD versão 1.0.0 do SPS e solicito a execução exclusiva da Sprint 01."*
- **Requisitos avaliados:** `RF-001` (base operacional e campos fiscais preparatórios do salão), `RF-002` (autenticação por e-mail e vínculo fixo de salão), `RNF-001` (isolamento multi-tenant base), `RNF-005` (leitura de configuração/secrets com `FileAwareEnv`, headers HTTPS de proxy e isenção de healthcheck).
- **Decisões aplicadas:** `DEC-001` (suíte de testes automatizados + revisão manual), `DEC-002` (vínculo único de usuário interno por salão), `DEC-003` (preparação estrutural de metadados fiscais no `Salon` e no `User`).
- **Operações de Git/GitHub executadas pela IA:** `Nenhuma` (`git_executado_pela_ia: false`).

---

## 2. Checklist de Tarefas da Sprint 01 e Rastreabilidade

| ID da Tarefa | Requisito / Decisão | Arquivos Principais Criados / Alterados | Situação | Evidência Registrada |
|---|---|---|---|---|
| `S01-T01` | Stack Baseline, `RNF-005` | `sps/.venv/`, `sps/requirements.txt`, `sps/.env.example`, `sps/.gitignore`, `sps/.dockerignore`, `sps/docker-compose.yml` | `[x]` | Venv `Python 3.13.6` criada; `Django 5.2.19`, `django-environ 0.14.0`, `psycopg 3.3.9` instalados; `pip check` sem conflitos. |
| `S01-T02` | `RNF-001`, `RNF-005` | `sps/manage.py`, `sps/core/settings.py`, `sps/core/urls.py`, `sps/base/models.py`, `sps/base/views.py`, `sps/base/urls.py`, `sps/base/management/commands/wait_for_db.py` | `[x]` | `FileAwareEnv` configurado; `TimeStampedModel` e `TenantScopedModel` criados; `/healthz/`, `/readyz/` e `wait_for_db` testados. |
| `S01-T03` | `RF-001`, `DEC-002`, `DEC-003` | `sps/salons/models.py`, `sps/salons/admin.py`, `sps/salons/migrations/0001_initial.py` | `[x]` | Model `Salon` criado com `slug` único, `cancellation_min_hours` e campos fiscais preparatórios (CNPJ, IM, IE, regime, código IBGE e flag Salão-Parceiro). |
| `S01-T04` | `RF-002`, `DEC-002`, `DEC-003` | `sps/accounts/models.py`, `sps/accounts/forms.py`, `sps/accounts/views.py`, `sps/accounts/urls.py`, `sps/accounts/admin.py`, `sps/accounts/migrations/0001_initial.py` | `[x]` | `AUTH_USER_MODEL = 'accounts.User'` definido antes da 1ª migration; login por e-mail; validação estrita de `salon` obrigatório para `gestor`, `recepcionista` e `profissional`. |
| `S01-T05` | `RF-001`, `RF-002` | `sps/templates/base.html`, `sps/templates/base/home.html`, `sps/templates/accounts/login.html` | `[x]` | Migrations iniciais geradas e plano validado (`migrate --plan` e `migrate`); Django Admin e fluxo de login/logout por e-mail operacionais. |
| `S01-T06` | `DEC-001`, `RNF-001`, `RNF-005` | `sps/base/tests.py`, `sps/salons/tests.py`, `sps/accounts/tests.py` | `[x]` | `12` testes automatizados executados e aprovados (`OK` em `4.243s`). |
| `S01-T07` | Governança | `sps/docs/02_execucao/evidencias_da_sprint_001.md`, `sps/docs/02_execucao/estado_do_projeto.md` | `[x]` | Revisão realizada, achado corrigido e pacote pronto para commit/push manual do usuário. |

### 2.1 Fichas de Verificação por Tarefa (`S01-T01` a `S01-T06`)

```text
ID da tarefa: S01-T01
Requisito associado: Stack Baseline, RNF-005
Resultado esperado: Venv Python 3.13.6 criada, dependências instaladas e arquivos de ambiente/compose preparados.
Arquivos alterados: sps/.venv/, sps/requirements.txt, sps/.env.example, sps/.gitignore, sps/.dockerignore, sps/docker-compose.yml
Verificação executada: python --version e pip check na .venv
Resultado observado: Python 3.13.6; Django 5.2.19, django-environ 0.14.0 e psycopg 3.3.9 sem conflitos.
Critério atendido: sim

ID da tarefa: S01-T02
Requisito associado: RNF-001, RNF-005
Resultado esperado: Configuração central em core/settings.py com FileAwareEnv, modelos base (TimeStampedModel, TenantScopedModel), comando wait_for_db e rotas /healthz/ e /readyz/.
Arquivos alterados: sps/core/settings.py, sps/core/urls.py, sps/base/models.py, sps/base/views.py, sps/base/urls.py, sps/base/management/commands/wait_for_db.py
Verificação executada: manage.py check, manage.py wait_for_db e HealthcheckAndWaitForDbTests (5 testes).
Resultado observado: Rotas /healthz/ e /readyz/ respondem 200 OK e são isentas de redirect HTTPS quando DEBUG=False.
Critério atendido: sim

ID da tarefa: S01-T03
Requisito associado: RF-001, DEC-002, DEC-003
Resultado esperado: Modelo Salon com slug único, antecedência mínima de cancelamento e campos fiscais preparatórios (CNPJ, IM, IE, regime tributário, código IBGE e flag Salão-Parceiro).
Arquivos alterados: sps/salons/models.py, sps/salons/admin.py, sps/salons/migrations/0001_initial.py
Verificação executada: SalonModelTests (3 testes de criação e validação de CNPJ/IBGE).
Resultado observado: Normalização de CNPJ (14 dígitos) e código IBGE (7 dígitos) e rejeição de entradas inválidas.
Critério atendido: sim

ID da tarefa: S01-T04 e S01-T05
Requisito associado: RF-002, DEC-002, DEC-003
Resultado esperado: Usuário customizado com login por e-mail definido antes da 1ª migration, vínculo obrigatório a um único salão para perfis internos e telas de login/logout e painel inicial.
Arquivos alterados: sps/accounts/models.py, sps/accounts/forms.py, sps/accounts/views.py, sps/accounts/urls.py, sps/accounts/admin.py, sps/accounts/migrations/0001_initial.py, sps/templates/
Verificação executada: migrate --plan, migrate e AccountsAndTenantBindingTests (4 testes).
Resultado observado: Perfis internos sem salão são bloqueados com ValidationError; login por e-mail autentica e exibe o salão vinculado.
Critério atendido: sim
```

---

## 3. Avaliação nas Oito Dimensões de Revisão

| Dimensão | Pergunta Central | Avaliação na Sprint 01 |
|---|---|---|
| **Produto** | O comportamento aprovado foi implementado? | Sim: `Salon` (com dados operacionais e fiscais) e `User` (login por e-mail e vínculo fixo de salão) implementados conforme `RF-001` e `RF-002`. |
| **Escopo** | Foi incluída alguma função não solicitada? | Não: implementação restrita exclusivamente às tarefas `S01-T01` a `S01-T07`. |
| **Acesso** | Quem pode ler, alterar e exportar dados? | Rota inicial `/` exige autenticação (`LoginRequiredMixin`); perfis internos exigem vínculo fixo com um `Salon` (`DEC-002`). |
| **Integridade** | Falha ou concorrência pode corromper o estado? | `on_delete=models.PROTECT` no vínculo `User.salon` impede exclusão acidental de salão com equipe vinculada; `full_clean()` garante invariantes no `UserManager`. |
| **UX** | Usuário entende sucesso, erro, vazio e espera? | Interface 100% em português brasileiro (`pt-BR`), com mensagens de erro claras em formulários e validações de CNPJ/IBGE/vínculo de salão. |
| **Operação** | Falhas são observáveis e recuperáveis? | Separados `/healthz/` (liveness leve) e `/readyz/` (readiness de banco com `503` em falha), além de `wait_for_db` com timeout configurável. |
| **Configuração** | Há segredos, defaults perigosos ou dependências implícitas? | Nenhum segredo versionado; `.env.example` documentado; leitura de Docker Secrets suportada via `environ.FileAwareEnv()`. |
| **Documentação** | Outra sessão consegue retomar corretamente? | Sim: `estado_do_projeto.md`, `parametros_do_projeto.json`, `sprints_de_implementacao_prd.md` e este relatório estão sincronizados. |

---

## 4. Procedimentos de Verificação Executados e Resultados Observados

### 3.1 Ambiente Virtual e Dependências (`S01-T01`)
- **Comando executado:**
  ```powershell
  .\.venv\Scripts\python.exe --version
  .\.venv\Scripts\python.exe -m pip check
  ```
- **Resultado observado:**
  - `Python 3.13.6` isolado em `sps/.venv`.
  - Pacotes instalados e fixados em `sps/requirements.txt`: `Django==5.2.19`, `django-environ==0.14.0`, `psycopg==3.3.9`, `psycopg-binary==3.3.9`, `asgiref==3.13.0`, `sqlparse==0.6.1`, `tzdata==2026.6`.
  - `No broken requirements found.`

### 3.2 Verificação Estática, Migrations e Comando `wait_for_db` (`S01-T02` a `S01-T05`)
- **Comandos executados:**
  ```powershell
  .\.venv\Scripts\python.exe manage.py check
  .\.venv\Scripts\python.exe manage.py makemigrations salons accounts base
  $env:USE_SQLITE_FALLBACK="True"; .\.venv\Scripts\python.exe manage.py migrate --plan
  $env:USE_SQLITE_FALLBACK="True"; .\.venv\Scripts\python.exe manage.py migrate
  $env:USE_SQLITE_FALLBACK="True"; .\.venv\Scripts\python.exe manage.py wait_for_db
  ```
- **Resultado observado:**
  - `System check identified no issues (0 silenced).`
  - Geração limpa de `salons/migrations/0001_initial.py` e `accounts/migrations/0001_initial.py` com `AUTH_USER_MODEL = 'accounts.User'` definido antes de qualquer migration aplicada.
  - Execução do plano de migrations e do comando `wait_for_db` concluída com `Banco de dados disponivel!`.

### 3.3 Suíte de Testes Automatizados (`S01-T06` — `DEC-001`)
- **Comando executado:**
  ```powershell
  $env:USE_SQLITE_FALLBACK="True"; .\.venv\Scripts\python.exe manage.py test base salons accounts -v 2
  ```
- **Cenários verificados (12 testes, 100% aprovados):**
  1. `test_liveness_endpoint_returns_ok_even_without_https_header`: `/healthz/` responde `200 OK` com `{"status": "ok", "check": "liveness"}`.
  2. `test_readiness_endpoint_returns_ready_when_db_available`: `/readyz/` executa `SELECT 1` e responde `200 OK` com `{"status": "ready", "database": "ok"}`.
  3. `test_proxy_ssl_header_and_healthcheck_redirect_exemption`: com `DEBUG=False` e `SECURE_SSL_REDIRECT=True`, verifica que `/healthz/` é isento do redirect (`200 OK`), que requisições HTTP comuns redirecionam para HTTPS (`301`) e que requisições com `HTTP_X_FORWARDED_PROTO='https'` são aceitas (`200 OK`).
  4. `test_wait_for_db_succeeds_immediately_when_db_available`: comando `wait_for_db` retorna sucesso imediato com banco ativo.
  5. `test_wait_for_db_raises_command_error_on_timeout`: comando `wait_for_db` lança `CommandError` após esgotar o timeout quando o banco falha com `OperationalError`.
  6. `test_create_salon_with_operational_and_fiscal_fields`: criação de `Salon` normalizando CNPJ (`14` dígitos) e código IBGE (`7` dígitos) e persistindo regime tributário e flag Salão-Parceiro (`DEC-003`).
  7. `test_invalid_cnpj_length_raises_validation_error`: rejeita CNPJ inválido com `ValidationError`.
  8. `test_invalid_ibge_city_code_raises_validation_error`: rejeita código IBGE diferente de 7 dígitos com `ValidationError`.
  9. `test_internal_user_requires_fixed_salon_binding`: garante que `gestor`, `recepcionista` e `profissional` sem `salon` vinculado falham com `ValidationError` (`DEC-002`).
  10. `test_create_salon_member_and_normalize_email`: cria usuário interno vinculado ao salão e normaliza o e-mail para minúsculas.
  11. `test_create_superuser_saas_without_salon_succeeds`: cria `superadmin_saas` global sem exigir vínculo a um salão específico.
  12. `test_email_login_and_authenticated_home_view`: valida redirecionamento de anônimo em `/`, login via e-mail em `/conta/entrar/` e exibição do salão vinculado no painel inicial.

---

## 5. Achados de Revisão e Correções Realizadas (`S01-T07`)

- **Achado durante a primeira execução dos testes:**
  - Como `core/settings.py` define `DEBUG = False` por padrão seguro quando não há arquivo `.env` local, `SECURE_SSL_REDIRECT = True` estava ativo durante o teste `test_email_login_and_authenticated_home_view`, fazendo o cliente de teste HTTP receber `301` (redirect para HTTPS) em vez de `302` (redirect de login).
- **Correção aplicada e re-verificada:**
  - Aplicado `@override_settings(SECURE_SSL_REDIRECT=False)` na classe `AccountsAndTenantBindingTests` e adicionado um teste dedicado (`test_proxy_ssl_header_and_healthcheck_redirect_exemption` em `base/tests.py`) que valida explicitamente o comportamento de produção (`DEBUG=False`, `SECURE_SSL_REDIRECT=True`, `SECURE_PROXY_SSL_HEADER` e `SECURE_REDIRECT_EXEMPT`).
  - Após a correção, todos os `12` testes passaram sem erros.

---

## 6. Limites da Verificação e Pendências de Ambiente Local

1. **Banco PostgreSQL Local:**
   - Foi detectado um processo `postgres` nativo escutando em `127.0.0.1:5432` no Windows, porém ainda sem o usuário/banco `sps_user`/`sps_dev` configurado (ou sem o container `docker-compose.yml` ativo, pois o executável `docker` não está no `PATH` atual).
   - Para utilizar o PostgreSQL local no desenvolvimento diário, o desenvolvedor pode copiar `.env.example` para `.env` e ajustar `DATABASE_URL` para suas credenciais locais do Postgres ou subir `docker compose up -d postgres` após ativar o Docker Desktop.

---

## 7. Proposta de Mensagem de Commit e Comandos Manuais (Exclusivos do Usuário)

```bash
# EXECUCAO EXCLUSIVA DO DESENVOLVEDOR (NAO EXECUTADO PELA IA)
git status
git add sps/
git commit -m "feat(sprint-01): bootstrap django 5.2, custom user by email and salon tenant model"
git push
```
