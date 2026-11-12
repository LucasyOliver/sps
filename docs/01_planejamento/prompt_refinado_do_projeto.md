---
versao: 1.0.0
data_editorial: 2026-11-12
tipo: prompt_refinado_do_projeto
projeto: SPS (Sistema Para Salões)
modo_refinamento: assistido
estado: aprovado_pelo_desenvolvedor
origem_bruto: "prompt_inicial_do_projeto.md"
---

# Prompt Refinado do Projeto (Refinamento Assistido) — SPS (Sistema Para Salões)

## Objetivo deste Documento

Apresentar ao desenvolvedor a proposta de **Refinamento Assistido (Caminho B)** do prompt
bruto ([`prompt_inicial_do_projeto.md`](prompt_inicial_do_projeto.md)), estruturada com
tags XML funcionais, linguagem normativa precisa (`Obrigatório`, `Condicional`, `A definir`),
mapa de alterações rastreável, análise de parâmetros pendentes e checklist de prontidão
para a geração do PRD.

---

## 1. Prompt Refinado e Editável

````xml
<contexto>
Produto: SPS (Sistema Para Salões) — Slug técnico e nome de stack: `sps`.
Domínio de negócio: Plataforma SaaS multi-tenant para gestão integrada de salões de beleza
independentes no Brasil.
Organização de tenant (`DEC-002`): Cada "Salão" (`Salon`) é uma unidade organizacional
isolada. Cada usuário interno (`gestor`, `recepcionista`, `profissional`) pertence a um
único salão fixo, além do perfil global `superadmin_saas` da plataforma. Clientes finais,
catálogo de serviços, expediente, agendamentos, comandas, caixa, comissões, estoque de
produtos e registros fiscais preparatórios pertencem isoladamente a cada salão.
Referência metodológica: O estudo SCSI é utilizado estritamente como baseline técnico e
arquitetural; nenhum conceito ou entidade do mercado de seguros faz parte deste produto.
</contexto>

<objetivo>
Resolver a descentralização operacional, conflitos de horários na agenda, inconsistências
no pagamento de comissões de profissionais, falta de controle de estoque (venda na comanda
vs consumo interno) e ausência de preparação fiscal em salões de beleza, entregando um MVP
SaaS seguro, auditável e preparado estruturalmente para futura emissão de NFS-e e NFC-e.
</objetivo>

<tech_specs>
- [Obrigatório] Runtime e Framework: Python `3.13.6` (verificado localmente) e Django `5.2 LTS`.
- [Obrigatório] Ambiente e Dependências: Ambiente virtual `.venv` e `requirements.txt`
  sempre atualizado na raiz do projeto (`sps/`).
- [Obrigatório] Estrutura de Pacotes e Apps: Pacote principal de configuração chamado
  `core` (apenas um arquivo `core/settings.py`). App compartilhado chamado `base` (com
  `TimeStampedModel` contendo `created_at` e `updated_at` em todos os models, além de
  mixins e managers de isolamento por `salon`). Apps de domínio na raiz de `sps/`:
  `accounts`, `salons`, `catalog`, `clients`, `scheduling`, `orders`, `inventory`,
  `finance`, `fiscal`, `notifications`, `reports`, `ai_assistant`.
- [Obrigatório] Padrão de Código e Localização: Código em inglês, simples, seguindo PEP 8
  com uso consistente de aspas simples (`'`). Interface 100% em português brasileiro
  (`pt-BR`) e fuso horário de negócio `America/Sao_Paulo`. Preferência por Class-Based
  Views (CBVs) e recursos nativos do Django. Signals, quando necessários, isolados em
  `signals.py` dentro do respectivo app.
- [Obrigatório] Autenticação e Usuários: Sistema nativo de autenticação do Django com
  login por e-mail. Definir `AUTH_USER_MODEL` customizado no app `accounts` antes da
  primeira migration do projeto.
- [Obrigatório] Persistência e Mensageria Assíncrona: PostgreSQL como banco relacional;
  Celery integrado ao Django com RabbitMQ como broker, Redis como result backend e cache,
  Celery Beat para jobs agendados e `dj-celery-panel` habilitado no Django Admin.
- [Obrigatório] Relatórios, Documentação e Dados de Demonstração: `ReportLab` e `PyPDF`
  para geração de relatórios privados em PDF; documentação em `docs/` servida com `MkDocs`
  e suporte a diagramas `Mermaid`; management command `seed_demo_data` criando massa
  sintética multi-salão e multi-data para demonstrações completas.
- [Obrigatório — DEC-001] Política de Validação e Testes: Implementar testes automatizados
  focados nos fluxos críticos (isolamento cross-tenant, permissões por perfil, colisão de
  horário na agenda, cálculo de comissão exclusivamente no pagamento da comanda, bloqueio
  de saldo negativo de estoque e escopo de tenant nas tools de IA), combinados com
  revisão e verificação manual obrigatória ao término de cada sprint.
- [Condicional] Design System: Usar exclusivamente os artefatos que o desenvolvedor
  fornecer na pasta `design_system/` (`arquivo_design_system`: `a_definir` até a sprint
  de interface). Proibido inventar tokens ou buscar temas externos silenciosamente.
- [Condicional] Inteligência Artificial no Produto: Assistente Gerencial Interno construído
  com `LangChain` e `LangGraph`. O identificador do modelo (`modelo_llm`: `a_definir`) e
  respectiva chave de API devem ser lidos via variáveis de ambiente (`.env` / Docker Secret),
  sem fixar provedor hardcoded no código.
- [Obrigatório] Topologia Docker e Deploy: Docker Compose para desenvolvimento local;
  Docker Swarm em VPS Ubuntu para produção com serviços `app`, `postgres`, `celery_worker`,
  `celery_beat`, `rabbitmq`, `redis` e `traefik`. Redes `traefik_public`, `sps_internal`
  (`internal: true`) e `sps_egress`. TLS wildcard via desafio DNS-01 na Cloudflare usando
  Docker Secret `CLOUDFLARE_DNS_API_TOKEN` (`CF_DNS_API_TOKEN_FILE`). Configurar
  `SECURE_PROXY_SSL_HEADER`, `SECURE_REDIRECT_EXEMPT` para healthcheck, `wait_for_db`,
  separação entre liveness e readiness, e `scripts/deploy.sh` sem nenhum comando Git/GH.
  Parâmetros `dominio_principal` e `registry_imagem` permanecem `a_definir` até a etapa
  de implantação.
</tech_specs>

<requisitos_funcionais>
- [RF-001 — Essencial] Gestão de Salões (Tenants) e Parâmetros Operacionais/Fiscais:
  Cadastro e ativação de salões (`superadmin_saas`) e configuração pelo `gestor` do salão:
  dados cadastrais, `slug` público único, expediente por dia da semana, feriados, prazo
  mínimo em horas para cancelamento público pelo cliente e metadados fiscais preparatórios
  (CNPJ, Inscrição Municipal, Inscrição Estadual, Regime Tributário, código IBGE do
  município e flag de Salão-Parceiro).
- [RF-002 — Essencial] Autenticação por E-mail e Equipe do Salão (`DEC-002`):
  Login por e-mail; vínculo fixo de cada membro interno a um único salão nos perfis
  `gestor`, `recepcionista` ou `profissional`; cadastro de CPF/CNPJ opcional do
  profissional parceiro, expediente individual por dia da semana e bloqueios de agenda
  (folgas, férias, ausências).
- [RF-003 — Essencial] Catálogo de Serviços e Regras de Comissão:
  Cadastro de serviços por salão com nome, categoria, duração em minutos, preço base,
  status, profissionais habilitados, comissão padrão (`%`), regra de sobrescrita de
  comissão específica por par `(profissional, servico)` e metadados fiscais opcionais
  (código de serviço municipal LC 116, CNAE e alíquota ISS referencial).
- [RF-004 — Essencial] Cadastro e Histórico de Clientes por Salão:
  Base de clientes isolada por salão com nome, telefone, e-mail, observações/alergias,
  prevenção de duplicidade dentro do salão, histórico de agendamentos/comandas e dados
  fiscais opcionais para tomador (CPF/CNPJ e endereço completo).
- [RF-005 — Essencial] Agenda Inteligente Interna com Múltiplos Serviços:
  Agendamento contendo 1 ou mais serviços (somando durações e valores estimados), com
  validação atômica (`select_for_update`) contra sobreposição de horários do mesmo
  profissional, validação de expediente do salão/profissional e bloqueios, operando os
  estados `agendado`, `confirmado`, `em_atendimento`, `concluido`, `cancelado` e
  `nao_compareceu`.
- [RF-006 — Essencial] Autoagendamento e Cancelamento Público (`/s/<slug_salao>/`):
  Página pública responsiva onde o cliente final escolhe um ou mais serviços, visualiza
  apenas horários reais compatíveis com a duração total, confirma o agendamento e pode
  cancelá-lo mediante link/token somente se respeitada a antecedência mínima configurada
  pelo salão.
- [RF-007 — Essencial] Comandas de Atendimento (Serviços + Produtos):
  Abertura de comanda a partir de agendamento ou atendimento avulso, adição de múltiplos
  serviços (identificando o profissional executante de cada item) e produtos do estoque,
  aplicação de descontos/acréscimos e controle de estados (`aberta`, `fechada_paga`,
  `cancelada`).
- [RF-008 — Essencial] Controle de Estoque de Produtos por Salão:
  Cadastro de produtos (`venda`, `consumo_interno`, `ambos`) com saldo atual, estoque
  mínimo, custo, preço de venda e metadados fiscais opcionais (NCM, CEST, CFOP, origem e
  alíquotas referenciais). Baixa automática ao pagar comanda (bloqueando fechamento se
  saldo for insuficiente), registro auditável de entradas, consumo interno e ajustes em
  `StockMovement`, e alerta de estoque crítico (`saldo_atual <= estoque_minimo`).
- [RF-009 — Essencial] Caixa Diário e Geração de Comissões no Pagamento:
  Abertura/fechamento de caixa, registro de receitas e despesas e suporte a pagamentos
  simples ou mistos (`dinheiro`, `pix`, `cartao_credito`, `cartao_debito`). As comissões
  (`CommissionEntry`) são geradas **exclusivamente** no fechamento/pagamento da comanda
  no caixa, aplicando o percentual específico `(profissional, servico)` ou, na ausência,
  o percentual padrão do serviço. Estorno de comanda paga reverte atomicamente caixa,
  comissões e estoque.
- [RF-010 — Essencial] Notificações e Lembretes Assíncronos por E-mail:
  Envio assíncrono via Celery + RabbitMQ + Redis usando o sistema de e-mail do Django para
  confirmação, cancelamento e lembrete periódico (Celery Beat) de agendamentos, com
  controle de idempotência para evitar duplicidade.
- [RF-011 — Essencial] Dashboard Gerencial e Relatórios PDF Privados:
  Painel de indicadores operacionais/financeiros por período e exportação de relatórios
  em PDF (`ReportLab`/`PyPDF`) de comissões, fechamento de caixa e estoque, protegidos
  por verificação estrita de tenant e perfil.
- [RF-012 — Essencial] Assistente Gerencial Interno de IA (`LangChain` + `LangGraph`):
  Chat interno para `gestor` e `recepcionista` consultarem agenda, horários vagos,
  faturamento, comissões pendentes, clientes inativos e alertas de estoque do seu salão,
  com `salon_id` injetado pelo servidor nas tools e nunca controlado pelo texto do prompt.
- [RF-013 — Essencial (Estrutura) / Futuro (Transmissão) — DEC-003] Preparação Estrutural
  para Emissão de Notas Fiscais (NFS-e / NFC-e):
  Geração automática de registro fiscal preparatório (`FiscalDocumentRecord`) no
  fechamento da comanda paga, consolidando snapshots fiscais do emitente (salão),
  tomador (cliente), itens de serviço (base NFS-e e rateio Salão-Parceiro quando
  configurado) e itens de produto (base NFC-e), integrado a uma interface desacoplada
  (`FiscalGatewayAdapter` com implementação stub no MVP) pronta para futura ativação de
  provedor fiscal externo via Celery.
</requisitos_funcionais>

<requisitos_nao_funcionais>
- [RNF-001 — Segurança e Isolamento] Zero vazamento de dados entre salões em views, ORM,
  PDFs, tasks Celery e tools de IA; retorno `403`/`404` em acessos não autorizados,
  verificado por testes automatizados (`DEC-001`).
- [RNF-002 — Desempenho e Concorrência] Resposta `<= 2s (p95)` nas jornadas de agenda e
  comanda para carga de até 50 salões simultâneos; bloqueio transacional contra colisão
  de horários e saldo negativo de estoque.
- [RNF-003 — Usabilidade e Responsividade] Interface em `pt-BR` (`America/Sao_Paulo`),
  responsiva para Desktop (recepção/gestão) e Mobile (profissionais e agendamento público
  do cliente), fiel ao `design_system/` do desenvolvedor.
- [RNF-004 — Recuperação] Backup diário automatizado (`RPO <= 24h`) e restauração
  documentada e verificável em VPS única (`RTO <= 2h`).
- [RNF-005 — Privacidade e Segredos] Proibição de segredos em repositório; uso de `.env`
  local e Docker Secrets no Swarm; proteção de relatórios PDF e mídias privadas por
  autenticação e validação de tenant.
- [RNF-006 — Documentação e Demonstração] Documentação viva em `docs/` (MkDocs + Mermaid)
  e comando `seed_demo_data` populando cenários completos de múltiplos salões.
</requisitos_nao_funcionais>

<restricoes>
- Não implementar integração externa ativa com prefeituras/SEFAZ no MVP (manter apenas a
  modelagem completa e o contrato `FiscalGatewayAdapter` conforme `DEC-003` e `RF-013`).
- Não implementar gateway de pagamento online no autoagendamento público no MVP.
- Não converter parâmetros `a_definir` (`modelo_llm`, `dominio_principal`,
  `registry_imagem`, `arquivo_design_system`) em valores fictícios hardcoded.
</restricoes>

<tarefa_final>
Gerar o PRD (Product Requirement Document) do projeto SPS (Sistema Para Salões) em
módulos Markdown dentro de `sps/docs/01_planejamento/` (respeitando o limite de 150 a
400 linhas por módulo, com índice central em `prd_do_projeto.md`), contendo visão, escopo,
requisitos detalhados e critérios de aceite, arquitetura multi-tenant e fiscal
preparatória, guia passo a passo de deploy em VPS Ubuntu com Docker Swarm/Traefik/
Cloudflare DNS-01 e planejamento de sprints pequenas em formato checklist, deixando o
PRD em estado `aguardando_revisao_prd`.
</tarefa_final>

<controle>
- Não escrever código de negócio antes da aprovação explícita do PRD pelo desenvolvedor.
- Trabalhar estritamente em uma sprint por vez, somente após solicitação explícita.
- Revisar, testar e corrigir cada sprint antes de entregá-la ao desenvolvedor.
- Git e GitHub permanecem sob controle 100% exclusivo do desenvolvedor: a IA não deve
  executar nenhum comando `git` ou `gh`, direta ou indiretamente.
</controle>
````

---

## 2. Mapa Resumido das Mudanças em Relação ao Prompt Bruto

| Tipo de Mudança | Alteração Realizada | Justificativa / Decisão Associada |
|---|---|---|
| **Parametrização** | Definição de `nome_projeto = SPS (Sistema Para Salões)` e `slug_projeto / nome_stack = sps`. | Confirmado pelo desenvolvedor. |
| **Arquitetura** | Substituição da cláusula histórica "Não implementar testes" pela diretriz de testes automatizados para fluxos críticos + revisão manual. | Registrado formalmente em `DEC-001`. |
| **Semântica / Domínio** | Especificação do modelo multi-tenant com vínculo único de usuário interno por salão e clientes isolados por salão. | Registrado formalmente em `DEC-002`. |
| **Escopo Estrutural** | Inclusão de metadados fiscais em `RF-001`, `RF-003`, `RF-004`, `RF-008` e criação do `RF-013` (`FiscalDocumentRecord` + `FiscalGatewayAdapter` stub). | Solicitado pelo desenvolvedor para preparar futura integração de emissão de notas fiscais (`DEC-003`). |
| **Parametrização Aberta** | Manutenção explícita de `modelo_llm = a_definir`, `dominio_principal = a_definir`, `registry_imagem = a_definir` e `arquivo_design_system = a_definir`. | Evita invenção de parâmetros ainda não fixados pelo desenvolvedor. |
| **Editorial** | Organização em tags XML funcionais (`<contexto>`, `<objetivo>`, `<tech_specs>`, `<requisitos_funcionais>`, `<requisitos_nao_funcionais>`, `<restricoes>`, `<tarefa_final>`, `<controle>`). | Conformidade com o módulo de refinamento assistido do guia. |

---

## 3. Parâmetros Pendentes (`a_definir`) e Análise de Impacto

| Parâmetro | Situação Atual | Bloqueia a Geração do PRD? | Momento Limite para Definição |
|---|---|---|---|
| `modelo_llm` | `a_definir` | **Não.** O PRD especificará injeção via variável `LLM_MODEL_NAME` e `LLM_API_KEY` no `.env`. | Antes da Sprint do Assistente de IA (`ai_assistant`). |
| `arquivo_design_system` | `a_definir` | **Não.** As primeiras sprints são de fundação, modelos e regras de domínio. | Antes da Sprint de extração do catálogo visual e templates de interface. |
| `dominio_principal` | `a_definir` | **Não.** O guia de deploy no PRD usará o placeholder parametrizado `{{dominio_principal}}`. | Antes da execução real do deploy em homologação/produção na VPS. |
| `registry_imagem` | `a_definir` | **Não.** O PRD documentará o fluxo padrão via registry privado/GHCR operado pelo usuário. | Antes do build/push manual da imagem Docker pelo usuário. |

---

## 4. Checklist de Prontidão para Gerar o PRD

- [x] O desenvolvedor escolheu o modo de refinamento (**Refinamento Assistido — Caminho B**).
- [x] Nome do projeto (`SPS — Sistema Para Salões`) e stack (`Python 3.13.6`, `Django 5.2 LTS`) confirmados.
- [x] Requisitos funcionais (`RF-001` a `RF-013`, incluindo preparação para notas fiscais) e não funcionais (`RNF-001` a `RNF-006`) estruturados.
- [x] Mudanças arquiteturais (`DEC-001`, `DEC-002`, `DEC-003`) registradas com contexto e consequências.
- [x] Parâmetros `a_definir` isolados e explicados, sem invenção de valores.
- [x] **Prompt Refinado revisado e aprovado explicitamente pelo desenvolvedor em 2026-11-12 ("Aprovado, gerar o PRD").**
