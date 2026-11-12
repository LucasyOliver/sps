---
versao: 1.0.0
data_editorial: 2026-11-12
tipo: prd_indice_central
projeto: SPS (Sistema Para Salões)
estado: prd_aprovado
origem_prompt_refinado: "prompt_refinado_do_projeto.md (aprovado em 2026-11-12)"
---

# PRD — SPS (Sistema Para Salões) — Documento Central e Índice

## 1. Identificação e Situação do PRD

- **Projeto:** SPS (Sistema Para Salões) — Slug técnico e stack: `sps`
- **Problema central:** Descentralização e falhas operacionais em salões de beleza independentes (conflitos de agenda, erros de cálculo de comissões no fechamento de comandas, descontrole entre estoque de venda e consumo interno, ausência de indicadores gerenciais e falta de preparação estrutural de dados para emissão fiscal).
- **Responsável pelo produto e decisões:** Desenvolvedor (controle exclusivo de aprovação, prioridades, Git/GitHub e produção).
- **Colaboração técnica:** IA operando sob contrato do guia operacional.
- **Versão do PRD:** `1.0.0`
- **Situação atual:** `prd_aprovado`
- **Origem:** Gerado a partir de [`prompt_refinado_do_projeto.md`](prompt_refinado_do_projeto.md) (aprovado em `2026-11-12`) e [`requisitos_do_projeto.md`](requisitos_do_projeto.md).
- **Aprovação explícita do PRD:** Aprovado pelo desenvolvedor em `2026-11-12` ("Aprovo o PRD versão 1.0.0 do SPS e solicito a execução exclusiva da Sprint 01.").

---

## 2. Mapa Modular do PRD

Para respeitar a diretriz de modularidade (150 a 400 linhas por arquivo Markdown, sem texto artificial), o PRD do **SPS** está organizado nos seguintes módulos complementares e indissociáveis:

| Módulo do PRD | Versão | Conteúdo e Responsabilidade |
|---|---|---|
| [`prd_do_projeto.md`](prd_do_projeto.md) *(este arquivo)* | `1.0.0` | Visão, objetivos, escopo do MVP, exclusões, matriz de acesso, síntese de RF/RNF, rastreabilidade, riscos e aceite do PRD. |
| [`requisitos_do_projeto.md`](requisitos_do_projeto.md) | `1.0.0` | Fichas detalhadas de `RF-001` a `RF-013` (incluindo preparação fiscal) e `RNF-001` a `RNF-006` com critérios de aceite verificáveis. |
| [`arquitetura_dados_e_seguranca_prd.md`](arquitetura_dados_e_seguranca_prd.md) | `1.0.0` | Organização de apps Django, modelagem conceitual completa das entidades, invariantes, multi-tenancy (`DEC-002`), preparação fiscal (`DEC-003`), filas Celery e agente de IA. |
| [`guia_deploy_vps_swarm_e_operacao_prd.md`](guia_deploy_vps_swarm_e_operacao_prd.md) | `1.0.0` | Guia passo a passo de deploy do zero em VPS Ubuntu com Docker Swarm, Traefik, Cloudflare DNS-01, Docker Secrets, `scripts/deploy.sh`, backup e restauração. |
| [`sprints_de_implementacao_prd.md`](sprints_de_implementacao_prd.md) | `1.0.0` | Plano de execução em 10 sprints sequenciais com pré-condições, checklists `[ ]`, testes automatizados (`DEC-001`) e critérios de entrega por sprint. |
| [`../03_decisoes/decisoes_arquiteturais_iniciais.md`](../03_decisoes/decisoes_arquiteturais_iniciais.md) | `1.0.0` | Registro formal das decisões `DEC-001` (Testes), `DEC-002` (Multi-tenant) e `DEC-003` (Preparação Fiscal). |

---

## 3. Visão do Produto e Objetivos de Negócio

O **SPS (Sistema Para Salões)** é uma plataforma web SaaS multi-tenant projetada para salões de beleza, barbearias e centros de estética independentes. Cada salão opera em um ambiente lógico estritamente isolado (`Salon`), gerenciando desde a captação do agendamento (na recepção ou via página pública `/s/<slug>/`) até o fechamento da comanda no caixa, geração exata de comissões, baixa de estoque, análise por relatórios em PDF, assistência gerencial por Inteligência Artificial e consolidação estruturada de dados para futura emissão de notas fiscais (NFS-e e NFC-e).

### Objetivos de Negócio Verificáveis

- **OBJ-001 — Integridade de Agenda:** Eliminar `100%` dos agendamentos sobrepostos (*double-booking*) para um mesmo profissional através de cálculo automático da soma de durações de múltiplos serviços e bloqueio transacional no banco de dados.
- **OBJ-002 — Exatidão Financeira e de Comissões:** Garantir que `100%` das comissões sejam geradas exclusivamente no ato do fechamento/pagamento da comanda no caixa, aplicando a regra de precedência entre percentual específico `(profissional, servico)` e percentual padrão do serviço.
- **OBJ-003 — Controle Físico e Financeiro de Estoque:** Impedir vendas de produtos sem saldo disponível na comanda e rastrear todas as entradas, saídas por venda, consumos internos e ajustes de inventário com alerta de estoque mínimo.
- **OBJ-004 — Prontidão Estrutural Fiscal (`DEC-003`):** Persistir desde o MVP todos os metadados cadastrais e transacionais necessários para futura emissão de NFS-e (serviços e rateio Salão-Parceiro) e NFC-e (venda de produtos), evitando refatorações destrutivas futuras.

---

## 4. Escopo do MVP e Exclusões Explícitas

### Escopo Incluído no MVP
1. **Gestão Multi-tenant de Salões (`RF-001`):** Cadastro de salões, horários de funcionamento, feriados, antecedência mínima de cancelamento público e parâmetros fiscais do emitente.
2. **Autenticação e Equipe (`RF-002`):** Login por e-mail (`AUTH_USER_MODEL` customizado), vínculo único de usuário interno por salão (`DEC-002`), expediente individual e bloqueios de agenda do profissional.
3. **Catálogo de Serviços e Comissões (`RF-003`):** Serviços com duração, preço, comissão padrão, exceção de comissão por profissional e códigos fiscais de serviço opcionais.
4. **Clientes por Salão (`RF-004`):** Base isolada por salão com histórico de atendimentos/gastos e dados opcionais de tomador fiscal (CPF/CNPJ e endereço).
5. **Agenda Interna e Autoagendamento Público (`RF-005`, `RF-006`):** Agendamento com múltiplos serviços, validação atômica de conflito de horário e página pública `/s/<slug_salao>/` com regra de prazo mínimo de cancelamento.
6. **Comandas, Estoque e Caixa/Comissões (`RF-007`, `RF-008`, `RF-009`):** Comandas mistas (serviços + produtos), baixa automática de estoque sem permitir saldo negativo, caixa diário e geração atômica de comissões no pagamento.
7. **Preparação Fiscal Desacoplada (`RF-013`):** Geração de `FiscalDocumentRecord` no fechamento da comanda e contrato `FiscalGatewayAdapter` (implementação *stub* no MVP).
8. **Notificações Assíncronas (`RF-010`):** E-mails nativos do Django via Celery + RabbitMQ + Redis para confirmação, cancelamento e lembrete periódico (Celery Beat) com idempotência.
9. **Dashboard, Relatórios PDF e Assistente de IA (`RF-011`, `RF-012`):** Indicadores gerenciais, exportação privada em PDF (`ReportLab`/`PyPDF`) e chat gerencial interno com `LangChain`/`LangGraph` restrito ao tenant.
10. **Documentação e Demonstração (`RNF-006`):** Documentação `MkDocs` com `Mermaid` e comando `seed_demo_data`.

### Exclusões Explícitas do MVP
- **Transmissão externa de NFS-e / NFC-e:** A comunicação de rede com webservices de prefeituras, SEFAZ ou gateways fiscais e o uso de certificado digital A1 ficam excluídos do MVP (entrando em sprint futura sobre a base já pronta do `RF-013`).
- **Gateway de pagamento online no autoagendamento:** O cliente agenda online gratuitamente; a liquidação financeira é registrada no caixa do salão.
- **Integração oficial com API de WhatsApp:** As notificações do MVP utilizam exclusivamente o sistema de e-mails do Django via Celery.
- **Múltiplos salões por mesmo login de colaborador:** Cada usuário interno está vinculado a 1 salão fixo no MVP (`DEC-002`).

---

## 5. Usuários, Organizações e Matriz de Acesso

| Perfil | Escopo de Tenant | Autenticação | Operações Autorizadas | Operações Negadas (`403` / `404`) |
|---|---|---|---|---|
| `superadmin_saas` | Plataforma Global | E-mail + Senha | Criar/ativar/suspender salões, visualizar saúde operacional e filas no Admin | Operar caixa/comandas de um salão sem contexto administrativo auditado |
| `gestor` | 1 Salão fixo (`user.salon_id`) | E-mail + Senha | Configurar salão e dados fiscais, gerir equipe, catálogo, comissões, clientes, agenda, comandas, estoque, caixa, PDFs e IA Gerencial | Ler ou alterar qualquer dado pertencente a outro `salon_id` |
| `recepcionista` | 1 Salão fixo (`user.salon_id`) | E-mail + Senha | Gerir clientes, operar agenda do salão, abrir/fechar comandas, operar caixa diário, consultar estoque e usar IA Gerencial no escopo de atendimento/agenda | Alterar percentuais de comissão, configurações fiscais do salão, estornar comandas fechadas ou ver outros salões |
| `profissional` | 1 Salão fixo (`user.salon_id`) | E-mail + Senha | Consultar própria agenda, registrar início/conclusão de atendimento e consultar/exportar apenas o próprio extrato de comissões | Ver caixa geral do salão, comissões de colegas, alterar preços ou acessar outros salões |
| `cliente_final` | Público por Salão (`/s/<slug>/`) | Token público por agendamento | Consultar serviços/horários livres do salão, criar agendamento público e cancelar dentro da antecedência mínima | Acessar rotas internas do sistema ou agendamentos de terceiros |

### 5.1 Ciclos de Vida e Máquinas de Estado Principais

| Entidade | Estados Permitidos | Transições Autorizadas | Regra de Integridade Associada |
|---|---|---|---|
| `Appointment` (Agendamento) | `agendado`, `confirmado`, `em_atendimento`, `concluido`, `cancelado`, `nao_compareceu` | `agendado -> confirmado -> em_atendimento -> concluido`; `agendado/confirmado -> cancelado` ou `nao_compareceu` | Cancelamento pelo cliente no link público só é permitido se `agora <= start_at - cancellation_min_hours`. |
| `ServiceOrder` (Comanda) | `aberta`, `fechada_paga`, `cancelada` | `aberta -> fechada_paga` (no caixa); `aberta -> cancelada`; `fechada_paga -> cancelada` (apenas estorno pelo `gestor`) | Fechamento exige caixa aberto e saldo suficiente de estoque para todos os produtos da comanda. |
| `CommissionEntry` (Comissão) | `pendente_repasse`, `pago_ao_profissional`, `estornado` | Nasce `pendente_repasse` ao pagar a comanda; `pendente_repasse -> pago_ao_profissional` ou `estornado` | Nunca é criada antes do pagamento integral da comanda no caixa. |
| `FiscalDocumentRecord` (Fiscal) | `nao_solicitada`, `pendente_integracao_futura`, `pronta_para_envio`, `emitida`, `erro_emissao`, `cancelada` | Nasce `pendente_integracao_futura` ao fechar comanda paga no MVP (`DEC-003`) | Armazena snapshots imutáveis de emitente, tomador, serviços (NFS-e) e produtos (NFC-e). |

---

## 6. Matriz de Rastreabilidade Geral (Requisitos $\leftrightarrow$ Decisões $\leftrightarrow$ Sprints)

| Requisito | Título Resumido | Decisões | Sprint Alvo | Verificação Prevista (`DEC-001`) |
|---|---|---|---|---|
| `RF-001` | Gestão de Salões, Expediente e Dados Fiscais do Emitente | `DEC-002`, `DEC-003` | Sprint 01, Sprint 02 | Teste de isolamento de tenant e validação de configuração de expediente |
| `RF-002` | Autenticação por E-mail, Equipe por Salão e Bloqueios | `DEC-001`, `DEC-002` | Sprint 01, Sprint 02 | Teste de login por e-mail, permissões por perfil e vínculo fixo de salão |
| `RF-003` | Catálogo de Serviços, Regra de Comissão e Códigos Fiscais | `DEC-001`, `DEC-003` | Sprint 03 | Teste de precedência de comissão `(profissional, servico)` vs padrão |
| `RF-004` | Cadastro e Histórico de Clientes por Salão (com CPF/Endereço) | `DEC-002`, `DEC-003` | Sprint 03 | Teste de unicidade de cliente por salão e bloqueio cross-tenant |
| `RF-005` | Agenda Interna com Múltiplos Serviços e Conflito Zero | `DEC-001`, `DEC-002` | Sprint 04 | Teste automatizado de soma de durações, colisão de horário e bloqueios |
| `RF-006` | Autoagendamento e Cancelamento Público (`/s/<slug>/`) | `DEC-001`, `DEC-002` | Sprint 05 | Teste de oferta de slots livres e bloqueio de cancelamento fora do prazo |
| `RF-007` | Comandas de Atendimento (Serviços + Produtos) | `DEC-001`, `DEC-003` | Sprint 06 | Teste de cálculo de subtotal, descontos e imutabilidade pós-pagamento |
| `RF-008` | Controle de Estoque, Consumo Interno e Alerta de Mínimo | `DEC-001`, `DEC-003` | Sprint 06 | Teste de baixa na comanda, bloqueio de saldo negativo e alerta crítico |
| `RF-009` | Caixa Diário e Geração de Comissões no Pagamento | `DEC-001`, `DEC-002` | Sprint 07 | Teste transacional: pagamento gera caixa + comissão; estorno reverte tudo |
| `RF-010` | Notificações e Lembretes Assíncronos (Celery + RabbitMQ) | `DEC-001` | Sprint 08 | Teste de disparo assíncrono de e-mail e idempotência de lembretes |
| `RF-011` | Dashboard Gerencial e Relatórios Privados em PDF | `DEC-001`, `DEC-002` | Sprint 08 | Teste de geração de PDF e negação (`403`) para perfil/tenant incorreto |
| `RF-012` | Assistente Gerencial Interno de IA (`LangChain`/`LangGraph`) | `DEC-001`, `DEC-002` | Sprint 09 | Teste de injeção forçada de `salon_id` nas tools e resistência a vazamento |
| `RF-013` | Preparação Estrutural e Contrato para Emissão Fiscal | `DEC-003` | Sprint 07 | Teste de geração de `FiscalDocumentRecord` com snapshots no fechamento |
| `RNF-001` a `006` | Segurança, Desempenho, UX, Backup/Restore, Segredos, Docs | `DEC-001` a `DEC-003` | Sprints 01 a 10 | Suíte de segurança/concorrência, `seed_demo_data`, MkDocs e runbook VPS |

### 6.1 Resumo dos Compromissos Não Funcionais (`RNF-001` a `RNF-006`)

| ID | Categoria | Meta Acordada no PRD | Evidência Obrigatória |
|---|---|---|---|
| `RNF-001` | Segurança e Isolamento | `0` vazamentos cross-tenant; `403`/`404` em acessos indevidos | Testes automatizados de isolamento entre Salão A e Salão B em todas as sprints |
| `RNF-002` | Desempenho e Concorrência | Resposta `<= 2s (p95)` até 50 salões; `0` *double-bookings* ou estoque negativo | `select_for_update()` em transações de agenda e comanda + índices compostos por `salon` |
| `RNF-003` | Usabilidade e Design | Interface 100% `pt-BR` (`America/Sao_Paulo`), Desktop + Mobile responsivos | Aplicação fiel dos tokens fornecidos na pasta `sps/design_system/` |
| `RNF-004` | Recuperação Operacional | `RPO <= 24h` (backup diário) e `RTO <= 2h` (restauração em VPS única) | Scripts de backup e procedimento de `pg_restore` no runbook de operação |
| `RNF-005` | Privacidade e Segredos | `0` segredos no código; PDFs privados validados por tenant; Docker Secrets | Leitura via `FileAwareEnv` e teste de bloqueio de download cruzado de PDF |
| `RNF-006` | Documentação e Demo | Docs em `MkDocs` + `Mermaid` e comando `seed_demo_data` multi-cenário | Build validado do `MkDocs` e execução do `seed_demo_data` em desenvolvimento |

---

## 7. Riscos, Hipóteses Remanescentes e Parâmetros Pendentes

| ID | Risco ou Pendência | Impacto | Mitigação / Condição de Resolução |
|---|---|---|---|
| `RSK-001` | Concorrência de agendamento simultâneo (recepção + link público) para o mesmo profissional e horário. | *Double-booking* na agenda. | Uso obrigatório de `transaction.atomic()` com `select_for_update()` no registro do profissional ao validar e gravar o slot (`Sprint 04` e `Sprint 05`). |
| `RSK-002` | Docker Desktop ainda não detectado no `PATH` do ambiente Windows local do desenvolvedor. | Impede subir containers locais de PostgreSQL, RabbitMQ e Redis. | Desenvolvedor instalará/ativará o Docker Desktop antes da execução das migrations e containers na `Sprint 01`. |
| `RSK-003` | Parâmetro `arquivo_design_system` ainda `a_definir`. | Sem referência visual oficial na pasta `sps/design_system/`. | Sprints 01 a 04 focam em fundação, autenticação, modelos, serviços e testes; o `design_system/` deve ser fornecido antes do refinamento visual completo das telas. |
| `RSK-004` | Parâmetro `modelo_llm` ainda `a_definir`. | Necessário para conectar provedor real na `Sprint 09`. | Arquitetura do `ai_assistant` usará fábrica configurável via `.env` (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`) com modo de fallback determinístico para testes locais sem custo de API. |
| `RSK-005` | Parâmetros `dominio_principal` e `registry_imagem` ainda `a_definir`. | Necessários apenas no momento do deploy real em VPS. | Documentados de forma parametrizada no runbook e validados por `scripts/deploy.sh` na `Sprint 10`. |

---

## 8. Checklist de Aceite do PRD pelo Desenvolvedor

- [x] Os problemas, objetivos, escopo do MVP e exclusões refletem exatamente o **SPS (Sistema Para Salões)**.
- [x] As fichas de `RF-001` a `RF-013` (incluindo preparação fiscal) e `RNF-001` a `RNF-006` estão corretas.
- [x] A arquitetura de apps, dados, segurança e preparação fiscal ([`arquitetura_dados_e_seguranca_prd.md`](arquitetura_dados_e_seguranca_prd.md)) está aprovada.
- [x] O guia de deploy em VPS Ubuntu com Docker Swarm ([`guia_deploy_vps_swarm_e_operacao_prd.md`](guia_deploy_vps_swarm_e_operacao_prd.md)) está aprovado.
- [x] A sequência das 10 sprints ([`sprints_de_implementacao_prd.md`](sprints_de_implementacao_prd.md)) está aprovada.
- [x] **Versão `1.0.0` do PRD aprovada explicitamente pelo desenvolvedor:** `aprovado em 2026-11-12`.
- [x] **Primeira sprint (`Sprint 01`) solicitada explicitamente pelo desenvolvedor:** `solicitada em 2026-11-12`.

### Como Aprovar este PRD e Solicitar a Primeira Sprint

Conforme [`geracao_e_revisao_do_prd.md`](../../../guia_desenvolvimento_ia/04_prompts_e_prd/geracao_e_revisao_do_prd.md),
para aprovar esta versão e iniciar o desenvolvimento de forma controlada, informe:

```text
Aprovo o PRD versão 1.0.0 do SPS e solicito a execução exclusiva da Sprint 01.
```
