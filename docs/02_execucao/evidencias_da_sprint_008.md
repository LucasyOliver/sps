---
versao: 1.0.0
data_editorial: 2026-11-18
tipo: evidencias_de_sprint
projeto: SPS (Sistema Para Salões)
id_sprint: Sprint 08
estado: concluida_e_verificada
---

# Evidências de Execução e Revisão — Sprint 08 — SPS (Sistema Para Salões)

## 1. Identificação e Escopo da Sprint 08

- **Sprint Executada:** `Sprint 08 — Filas Assíncronas (Celery), Notificações, Dashboard e Relatórios PDF`
- **Solicitação Explícita do Desenvolvedor:** *"Inicie a sprint 08"* (registrada em `2026-11-18`).
- **Requisitos Atendidos:**
  - `RF-010`: Notificações e Lembretes Assíncronos por E-mail (`Celery` + `RabbitMQ` + `Redis` + `dj-celery-panel`), com `NotificationLog` e chave de idempotência (`UniqueConstraint(fields=['appointment', 'notification_type', 'reference_window'])`), impedindo envios duplicados em retentativas e revalidando no banco se o salão e o agendamento permanecem ativos (`SEC-F`).
  - `RF-011`: Dashboard Gerencial (`faturamento bruto/líquido`, `ticket médio`, `comissões pendentes/pagas`, `taxa de comparecimento/no-show` e `alertas de estoque crítico`) e exportação privada de 3 relatórios em PDF (`ReportLab` + `PyPDF`):
    1. Extrato de Comissões por Profissional e Período;
    2. Relatório de Fechamento de Caixa;
    3. Posição e Movimentação de Estoque.
  - `RNF-001` e `RNF-005`: Proteção estrita de downloads de PDFs por view autenticada validando `salon` e perfil do solicitante (`403 Forbidden` em tentativas cruzadas entre profissionais ou entre salões — `SEC-E`).
- **Decisões Arquiteturais Aplicadas:** `DEC-001` (Testes automatizados + revisão manual) e `DEC-002` (Isolamento multi-tenant por `Salon`).

---

## 2. Resumo das Entregas por Tarefa (`S08-T01` a `S08-T06`)

| ID Tarefa | Descrição no PRD (`sprints_de_implementacao_prd.md`) | Arquivos Criados / Atualizados | Situação |
|---|---|---|---|
| `S08-T01` | Configurar `core/celery.py` (RabbitMQ broker, Redis result backend/cache), schedules do Celery Beat e integrar `dj-celery-panel` ao Django Admin. | [`sps/core/celery.py`](../../core/celery.py), [`sps/core/__init__.py`](../../core/__init__.py), [`sps/core/settings.py`](../../core/settings.py), [`sps/core/urls.py`](../../core/urls.py), [`sps/requirements.txt`](../../requirements.txt) | Concluída (`[x]`) |
| `S08-T02` | Criar app `notifications` com `NotificationLog` e tasks Celery idempotentes para envio de e-mail nativo do Django na confirmação, cancelamento e lembrete periódico de agendamentos. | [`sps/notifications/models.py`](../../notifications/models.py), [`sps/notifications/services.py`](../../notifications/services.py), [`sps/notifications/tasks.py`](../../notifications/tasks.py), [`sps/notifications/admin.py`](../../notifications/admin.py), [`sps/notifications/migrations/0001_initial.py`](../../notifications/migrations/0001_initial.py) | Concluída (`[x]`) |
| `S08-T03` | Criar app `reports` com Dashboard Gerencial (faturamento bruto/líquido, comandas, comissões pendentes/pagas, taxa de comparecimento e alertas de estoque crítico). | [`sps/reports/services.py`](../../reports/services.py), [`sps/reports/views.py`](../../reports/views.py), [`sps/templates/reports/dashboard.html`](../../templates/reports/dashboard.html), [`sps/templates/base.html`](../../templates/base.html) | Concluída (`[x]`) |
| `S08-T04` | Implementar exportação privada de relatórios em PDF (`ReportLab` + `PyPDF`) para: (1) Extrato de Comissões por Profissional/Período; (2) Fechamento de Caixa; (3) Posição e Movimentação de Estoque, validando tenant e perfil antes de entregar o PDF. | [`sps/reports/pdf_generators.py`](../../reports/pdf_generators.py), [`sps/reports/views.py`](../../reports/views.py), [`sps/reports/urls.py`](../../reports/urls.py), [`sps/templates/finance/commission_list.html`](../../templates/finance/commission_list.html), [`sps/templates/finance/cash_register_dashboard.html`](../../templates/finance/cash_register_dashboard.html) | Concluída (`[x]`) |
| `S08-T05` | Escrever e executar testes automatizados (`DEC-001`) de idempotência de notificações e de bloqueio (`403`) ao tentar baixar PDF de outro salão ou de outro profissional. | [`sps/notifications/tests.py`](../../notifications/tests.py) (2 testes) e [`sps/reports/tests.py`](../../reports/tests.py) (2 testes), totalizando **50 testes** na suíte do projeto | Concluída (`[x]`) |
| `S08-T06` | Revisar incremento, registrar [`evidencias_da_sprint_008.md`](evidencias_da_sprint_008.md) e entregar para ação de Git/GitHub do usuário. | [`evidencias_da_sprint_008.md`](evidencias_da_sprint_008.md), [`estado_do_projeto.md`](estado_do_projeto.md), [`sprints_de_implementacao_prd.md`](../01_planejamento/sprints_de_implementacao_prd.md), [`parametros_do_projeto.json`](../../parametros_do_projeto.json) | Concluída (`[x]`) |

---

## 3. Detalhamento Técnico da Implementação

### 3.1 Configuração de Filas Celery, Beat e `dj-celery-panel` (`S08-T01`)
1. **[`sps/core/celery.py`](../../core/celery.py) e [`sps/core/settings.py`](../../core/settings.py):**
   - Instância `Celery('sps')` configurada com `namespace='CELERY'`, `CELERY_BROKER_URL` (RabbitMQ), `CELERY_RESULT_BACKEND` (Redis) e `CELERY_TIMEZONE = 'America/Sao_Paulo'`.
   - Schedule `CELERY_BEAT_SCHEDULE` configurado para executar `notifications.dispatch_upcoming_appointment_reminders_task` a cada 30 minutos (`1800.0s`).
   - Painel administrativo `dj_celery_panel` registrado em `INSTALLED_APPS` e exposto sob `/admin/dj-celery-panel/`.

### 3.2 Notificações Idempotentes e Revalidação de Segurança (`S08-T02`, `RF-010`, `SEC-F`)
1. **Modelo `NotificationLog` ([`sps/notifications/models.py`](../../notifications/models.py)):**
   - Restrição de unicidade `UniqueConstraint(fields=['appointment', 'notification_type', 'reference_window'], name='unique_appointment_notification_window')`.
2. **`NotificationService` e Tasks Celery ([`sps/notifications/services.py`](../../notifications/services.py), [`sps/notifications/tasks.py`](../../notifications/tasks.py)):**
   - As tasks `send_appointment_notification_task` e `dispatch_upcoming_appointment_reminders_task` recebem IDs primitivos (`salon_id`, `appointment_id`), consultam o banco no momento da execução, verificam se já existe `NotificationLog` para a janela (`reference_window`) e revalidam se `salon.is_active` é verdadeiro e se o agendamento permanece em estado compatível (`SEC-F`).

### 3.3 Dashboard Gerencial e Exportação Privada em PDF (`S08-T03`, `S08-T04`, `RF-011`, `SEC-E`)
1. **`DashboardAnalyticsService` ([`sps/reports/services.py`](../../reports/services.py)):**
   - Consolida `gross_revenue`, `net_revenue`, `average_ticket`, `commissions_pending_total`, `commissions_paid_total`, `attendance_rate_pct`, `no_show_rate_pct` e `low_stock_products` filtrados estritamente por `salon`.
2. **Geradores PDF com `ReportLab` + `PyPDF` ([`sps/reports/pdf_generators.py`](../../reports/pdf_generators.py)):**
   - Renderizam os relatórios em memória (`io.BytesIO`) usando `reportlab.pdfgen.canvas.Canvas` e injetam metadados institucionais (`/Title`, `/Author: SPS — <Salão>`, `/Producer: ReportLab + PyPDF`) com `pypdf.PdfReader`/`PdfWriter`, sem jamais gravar arquivos em diretório estático público (`RNF-005`).
3. **Views Protegidas ([`sps/reports/views.py`](../../reports/views.py)):**
   - `CommissionReportPdfView`: `profissional` baixa apenas o próprio PDF (qualquer tentativa de informar `professional` de terceiro retorna `403 Forbidden`); `gestor` baixa de qualquer profissional do seu salão (`403` se informar profissional ou salão externo).
   - `CashClosingReportPdfView`: restrito a `gestor` e `recepcionista` do salão proprietário da sessão (`403` para `profissional` ou para sessão de outro salão).
   - `InventoryReportPdfView`: exclusivo do `gestor` do próprio salão (`403` para demais perfis ou salão externo).

---

## 4. Revisão Manual Estruturada do Incremento (`DEC-001`)

| Código | Verificação Realizada | Resultado |
|---|---|---|
| **SEC-E** | `profissional` tentando baixar PDF de comissões de outro profissional ou PDF de caixa/estoque do salão recebe `403 Forbidden`? | **Aprovado:** Validado em `test_pdf_export_blocks_other_professional_and_cross_tenant_with_403`. |
| **SEC-B / SEC-E** | `gestor` do Salão A tentando baixar PDF de caixa, comissão ou estoque do Salão B recebe `403 Forbidden`? | **Aprovado:** Validado em `test_pdf_export_blocks_other_professional_and_cross_tenant_with_403`. |
| **SEC-F** | Task Celery executada após cancelamento do agendamento ou desativação do salão aborta envio de lembrete sem disparar e-mail indevido? | **Aprovado:** Validado em `test_sec_f_task_aborts_cleanly_when_appointment_cancelled_or_salon_inactive`. |
| **IDEMP-01** | Duas execuções seguidas da task de lembrete para a mesma janela enviam apenas 1 e-mail? | **Aprovado:** Validado em `test_reminder_task_idempotency_sends_single_email_when_executed_twice`. |

---

## 5. Resultados dos Testes Automatizados Executados (`S08-T05`, `DEC-001`)

### Comando Executado
```powershell
Set-Location "c:\Users\lucas\Desktop\Sistema para barbearia\sps"
$env:USE_SQLITE_FALLBACK="True"
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test base salons accounts scheduling catalog clients inventory orders finance fiscal notifications reports -v 2
```

### Cobertura Adicionada na `Sprint 08` (`notifications/tests.py` e `reports/tests.py`)
1. `test_reminder_task_idempotency_sends_single_email_when_executed_twice`: Executa duas vezes `dispatch_upcoming_appointment_reminders_task` para o mesmo agendamento confirmado e comprova que apenas `1` e-mail é enviado (`len(mail.outbox) == 1`) e `1` registro consta em `NotificationLog`.
2. `test_sec_f_task_aborts_cleanly_when_appointment_cancelled_or_salon_inactive`: Comprova que agendamento cancelado ou salão inativo bloqueia o envio de lembrete, gravando `status='ignorado_inativo'`.
3. `test_dashboard_metrics_and_valid_pdf_downloads_with_pypdf_metadata`: Verifica métricas do Dashboard Gerencial e leitura estrutural dos 3 PDFs via `PyPDF` (`PdfReader`).
4. `test_pdf_export_blocks_other_professional_and_cross_tenant_with_403`: Comprova resposta `403 Forbidden` em todas as tentativas de acesso cruzado entre profissionais ou entre salões.

### Saída Consolidada dos Testes (`50 testes — OK`)
```text
No changes detected
System check identified no issues (0 silenced).
Found 50 test(s).
test_liveness_endpoint_returns_ok_even_without_https_header (base.tests.HealthcheckAndWaitForDbTests) ... ok
test_proxy_ssl_header_and_healthcheck_redirect_exemption (base.tests.HealthcheckAndWaitForDbTests) ... ok
test_readiness_endpoint_returns_ready_when_db_available (base.tests.HealthcheckAndWaitForDbTests) ... ok
test_wait_for_db_raises_command_error_on_timeout (base.tests.HealthcheckAndWaitForDbTests) ... ok
test_wait_for_db_succeeds_immediately_when_db_available (base.tests.HealthcheckAndWaitForDbTests) ... ok
test_business_hours_and_holiday_validation (salons.tests.SalonModelAndIsolationTests) ... ok
test_create_salon_with_operational_and_fiscal_fields (salons.tests.SalonModelAndIsolationTests) ... ok
test_gestor_can_update_own_salon_settings_and_fiscal_data (salons.tests.SalonModelAndIsolationTests) ... ok
test_gestor_cannot_edit_other_salon_settings_cross_tenant (salons.tests.SalonModelAndIsolationTests) ... ok
test_invalid_cnpj_and_ibge_raise_validation_error (salons.tests.SalonModelAndIsolationTests) ... ok
test_recepcionista_and_profissional_receive_403_on_salon_settings_and_hours_write (salons.tests.SalonModelAndIsolationTests) ... ok
test_create_salon_member_and_normalize_email (accounts.tests.AccountsAndTenantBindingTests) ... ok
test_create_superuser_saas_without_salon_succeeds (accounts.tests.AccountsAndTenantBindingTests) ... ok
test_email_login_and_authenticated_home_view (accounts.tests.AccountsAndTenantBindingTests) ... ok
test_gestor_cannot_edit_team_member_from_other_salon (accounts.tests.AccountsAndTenantBindingTests) ... ok
test_gestor_creates_team_member_bound_to_own_salon_and_isolates_list (accounts.tests.AccountsAndTenantBindingTests) ... ok
test_internal_user_requires_fixed_salon_binding (accounts.tests.AccountsAndTenantBindingTests) ... ok
test_non_gestor_cannot_access_team_management (accounts.tests.AccountsAndTenantBindingTests) ... ok
test_agenda_views_professional_scope_and_cross_tenant_isolation (scheduling.tests.ProfessionalScheduleAndBlockTests) ... ok
test_availability_service_respects_breaks_blocks_and_holidays (scheduling.tests.ProfessionalScheduleAndBlockTests) ... ok
test_cross_tenant_professional_assignment_is_rejected (scheduling.tests.ProfessionalScheduleAndBlockTests) ... ok
test_multi_service_duration_sum_and_double_booking_rejection (scheduling.tests.ProfessionalScheduleAndBlockTests) ... ok
test_professional_schedule_must_fit_within_salon_business_hours (scheduling.tests.ProfessionalScheduleAndBlockTests) ... ok
test_public_booking_blocks_conflict_with_internal_agenda (scheduling.tests.ProfessionalScheduleAndBlockTests) ... ok
test_public_booking_creates_client_multi_service_appointment_and_reuses_client (scheduling.tests.ProfessionalScheduleAndBlockTests) ... ok
test_public_cancellation_deadline_enforcement (scheduling.tests.ProfessionalScheduleAndBlockTests) ... ok
test_public_routes_enforce_tenant_isolation_and_active_salon (scheduling.tests.ProfessionalScheduleAndBlockTests) ... ok
test_schedule_block_overlaps_and_professional_scope_isolation (scheduling.tests.ProfessionalScheduleAndBlockTests) ... ok
test_status_transitions_cancellation_reason_and_reschedule (scheduling.tests.ProfessionalScheduleAndBlockTests) ... ok
test_cross_tenant_association_rejected_in_forms_and_models (catalog.tests.CatalogAndCommissionTests) ... ok
test_resolve_commission_percentage_precedence_and_amount (catalog.tests.CatalogAndCommissionTests) ... ok
test_service_and_commission_views_permissions_and_cross_tenant_isolation (catalog.tests.CatalogAndCommissionTests) ... ok
test_client_normalization_and_uniqueness_scoped_per_salon (clients.tests.ClientModelAndIsolationTests) ... ok
test_client_search_detail_and_cross_tenant_isolation (clients.tests.ClientModelAndIsolationTests) ... ok
test_inventory_views_permissions_and_cross_tenant_isolation (inventory.tests.InventoryModelServiceAndIsolationTests) ... ok
test_product_fiscal_metadata_validation_and_uniqueness_per_salon (inventory.tests.InventoryModelServiceAndIsolationTests) ... ok
test_stock_movements_negative_balance_block_low_stock_alert_and_immutability (inventory.tests.InventoryModelServiceAndIsolationTests) ... ok
test_mixed_order_calculation_multiple_professionals_products_and_discounts (orders.tests.ServiceOrderAndIsolationTests) ... ok
test_open_order_from_appointment_and_prevent_duplicate_active_order (orders.tests.ServiceOrderAndIsolationTests) ... ok
test_order_rejects_internal_only_product_excess_stock_and_disabled_professional (orders.tests.ServiceOrderAndIsolationTests) ... ok
test_order_views_permissions_and_cross_tenant_isolation (orders.tests.ServiceOrderAndIsolationTests) ... ok
test_commission_statement_professional_scope_payout_and_cross_tenant_isolation (finance.tests.FinanceCheckoutCommissionAndIsolationTests) ... ok
test_insufficient_stock_at_checkout_aborts_entire_atomic_transaction (finance.tests.FinanceCheckoutCommissionAndIsolationTests) ... ok
test_no_commission_before_payment_and_checkout_generates_commission_stock_and_fiscal (finance.tests.FinanceCheckoutCommissionAndIsolationTests) ... ok
test_paid_order_reversal_by_gestor_reverts_cash_commissions_stock_and_fiscal (finance.tests.FinanceCheckoutCommissionAndIsolationTests) ... ok
test_stub_fiscal_adapter_determines_nfse_and_nfce_scopes (fiscal.tests.FiscalPreparationAdapterTests) ... ok
test_reminder_task_idempotency_sends_single_email_when_executed_twice (notifications.tests.NotificationIdempotencyAndSecurityTests) ... ok
test_sec_f_task_aborts_cleanly_when_appointment_cancelled_or_salon_inactive (notifications.tests.NotificationIdempotencyAndSecurityTests) ... ok
test_dashboard_metrics_and_valid_pdf_downloads_with_pypdf_metadata (reports.tests.DashboardAndPrivatePdfReportTests) ... ok
test_pdf_export_blocks_other_professional_and_cross_tenant_with_403 (reports.tests.DashboardAndPrivatePdfReportTests) ... ok

----------------------------------------------------------------------
Ran 50 tests

OK
```

---

## 6. Verificações Executadas vs. Não Executadas nesta Sessão

| Categoria | Descrição | Status |
|---|---|---|
| **Executada** | Instalação de `celery`, `redis`, `dj-celery-panel`, `reportlab` e `pypdf` em `.venv` e atualização de `requirements.txt`. | `OK` |
| **Executada** | Checagem de migrations (`makemigrations --check --dry-run`) e `manage.py check`. | `OK (0 issues)` |
| **Executada** | Suíte de testes de `notifications` e `reports` + regressão completa (`50` testes). | `OK (50 testes)` |
| **Não Executada (Governança)** | Comandos `git` e `gh` (`git status`, `git add`, `git commit`, `git push`). | Sob controle 100% exclusivo do desenvolvedor |

---

## 7. Status de Entrega e Próxima Ação do Desenvolvedor

- **Situação da Sprint 08:** Concluída, revisada e verificada com **50 testes automatizados aprovados (`OK`)**.
- **Operações Git/GitHub:** Nenhuma operação `git` ou `gh` foi executada pela IA (`git_executado_pela_ia: false`).
- **Sugestão de Commit Manual para o Desenvolvedor:**
  - `feat(sprint-08): add celery tasks, idempotent email notifications, dashboard and private pdf reports`
- **Próximo Passo Permitido:** Após revisar os arquivos e realizar (ou decidir adiar) o commit/push manual no seu repositório Git, solicite explicitamente o início da **`Sprint 09`** (*Assistente Gerencial Interno de IA — `LangChain` + `LangGraph`*).
