---
versao: 1.0.0
data_editorial: 2026-11-13
tipo: evidencias_de_sprint
projeto: SPS (Sistema Para Salões)
id_sprint: Sprint 05
estado: concluida_e_verificada
---

# Evidências de Execução e Revisão — Sprint 05 — SPS (Sistema Para Salões)

## 1. Identificação e Escopo da Sprint 05

- **Sprint Executada:** `Sprint 05 — Design System, Autoagendamento Público (/s/<slug>/) e Cancelamento`
- **Solicitação Explícita do Desenvolvedor:** *"Pode iniciar a sprint 05, adicionei o design system em sps/design_system/refs"* (registrada em `2026-11-13`).
- **Requisitos Atendidos:**
  - `RF-006`: Autoagendamento e cancelamento público pelo cliente (`/s/<slug_salao>/` e `/s/<slug_salao>/agendamento/<public_token>/`) com seleção de múltiplos serviços, cálculo de horários livres reais (`AvailabilityService`) e validação de antecedência mínima de cancelamento (`cancellation_min_hours`).
  - `RNF-001`: Isolamento estrito multi-tenant nas rotas públicas (bloqueio de acesso a tokens de outro salão ou de salões inativos com `404 Not Found`).
  - `RNF-002`: Prevenção transacional de *double-booking* entre o portal público e a agenda interna.
  - `RNF-003`: Extração de tokens e componentes da pasta `sps/design_system/refs/` para o catálogo visual e aplicação nos layouts Desktop e Mobile em `pt-BR`.
- **Decisões Arquiteturais Aplicadas:** `DEC-001` (Testes automatizados obrigatórios + revisão manual) e `DEC-002` (Isolamento multi-tenant por `Salon`).

---

## 2. Resumo das Entregas por Tarefa (`S05-T01` a `S05-T05`)

| ID Tarefa | Descrição no PRD (`sprints_de_implementacao_prd.md`) | Arquivos Criados / Atualizados | Situação |
|---|---|---|---|
| `S05-T01` | Inventariar `sps/design_system/refs/`, documentar [`catalogo_design_system.md`](../01_planejamento/catalogo_design_system.md) e aplicar tokens/componentes nos layouts base Desktop e Mobile. | [`catalogo_design_system.md`](../01_planejamento/catalogo_design_system.md), [`sps/static/css/sps-design-system.css`](../../static/css/sps-design-system.css), [`sps/core/settings.py`](../../core/settings.py), [`sps/templates/base.html`](../../templates/base.html), [`sps/templates/public_base.html`](../../templates/public_base.html), [`sps/templates/base/home.html`](../../templates/base/home.html) | Concluída (`[x]`) |
| `S05-T02` | Implementar páginas públicas `/s/<slug_salao>/` onde o cliente seleciona múltiplos serviços, escolhe profissional e horário livre real (via `AvailabilityService`) e confirma o agendamento recebendo `public_token`. | [`sps/scheduling/services.py`](../../scheduling/services.py), [`sps/scheduling/forms.py`](../../scheduling/forms.py), [`sps/scheduling/views.py`](../../scheduling/views.py), [`sps/scheduling/public_urls.py`](../../scheduling/public_urls.py), [`sps/core/urls.py`](../../core/urls.py), [`sps/templates/scheduling/public_booking.html`](../../templates/scheduling/public_booking.html) | Concluída (`[x]`) |
| `S05-T03` | Implementar rota pública de consulta e cancelamento `/s/<slug_salao>/agendamento/<public_token>/` que valida `timezone.now() <= appointment.start_at - timedelta(hours=salon.cancellation_min_hours)`. | [`sps/scheduling/services.py`](../../scheduling/services.py), [`sps/scheduling/views.py`](../../scheduling/views.py), [`sps/templates/scheduling/public_appointment_detail.html`](../../templates/scheduling/public_appointment_detail.html), [`sps/templates/scheduling/appointment_list.html`](../../templates/scheduling/appointment_list.html), [`sps/templates/scheduling/appointment_detail.html`](../../templates/scheduling/appointment_detail.html) | Concluída (`[x]`) |
| `S05-T04` | Escrever e executar testes automatizados (`DEC-001`) de agendamento público com múltiplos serviços, bloqueio de conflito com agenda interna e negação de cancelamento fora da antecedência mínima configurada pelo salão. | [`sps/scheduling/tests.py`](../../scheduling/tests.py) (4 novos testes em `ProfessionalScheduleAndBlockTests`, totalizando **34 testes** na suíte do projeto) | Concluída (`[x]`) |
| `S05-T05` | Revisar incremento em larguras Desktop e Mobile, registrar [`evidencias_da_sprint_005.md`](evidencias_da_sprint_005.md) e entregar para ação de Git/GitHub do usuário. | [`evidencias_da_sprint_005.md`](evidencias_da_sprint_005.md), [`estado_do_projeto.md`](estado_do_projeto.md), [`sprints_de_implementacao_prd.md`](../01_planejamento/sprints_de_implementacao_prd.md), [`parametros_do_projeto.json`](../../parametros_do_projeto.json) | Concluída (`[x]`) |

---

## 3. Detalhamento Técnico da Implementação

### 3.1 Extração Segura do Design System (`S05-T01`)
1. **Inventário e Segurança de Assets (`sps/design_system/refs/`):**
   - Foram inspecionados `design-system.html`, `index.html`, `css2`, `main-BsXTeVfQ.css`, `main-DLZ6GWhB.js`, `iconify-icon.min.js` e `logo-aura-gray.svg`.
   - Os scripts e chamadas externas de prototipação (`46mjiy.aura.build`, `hoirqrkdgbmvpwutwuwj.supabase.co`, `cdn.tailwindcss.com` e URLs do Unsplash) foram **descartados por segurança**, preservando o produto livre de rastreadores ou dependências remotas de terceiros.
2. **Tokens e Componentes Consolidados em [`sps/static/css/sps-design-system.css`](../../static/css/sps-design-system.css):**
   - **Paleta:** Fundo geral `#f9fafb` (`gray-50`), superfície `#ffffff` (`white`), borda estrutural `#e5e7eb` (`gray-200`), destaque primário `#7c3aed` (`violet-600`) com hover `#6d28d9` (`violet-700`), item ativo `#f5f3ff` (`violet-50`) e pílulas semânticas (`#dcfce7`/`#166534` para confirmado/concluído, `#fef9c3`/`#854d0e` para agendado, `#ede9fe`/`#5b21b6` para em atendimento e `#fee2e2`/`#991b1b` para cancelado/falta).
   - **Shell Interno ([`sps/templates/base.html`](../../templates/base.html)):** Barra lateral esquerda `w-64` (`256px`) com emblema violeta `S`, navegação por seções com ícones SVG inline (`24x24`), rodapé de perfil do usuário autenticado, cabeçalho superior com link direto para o portal público do salão (`/s/<slug>/`) e barra horizontal responsiva (`sps-mobile-nav`) para telas `< 768px`.
   - **Shell Público ([`sps/templates/public_base.html`](../../templates/public_base.html)):** Layout mobile-first centralizado (`max-width: 56rem`) exibindo a identidade do salão (`trade_name`), telefone de contato e selo da regra de cancelamento (`cancellation_min_hours`).

### 3.2 Autoagendamento Público com Múltiplos Serviços (`S05-T02`, `RF-006`)
- **`SchedulingService.upsert_public_client()` e `create_public_appointment()` ([`sps/scheduling/services.py`](../../scheduling/services.py)):**
  - Normaliza o telefone (`10` ou `11` dígitos) e o CPF/CNPJ opcional (`11` ou `14` dígitos) informados pelo cliente final.
  - Localiza ou cria o registro `Client` estritamente no escopo de `salon` (`Client.objects.for_salon(salon)`), evitando erro de duplicidade quando um cliente recorrente agenda novamente pelo portal público.
  - Aciona `SchedulingService.create_appointment()` dentro de `transaction.atomic()` com `select_for_update()` no profissional, somando durações e valores de todos os serviços selecionados e barrando qualquer colisão com a agenda interna.
- **`PublicSalonBookingView` ([`sps/scheduling/views.py`](../../scheduling/views.py)):**
  - Publicada em `/s/<slug:salon_slug>/`. Retorna `404` se o salão não existir ou estiver inativo (`is_active=False`).
  - Permite simular em tempo real os horários disponíveis (`AvailabilityService.get_available_slots()`) para o profissional, data e múltiplos serviços selecionados, preenchendo o horário clicado e redirecionando após confirmação para `/s/<slug_salao>/agendamento/<public_token>/`.

### 3.3 Consulta e Cancelamento Público Condicionado ao Prazo (`S05-T03`, `RF-006`)
- **`SchedulingService.can_cancel_publicly()` e `cancel_public_appointment()` ([`sps/scheduling/services.py`](../../scheduling/services.py)):**
  - Calcula o limite máximo de cancelamento online: `cutoff = appointment.start_at - timedelta(hours=salon.cancellation_min_hours)`.
  - Permite o cancelamento exclusivamente quando o agendamento pertence ao salão, está em status ativo (`agendado`, `confirmado` ou `em_atendimento`) e `current_time <= cutoff`.
  - Caso `current_time > cutoff`, lança `ValidationError` mantendo o agendamento ativo e orientando o cliente a contatar a recepção do salão.

---

## 4. Revisão Manual Estruturada do Incremento (Segurança, Concorrência e UI)

| Código | Verificação Realizada | Resultado |
|---|---|---|
| **SEC-A** | As rotas públicas `/s/<slug>/` e `/s/<slug>/agendamento/<token>/` dispensam login para o cliente final, enquanto todas as rotas internas (`/agenda/`, `/catalogo/`, `/clientes/`, `/salao/`) continuam exigindo autenticação? | **Aprovado:** Escopos público e interno separados em `scheduling/public_urls.py` e `scheduling/urls.py`. |
| **SEC-B** | Um token público `public_token` do Salão A pode ser consultado ou cancelado através da URL do Salão B (`/s/salao-beta/agendamento/<token_a>/`)? | **Aprovado:** `PublicAppointmentDetailCancelView` filtra por `Appointment.objects.for_salon(self.salon)`, retornando `404 Not Found`. |
| **SEC-C** | O cadastro de cliente no portal público do Salão A vaza ou sobrescreve clientes do Salão B? | **Aprovado:** `upsert_public_client()` opera exclusivamente sobre `Client.objects.for_salon(salon)`. |
| **SEC-D** | Um cliente consegue agendar pelo portal público um serviço ou profissional pertencente a outro salão manipulando o POST? | **Aprovado:** `PublicBookingForm` restringe os querysets a `self.salon` e `SchedulingService._validate_entities_and_compute_totals()` revalida `salon_id`. |
| **CONC-01** | O agendamento público utiliza o mesmo bloqueio pessimista (`select_for_update()`) da agenda interna? | **Aprovado:** `create_public_appointment()` delega a criação para `SchedulingService.create_appointment()` dentro de `transaction.atomic()`. |
| **UI-01** | Os templates internos e públicos renderizam sem scripts externos do Aura/Supabase e funcionam em larguras Desktop e Mobile? | **Aprovado:** Folha local `sps-design-system.css` servida via ` {% static 'css/sps-design-system.css' %}` com sidebar responsiva e cards fluidos. |

---

## 5. Resultados dos Testes Automatizados Executados (`DEC-001`)

### Comando Executado
```powershell
Set-Location "c:\Users\lucas\Desktop\Sistema para barbearia\sps"
$env:USE_SQLITE_FALLBACK="True"
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test base salons accounts scheduling catalog clients -v 2
```

### Cobertura Adicionada na `Sprint 05` (`scheduling/tests.py`)
1. `test_public_booking_creates_client_multi_service_appointment_and_reuses_client`: Verifica renderização do Design System e cálculo de slots para 2 serviços (`30m + 45m = 75m`) no GET `/s/salao-alpha/`, criação do `Client` e `Appointment` (`R$ 120,00`) no POST, redirecionamento para `/s/salao-alpha/agendamento/<public_token>/` e reutilização do `Client` em novo agendamento com o mesmo telefone.
2. `test_public_booking_blocks_conflict_with_internal_agenda`: Verifica que um horário ocupado na agenda interna (`14:00` às `15:15`) bloqueia tentativa de agendamento público concorrente às `14:30` com mensagem de conflito.
3. `test_public_cancellation_deadline_enforcement`: Valida o critério de aceite exato de `RF-006` (salão com `cancellation_min_hours = 3` e agendamento às `16:00`: tentativa às `14:00` é negada e tentativa às `12:30` é aprovada, além de teste ponta a ponta via POST HTTP).
4. `test_public_routes_enforce_tenant_isolation_and_active_salon`: Confirma `404 Not Found` ao tentar acessar token de outro salão ou página de salão inativo.

### Saída Real da Execução (`34 testes — OK`)
```text
System check identified no issues (0 silenced).
Found 34 test(s).
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

----------------------------------------------------------------------
Ran 34 tests in 68.975s

OK
```

---

## 6. Verificações Executadas vs. Não Executadas nesta Sessão

| Categoria | Descrição | Status |
|---|---|---|
| **Executada** | Auditoria de segurança e extração de tokens de `sps/design_system/refs/` para [`catalogo_design_system.md`](../01_planejamento/catalogo_design_system.md) e [`sps-design-system.css`](../../static/css/sps-design-system.css). | `OK` |
| **Executada** | Checagem estrutural do Django (`python manage.py check`). | `OK (0 issues)` |
| **Executada** | Suíte completa de testes automatizados (`base`, `salons`, `accounts`, `scheduling`, `catalog`, `clients`). | `OK (34 testes)` |
| **Não Executada (Governança)** | Comandos `git` e `gh` (`git status`, `git add`, `git commit`, `git push`). | Sob controle 100% exclusivo do desenvolvedor |

---

## 7. Status de Entrega e Próxima Ação do Desenvolvedor

- **Situação da Sprint 05:** Concluída, revisada e verificada com **34 testes automatizados aprovados (`OK`)**.
- **Operações Git/GitHub:** Nenhuma operação `git` ou `gh` foi executada pela IA (`git_executado_pela_ia: false`).
- **Sugestão de Commit Manual para o Desenvolvedor:**
  - `feat(sprint-05): apply design system and add public self-scheduling and cancellation (/s/<slug>/)`
- **Próximo Passo Permitido:** Após revisar os arquivos e realizar (ou decidir adiar) o commit/push manual no seu repositório Git, solicite explicitamente o início da **`Sprint 06`** (*Controle de Estoque de Produtos e Comandas de Atendimento*).
