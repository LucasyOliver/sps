---
versao: 1.0.0
data_editorial: 2026-11-12
tipo: prd_planejamento_sprints
projeto: SPS (Sistema Para Salões)
estado: aguardando_revisao_prd
modulo_pai: "prd_do_projeto.md"
---

# PRD — Planejamento de Sprints de Implementação — SPS (Sistema Para Salões)

## 1. Regras de Execução de Sprints

- **Uma Sprint por Solicitação Explícita:** A aprovação do PRD **não** inicia automaticamente a `Sprint 01`. Cada sprint só pode ser executada quando o desenvolvedor a solicitar expressamente.
- **Ordem de Dependências:** `AUTH_USER_MODEL` e `Salon` (`Sprint 01`) precedem todas as migrations de negócio; catálogo, clientes e agenda (`Sprints 02 a 05`) precedem comandas, estoque, caixa e preparação fiscal (`Sprints 06 e 07`); filas Celery (`Sprint 08`) precedem ou apoiam notificações e IA (`Sprint 09`).
- **Qualidade e Entrega (`DEC-001`):** Toda sprint termina com execução dos testes automatizados do incremento, verificação manual, correção de falhas, registro de evidências em `docs/02_execucao/evidencias_da_sprint_0XX.md` e entrega ao desenvolvedor para realização manual de commit/push no Git/GitHub.

---

## Sprint 01: Fundação Técnica, Usuário Customizado (`AUTH_USER_MODEL`) e Tenant (`Salon`)

- **Solicitação do usuário:** `solicitada e concluída em 2026-11-12`
- **Requisitos atendidos:** `RF-001` (base e fiscal do salão), `RF-002` (autenticação por e-mail e vínculo fixo de salão), `RNF-001`, `RNF-005`
- **Pré-condições:** PRD `v1.0.0` aprovado pelo desenvolvedor e Docker Desktop ativo para banco local.
- **Tarefas da Sprint:**
  - [x] `S01-T01`: Criar `.venv` (`Python 3.13.6`), `requirements.txt` inicial, `.env.example` e `docker-compose.yml` local (`postgres`, `rabbitmq`, `redis`).
  - [x] `S01-T02`: Inicializar pacote `core` (`settings.py` único com `FileAwareEnv`, fuso `America/Sao_Paulo`, `pt-br`) e app `base` (`TimeStampedModel`, `TenantScopedModel`, comando `wait_for_db` e rotas `/healthz/` e `/readyz/`).
  - [x] `S01-T03`: Criar app `salons` com model `Salon` (incluindo `slug`, configurações de cancelamento e campos fiscais preparatórios: CNPJ, IM, IE, regime tributário, código IBGE e flag Salão-Parceiro — `DEC-003`).
  - [x] `S01-T04`: Criar app `accounts` com model customizado `User` (login por e-mail, `AUTH_USER_MODEL = 'accounts.User'`, papéis `superadmin_saas`, `gestor`, `recepcionista`, `profissional` e vínculo fixo `salon` — `DEC-002`) **antes da primeira migration**.
  - [x] `S01-T05`: Gerar e aplicar as primeiras migrations, configurar Django Admin para `Salon` e `User` e implementar login/logout nativo por e-mail.
  - [x] `S01-T06`: Escrever e executar testes automatizados (`DEC-001`) de criação de usuário por e-mail, obrigatoriedade de `salon` para perfis internos e funcionamento de `/healthz/` e `/readyz/`.
  - [x] `S01-T07`: Revisar incremento, corrigir pendências, registrar `evidencias_da_sprint_001.md` e entregar para ação de Git/GitHub do usuário.

---

## Sprint 02: Configurações do Salão, Expediente, Equipe e Isolamento Multi-tenant

- **Solicitação do usuário:** `solicitada e concluída em 2026-11-12`
- **Requisitos atendidos:** `RF-001`, `RF-002`, `RNF-001`
- **Pré-condições:** `Sprint 01` concluída.
- **Tarefas da Sprint:**
  - [x] `S02-T01`: Implementar `SalonBusinessHours` (expediente do salão por dia da semana) e `SalonHoliday` (feriados/fechamentos) no app `salons`.
  - [x] `S02-T02`: Implementar `SalonTenantRequiredMixin` e mixins de autorização por perfil (`GestorRequiredMixin`, `RecepcaoOrGestorMixin`, `ProfissionalScopeMixin`) em `base`.
  - [x] `S02-T03`: Implementar CBVs para o `gestor` editar dados operacionais e fiscais do próprio salão e gerir membros da equipe (`gestor`, `recepcionista`, `profissional` com CPF/CNPJ opcional de parceiro).
  - [x] `S02-T04`: Implementar no app `scheduling` os modelos e telas de expediente individual do profissional (`ProfessionalSchedule`) e bloqueios de agenda (`ScheduleBlock` para férias/folgas/ausências).
  - [x] `S02-T05`: Escrever e executar testes automatizados (`DEC-001`) garantindo que usuários do Salão A recebem `403`/`404` ao tentar acessar/editar equipe ou configurações do Salão B e que `recepcionista`/`profissional` não alteram dados fiscais do salão.
  - [x] `S02-T06`: Revisar incremento, registrar `evidencias_da_sprint_002.md` e entregar para ação de Git/GitHub do usuário.

---

## Sprint 03: Catálogo de Serviços, Regras de Comissão e Cadastro de Clientes

- **Solicitação do usuário:** `solicitada e concluída em 2026-11-12`
- **Requisitos atendidos:** `RF-003`, `RF-004`, `RNF-001`
- **Pré-condições:** `Sprint 02` concluída.
- **Tarefas da Sprint:**
  - [x] `S03-T01`: Criar app `catalog` com `ServiceCategory`, `Service` (duração em minutos, preço base, comissão padrão `%`, profissionais habilitados e códigos fiscais opcionais LC 116, CNAE e ISS) e `ProfessionalServiceCommission` (comissão específica por profissional e serviço).
  - [x] `S03-T02`: Implementar função de domínio `resolve_commission_percentage(salon, professional, service)` que retorna o percentual específico do profissional ou, na ausência, o percentual padrão do serviço.
  - [x] `S03-T03`: Criar app `clients` com model `Client` isolado por salão (dados de contato, observações/alergias e dados fiscais opcionais de tomador: CPF/CNPJ e endereço completo com CEP/IBGE) e validação de unicidade dentro do salão.
  - [x] `S03-T04`: Implementar CBVs de listagem, busca, criação e edição de Serviços, Regras de Comissão e Clientes (com aba de histórico de atendimentos).
  - [x] `S03-T05`: Escrever e executar testes automatizados (`DEC-001`) de isolamento cross-tenant de clientes/serviços e de resolução de precedência de comissão (`ProfessionalServiceCommission` vs `Service.default_commission_pct`).
  - [x] `S03-T06`: Revisar incremento, registrar `evidencias_da_sprint_003.md` e entregar para ação de Git/GitHub do usuário.

---

## Sprint 04: Motor de Disponibilidade e Agenda Inteligente Interna (Múltiplos Serviços)

- **Solicitação do usuário:** `solicitada e concluída em 2026-11-13`
- **Requisitos atendidos:** `RF-005`, `RNF-001`, `RNF-002`
- **Pré-condições:** `Sprint 03` concluída.
- **Tarefas da Sprint:**
  - [x] `S04-T01`: Implementar modelos `Appointment` e `AppointmentItem` no app `scheduling`, suportando 1 ou mais serviços no mesmo agendamento com soma automática de `duration_minutes` e `total_estimated_amount`.
  - [x] `S04-T02`: Implementar `AvailabilityService` (cálculo de horários livres considerando expediente do salão, feriados, expediente do profissional, `ScheduleBlock` e agendamentos ativos).
  - [x] `S04-T03`: Implementar `SchedulingService` com bloqueio transacional (`transaction.atomic()` + `select_for_update()` no profissional) impedindo sobreposição de horários (`[start_at, end_at)`) e gerenciando transições de estado (`agendado`, `confirmado`, `em_atendimento`, `concluido`, `cancelado`, `nao_compareceu`).
  - [x] `S04-T04`: Implementar CBVs da Agenda Interna (visão diária/semanal por profissional, criação rápida, remarcação e mudança de status com escopo restrito ao próprio profissional quando perfil = `profissional`).
  - [x] `S04-T05`: Escrever e executar testes automatizados (`DEC-001`) cobrindo soma de múltiplos serviços, rejeição de *double-booking*, bloqueio em horário de folga e isolamento entre salões.
  - [x] `S04-T06`: Revisar incremento, registrar `evidencias_da_sprint_004.md` e entregar para ação de Git/GitHub do usuário.

---

## Sprint 05: Design System, Autoagendamento Público (`/s/<slug>/`) e Cancelamento

- **Solicitação do usuário:** `solicitada e concluída em 2026-11-13`
- **Requisitos atendidos:** `RF-006`, `RNF-002`, `RNF-003`
- **Pré-condições:** `Sprint 04` concluída e pasta `sps/design_system/` fornecida pelo desenvolvedor.
- **Tarefas da Sprint:**
  - [x] `S05-T01`: Inventariar `sps/design_system/`, documentar o catálogo visual em `docs/01_planejamento/catalogo_design_system.md` e aplicar tokens/componentes nos layouts base Desktop e Mobile.
  - [x] `S05-T02`: Implementar páginas públicas `/s/<slug_salao>/` onde o cliente seleciona múltiplos serviços, escolhe profissional e horário livre real (via `AvailabilityService`) e confirma o agendamento recebendo `public_token`.
  - [x] `S05-T03`: Implementar rota pública de consulta e cancelamento `/s/<slug_salao>/agendamento/<public_token>/` que valida `timezone.now() <= appointment.start_at - timedelta(hours=salon.cancellation_min_hours)`.
  - [x] `S05-T04`: Escrever e executar testes automatizados (`DEC-001`) de agendamento público com múltiplos serviços, bloqueio de conflito com agenda interna e negação de cancelamento fora da antecedência mínima configurada pelo salão.
  - [x] `S05-T05`: Revisar incremento em larguras Desktop e Mobile, registrar `evidencias_da_sprint_005.md` e entregar para ação de Git/GitHub do usuário.

---

## Sprint 06: Controle de Estoque de Produtos e Comandas de Atendimento

- **Solicitação do usuário:** `solicitada e concluída em 2026-11-13`
- **Requisitos atendidos:** `RF-007`, `RF-008`, `RNF-001`, `RNF-002`
- **Pré-condições:** `Sprint 05` concluída.
- **Tarefas da Sprint:**
  - [x] `S06-T01`: Criar app `inventory` com `Product` (tipo `venda`/`consumo_interno`/`ambos`, custo, preço de venda, `current_stock`, `min_stock_alert` e metadados fiscais NCM, CEST, CFOP, origem e alíquotas) e `StockMovement`.
  - [x] `S06-T02`: Implementar serviço de movimentação manual de estoque (entradas de compra, baixas por consumo interno e ajustes auditados) com bloqueio de saldo negativo e listagem de alertas (`current_stock <= min_stock_alert`).
  - [x] `S06-T03`: Criar app `orders` com `ServiceOrder`, `OrderServiceItem` (vinculando serviço e profissional executante) e `OrderProductItem` (vinculando produto do estoque e quantidade), permitindo abrir comanda a partir de um `Appointment` ou avulsa.
  - [x] `S06-T04`: Implementar CBVs de gestão de Estoque e operação de Comandas abertas (adição/remoção de itens, descontos e cálculo de totais).
  - [x] `S06-T05`: Escrever e executar testes automatizados (`DEC-001`) de movimentação de estoque, alerta de estoque mínimo e cálculo de comanda mista (serviços + produtos).
  - [x] `S06-T06`: Revisar incremento, registrar `evidencias_da_sprint_006.md` e entregar para ação de Git/GitHub do usuário.

---

## Sprint 07: Caixa Diário, Comissões no Pagamento e Preparação Fiscal (`RF-013`)

- **Solicitação do usuário:** `solicitada e concluída em 2026-11-18`
- **Requisitos atendidos:** `RF-009`, `RF-013`, `RNF-001`, `RNF-002`
- **Pré-condições:** `Sprint 06` concluída.
- **Tarefas da Sprint:**
  - [x] `S07-T01`: Criar app `finance` com `CashRegisterSession` (abertura/fechamento de caixa), `CashTransaction` (entradas e despesas), `OrderPayment` (múltiplos meios de pagamento) e `CommissionEntry`.
  - [x] `S07-T02`: Criar app `fiscal` com `FiscalDocumentRecord` (snapshots de emitente, tomador, payload fiscal de serviços/Salão-Parceiro para NFS-e e payload de produtos para NFC-e) e interface `FiscalGatewayAdapter` (*NoOp/Stub* documentado para futura integração — `DEC-003`).
  - [x] `S07-T03`: Implementar `OrderCheckoutService.close_and_pay_order()` em transação atômica única: valida caixa aberto, valida e baixa estoque dos produtos vendidos (abortando se saldo for insuficiente), registra pagamentos no caixa, gera `CommissionEntry` para cada serviço pago e cria `FiscalDocumentRecord`.
  - [x] `S07-T04`: Implementar fluxo de estorno de comanda paga (exclusivo do `gestor`) revertendo atomicamente caixa, comissões, saldo de estoque e status do registro fiscal, além de tela de extrato e baixa de repasse de comissões aos profissionais.
  - [x] `S07-T05`: Escrever e executar testes automatizados (`DEC-001`) provando que comissões **não** nascem antes do pagamento, que o pagamento gera comissão com o percentual correto, que falta de estoque aborta o fechamento e que o `FiscalDocumentRecord` é populado.
  - [x] `S07-T06`: Revisar incremento, registrar `evidencias_da_sprint_007.md` e entregar para ação de Git/GitHub do usuário.

---

## Sprint 08: Filas Assíncronas (Celery), Notificações, Dashboard e Relatórios PDF

- **Solicitação do usuário:** `solicitada e concluída em 2026-11-18`
- **Requisitos atendidos:** `RF-010`, `RF-011`, `RNF-001`, `RNF-005`
- **Pré-condições:** `Sprint 07` concluída.
- **Tarefas da Sprint:**
  - [x] `S08-T01`: Configurar `core/celery.py` (RabbitMQ broker, Redis result backend/cache), schedules do Celery Beat e integrar `dj-celery-panel` ao Django Admin.
  - [x] `S08-T02`: Criar app `notifications` com `NotificationLog` e tasks Celery idempotentes para envio de e-mail nativo do Django na confirmação, cancelamento e lembrete periódico de agendamentos.
  - [x] `S08-T03`: Criar app `reports` com Dashboard Gerencial (faturamento bruto/líquido, comandas, comissões pendentes/pagas, taxa de comparecimento e alertas de estoque crítico).
  - [x] `S08-T04`: Implementar exportação privada de relatórios em PDF (`ReportLab` + `PyPDF`) para: (1) Extrato de Comissões por Profissional/Período; (2) Fechamento de Caixa; (3) Posição e Movimentação de Estoque, validando tenant e perfil antes de entregar o PDF.
  - [x] `S08-T05`: Escrever e executar testes automatizados (`DEC-001`) de idempotência de notificações e de bloqueio (`403`) ao tentar baixar PDF de outro salão ou de outro profissional.
  - [x] `S08-T06`: Revisar incremento, registrar `evidencias_da_sprint_008.md` e entregar para ação de Git/GitHub do usuário.

---

## Sprint 09: Assistente Gerencial Interno de IA (`LangChain` + `LangGraph`)

- **Solicitação do usuário:** `solicitada e concluída em 2026-11-18`
- **Requisitos atendidos:** `RF-012`, `RNF-001`, `RNF-005`
- **Pré-condições:** `Sprint 08` concluída.
- **Tarefas da Sprint:**
  - [x] `S09-T01`: Criar app `ai_assistant` com modelos de sessão/mensagens de chat escopados por `salon` e usuário, e fábrica de LLM parametrizada por `.env` (`LLM_MODEL`, `LLM_API_KEY`).
  - [x] `S09-T02`: Implementar *tools* somente-leitura (`get_salon_agenda_summary`, `get_revenue_and_commissions_summary`, `get_low_stock_products`, `get_inactive_clients`) que recebem `salon_id` e `user_role` fixados pelo servidor autenticado.
  - [x] `S09-T03`: Orquestrar o agente com `LangGraph`, garantindo que `recepcionista` tenha acesso às tools operacionais de agenda/estoque/clientes e `gestor` tenha acesso completo incluindo faturamento/comissões globais.
  - [x] `S09-T04`: Implementar interface de chat do Assistente Gerencial Interno no painel do salão.
  - [x] `S09-T05`: Escrever e executar testes automatizados (`DEC-001`) verificando que uma sessão do Salão A jamais retorna dados do Salão B nas tools mesmo sob tentativa de *prompt injection*, e que um `profissional` não acessa o assistente gerencial.
  - [x] `S09-T06`: Revisar incremento, registrar `evidencias_da_sprint_009.md` e entregar para ação de Git/GitHub do usuário.

---

## Sprint 10: Carga Demo (`seed_demo_data`), Documentação `MkDocs` e Deploy Swarm

- **Solicitação do usuário:** `pendente`
- **Requisitos atendidos:** `RNF-004`, `RNF-005`, `RNF-006`
- **Pré-condições:** `Sprint 09` concluída.
- **Tarefas da Sprint:**
  - [ ] `S10-T01`: Implementar management command `seed_demo_data` populando múltiplos salões, equipes, serviços, regras de comissão, clientes, agendamentos passados/atuais/futuros, comandas pagas, movimentações de estoque e registros fiscais preparatórios (bloqueando execução acidental quando `DEBUG=False`).
  - [ ] `S10-T02`: Configurar `mkdocs.yml` com suporte a renderização `Mermaid` e consolidar a documentação técnica e operacional em `sps/docs/`.
  - [ ] `S10-T03`: Criar `Dockerfile` de produção, `docker-stack.yml` (Swarm + Traefik + Cloudflare DNS-01 + Docker Secrets), `scripts/deploy.sh` (sem nenhum comando Git/GH) e scripts de backup/restauração em `docs/04_operacao/runbook_de_implantacao.md`.
  - [ ] `S10-T04`: Executar suíte completa de testes automatizados do projeto e validar carga `seed_demo_data` e build do `MkDocs`.
  - [ ] `S10-T05`: Revisar entrega final do MVP, registrar `evidencias_da_sprint_010.md` e entregar ao usuário para versionamento Git/GitHub e decisão de deploy.
