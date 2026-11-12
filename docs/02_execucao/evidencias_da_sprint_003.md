---
versao: 1.0.0
data_editorial: 2026-11-12
tipo: evidencias_de_sprint
projeto: SPS (Sistema Para Salões)
sprint: Sprint 03
estado: concluida_aguardando_acao_git_do_usuario
---

# Evidências de Execução e Revisão — Sprint 03 — SPS (Sistema Para Salões)

## 1. Identificação da Entrega

- **Sprint:** `Sprint 03 — Catálogo de Serviços, Regras de Comissão e Cadastro de Clientes`
- **Versão do PRD de referência:** `1.0.0` (aprovada pelo desenvolvedor em `2026-11-12`)
- **Solicitação explícita do desenvolvedor:** *"Pode iniciar a sprint 03"*
- **Requisitos avaliados:**
  - `RF-003`: Catálogo de Serviços, Comissões e Metadados Fiscais de Serviço (`ServiceCategory`, `Service`, `ProfessionalServiceCommission` e resolução de precedência de comissão).
  - `RF-004`: Cadastro e Histórico de Clientes por Salão com Dados para Tomador Fiscal (`Client`, normalização e unicidade por salão, busca e aba de histórico de atendimentos).
  - `RNF-001`: Isolamento Multi-tenant estrito e controle de acesso por perfil (`gestor`, `recepcionista`, `profissional`).
- **Decisões aplicadas:** `DEC-001` (testes automatizados de isolamento, permissões e regra de negócio de comissão), `DEC-002` (isolamento de catálogo e carteira de clientes por salão), `DEC-003` (metadados fiscais `lc116_service_code`, `cnae_code`, `iss_rate_pct` em `Service` e `cpf_cnpj`, endereço e `ibge_city_code` em `Client`).
- **Operações de Git/GitHub executadas pela IA:** `Nenhuma` (`git_executado_pela_ia: false`).

---

## 2. Checklist de Tarefas da Sprint 03 e Rastreabilidade

| ID da Tarefa | Requisito / Decisão | Arquivos Principais Criados / Alterados | Situação | Evidência Registrada |
|---|---|---|---|---|
| `S03-T01` | `RF-003`, `DEC-003` | `sps/catalog/models.py`, `sps/catalog/admin.py`, `sps/catalog/migrations/0001_initial.py` | `[x]` | Modelos `ServiceCategory`, `Service` (com LC 116, CNAE, ISS e profissionais M2M) e `ProfessionalServiceCommission` criados e validados. |
| `S03-T02` | `RF-003`, `DEC-001` | `sps/catalog/services.py` | `[x]` | Funções `resolve_commission_percentage(salon, professional, service)` e `calculate_commission_amount(base_amount, commission_pct)` implementadas com `ROUND_HALF_UP`. |
| `S03-T03` | `RF-004`, `DEC-002`, `DEC-003` | `sps/clients/models.py`, `sps/clients/admin.py`, `sps/clients/migrations/0001_initial.py` | `[x]` | Modelo `Client` isolado por salão com normalização e unicidade de `(salon, phone)` e `(salon, cpf_cnpj)`, observações técnicas e dados fiscais de tomador. |
| `S03-T04` | `RF-003`, `RF-004`, `RNF-001` | `sps/catalog/forms.py`, `sps/catalog/views.py`, `sps/catalog/urls.py`, `sps/clients/forms.py`, `sps/clients/views.py`, `sps/clients/urls.py`, `sps/templates/catalog/`, `sps/templates/clients/` | `[x]` | CBVs de listagem, busca, criação, edição e detalhe (com aba de histórico de atendimentos) para Serviços, Categorias, Comissões e Clientes. |
| `S03-T05` | `DEC-001`, `RNF-001` | `sps/catalog/tests.py`, `sps/clients/tests.py` | `[x]` | Suíte acumulada de `26` testes automatizados executada e aprovada (`OK`). |
| `S03-T06` | Governança | `sps/docs/02_execucao/evidencias_da_sprint_003.md`, `sps/docs/02_execucao/estado_do_projeto.md` | `[x]` | Revisão nas oito dimensões concluída e pacote pronto para ação manual de Git/GitHub pelo desenvolvedor. |

---

## 3. Fichas de Verificação por Tarefa (`S03-T01` a `S03-T05`)

```text
ID da tarefa: S03-T01
Requisito associado: RF-003, DEC-002, DEC-003
Resultado esperado: Modelos ServiceCategory, Service e ProfessionalServiceCommission isolados por salão, com campos fiscais preparatórios e restrições de unicidade.
Arquivos alterados: sps/catalog/models.py, sps/catalog/migrations/0001_initial.py
Verificação executada: CatalogAndCommissionTests
Resultado observado: Serviços persistem duração > 0, preço base, comissão padrão 0..100%, profissionais habilitados e códigos LC 116/CNAE/ISS; tentativa de vincular categoria ou profissional de outro salão é bloqueada.
Critério atendido: sim

ID da tarefa: S03-T02
Requisito associado: RF-003, DEC-001
Resultado esperado: Função resolve_commission_percentage(salon, professional, service) prioriza regra ativa de ProfessionalServiceCommission e cai para Service.default_commission_pct na ausência.
Arquivos alterados: sps/catalog/services.py
Verificação executada: CatalogAndCommissionTests.test_resolve_commission_percentage_precedence_and_amount
Resultado observado: Para serviço "Corte + Escova" (R$ 100,00, padrão 40%) e regra específica da Profissional Ana (50%), retorna 50.00% (R$ 50,00); para Bruno sem regra específica, retorna 40.00% (R$ 40,00); se a regra de Ana for desativada, retorna 40.00%.
Critério atendido: sim

ID da tarefa: S03-T03
Requisito associado: RF-004, DEC-002, DEC-003
Resultado esperado: Modelo Client isolado por salão com normalização de telefone, CPF/CNPJ, CEP, UF e IBGE, garantindo unicidade apenas dentro do mesmo salão.
Arquivos alterados: sps/clients/models.py, sps/clients/migrations/0001_initial.py
Verificação executada: ClientModelAndIsolationTests.test_client_normalization_and_uniqueness_scoped_per_salon
Resultado observado: Telefone e CPF duplicados no mesmo salão lançam ValidationError; o mesmo telefone/CPF em outro salão é aceito normalmente.
Critério atendido: sim

ID da tarefa: S03-T04 e S03-T05
Requisito associado: RF-003, RF-004, RNF-001, DEC-001
Resultado esperado: CBVs de Catálogo e Clientes com busca, aba de histórico de atendimentos e isolamento multi-tenant / permissões por perfil.
Arquivos alterados: sps/catalog/views.py, sps/clients/views.py, sps/catalog/tests.py, sps/clients/tests.py
Verificação executada: test_service_and_commission_views_permissions_and_cross_tenant_isolation, test_client_search_detail_and_cross_tenant_isolation
Resultado observado: Operador do Salão B buscando por "João" do Salão A não obtém nenhum registro; tentativa de acesso por ID cruzado retorna 404; recepcionista recebe 403 ao tentar criar/editar serviços ou comissões; profissional recebe 403 ao tentar listar clientes globais.
Critério atendido: sim
```

---

## 4. Avaliação nas Oito Dimensões de Revisão

| Dimensão | Pergunta Central | Avaliação na Sprint 03 |
|---|---|---|
| **Produto** | O comportamento aprovado foi implementado? | Sim: catálogo de serviços por categoria, comissão específica por profissional, função de resolução de comissão e carteira de clientes com dados fiscais e aba de histórico estão operacionais. |
| **Escopo** | Foi incluída alguma função não solicitada? | Não: motor de agendamento e comandas permanecem reservados para as `Sprints 04` e `06`. |
| **Acesso** | Quem pode ler, alterar e exportar dados? | Escrita em serviços/categorias/comissões restrita a `gestor` (`GestorRequiredMixin`); clientes restritos a `gestor` e `recepcionista` (`RecepcaoOrGestorMixin`); leitura de comissões escopada para `profissional` (`ProfissionalScopeMixin`). |
| **Integridade** | Falha ou concorrência pode corromper o estado? | Constraints `unique_service_category_per_salon`, `unique_service_name_per_salon`, `unique_professional_service_commission`, `unique_client_phone_per_salon` e `unique_client_cpf_cnpj_per_salon` ativas no banco. |
| **UX** | Usuário entende sucesso, erro, vazio e espera? | Busca por texto/categoria em Serviços, busca por nome/telefone/CPF em Clientes, mensagens de confirmação e aba de histórico na ficha do cliente. |
| **Operação** | Falhas são observáveis e recuperáveis? | Endpoints `/healthz/` e `/readyz/` permanecem ativos e validados pela suíte. |
| **Configuração** | Há segredos, defaults perigosos ou dependências implícitas? | Nenhuma dependência externa adicionada; todas as configurações permanecem centralizadas em `core/settings.py`. |
| **Documentação** | Outra sessão consegue retomar corretamente? | Sim: estado do projeto, checklist de sprints e evidências da `Sprint 03` atualizados. |

---

## 5. Detalhamento da Suíte de Testes Automatizados Executada (`26` Testes)

### 5.1 Comandos Executados
```powershell
$env:USE_SQLITE_FALLBACK="True"
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations catalog clients
.\.venv\Scripts\python.exe manage.py migrate --plan
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py test base salons accounts scheduling catalog clients -v 2
```

### 5.2 Novos Cenários Testados na Sprint 03 (`catalog` e `clients`)

| Classe / Teste | Cenário Coberto (`DEC-001` / `RNF-001`) | Resultado |
|---|---|---|
| `CatalogAndCommissionTests.test_resolve_commission_percentage_precedence_and_amount` | `RF-003`: Valida precedência de `ProfessionalServiceCommission` (50% Ana) sobre `Service.default_commission_pct` (40% Bruno), fallback quando regra inativa e erro em vínculo cross-tenant. | `OK` |
| `CatalogAndCommissionTests.test_service_and_commission_views_permissions_and_cross_tenant_isolation` | `SEC-A`, `SEC-B`, `SEC-C`: Gestor cria serviço com LC116/CNAE/ISS; recebe `404` em registros do Salão B; recepcionista e profissional recebem `403` na escrita; profissional vê apenas a própria comissão. | `OK` |
| `CatalogAndCommissionTests.test_cross_tenant_association_rejected_in_forms_and_models` | `SEC-D`: Rejeita submissão de `ServiceForm` e `ProfessionalServiceCommissionForm` com categoria, profissional ou serviço de outro salão. | `OK` |
| `ClientModelAndIsolationTests.test_client_normalization_and_uniqueness_scoped_per_salon` | `RF-004`, `DEC-002`: Normaliza telefone, CPF, CEP e UF; bloqueia duplicidade no mesmo salão e permite mesmo telefone/CPF em salão distinto. | `OK` |
| `ClientModelAndIsolationTests.test_client_search_detail_and_cross_tenant_isolation` | `RF-004`, `SEC-A`, `SEC-B`, `SEC-C`: Busca e ficha do cliente com aba de histórico no Salão A; busca no Salão B por "João" não retorna dados do Salão A; acesso cruzado retorna `404`; profissional recebe `403`. | `OK` |

### 5.3 Rotas e Views Entregues na Sprint 03

| Rota (URL) | Nome da Rota (`url_name`) | View (CBV) | Perfis Autorizados |
|---|---|---|---|
| `/catalogo/servicos/` | `catalog:service_list` | `ServiceListView` | `gestor`, `recepcionista`, `profissional` |
| `/catalogo/servicos/novo/` | `catalog:service_create` | `ServiceCreateView` | `gestor` |
| `/catalogo/servicos/<int:pk>/editar/` | `catalog:service_edit` | `ServiceUpdateView` | `gestor` (apenas próprio salão) |
| `/catalogo/categorias/` | `catalog:category_list` | `ServiceCategoryListView` | `gestor`, `recepcionista`, `profissional` |
| `/catalogo/categorias/nova/` | `catalog:category_create` | `ServiceCategoryCreateView` | `gestor` |
| `/catalogo/categorias/<int:pk>/editar/` | `catalog:category_edit` | `ServiceCategoryUpdateView` | `gestor` (apenas próprio salão) |
| `/catalogo/comissoes/` | `catalog:commission_rule_list` | `CommissionRuleListView` | `gestor`, `recepcionista`, `profissional` (escopado) |
| `/catalogo/comissoes/nova/` | `catalog:commission_rule_create` | `CommissionRuleCreateView` | `gestor` |
| `/catalogo/comissoes/<int:pk>/editar/` | `catalog:commission_rule_edit` | `CommissionRuleUpdateView` | `gestor` (apenas próprio salão) |
| `/catalogo/comissoes/<int:pk>/excluir/` | `catalog:commission_rule_delete` | `CommissionRuleDeleteView` | `gestor` (apenas próprio salão) |
| `/clientes/` | `clients:client_list` | `ClientListView` | `gestor`, `recepcionista` |
| `/clientes/novo/` | `clients:client_create` | `ClientCreateView` | `gestor`, `recepcionista` |
| `/clientes/<int:pk>/` | `clients:client_detail` | `ClientDetailView` | `gestor`, `recepcionista` (apenas próprio salão) |
| `/clientes/<int:pk>/editar/` | `clients:client_edit` | `ClientUpdateView` | `gestor`, `recepcionista` (apenas próprio salão) |

### 5.4 Contratos de Domínio Preparados para as Próximas Sprints

- `catalog.services.resolve_commission_percentage(salon, professional, service)`: pronto para consumo pelo `OrderCheckoutService` na `Sprint 07`.
- `catalog.services.calculate_commission_amount(base_amount, commission_pct)`: cálculo financeiro com `ROUND_HALF_UP` (2 casas decimais).
- `clients.models.Client.get_appointment_history()` e `get_service_order_history()`: métodos de integração da aba de histórico da ficha do cliente com `Appointment` (`Sprint 04`) e `ServiceOrder` (`Sprint 06`).

---

## 6. Proposta de Mensagem de Commit e Comandos Manuais (Exclusivos do Usuário)

```bash
# EXECUCAO EXCLUSIVA DO DESENVOLVEDOR (NAO EXECUTADO PELA IA)
git status
git add sps/
git commit -m "feat(sprint-03): service catalog, commission precedence rules and salon-scoped clients with fiscal fields"
git push
```

---

## 7. Limites da Verificação e Próximo Passo

- **Limites da verificação:** Todos os 26 testes automatizados (`base`, `salons`, `accounts`, `scheduling`, `catalog`, `clients`) foram executados localmente (`Python 3.13.6` + `Django 5.2.19`) com dados sintéticos.
- **Próxima ação esperada do desenvolvedor:** Revisar a entrega da `Sprint 03`, realizar manualmente o commit/push no Git/GitHub (ou decidir adiar) e solicitar explicitamente a execução da **`Sprint 04`** (*Motor de Disponibilidade e Agenda Inteligente Interna com Múltiplos Serviços*).
