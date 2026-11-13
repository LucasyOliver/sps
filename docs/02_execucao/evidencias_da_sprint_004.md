---
versao: 1.0.0
data_editorial: 2026-11-13
tipo: evidencias_de_sprint
projeto: SPS (Sistema Para Salões)
sprint: Sprint 04
estado: concluida_aguardando_acao_git_do_usuario
---

# Evidências de Execução e Revisão — Sprint 04 — SPS (Sistema Para Salões)

## 1. Identificação da Entrega

- **Sprint:** `Sprint 04 — Motor de Disponibilidade e Agenda Inteligente Interna (Múltiplos Serviços)`
- **Versão do PRD de referência:** `1.0.0` (aprovada pelo desenvolvedor em `2026-11-12`)
- **Solicitação explícita do desenvolvedor:** *"Pode iniciar a sprint 04"*
- **Requisitos avaliados:**
  - `RF-005`: Agenda Inteligente Interna com Múltiplos Serviços e Prevenção de Conflitos (`Appointment`, `AppointmentItem`, soma automática de durações e valores, `AvailabilityService`, `SchedulingService` transacional com `select_for_update` e máquina de estados).
  - `RNF-001`: Isolamento Multi-tenant estrito e escopo do profissional na agenda (`ProfissionalScopeMixin`).
  - `RNF-002`: Prevenção de colisão concorrente (*double-booking*) via bloqueio de linha (`select_for_update()`).
- **Decisões aplicadas:** `DEC-001` (testes automatizados de soma de múltiplos serviços, prevenção de conflitos, bloqueios/feriados e isolamento entre salões), `DEC-002` (isolamento estrito por `Salon`).
- **Operações de Git/GitHub executadas pela IA:** `Nenhuma` (`git_executado_pela_ia: false`).

---

## 2. Checklist de Tarefas da Sprint 04 e Rastreabilidade

| ID da Tarefa | Requisito / Decisão | Arquivos Principais Criados / Alterados | Situação | Evidência Registrada |
|---|---|---|---|---|
| `S04-T01` | `RF-005`, `DEC-002` | `sps/scheduling/models.py`, `sps/scheduling/admin.py`, `sps/scheduling/migrations/0002_appointment_appointmentitem_and_more.py` | `[x]` | Modelos `Appointment` e `AppointmentItem` criados com `public_token`, snapshots de duração/preço e índice composto `idx_appt_salon_prof_interval`. |
| `S04-T02` | `RF-005` | `sps/scheduling/services.py` | `[x]` | `AvailabilityService` implementado considerando `SalonHoliday`, `SalonBusinessHours`, `ProfessionalSchedule` (e intervalo), `ScheduleBlock` e `Appointment` ativos. |
| `S04-T03` | `RF-005`, `RNF-002` | `sps/scheduling/services.py` | `[x]` | `SchedulingService` implementado com `transaction.atomic()` + `select_for_update()` no profissional, impedindo *double-booking* e gerenciando transições de estado. |
| `S04-T04` | `RF-005`, `RNF-001` | `sps/scheduling/forms.py`, `sps/scheduling/views.py`, `sps/scheduling/urls.py`, `sps/templates/scheduling/` | `[x]` | CBVs da Agenda Interna (`AppointmentAgendaListView`, `AppointmentCreateView`, `AppointmentDetailView`, `AppointmentRescheduleView`, `AppointmentStatusTransitionView`) operacionais. |
| `S04-T05` | `DEC-001`, `RNF-001`, `RNF-002` | `sps/scheduling/tests.py` | `[x]` | Suíte acumulada de `30` testes automatizados executada e aprovada (`OK`). |
| `S04-T06` | Governança | `sps/docs/02_execucao/evidencias_da_sprint_004.md`, `sps/docs/02_execucao/estado_do_projeto.md` | `[x]` | Revisão nas oito dimensões concluída e pacote pronto para ação manual de Git/GitHub pelo desenvolvedor. |

---

## 3. Fichas de Verificação por Tarefa (`S04-T01` a `S04-T05`)

```text
ID da tarefa: S04-T01
Requisito associado: RF-005, DEC-002
Resultado esperado: Modelos Appointment e AppointmentItem isolados por salão, suportando 1..N serviços com soma de duration_minutes e total_estimated_amount.
Arquivos alterados: sps/scheduling/models.py, sps/scheduling/migrations/0002_appointment_appointmentitem_and_more.py
Verificação executada: test_multi_service_duration_sum_and_double_booking_rejection
Resultado observado: Agendamento com dois serviços (30 min R$ 50,00 + 45 min R$ 70,00) grava total_duration_minutes = 75, total_estimated_amount = 120.00 e end_at = start_at + 75 min, além de 2 registros em AppointmentItem.
Critério atendido: sim

ID da tarefa: S04-T02
Requisito associado: RF-005
Resultado esperado: AvailabilityService calcula slots livres e valida intervalos respeitando feriados, expediente do salão, expediente/intervalo do profissional, bloqueios e agendamentos ativos.
Arquivos alterados: sps/scheduling/services.py
Verificação executada: test_availability_service_respects_breaks_blocks_and_holidays
Resultado observado: Intervalos de descanso (12:00..13:00), bloqueios (16:00..17:00) e feriados municipais são excluídos dos slots livres e rejeitados na validação direta.
Critério atendido: sim

ID da tarefa: S04-T03
Requisito associado: RF-005, RNF-002, DEC-001
Resultado esperado: SchedulingService serializa agendamentos por profissional com select_for_update(), rejeita sobreposição [start_at, end_at) e controla transições de estado.
Arquivos alterados: sps/scheduling/services.py
Verificação executada: test_multi_service_duration_sum_and_double_booking_rejection, test_status_transitions_cancellation_reason_and_reschedule
Resultado observado: Tentativa de agendar às 15:00 sobre agendamento das 14:00 às 15:15 é bloqueada com ValidationError; agendamento às 15:15 é aceito; cancelamento exige motivo obrigatório; agendamento concluído bloqueia novas transições.
Critério atendido: sim

ID da tarefa: S04-T04 e S04-T05
Requisito associado: RF-005, RNF-001, DEC-001
Resultado esperado: CBVs da Agenda Interna com filtro diário/semanal, criação com múltiplos serviços, remarcação, mudança de status e isolamento estrito por salão e por profissional.
Arquivos alterados: sps/scheduling/forms.py, sps/scheduling/views.py, sps/scheduling/urls.py, sps/scheduling/tests.py
Verificação executada: test_agenda_views_professional_scope_and_cross_tenant_isolation
Resultado observado: Profissional vê apenas os próprios agendamentos e recebe 404 ao tentar acessar ou remarcar agendamento de outro profissional; operador do Salão A recebe 404 em agendamentos do Salão B; formulários rejeitam IDs de outro salão.
Critério atendido: sim
```

---

## 4. Avaliação nas Oito Dimensões de Revisão

| Dimensão | Pergunta Central | Avaliação na Sprint 04 |
|---|---|---|
| **Produto** | O comportamento aprovado foi implementado? | Sim: agendamento interno com múltiplos serviços, cálculo automático de duração/valor, motor de disponibilidade, remarcação e ciclo de status estão operacionais. |
| **Escopo** | Foi incluída alguma função não solicitada? | Não: o autoagendamento público (`/s/<slug>/`) permanece reservado para a `Sprint 05`. |
| **Acesso** | Quem pode ler, alterar e exportar dados? | `ProfissionalScopeMixin` restringe `profissional` exclusivamente à própria agenda (`404` em agendamentos de colegas); `gestor` e `recepcionista` operam a agenda completa do próprio salão (`404` cross-tenant). |
| **Integridade** | Falha ou concorrência pode corromper o estado? | `SchedulingService` utiliza `transaction.atomic()` + `User.objects.select_for_update()` no profissional antes de validar e gravar `Appointment` e `AppointmentItem`. |
| **UX** | Usuário entende sucesso, erro, vazio e espera? | Erros de colisão de horário, folga, intervalo ou motivo de cancelamento ausente são anexados ao formulário em português claro; visão diária exibe sugestão de horários livres. |
| **Operação** | Falhas são observáveis e recuperáveis? | Endpoints `/healthz/` e `/readyz/` continuam ativos e validados pela suíte. |
| **Configuração** | Há segredos, defaults perigosos ou dependências implícitas? | Nenhuma dependência externa adicionada; fuso `America/Sao_Paulo` respeitado em todas as conversões. |
| **Documentação** | Outra sessão consegue retomar corretamente? | Sim: estado do projeto, checklist de sprints e evidências da `Sprint 04` atualizados. |

---

## 5. Detalhamento da Suíte de Testes Automatizados Executada (`30` Testes)

### 5.1 Comandos Executados
```powershell
$env:USE_SQLITE_FALLBACK="True"
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations scheduling
.\.venv\Scripts\python.exe manage.py migrate --plan
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py test base salons accounts scheduling catalog clients -v 2
```

### 5.2 Novos Cenários Testados na Sprint 04 (`scheduling`)

| Classe / Teste | Cenário Coberto (`DEC-001` / `RNF-001` / `RNF-002`) | Resultado |
|---|---|---|
| `ProfessionalScheduleAndBlockTests.test_multi_service_duration_sum_and_double_booking_rejection` | `RF-005`, `RNF-002`: Soma de 2 serviços (30m + 45m = 75m, R$ 120,00) das 14:00 às 15:15; rejeita conflito às 15:00 e permite encaixe às 15:15. | `OK` |
| `ProfessionalScheduleAndBlockTests.test_availability_service_respects_breaks_blocks_and_holidays` | `RF-005`: Rejeita e remove dos slots livres o horário de intervalo (12:00..13:00), bloqueio (16:00..17:00) e feriado fechado. | `OK` |
| `ProfessionalScheduleAndBlockTests.test_status_transitions_cancellation_reason_and_reschedule` | `RF-005`: Remarcação sem auto-colisão, obrigatoriedade de motivo ao cancelar e ciclo `agendado -> confirmado -> em_atendimento -> concluido`. | `OK` |
| `ProfessionalScheduleAndBlockTests.test_agenda_views_professional_scope_and_cross_tenant_isolation` | `SEC-A`, `SEC-B`, `SEC-C`, `SEC-D`: Isolamento de agenda por profissional (`404` em colega), isolamento entre salões (`404` cross-tenant) e rejeição de IDs cruzados no form. | `OK` |

### 5.3 Rotas e Views da Agenda Interna Entregues na Sprint 04

| Rota (URL) | Nome da Rota (`url_name`) | View (CBV) | Perfis Autorizados |
|---|---|---|---|
| `/agenda/` | `scheduling:appointment_list` | `AppointmentAgendaListView` | `gestor`, `recepcionista`, `profissional` (escopado) |
| `/agenda/novo/` | `scheduling:appointment_create` | `AppointmentCreateView` | `gestor`, `recepcionista`, `profissional` (próprio) |
| `/agenda/<int:pk>/` | `scheduling:appointment_detail` | `AppointmentDetailView` | `gestor`, `recepcionista`, `profissional` (próprio) |
| `/agenda/<int:pk>/remarcar/` | `scheduling:appointment_reschedule` | `AppointmentRescheduleView` | `gestor`, `recepcionista`, `profissional` (próprio) |
| `/agenda/<int:pk>/status/` | `scheduling:appointment_status` | `AppointmentStatusTransitionView` | `gestor`, `recepcionista`, `profissional` (próprio) |

### 5.4 Integração Automática com a Ficha do Cliente (`Sprint 03`)

- Como `Appointment.client` define `related_name='appointments'`, o método `Client.get_appointment_history()` implementado na `Sprint 03` passa automaticamente a listar os agendamentos cronológicos na aba de histórico da ficha do cliente (`/clientes/<id>/`).

---

## 6. Achados de Revisão e Correções Realizadas (`S04-T06`)

- **Achado durante a execução da suíte de testes:**
  - Na primeira execução de `AvailabilityService`, a consulta a `SalonHoliday` filtrava por `is_closed=True` em vez do campo real `is_closed_all_day` definido na `Sprint 02` (`salons.models.SalonHoliday`).
- **Correção aplicada e re-verificada:**
  - Ajustado `AvailabilityService.validate_interval_available()` e `AvailabilityService.get_available_slots()` para consultar `holiday.is_closed_all_day` e também respeitar horários parciais de feriado (`holiday.opening_time` e `holiday.closing_time`) quando `is_closed_all_day=False`.
  - Toda a suíte de **30 testes automatizados** foi reexecutada e aprovada integralmente (`OK`).

---

## 7. Proposta de Mensagem de Commit e Comandos Manuais (Exclusivos do Usuário)

```bash
# EXECUCAO EXCLUSIVA DO DESENVOLVEDOR (NAO EXECUTADO PELA IA)
git status
git add sps/
git commit -m "feat(sprint-04): availability engine, multi-service appointments and atomic collision prevention"
git push
```

---

## 8. Limites da Verificação e Próximo Passo

- **Limites da verificação:** Todos os 30 testes automatizados (`base`, `salons`, `accounts`, `scheduling`, `catalog`, `clients`) foram executados localmente (`Python 3.13.6` + `Django 5.2.19`) com dados sintéticos.
- **Próxima ação esperada do desenvolvedor:** Revisar a entrega da `Sprint 04`, realizar manualmente o commit/push no Git/GitHub (ou decidir adiar) e solicitar explicitamente a execução da **`Sprint 05`** (*Design System, Autoagendamento Público `/s/<slug>/` e Cancelamento*).
