---
versao: 1.0.0
data_editorial: 2026-11-13
tipo: evidencias_de_sprint
projeto: SPS (Sistema Para Salões)
id_sprint: Sprint 06
estado: concluida_e_verificada
---

# Evidências de Execução e Revisão — Sprint 06 — SPS (Sistema Para Salões)

## 1. Identificação e Escopo da Sprint 06

- **Sprint Executada:** `Sprint 06 — Controle de Estoque de Produtos e Comandas de Atendimento`
- **Solicitação Explícita do Desenvolvedor:** *"Pode prosseguir com a sprint 06"* e retomada *"Retome a implementação da Sprint 06 de onde parou"* (registradas em `2026-11-13`).
- **Requisitos Atendidos:**
  - `RF-007`: Comandas de Atendimento (`ServiceOrder`, `OrderServiceItem`, `OrderProductItem`), com abertura avulsa ou a partir de `Appointment`, inclusão de múltiplos serviços executados por diferentes profissionais, venda de produtos do estoque, descontos por item, desconto/acréscimo geral e imutabilidade quando fechada/cancelada.
  - `RF-008`: Controle de Estoque de Produtos (`Product`, `StockMovement`), com tipos `venda`/`consumo_interno`/`ambos`, livro razão auditável imutável, bloqueio estrito de saldo negativo (`InsufficientStockError`), alerta de estoque mínimo (`current_stock <= min_stock_alert`) e metadados fiscais preparatórios (NCM, CEST, CFOP, origem, ICMS e PIS/COFINS — `DEC-003`).
  - `RNF-001`: Isolamento estrito multi-tenant e autorização por perfil (`GestorRequiredMixin`, `RecepcaoOrGestorMixin`) em todas as views e formulários de estoque e comandas.
  - `RNF-002`: Atualização transacional (`transaction.atomic()` + `select_for_update()` + `F('current_stock')`) no controle de estoque e operação de comandas.
- **Decisões Arquiteturais Aplicadas:** `DEC-001` (Testes automatizados + revisão manual), `DEC-002` (Isolamento por `Salon`) e `DEC-003` (Preparação fiscal de produtos para futura NFC-e/NF-e).

---

## 2. Resumo das Entregas por Tarefa (`S06-T01` a `S06-T06`)

| ID Tarefa | Descrição no PRD (`sprints_de_implementacao_prd.md`) | Arquivos Criados / Atualizados | Situação |
|---|---|---|---|
| `S06-T01` | Criar app `inventory` com `Product` (tipo `venda`/`consumo_interno`/`ambos`, custo, preço de venda, `current_stock`, `min_stock_alert` e metadados fiscais NCM, CEST, CFOP, origem e alíquotas) e `StockMovement`. | [`sps/inventory/models.py`](../../inventory/models.py), [`sps/inventory/admin.py`](../../inventory/admin.py), [`sps/inventory/migrations/0001_initial.py`](../../inventory/migrations/0001_initial.py), [`sps/inventory/migrations/0002_initial.py`](../../inventory/migrations/0002_initial.py) | Concluída (`[x]`) |
| `S06-T02` | Implementar serviço de movimentação manual de estoque (entradas de compra, baixas por consumo interno e ajustes auditados) com bloqueio de saldo negativo e listagem de alertas (`current_stock <= min_stock_alert`). | [`sps/inventory/services.py`](../../inventory/services.py), [`sps/inventory/forms.py`](../../inventory/forms.py) | Concluída (`[x]`) |
| `S06-T03` | Criar app `orders` com `ServiceOrder`, `OrderServiceItem` (vinculando serviço e profissional executante) e `OrderProductItem` (vinculando produto do estoque e quantidade), permitindo abrir comanda a partir de um `Appointment` ou avulsa. | [`sps/orders/models.py`](../../orders/models.py), [`sps/orders/services.py`](../../orders/services.py), [`sps/orders/admin.py`](../../orders/admin.py), [`sps/orders/migrations/0001_initial.py`](../../orders/migrations/0001_initial.py) | Concluída (`[x]`) |
| `S06-T04` | Implementar CBVs de gestão de Estoque e operação de Comandas abertas (adição/remoção de itens, descontos e cálculo de totais). | [`sps/inventory/views.py`](../../inventory/views.py), [`sps/inventory/urls.py`](../../inventory/urls.py), [`sps/orders/views.py`](../../orders/views.py), [`sps/orders/forms.py`](../../orders/forms.py), [`sps/orders/urls.py`](../../orders/urls.py), [`sps/templates/inventory/`](../../templates/inventory/product_list.html), [`sps/templates/orders/`](../../templates/orders/order_detail.html), [`sps/templates/base.html`](../../templates/base.html), [`sps/templates/scheduling/appointment_detail.html`](../../templates/scheduling/appointment_detail.html), [`sps/templates/clients/client_detail.html`](../../templates/clients/client_detail.html) | Concluída (`[x]`) |
| `S06-T05` | Escrever e executar testes automatizados (`DEC-001`) de movimentação de estoque, alerta de estoque mínimo e cálculo de comanda mista (serviços + produtos). | [`sps/inventory/tests.py`](../../inventory/tests.py) (3 testes) e [`sps/orders/tests.py`](../../orders/tests.py) (4 testes), totalizando **41 testes** na suíte do projeto | Concluída (`[x]`) |
| `S06-T06` | Revisar incremento, registrar [`evidencias_da_sprint_006.md`](evidencias_da_sprint_006.md) e entregar para ação de Git/GitHub do usuário. | [`evidencias_da_sprint_006.md`](evidencias_da_sprint_006.md), [`estado_do_projeto.md`](estado_do_projeto.md), [`sprints_de_implementacao_prd.md`](../01_planejamento/sprints_de_implementacao_prd.md) | Concluída (`[x]`) |

---

## 3. Detalhamento Técnico da Implementação

### 3.1 Controle de Estoque, Livro Razão Imutável e Metadados Fiscais (`S06-T01`, `S06-T02`, `RF-008`, `DEC-003`)
1. **Modelo `Product` ([`sps/inventory/models.py`](../../inventory/models.py)):**
   - Escopado por `Salon` (`TenantScopedModel`), com constraints de unicidade `(salon, name)` e `(salon, sku)` (quando `sku` não é vazio).
   - `current_stock` definido como `editable=False`, impedindo edição direta por formulário: toda alteração de saldo ocorre exclusivamente via `StockService.register_movement()`.
   - Propriedades `is_below_min_stock` (`current_stock <= min_stock_alert`) e `is_sellable` (`usage_type in ('venda', 'ambos')`).
   - Metadados fiscais preparatórios para futura emissão de NFC-e/NF-e: `ncm_code` (normalizado para 8 dígitos), `cest_code` (7 dígitos), `cfop_default` (4 dígitos), `tax_origin` (`0`, `1`, `2`), `icms_rate_pct` e `pis_cofins_regime`.
2. **Modelo `StockMovement` e `StockService` ([`sps/inventory/services.py`](../../inventory/services.py)):**
   - Movimentações tipadas (`entrada_compra`, `saida_venda_comanda`, `saida_consumo_interno`, `ajuste_inventario`, `estorno_comanda`) com bloqueio de mutação/exclusão em `save()`/`delete()`.
   - `StockService.register_movement()` abre `transaction.atomic()`, bloqueia o registro `Product` com `select_for_update()`, valida se o saldo resultante seria `< 0` (lançando `InsufficientStockError`), atualiza com `F('current_stock') + delta` e grava o `StockMovement` com `balance_after`.

### 3.2 Comandas de Atendimento e Cálculo Financeiro (`S06-T03`, `S06-T04`, `RF-007`)
1. **Modelos `ServiceOrder`, `OrderServiceItem` e `OrderProductItem` ([`sps/orders/models.py`](../../orders/models.py)):**
   - `ServiceOrder` suporta vínculo opcional com `Appointment` (protegido por `UniqueConstraint` parcial `unique_active_order_per_appointment` enquanto `status != 'cancelada'`) e com `Client`.
   - `OrderServiceItem` registra `service`, `professional` executante, `gross_price`, `discount_amount`, `net_price` e reserva `applied_commission_pct` (`null=True`) para preenchimento exclusivo no fechamento/pagamento da comanda no caixa (`Sprint 07` — `RF-009`).
   - `OrderProductItem` registra `product`, `quantity` (`> 0`), `unit_price` e `total_price`.
2. **Serviço `OrderService` ([`sps/orders/services.py`](../../orders/services.py)):**
   - `open_order()` e `open_order_from_appointment()`: cria comanda avulsa ou importa automaticamente cliente, profissional e itens de um `Appointment` nos estados `em_atendimento` ou `concluido`.
   - `add_service_item()`, `remove_service_item()`, `add_product_item()`, `remove_product_item()`, `apply_adjustments()` e `cancel_order()`: operam sob `select_for_update()` na comanda, garantindo que apenas comandas `aberta` sofram mutação e recalculando `subtotal_services`, `subtotal_products` e `total_amount` com arredondamento `ROUND_HALF_UP`.

---

## 4. Revisão Manual Estruturada do Incremento (`DEC-001`)

| Código | Verificação Realizada | Resultado |
|---|---|---|
| **SEC-A** | `gestor` e `recepcionista` operam comandas e consultam estoque do próprio salão; `gestor` cadastra produtos e registra movimentações manuais? | **Aprovado:** Views protegidas por `RecepcaoOrGestorMixin` e `GestorRequiredMixin`. |
| **SEC-B** | Operador do Salão A recebe `404 Not Found` ao tentar visualizar, editar ou cancelar produto ou comanda pertencente ao Salão B? | **Aprovado:** `get_queryset()` e `BaseOrderActionView.get_order()` filtram estritamente por `for_salon(request.salon)`. |
| **SEC-C** | `recepcionista` é bloqueada (`403 Forbidden`) ao tentar criar/editar produto ou registrar ajuste manual de estoque, e `profissional` é bloqueado (`403`) em `/estoque/` e `/comandas/`? | **Aprovado:** Confirmado por `test_inventory_views_permissions_and_cross_tenant_isolation` e `test_order_views_permissions_and_cross_tenant_isolation`. |
| **SEC-D** | Formulários de movimentação de estoque e de itens da comanda rejeitam `product`, `service` ou `professional` de outro salão? | **Aprovado:** Querysets escopados por `salon` + dupla checagem em `StockService` e `OrderService`. |
| **CONC-01** | As referências cruzadas de migrations entre `inventory` (`StockMovement.order`) e `orders` (`OrderProductItem.product`) aplicam sem ciclo de dependência? | **Aprovado:** Separadas em `inventory/0001_initial.py`, `orders/0001_initial.py` e `inventory/0002_initial.py` (`makemigrations --check` sem pendências). |

---

## 5. Resultados dos Testes Automatizados Executados (`S06-T05`, `DEC-001`)

### Comando Executado
```powershell
Set-Location "c:\Users\lucas\Desktop\Sistema para barbearia\sps"
$env:USE_SQLITE_FALLBACK="True"
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test base salons accounts scheduling catalog clients inventory orders -v 2
```

### Cobertura Adicionada na `Sprint 06` (`inventory/tests.py` e `orders/tests.py`)
1. `test_product_fiscal_metadata_validation_and_uniqueness_per_salon`: Valida NCM (`8` dígitos), CEST (`7` dígitos), CFOP (`4` dígitos) e unicidade por salão.
2. `test_stock_movements_negative_balance_block_low_stock_alert_and_immutability`: Valida entrada de compra, baixa por consumo interno, ativação do alerta de estoque mínimo (`current_stock <= min_stock_alert`), bloqueio de saldo negativo (`InsufficientStockError`), exigência de motivo em ajustes e imutabilidade de `StockMovement`.
3. `test_inventory_views_permissions_and_cross_tenant_isolation`: Verifica criação de produto com saldo inicial pelo `gestor`, `404` cross-tenant e `403` para perfis não autorizados.
4. `test_mixed_order_calculation_multiple_professionals_products_and_discounts`: Valida comanda mista com 2 profissionais + produto de venda + descontos/acréscimos e ausência de comissão antes do pagamento (`RF-007`, `RF-009`).
5. `test_open_order_from_appointment_and_prevent_duplicate_active_order`: Valida abertura de comanda a partir de agendamento `em_atendimento` e bloqueio de duplicidade ativa.
6. `test_order_rejects_internal_only_product_excess_stock_and_disabled_professional`: Valida bloqueio de venda de insumo de uso interno, quantidade acima do estoque e profissional não habilitado.
7. `test_order_views_permissions_and_cross_tenant_isolation`: Valida fluxo HTTP completo de comandas e bloqueios `SEC-A` a `SEC-D`.

### Correção Realizada Durante a Verificação (`Product.clean_fields`)
- **Achado:** Ao testar `cfop_default='5.102'` (5 caracteres com ponto) em `Product.full_clean()`, a validação `clean_fields()` do Django executava `MaxLengthValidator(4)` antes de `Product.clean()` remover a pontuação.
- **Correção:** Adicionado `Product.clean_fields(self, exclude=None)` em [`sps/inventory/models.py`](../../inventory/models.py) para remover `.` e `-` de `ncm_code`, `cest_code` e `cfop_default` antes de `super().clean_fields()`. Reexecutada a suíte com 100% de aprovação.

### Saída Consolidada dos Testes (`41 testes — OK`)
```text
No changes detected
System check identified no issues (0 silenced).
Found 41 test(s).
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

----------------------------------------------------------------------
Ran 41 tests

OK
```

---

## 6. Verificações Executadas vs. Não Executadas nesta Sessão

| Categoria | Descrição | Status |
|---|---|---|
| **Executada** | Conferência de migrations (`python manage.py makemigrations --check --dry-run`) sem pendências ou ciclos entre `inventory` e `orders`. | `OK` |
| **Executada** | Checagem estrutural do Django (`python manage.py check`). | `OK (0 issues)` |
| **Executada** | Suíte automatizada de `inventory` e `orders` + regressão completa (`41` testes). | `OK (41 testes)` |
| **Não Executada (Governança)** | Comandos `git` e `gh` (`git status`, `git diff`, `git add`, `git commit`, `git push`). | Sob controle 100% exclusivo do desenvolvedor |

---

## 7. Status de Entrega e Próxima Ação do Desenvolvedor

- **Situação da Sprint 06:** Concluída, revisada e verificada com **41 testes automatizados aprovados (`OK`)**.
- **Operações Git/GitHub:** Nenhuma operação `git` ou `gh` foi executada pela IA (`git_executado_pela_ia: false`).
- **Sugestão de Commit Manual para o Desenvolvedor:**
  - `feat(sprint-06): add inventory ledger with low-stock alerts and service orders`
- **Próximo Passo Permitido:** Após revisar os arquivos e realizar (ou decidir adiar) o commit/push manual no seu repositório Git, solicite explicitamente o início da **`Sprint 07`** (*Caixa Diário, Comissões no Pagamento e Preparação Fiscal — `RF-013`*).
