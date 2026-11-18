---
versao: 1.0.0
data_editorial: 2026-11-18
tipo: evidencias_de_sprint
projeto: SPS (Sistema Para Salões)
id_sprint: Sprint 07
estado: concluida_e_verificada
---

# Evidências de Execução e Revisão — Sprint 07 — SPS (Sistema Para Salões)

## 1. Identificação e Escopo da Sprint 07

- **Sprint Executada:** `Sprint 07 — Caixa Diário, Comissões no Pagamento e Preparação Fiscal (RF-013)`
- **Solicitação Explícita do Desenvolvedor:** *"Pode prosseguir com a sprint 07"* (registrada em `2026-11-18`).
- **Requisitos Atendidos:**
  - `RF-009`: Caixa Diário (`CashRegisterSession`, `CashTransaction`, `OrderPayment`) com abertura/fechamento, pagamento único ou dividido/misto (`dinheiro`, `pix`, `cartao_credito`, `cartao_debito`), geração automática de `CommissionEntry` **exclusivamente no pagamento da comanda** (respeitando precedência `ProfessionalServiceCommission` vs `Service.default_commission_pct`), extrato de comissões por profissional, baixa de repasse pelo `gestor` e estorno atômico de comanda paga.
  - `RF-013`: Preparação Estrutural e Contrato Desacoplado para Futura Emissão Fiscal (`FiscalDocumentRecord` + `FiscalGatewayAdapter` / `StubFiscalGatewayAdapter`), consolidando snapshots de emitente (`Salon`), tomador (`Client`), base de serviços/rateio Salão-Parceiro (`Lei 13.352/2016`) para futura NFS-e e base de produtos para futura NFC-e.
  - `RNF-001`: Isolamento estrito multi-tenant e permissões por perfil (`GestorRequiredMixin`, `RecepcaoOrGestorMixin`, `ProfissionalScopeMixin`).
  - `RNF-002`: Invariante transacional de fechamento e estorno (`transaction.atomic()` + `select_for_update()`), abortando toda a operação se o saldo de estoque de qualquer produto vendido for insuficiente (`InsufficientStockError`).
- **Decisões Arquiteturais Aplicadas:** `DEC-001` (Testes automatizados + revisão manual), `DEC-002` (Isolamento por `Salon`) e `DEC-003` (Preparação fiscal desacoplada no MVP).

---

## 2. Resumo das Entregas por Tarefa (`S07-T01` a `S07-T06`)

| ID Tarefa | Descrição no PRD (`sprints_de_implementacao_prd.md`) | Arquivos Criados / Atualizados | Situação |
|---|---|---|---|
| `S07-T01` | Criar app `finance` com `CashRegisterSession` (abertura/fechamento de caixa), `CashTransaction` (entradas e despesas), `OrderPayment` (múltiplos meios de pagamento) e `CommissionEntry`. | [`sps/finance/models.py`](../../finance/models.py), [`sps/finance/admin.py`](../../finance/admin.py), [`sps/finance/migrations/0001_initial.py`](../../finance/migrations/0001_initial.py) | Concluída (`[x]`) |
| `S07-T02` | Criar app `fiscal` com `FiscalDocumentRecord` (snapshots de emitente, tomador, payload fiscal de serviços/Salão-Parceiro para NFS-e e payload de produtos para NFC-e) e interface `FiscalGatewayAdapter` (*NoOp/Stub* documentado — `DEC-003`). | [`sps/fiscal/models.py`](../../fiscal/models.py), [`sps/fiscal/services.py`](../../fiscal/services.py), [`sps/fiscal/admin.py`](../../fiscal/admin.py), [`sps/fiscal/migrations/0001_initial.py`](../../fiscal/migrations/0001_initial.py) | Concluída (`[x]`) |
| `S07-T03` | Implementar `OrderCheckoutService.close_and_pay_order()` em transação atômica única: valida caixa aberto, valida e baixa estoque dos produtos vendidos (abortando se saldo for insuficiente), registra pagamentos no caixa, gera `CommissionEntry` para cada serviço pago e cria `FiscalDocumentRecord`. | [`sps/finance/services.py`](../../finance/services.py) | Concluída (`[x]`) |
| `S07-T04` | Implementar fluxo de estorno de comanda paga (exclusivo do `gestor`) revertendo atomicamente caixa, comissões, saldo de estoque e status do registro fiscal, além de tela de extrato e baixa de repasse de comissões aos profissionais. | [`sps/finance/services.py`](../../finance/services.py), [`sps/finance/forms.py`](../../finance/forms.py), [`sps/finance/views.py`](../../finance/views.py), [`sps/finance/urls.py`](../../finance/urls.py), [`sps/templates/finance/cash_register_dashboard.html`](../../templates/finance/cash_register_dashboard.html), [`sps/templates/finance/commission_list.html`](../../templates/finance/commission_list.html), [`sps/templates/orders/order_detail.html`](../../templates/orders/order_detail.html) | Concluída (`[x]`) |
| `S07-T05` | Escrever e executar testes automatizados (`DEC-001`) provando que comissões **não** nascem antes do pagamento, que o pagamento gera comissão com o percentual correto, que falta de estoque aborta o fechamento e que o `FiscalDocumentRecord` é populado. | [`sps/finance/tests.py`](../../finance/tests.py) (4 testes) e [`sps/fiscal/tests.py`](../../fiscal/tests.py) (1 teste), totalizando **46 testes** na suíte do projeto | Concluída (`[x]`) |
| `S07-T06` | Revisar incremento, registrar [`evidencias_da_sprint_007.md`](evidencias_da_sprint_007.md) e entregar para ação de Git/GitHub do usuário. | [`evidencias_da_sprint_007.md`](evidencias_da_sprint_007.md), [`estado_do_projeto.md`](estado_do_projeto.md), [`sprints_de_implementacao_prd.md`](../01_planejamento/sprints_de_implementacao_prd.md), [`parametros_do_projeto.json`](../../parametros_do_projeto.json) | Concluída (`[x]`) |

---

## 3. Detalhamento Técnico da Implementação

### 3.1 Caixa Diário e Invariante de Fechamento Atômico (`S07-T01`, `S07-T03`, `RF-009`)
1. **`CashRegisterSession` e `CashRegisterService` ([`sps/finance/models.py`](../../finance/models.py), [`sps/finance/services.py`](../../finance/services.py)):**
   - Restrição de banco (`UniqueConstraint(fields=['salon'], condition=Q(status='aberto'))`) garantindo no máximo 1 sessão de caixa aberta por salão simultaneamente.
   - `calculate_expected_balance()` consolida `opening_balance` + entradas (`recebimento_comanda`, `entrada_avulsa`) − saídas (`saida_despesa`, `estorno_comanda`).
2. **`OrderCheckoutService.close_and_pay_order()` ([`sps/finance/services.py`](../../finance/services.py)):**
   - Executa dentro de `with transaction.atomic():`:
     1. Bloqueia a `ServiceOrder` com `select_for_update()` e valida que está `aberta` e possui itens.
     2. Bloqueia a `CashRegisterSession` aberta do salão com `select_for_update()`.
     3. Valida que a soma das parcelas de pagamento (`OrderPayment`) é exatamente igual a `order.total_amount`.
     4. Aciona `StockService.register_movement(..., movement_type='saida_venda_comanda')` para cada `OrderProductItem`; se qualquer produto não possuir saldo suficiente, `InsufficientStockError` aborta e faz rollback completo da transação.
     5. Para cada `OrderServiceItem`, resolve o percentual via `resolve_commission_percentage(salon, professional, service)`, calcula o valor com `ROUND_HALF_UP`, grava `applied_commission_pct` no item e cria `CommissionEntry(status='pendente_repasse')`.
     6. Persiste `OrderPayment`, `CashTransaction(recebimento_comanda)`, atualiza `closing_balance_expected`, muda a comanda para `fechada_paga` e aciona `StubFiscalGatewayAdapter.prepare_from_order()`.

### 3.2 Preparação Estrutural Fiscal (`S07-T02`, `RF-013`, `DEC-003`)
- **`FiscalDocumentRecord` e `StubFiscalGatewayAdapter` ([`sps/fiscal/models.py`](../../fiscal/models.py), [`sps/fiscal/services.py`](../../fiscal/services.py)):**
  - Determina automaticamente `document_scope` (`nfse_servico`, `nfce_produto` ou `misto`).
  - Grava `issuer_snapshot` (CNPJ, IM, IE, regime tributário, código IBGE e flag `is_partner_salon_regime`), `customer_snapshot` (CPF/CNPJ e endereço do cliente), `services_fiscal_payload` (com código LC 116, CNAE, ISS e estrutura `partner_salon_split` separando cota-parte do profissional-parceiro e cota-parte retida pelo salão) e `products_fiscal_payload` (com NCM, CEST, CFOP, origem e alíquotas).

### 3.3 Estorno Atômico e Repasse de Comissões (`S07-T04`, `RF-009`)
- **`OrderCheckoutService.reverse_paid_order()`:** Exclusivo para `actor.role == 'gestor'`. Marca `OrderPayment.is_reversed = True`, lança `CashTransaction(estorno_comanda)`, altera `CommissionEntry` para `estornado`, devolve os produtos ao estoque com `StockMovement(estorno_comanda)`, muda a comanda para `cancelada` e marca `FiscalDocumentRecord` como `cancelada`.
- **`CommissionService.pay_commission_entries()` e `CommissionEntryListView`:** `profissional` visualiza apenas suas próprias comissões (`ProfissionalScopeMixin`); `gestor` visualiza todas e realiza a baixa para `pago_ao_profissional`.

---

## 4. Revisão Manual Estruturada do Incremento (`DEC-001`)

| Código | Verificação Realizada | Resultado |
|---|---|---|
| **SEC-A** | `gestor` e `recepcionista` operam caixa e fecham comandas do próprio salão; `gestor` estorna comandas pagas e baixa comissões? | **Aprovado:** Views protegidas por `RecepcaoOrGestorMixin` e `GestorRequiredMixin`. |
| **SEC-B** | Operador do Salão A recebe `404 Not Found` ao tentar fechar ou estornar comanda pertencente ao Salão B? | **Aprovado:** Confirmado em `test_commission_statement_professional_scope_payout_and_cross_tenant_isolation`. |
| **SEC-C** | `profissional` vê apenas o próprio extrato de comissões e recebe `403 Forbidden` ao tentar acessar o caixa ou dar baixa em comissões; `recepcionista` recebe `403`/`PermissionDenied` ao tentar estornar comanda paga? | **Aprovado:** Validado nos testes de serviço e de views HTTP. |
| **CONC-01** | Falta de estoque de um produto durante o fechamento da comanda faz rollback de comissões, pagamentos, caixa e registro fiscal? | **Aprovado:** Confirmado por `test_insufficient_stock_at_checkout_aborts_entire_atomic_transaction`. |

---

## 5. Resultados dos Testes Automatizados Executados (`S07-T05`, `DEC-001`)

### Comando Executado
```powershell
Set-Location "c:\Users\lucas\Desktop\Sistema para barbearia\sps"
$env:USE_SQLITE_FALLBACK="True"
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test base salons accounts scheduling catalog clients inventory orders finance fiscal -v 2
```

### Cobertura Adicionada na `Sprint 07` (`finance/tests.py` e `fiscal/tests.py`)
1. `test_no_commission_before_payment_and_checkout_generates_commission_stock_and_fiscal`: Prova que `0` comissões existem enquanto a comanda está aberta, e que o pagamento misto gera comissões exatas (`50%` específica para Ana, `45%` padrão para Carlos), baixa estoque, atualiza caixa e popula `FiscalDocumentRecord`.
2. `test_insufficient_stock_at_checkout_aborts_entire_atomic_transaction`: Prova que saldo insuficiente no fechamento aborta toda a transação atômica.
3. `test_paid_order_reversal_by_gestor_reverts_cash_commissions_stock_and_fiscal`: Prova que o estorno pelo `gestor` reverte caixa, comissões, estoque e registro fiscal, e bloqueia `recepcionista`.
4. `test_commission_statement_professional_scope_payout_and_cross_tenant_isolation`: Prova o escopo restrito do `profissional` no extrato, a baixa de repasse pelo `gestor`, o fechamento do caixa e o bloqueio `404` cross-tenant.
5. `test_stub_fiscal_adapter_determines_nfse_and_nfce_scopes`: Valida escopos `nfse_servico` e `nfce_produto` no `StubFiscalGatewayAdapter`.

### Correção Realizada Durante a Verificação (`StubFiscalGatewayAdapter` Snapshot Digits)
- **Achado:** Quando um `Salon` era instanciado diretamente via `Salon.objects.create(cnpj='12.345.678/0001-99')` em cenários de teste sem passar por `full_clean()`, o `issuer_snapshot['cnpj']` mantinha pontuação.
- **Correção:** Aplicado `normalize_digits()` em `StubFiscalGatewayAdapter._build_issuer_snapshot()` e `_build_customer_snapshot()` ([`sps/fiscal/services.py`](../../fiscal/services.py)) sobre `cnpj`, `cpf_cnpj`, `phone`, `ibge_city_code` e `zip_code`. Reexecutada a suíte com 100% de aprovação.

### Saída Consolidada dos Testes (`46 testes — OK`)
```text
No changes detected
System check identified no issues (0 silenced).
Found 46 test(s).
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

----------------------------------------------------------------------
Ran 46 tests

OK
```

---

## 6. Verificações Executadas vs. Não Executadas nesta Sessão

| Categoria | Descrição | Status |
|---|---|---|
| **Executada** | Geração e verificação de migrations (`finance/0001_initial.py`, `fiscal/0001_initial.py`, `makemigrations --check`). | `OK` |
| **Executada** | Checagem estrutural do Django (`python manage.py check`). | `OK (0 issues)` |
| **Executada** | Suíte completa de testes automatizados (`46` testes cobrindo `Sprints 01 a 07`). | `OK (46 testes)` |
| **Não Executada (Governança)** | Comandos `git` e `gh` (`git status`, `git add`, `git commit`, `git push`). | Sob controle 100% exclusivo do desenvolvedor |

---

## 7. Status de Entrega e Próxima Ação do Desenvolvedor

- **Situação da Sprint 07:** Concluída, revisada e verificada com **46 testes automatizados aprovados (`OK`)**.
- **Operações Git/GitHub:** Nenhuma operação `git` ou `gh` foi executada pela IA (`git_executado_pela_ia: false`).
- **Sugestão de Commit Manual para o Desenvolvedor:**
  - `feat(sprint-07): add daily cash register, atomic order checkout commissions and fiscal preparation`
- **Próximo Passo Permitido:** Após revisar os arquivos e realizar (ou decidir adiar) o commit/push manual no seu repositório Git, solicite explicitamente o início da **`Sprint 08`** (*Filas Assíncronas Celery, Notificações, Dashboard e Relatórios PDF*).
