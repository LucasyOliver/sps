---
versao: 1.0.0
data_editorial: 2026-11-12
tipo: evidencias_de_sprint
projeto: SPS (Sistema Para Salões)
sprint: Sprint 02
estado: concluida_aguardando_acao_git_do_usuario
---

# Evidências de Execução e Revisão — Sprint 02 — SPS (Sistema Para Salões)

## 1. Identificação da Entrega

- **Sprint:** `Sprint 02 — Configurações do Salão, Expediente, Equipe e Isolamento Multi-tenant`
- **Versão do PRD de referência:** `1.0.0` (aprovada pelo desenvolvedor em `2026-11-12`)
- **Solicitação explícita do desenvolvedor:** *"Execute a sprint 02"*
- **Requisitos avaliados:** `RF-001` (configurações operacionais, expediente semanal, feriados e dados fiscais do salão), `RF-002` (gestão de membros da equipe por salão, expediente individual do profissional e bloqueios de agenda), `RNF-001` (isolamento multi-tenant estrito e permissões por perfil).
- **Decisões aplicadas:** `DEC-001` (testes automatizados de isolamento e permissões + revisão manual), `DEC-002` (vínculo fixo de usuário por salão e negação `403`/`404` em acessos cruzados), `DEC-003` (edição de dados fiscais do emitente e documento de profissional parceiro).
- **Operações de Git/GitHub executadas pela IA:** `Nenhuma` (`git_executado_pela_ia: false`).

---

## 2. Checklist de Tarefas da Sprint 02 e Rastreabilidade

| ID da Tarefa | Requisito / Decisão | Arquivos Principais Criados / Alterados | Situação | Evidência Registrada |
|---|---|---|---|---|
| `S02-T01` | `RF-001`, `DEC-002` | `sps/salons/models.py`, `sps/salons/admin.py`, `sps/salons/migrations/0002_salonbusinesshours_salonholiday.py` | `[x]` | Modelos `SalonBusinessHours` e `SalonHoliday` criados e validados quanto a horários e unicidade por salão. |
| `S02-T02` | `RNF-001`, `DEC-002` | `sps/base/mixins.py` | `[x]` | Mixins `SalonTenantRequiredMixin`, `GestorRequiredMixin`, `RecepcaoOrGestorMixin` e `ProfissionalScopeMixin` implementados. |
| `S02-T03` | `RF-001`, `RF-002`, `DEC-003` | `sps/salons/forms.py`, `sps/salons/views.py`, `sps/salons/urls.py`, `sps/accounts/forms.py`, `sps/accounts/views.py`, `sps/accounts/urls.py`, `sps/templates/salons/`, `sps/templates/accounts/` | `[x]` | CBVs de edição de configurações/dados fiscais do salão, expediente semanal, feriados e gestão de equipe (com CPF/CNPJ parceiro) operacionais. |
| `S02-T04` | `RF-002`, `DEC-002` | `sps/scheduling/models.py`, `sps/scheduling/forms.py`, `sps/scheduling/views.py`, `sps/scheduling/urls.py`, `sps/scheduling/admin.py`, `sps/scheduling/migrations/0001_initial.py`, `sps/templates/scheduling/` | `[x]` | App `scheduling` criado com `ProfessionalSchedule` (validado contra expediente do salão) e `ScheduleBlock` (férias, folgas, ausências com `overlaps()`). |
| `S02-T05` | `DEC-001`, `RNF-001` | `sps/salons/tests.py`, `sps/accounts/tests.py`, `sps/scheduling/tests.py` | `[x]` | `21` testes automatizados executados e aprovados cobrindo `SEC-A`, `SEC-B`, `SEC-C` e `SEC-D`. |
| `S02-T06` | Governança | `sps/docs/02_execucao/evidencias_da_sprint_002.md`, `sps/docs/02_execucao/estado_do_projeto.md` | `[x]` | Revisão concluída, validação acumulada de `Salon.clean()` corrigida e pacote pronto para versionamento do usuário. |

---

## 3. Fichas de Verificação por Tarefa (`S02-T01` a `S02-T05`)

```text
ID da tarefa: S02-T01
Requisito associado: RF-001, DEC-002
Resultado esperado: Expediente do salão por dia da semana (SalonBusinessHours) e feriados/fechamentos (SalonHoliday) isolados por salão.
Arquivos alterados: sps/salons/models.py, sps/salons/migrations/0002_salonbusinesshours_salonholiday.py
Verificação executada: SalonModelAndIsolationTests.test_business_hours_and_holiday_validation
Resultado observado: Horários inválidos (abertura >= fechamento) são rejeitados; dias fechados limpam horários; unicidade por (salon, weekday) e (salon, date) garantida.
Critério atendido: sim

ID da tarefa: S02-T02
Requisito associado: RNF-001, DEC-002
Resultado esperado: Mixins reutilizáveis para impor autenticação, salão ativo, filtro automático por salon no QuerySet e restrição por perfil (gestor, recepcionista, profissional).
Arquivos alterados: sps/base/mixins.py
Verificação executada: Testes de acesso autorizado e negado em salons.tests, accounts.tests e scheduling.tests.
Resultado observado: Tentativas cross-tenant retornam 404 Not Found e perfis sem permissão recebem 403 Forbidden.
Critério atendido: sim

ID da tarefa: S02-T03
Requisito associado: RF-001, RF-002, DEC-003
Resultado esperado: Gestor edita configurações operacionais e fiscais do próprio salão e cadastra/edita membros da equipe vinculados exclusivamente ao seu salão.
Arquivos alterados: sps/salons/forms.py, sps/salons/views.py, sps/accounts/forms.py, sps/accounts/views.py, sps/templates/
Verificação executada: test_gestor_can_update_own_salon_settings_and_fiscal_data, test_gestor_cannot_edit_other_salon_settings_cross_tenant, test_gestor_creates_team_member_bound_to_own_salon_and_isolates_list.
Resultado observado: Atualização persiste apenas no salão do gestor; tentativa de acessar ID de outro salão retorna 404; recepcionista e profissional recebem 403.
Critério atendido: sim

ID da tarefa: S02-T04 e S02-T05
Requisito associado: RF-002, RNF-001, DEC-001
Resultado esperado: Modelos e CBVs de expediente individual (ProfessionalSchedule) e bloqueios de agenda (ScheduleBlock) respeitando expediente do salão e escopo do profissional.
Arquivos alterados: sps/scheduling/models.py, sps/scheduling/forms.py, sps/scheduling/views.py, sps/scheduling/tests.py
Verificação executada: ProfessionalScheduleAndBlockTests (3 conjuntos de testes cobrindo limites de horário, vínculo cruzado e isolamento de bloqueios entre profissionais).
Resultado observado: Expediente do profissional fora do horário do salão ou em dia fechado é rejeitado; profissional de outro salão é rejeitado; profissional só visualiza/exclui os próprios bloqueios.
Critério atendido: sim
```

---

## 4. Avaliação nas Oito Dimensões de Revisão

| Dimensão | Pergunta Central | Avaliação na Sprint 02 |
|---|---|---|
| **Produto** | O comportamento aprovado foi implementado? | Sim: expediente do salão, feriados, configurações operacionais/fiscais, gestão de equipe, expediente individual do profissional e bloqueios de agenda estão completos. |
| **Escopo** | Foi incluída alguma função não solicitada? | Não: catálogo de serviços, clientes e agendamentos de clientes permanecem reservados para as `Sprints 03` e `04`. |
| **Acesso** | Quem pode ler, alterar e exportar dados? | `GestorRequiredMixin` protege configurações fiscais, expediente e equipe (`403` para recepcionista/profissional); `ProfissionalScopeMixin` isola bloqueios por profissional (`404` ao tentar excluir bloqueio de colega). |
| **Integridade** | Falha ou concorrência pode corromper o estado? | Constraints `unique_salon_business_hours_weekday`, `unique_salon_holiday_date` e `unique_professional_weekday_schedule` no banco + validação cross-tenant em `clean()`. |
| **UX** | Usuário entende sucesso, erro, vazio e espera? | Navegação integrada no topo (`base.html`), mensagens de confirmação (`django.contrib.messages`) e erros por campo acumulados em português. |
| **Operação** | Falhas são observáveis e recuperáveis? | Endpoints `/healthz/` e `/readyz/` continuam ativos e cobertos pela suíte. |
| **Configuração** | Há segredos, defaults perigosos ou dependências implícitas? | Nenhuma nova dependência externa adicionada; zero segredos expostos. |
| **Documentação** | Outra sessão consegue retomar corretamente? | Sim: estado, PRD e evidências atualizados. |

---

## 5. Detalhamento da Suíte de Testes Automatizados Executada (`21` Testes)

### 5.1 Comandos Executados
```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations salons scheduling accounts base
$env:USE_SQLITE_FALLBACK="True"; .\.venv\Scripts\python.exe manage.py migrate --plan
$env:USE_SQLITE_FALLBACK="True"; .\.venv\Scripts\python.exe manage.py migrate
$env:USE_SQLITE_FALLBACK="True"; .\.venv\Scripts\python.exe manage.py test base salons accounts scheduling -v 2
```

### 5.2 Matriz de Cenários de Segurança e Domínio Testados na Sprint 02

| Classe / Teste | Cenário Coberto (`DEC-001` / `RNF-001`) | Resultado |
|---|---|---|
| `SalonModelAndIsolationTests.test_business_hours_and_holiday_validation` | Rejeita abertura >= fechamento; valida isolamento `for_salon()` de `SalonBusinessHours` e `SalonHoliday`. | `OK` |
| `SalonModelAndIsolationTests.test_gestor_can_update_own_salon_settings_and_fiscal_data` | `SEC-A`: Gestor atualiza `cancellation_min_hours`, CNPJ, regime tributário e endereço do próprio salão. | `OK` |
| `SalonModelAndIsolationTests.test_gestor_cannot_edit_other_salon_settings_cross_tenant` | `SEC-B`: Gestor do Salão A tenta editar configurações do Salão B (`/salao/<id_b>/editar/`) e recebe `404 Not Found`. | `OK` |
| `SalonModelAndIsolationTests.test_recepcionista_and_profissional_receive_403_on_salon_settings_and_hours_write` | `SEC-C`: Recepcionista e Profissional tentam acessar `/salao/configuracoes/` ou gravar expediente do salão e recebem `403 Forbidden`. | `OK` |
| `SalonModelAndIsolationTests.test_invalid_cnpj_and_ibge_raise_validation_error` | Validação simultânea de CNPJ (14 dígitos) e código IBGE (7 dígitos) no `Salon.clean()`. | `OK` |
| `AccountsAndTenantBindingTests.test_gestor_creates_team_member_bound_to_own_salon_and_isolates_list` | `SEC-A`: Gestor lista apenas membros do próprio salão e cadastra profissional parceira com CPF/CNPJ (`tax_document`). | `OK` |
| `AccountsAndTenantBindingTests.test_gestor_cannot_edit_team_member_from_other_salon` | `SEC-B`: Gestor do Salão A recebe `404 Not Found` ao tentar editar colaborador do Salão B. | `OK` |
| `AccountsAndTenantBindingTests.test_non_gestor_cannot_access_team_management` | `SEC-C`: Recepcionista recebe `403 Forbidden` ao tentar listar ou criar membros da equipe. | `OK` |
| `ProfessionalScheduleAndBlockTests.test_professional_schedule_must_fit_within_salon_business_hours` | `RF-002`: Rejeita expediente do profissional fora do horário de funcionamento do salão ou em dia fechado. | `OK` |
| `ProfessionalScheduleAndBlockTests.test_cross_tenant_professional_assignment_is_rejected` | `SEC-D`: Rejeita vínculo de profissional do Salão B em expediente/agenda do Salão A (`ValidationError`). | `OK` |
| `ProfessionalScheduleAndBlockTests.test_schedule_block_overlaps_and_professional_scope_isolation` | `RF-002`, `SEC-C`: Valida `overlaps()` de bloqueio e garante que `profissional` vê/exclui apenas os próprios bloqueios (`404` no bloqueio de colega). | `OK` |

### 5.3 Rotas e Views Entregues na Sprint 02

| Rota (URL) | Nome da Rota (`url_name`) | View (CBV) | Perfis Autorizados |
|---|---|---|---|
| `/salao/configuracoes/` | `salons:settings` | `SalonSettingsUpdateView` | `gestor`, `superadmin_saas` |
| `/salao/<uuid:pk>/editar/` | `salons:settings_by_pk` | `SalonSettingsUpdateView` | `gestor` (apenas próprio salão) |
| `/salao/expediente/` | `salons:business_hours_list` | `SalonBusinessHoursListView` | `gestor`, `recepcionista`, `profissional` |
| `/salao/expediente/salvar/` | `salons:business_hours_upsert` | `SalonBusinessHoursUpsertView` | `gestor`, `superadmin_saas` |
| `/salao/feriados/` | `salons:holiday_list` | `SalonHolidayListView` | `gestor`, `recepcionista`, `profissional` |
| `/salao/feriados/novo/` | `salons:holiday_create` | `SalonHolidayCreateView` | `gestor`, `superadmin_saas` |
| `/salao/feriados/<uuid:pk>/excluir/` | `salons:holiday_delete` | `SalonHolidayDeleteView` | `gestor` (apenas próprio salão) |
| `/contas/equipe/` | `accounts:team_list` | `TeamMemberListView` | `gestor`, `superadmin_saas` |
| `/contas/equipe/novo/` | `accounts:team_create` | `TeamMemberCreateView` | `gestor`, `superadmin_saas` |
| `/contas/equipe/<uuid:pk>/editar/` | `accounts:team_edit` | `TeamMemberUpdateView` | `gestor` (apenas próprio salão) |
| `/agenda/expedientes/` | `scheduling:schedule_list` | `ProfessionalScheduleListView` | `gestor`, `recepcionista`, `profissional` (escopado) |
| `/agenda/expedientes/novo/` | `scheduling:schedule_create` | `ProfessionalScheduleCreateView` | `gestor`, `superadmin_saas` |
| `/agenda/expedientes/<uuid:pk>/editar/` | `scheduling:schedule_edit` | `ProfessionalScheduleUpdateView` | `gestor` (apenas próprio salão) |
| `/agenda/bloqueios/` | `scheduling:block_list` | `ScheduleBlockListView` | `gestor`, `recepcionista`, `profissional` (escopado) |
| `/agenda/bloqueios/novo/` | `scheduling:block_create` | `ScheduleBlockCreateView` | `gestor`, `recepcionista`, `profissional` (próprio) |
| `/agenda/bloqueios/<uuid:pk>/excluir/` | `scheduling:block_delete` | `ScheduleBlockDeleteView` | `gestor`, `recepcionista`, `profissional` (próprio) |

---

## 6. Achados de Revisão e Correções Realizadas (`S02-T06`)

- **Achado durante a execução da suíte de testes:**
  - No método `Salon.clean()` (`sps/salons/models.py`), a validação de `cnpj` lançava `ValidationError` imediatamente antes de validar `ibge_city_code`. Quando ambos os campos eram enviados com valores inválidos no mesmo formulário, apenas o erro de `cnpj` era reportado na primeira tentativa.
- **Correção aplicada e re-verificada:**
  - Refatorado `Salon.clean()` para acumular todas as falhas no dicionário `errors` e lançar `ValidationError(errors)` ao final, reportando simultaneamente erros de `cnpj` e `ibge_city_code`.
  - A suíte completa com **21 testes automatizados** (`base`, `salons`, `accounts`, `scheduling`) foi reexecutada e aprovada integralmente.

---

## 7. Proposta de Mensagem de Commit e Comandos Manuais (Exclusivos do Usuário)

> **Lembrete de Governança:** Caso ainda não tenha realizado o commit da `Sprint 01`, você pode versionar ambos os incrementos ou realizar o commit consolidado abaixo.

```bash
# EXECUCAO EXCLUSIVA DO DESENVOLVEDOR (NAO EXECUTADO PELA IA)
git status
git add sps/
git commit -m "feat(sprint-02): salon business hours, holidays, team management, professional schedules and tenant isolation mixins"
git push
```

---

## 8. Limites da Verificação e Próximo Passo

- **Limites da verificação:** Todos os 21 testes automatizados foram executados no ambiente local (`Python 3.13.6` + `Django 5.2.19`) com dados sintéticos. O PostgreSQL de desenvolvimento está parametrizado em `docker-compose.yml` e `.env.example`.
- **Próxima ação esperada do desenvolvedor:** Revisar os arquivos da `Sprint 02`, executar manualmente seu commit/push (ou decidir adiar) e solicitar explicitamente a execução da **`Sprint 03`** (*Catálogo de Serviços, Regras de Comissão e Cadastro de Clientes*).
