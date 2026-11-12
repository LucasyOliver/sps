---
versao: 1.0.0
data_editorial: 2026-11-12
tipo: especificacao_de_requisitos
projeto: SPS (Sistema Para Salões)
estado: em_revisao_pelo_desenvolvedor
---

# Requisitos Funcionais e Não Funcionais — SPS (Sistema Para Salões)

## 1. Visão Geral, Problema de Negócio e Escopo do MVP

- **Projeto:** SPS (Sistema Para Salões) — Slug: `sps`
- **Problema atendido:** Salões de beleza independentes sofrem com conflitos de horário na agenda, divergências no cálculo de comissões de profissionais, falta de controle entre produtos vendidos e insumos consumidos internamente, ausência de histórico estruturado de clientes e dificuldade para organizar dados financeiros e fiscais.
- **Resultado esperado do MVP:** Plataforma SaaS multi-tenant onde cada salão opera de forma estritamente isolada sua equipe, catálogo de serviços, agenda híbrida (interna + link público para clientes), comandas de atendimento, caixa diário, comissões geradas no pagamento, estoque de produtos, relatórios em PDF, assistente gerencial interno de IA e estrutura de dados pronta para futura emissão de notas fiscais (NFS-e/NFC-e).
- **Exclusões explícitas do MVP:**
  - Conector ativo de transmissão síncrona/assíncrona com SEFAZ/Prefeituras (o MVP entrega a modelagem fiscal completa e o contrato desacoplado de integração conforme `DEC-003` e `RF-013`).
  - Pagamento online integrado no link público de agendamento (o pagamento ocorre no fechamento da comanda no caixa do salão).
  - Aplicativo mobile nativo iOS/Android (o acesso mobile ocorre via interface web responsiva).
  - Conta única de cliente compartilhada entre salões diferentes (cada salão mantém sua própria base de clientes isolada conforme `DEC-002`).

---

## 2. Perfis de Usuário e Regras de Acesso Multi-tenant (`DEC-002`)

| Perfil | Escopo | Permissões Essenciais | Restrições Explícitas |
|---|---|---|---|
| `superadmin_saas` | Plataforma | Gerir salões (tenants), ativar/suspender contas e auditar saúde técnica da plataforma | Não opera caixa ou comandas de salões sem trilha de auditoria |
| `gestor` | 1 Salão fixo | Acesso total ao seu salão: configurações, dados fiscais, equipe, catálogo, agenda, comandas, caixa, comissões, estoque, PDFs e IA Gerencial | Proibido acessar ou listar qualquer registro de outro salão |
| `recepcionista` | 1 Salão fixo | Gerir clientes, agenda, abertura/fechamento de comandas, recebimento no caixa, consulta de estoque e uso operacional da IA Gerencial | Proibido alterar percentuais de comissão, configurações fiscais do salão ou excluir lançamentos financeiros |
| `profissional` | 1 Salão fixo | Visualizar própria agenda, bloquear horários próprios (quando permitido), atualizar execução de atendimento e consultar próprio extrato de comissões | Proibido ver faturamento global do salão, comissões de terceiros ou configurações do tenant |
| `cliente_final` | Público por Salão | Acessar `/s/<slug_salao>/`, consultar serviços e horários livres, agendar múltiplos serviços e cancelar dentro da antecedência mínima | Sem acesso ao painel interno ou dados de outros clientes |

---

## 3. Requisitos Funcionais (RF-001 a RF-013)

### RF-001: Gestão de Salões (Tenants), Expediente e Parâmetros Operacionais/Fiscais
- **Ator e organização:** `superadmin_saas` (criação/status do tenant) e `gestor` (configurações do próprio salão).
- **Pré-condições:** Usuário autenticado com perfil autorizado.
- **Entrada:** Nome fantasia, razão social, `slug` único, telefone, e-mail, endereço, horários de funcionamento por dia da semana, feriados/fechamentos, prazo mínimo (em horas) para cancelamento público e dados fiscais preparatórios (CNPJ, Inscrição Municipal, Inscrição Estadual, Regime Tributário, código IBGE do município e indicador de parceria/Salão-Parceiro).
- **Fluxo principal e regras:** O sistema valida unicidade do `slug` e formato do CNPJ (quando informado), persistindo os horários de abertura/fechamento que limitam toda a grade de agendamento do salão.
- **Exceções e permissões:** `recepcionista` e `profissional` recebem `403 Forbidden` ao tentar editar configurações do salão.
- **Critério de aceite:** Dado um gestor autenticado no Salão A, quando atualizar a antecedência mínima de cancelamento para 4 horas e preencher os dados fiscais do Salão A, então o sistema persiste os dados apenas no Salão A; em tentativa de editar o Salão B, retorna `403/404`.
- **Prioridade:** Essencial | **Decisões:** `DEC-002`, `DEC-003` | **Situação:** Em revisão.

### RF-002: Autenticação por E-mail, Gestão de Equipe e Expediente Individual
- **Ator e organização:** `gestor` do salão.
- **Pré-condições:** `AUTH_USER_MODEL` customizado com login por e-mail e vínculo fixo a um único salão (`salon`).
- **Entrada:** Nome, e-mail único, papel (`gestor`, `recepcionista`, `profissional`), telefone, documento (CPF/CNPJ opcional para profissional parceiro), grade de expediente individual por dia da semana e bloqueios de agenda (férias, folgas, ausências).
- **Fluxo principal e regras:** O gestor cadastra membros da equipe no seu salão. O expediente do profissional deve estar contido no horário de funcionamento do salão ou respeitar regras explícitas de turno.
- **Exceções e permissões:** E-mail já utilizado impede novo cadastro; usuário inativo não autentica nem aparece disponível na agenda pública.
- **Critério de aceite:** Dado um profissional com expediente das 09:00 às 18:00 e bloqueio das 12:00 às 13:00, quando consultada sua disponibilidade, o intervalo bloqueado não pode ser ofertado para agendamento.
- **Prioridade:** Essencial | **Decisões:** `DEC-002` | **Situação:** Em revisão.

### RF-003: Catálogo de Serviços, Comissões e Metadados Fiscais de Serviço
- **Ator e organização:** `gestor` (escrita) e `recepcionista`/`profissional` (leitura no próprio salão).
- **Entrada:** Nome do serviço, categoria, duração estimada em minutos (múltiplos de 5/10/15 min), preço base (`Decimal`), comissão padrão (`%`), profissionais habilitados, status ativo/inativo e metadados fiscais opcionais (código de serviço municipal LC 116, CNAE e alíquota ISS referencial). Regras de exceção: tabela de comissão específica por `(profissional, servico)`.
- **Fluxo principal e regras:** A duração deve ser maior que zero e o percentual de comissão entre `0%` e `100%`. Se houver percentual específico para o profissional que executou o serviço, ele prevalece sobre o percentual padrão do serviço.
- **Critério de aceite:** Dado o serviço "Corte + Escova" com preço R$ 100,00 e comissão padrão de 40%, e uma regra específica para a Profissional Ana de 50%, quando o cálculo de comissão for acionado para Ana nesse serviço, o percentual aplicado deve ser 50%.
- **Prioridade:** Essencial | **Decisões:** `DEC-001`, `DEC-003` | **Situação:** Em revisão.

### RF-004: Cadastro e Histórico de Clientes por Salão (com Dados para Tomador Fiscal)
- **Ator e organização:** `gestor` e `recepcionista` do salão; criação/atualização vinculada ao autoagendamento público.
- **Entrada:** Nome completo, telefone/celular, e-mail, data de nascimento (opcional), observações técnicas/alergias e dados fiscais opcionais para futuro receptor de NFS-e/NFC-e (CPF/CNPJ e endereço completo com CEP/município).
- **Fluxo principal e regras:** Registro estritamente isolado por `salon`. Telefone e CPF (quando preenchidos) são normalizados e validados quanto à unicidade dentro do mesmo salão. Exibe histórico cronológico de agendamentos, comandas e valores gastos no salão.
- **Critério de aceite:** Dado o Cliente João cadastrado no Salão A, quando um operador do Salão B buscar por João, nenhum registro do Salão A é retornado (`RNF-001`).
- **Prioridade:** Essencial | **Decisões:** `DEC-002`, `DEC-003` | **Situação:** Em revisão.

### RF-005: Agenda Inteligente Interna com Múltiplos Serviços e Prevenção de Conflitos
- **Ator e organização:** `gestor`, `recepcionista` e `profissional` (restrito à própria agenda).
- **Entrada:** Cliente, profissional, data/hora de início, lista de 1 ou mais serviços habilitados para o profissional e observações.
- **Fluxo principal e regras:** O sistema soma a duração e o valor estimado de todos os serviços selecionados para determinar ` end_time = start_time + duracao_total`. Valida em transação atômica (`select_for_update`) que o profissional está ativo, dentro do seu expediente, sem bloqueio de agenda e sem sobreposição (`start < existente.end` e `end > existente.start`) com outro agendamento nos estados `agendado`, `confirmado` ou `em_atendimento`. Ciclo de vida: `agendado -> confirmado -> em_atendimento -> concluido`, além de `cancelado` (com motivo) e `nao_compareceu`.
- **Critério de aceite:** Dados dois serviços de 30 min e 45 min agendados a partir das 14:00 para o Profissional Carlos, o sistema reserva das 14:00 às 15:15; qualquer tentativa concorrente de agendar Carlos às 15:00 é rejeitada com mensagem de conflito de horário.
- **Prioridade:** Essencial | **Decisões:** `DEC-001`, `DEC-002` | **Situação:** Em revisão.

### RF-006: Autoagendamento e Cancelamento Público pelo Cliente (`/s/<slug_salao>/`)
- **Ator e organização:** `cliente_final` acessando a página pública de um salão ativo.
- **Entrada:** Seleção de 1 ou mais serviços ativos, profissional habilitado, data/horário disponível e dados do cliente (nome, telefone, e-mail, CPF opcional).
- **Fluxo principal e regras:** A página exibe apenas horários livres compatíveis com a soma das durações dos serviços escolhidos. Ao confirmar, cria o agendamento com status inicial `agendado` (ou `confirmado` conforme configuração do salão), gera token seguro de consulta/cancelamento e enfileira e-mail de confirmação via Celery (`RF-010`). O cliente só pode cancelar pelo link público se `agora <= horario_inicio - antecedencia_minima_horas` do salão; fora do prazo, o sistema bloqueia e orienta contato com a recepção.
- **Critério de aceite:** Dado um salão com antecedência mínima de cancelamento de 3 horas e um agendamento para hoje às 16:00, quando o cliente tentar cancelar pelo link às 14:00, a operação é negada e o agendamento permanece ativo.
- **Prioridade:** Essencial | **Decisões:** `DEC-001`, `DEC-002` | **Situação:** Em revisão.

### RF-007: Comandas de Atendimento (Serviços Executados + Venda de Produtos)
- **Ator e organização:** `gestor` e `recepcionista` do salão.
- **Entrada:** Vínculo opcional com agendamento, cliente, itens de serviço (serviço, profissional executante, valor unitário, desconto), itens de produto do estoque (produto, quantidade, valor unitário) e observações.
- **Fluxo principal e regras:** Uma comanda pode ser aberta a partir de um agendamento (`em_atendimento`/`concluido`) ou diretamente para atendimento avulso. Permite incluir múltiplos serviços (inclusive executados por profissionais diferentes na mesma comanda) e produtos vendidos. Estados da comanda: `aberta`, `fechada_paga`, `cancelada`. Comandas `fechada_paga` são imutáveis em seus itens sem estorno formal auditado pelo gestor.
- **Critério de aceite:** Dada uma comanda aberta com 2 serviços (Profissionais A e B) e 1 produto de venda, o total líquido reflete a soma dos itens menos descontos autorizados, preparando o fechamento no caixa (`RF-009`).
- **Prioridade:** Essencial | **Decisões:** `DEC-001`, `DEC-003` | **Situação:** Em revisão.

### RF-008: Controle de Estoque de Produtos, Consumo Interno, Alertas e Metadados Fiscais
- **Ator e organização:** `gestor` (cadastro/ajustes) e `recepcionista` (consulta e venda em comanda).
- **Entrada:** Nome do produto, SKU/código de barras, tipo (`venda`, `consumo_interno`, `ambos`), unidade, preço de custo, preço de venda, saldo atual, estoque mínimo e metadados fiscais opcionais para futura NFC-e/NF-e (NCM, CEST, CFOP padrão, origem da mercadoria e alíquota ICMS/PIS/COFINS referencial).
- **Fluxo principal e regras:** Toda alteração de saldo gera registro imutável em `StockMovement` (`entrada_compra`, `saida_venda_comanda`, `saida_consumo_interno`, `ajuste_inventario`, `estorno_comanda`). Não é permitido saldo negativo: ao fechar comanda com item de produto cujo `saldo_atual < quantidade_vendida`, a transação é abortada com erro claro. Produtos com `saldo_atual <= estoque_minimo` são sinalizados com alerta de reposição.
- **Critério de aceite:** Dado um produto com saldo 2 e estoque mínimo 2, quando fechar uma comanda vendendo 3 unidades, o fechamento é bloqueado; quando vender 1 unidade, o saldo passa para 1, registra-se a movimentação vinculada à comanda e o alerta de estoque mínimo permanece ativo.
- **Prioridade:** Essencial | **Decisões:** `DEC-001`, `DEC-003` | **Situação:** Em revisão.

### RF-009: Caixa Diário e Geração Automática de Comissões no Pagamento
- **Ator e organização:** `gestor` e `recepcionista` (operação de caixa); `profissional` (consulta apenas das próprias comissões).
- **Entrada:** Abertura de caixa (saldo inicial), pagamentos de comandas (`dinheiro`, `pix`, `cartao_credito`, `cartao_debito`, aceitando pagamento dividido/misto), lançamentos avulsos de entrada/saída (despesas do salão) e fechamento de caixa (conferência de valores).
- **Fluxo principal e regras:** A comissão do profissional **nunca** é gerada apenas pela marcação do agendamento, mas **exclusivamente quando a comanda é fechada/paga no caixa** (em mesma transação atômica). Para cada item de serviço pago na comanda, o sistema aplica o percentual específico do par `(profissional, servico)` ou, se inexistente, o percentual padrão do serviço, criando um registro `CommissionEntry` (`pendente_repasse` / `pago_ao_profissional`). Se uma comanda paga for estornada pelo gestor, a comissão e a baixa de estoque correspondentes são estornadas na mesma transação.
- **Critério de aceite:** Dada uma comanda aberta de R$ 200,00, enquanto não for paga no caixa, nenhuma comissão consta como devida; ao registrar o pagamento integral no caixa, a comanda muda para `fechada_paga`, o lançamento financeiro entra no caixa e a comissão exata do profissional é criada.
- **Prioridade:** Essencial | **Decisões:** `DEC-001`, `DEC-002` | **Situação:** Em revisão.

### RF-010: Notificações e Lembretes Assíncronos por E-mail (Celery + RabbitMQ + Redis)
- **Ator e organização:** Sistema (workers Celery e Celery Beat) operando no contexto do salão do agendamento.
- **Fluxo principal e regras:** Disparo assíncrono usando o sistema nativo de e-mails do Django (configurado via `.env -> settings.py`) para: (1) confirmação de novo agendamento; (2) aviso de cancelamento/remarcação; (3) tarefa agendada (Celery Beat) que envia lembrete de agendamentos futuros próximos. Cada disparo grava chave de idempotência e status no banco/Redis para impedir envio duplicado em caso de retry da fila. Visibilidade operacional das tasks no Django Admin via `dj-celery-panel`.
- **Critério de aceite:** Dado um agendamento confirmado, quando a task de lembrete rodar duas vezes para a mesma janela, apenas 1 e-mail de lembrete é enviado ao cliente e o histórico registra a execução idempotente.
- **Prioridade:** Essencial | **Situação:** Em revisão.

### RF-011: Dashboard Gerencial e Exportação de Relatórios Privados em PDF (ReportLab/PyPDF)
- **Ator e organização:** `gestor` (todos os relatórios e indicadores do salão), `recepcionista` (fechamento de caixa diário) e `profissional` (apenas próprio demonstrativo de comissões).
- **Fluxo principal e regras:** Dashboard com indicadores filtráveis por período (faturamento bruto/líquido, ticket médio, total de comissões geradas, agendamentos por status/taxa de no-show e produtos abaixo do estoque mínimo). Geração de relatórios em PDF via `ReportLab`/`PyPDF`: (1) Extrato de Comissões por Profissional e Período; (2) Relatório de Fechamento de Caixa; (3) Posição e Movimentação de Estoque. Download protegido por view autenticada que valida o `salon` e o perfil do solicitante.
- **Critério de aceite:** Quando um profissional tentar baixar o PDF de comissões de outro profissional ou o relatório geral de caixa do salão, recebe `403 Forbidden`.
- **Prioridade:** Essencial | **Decisões:** `DEC-001`, `DEC-002` | **Situação:** Em revisão.

### RF-012: Assistente Gerencial Interno de IA (LangChain + LangGraph)
- **Ator e organização:** `gestor` e `recepcionista` autenticados no seu salão.
- **Fluxo principal e regras:** Chat interno onde o usuário faz perguntas em linguagem natural sobre a operação do seu salão (ex.: *"Qual o faturamento desta semana e quanto tenho de comissão pendente por profissional?"*, *"Quais horários estão vagos amanhã à tarde?"*, *"Quais produtos estão com estoque baixo?"*, *"Quais clientes não agendam há 60 dias?"*). O grafo `LangGraph` utiliza *tools* somente-leitura que recebem o `salon_id` injetado diretamente do contexto de servidor autenticado (nunca confiando em `salon_id` vindo do prompt do LLM) e respeitam as permissões do perfil (`recepcionista` não acessa tools restritas exclusivamente ao `gestor`). O identificador do modelo (`modelo_llm`) é lido via variável de ambiente (`.env`), permanecendo parametrizável (`a_definir`).
- **Critério de aceite:** Dada uma pergunta no chat do Salão A tentando induzir o agente a consultar dados do Salão B (prompt injection), as tools executam queries estritamente filtradas por `salon_id = Salão A` e nenhum dado externo é exposto.
- **Prioridade:** Essencial | **Decisões:** `DEC-001`, `DEC-002` | **Situação:** Em revisão.

### RF-013: Preparação Estrutural e Contrato Desacoplado para Futura Emissão Fiscal (NFS-e / NFC-e)
- **Ator e organização:** `gestor` e `recepcionista` (no fechamento/visualização da comanda) e futura camada de integração fiscal.
- **Fluxo principal e regras:** Ao fechar/pagar uma comanda (`RF-009`), o sistema consolida os dados fiscais da operação em um registro preparatório `FiscalDocumentRecord` vinculado ao salão e à comanda, separando base de serviços (para futura NFS-e municipal, incluindo rateio/retenção de Salão-Parceiro quando configurado no salão e no profissional) e base de produtos vendidos (para futura NFC-e estadual), com estados fiscais (`nao_solicitada`, `pendente_integracao_futura`, `pronta_para_envio`, `emitida`, `erro_emissao`, `cancelada`), campos para chave de acesso/número/série/URL de XML-DANFE e log de tentativas. No MVP, o sistema implementa a interface de serviço (`FiscalGatewayAdapter`) com implementação *NoOp/Stub* documentada, sem chamada externa bloqueante.
- **Critério de aceite:** Ao pagar uma comanda contendo serviços e produtos, o sistema gera/atualiza a estrutura fiscal associada com os snapshots de CNPJ do salão, CPF do cliente (se informado) e códigos fiscais dos itens, permitindo futura emissão via task Celery sem alterar o esquema das tabelas financeiras.
- **Prioridade:** Essencial (estrutura de dados e contrato no MVP) / Futuro (conector externo de transmissão) | **Decisões:** `DEC-003` | **Situação:** Em revisão.

---

## 4. Requisitos Não Funcionais Verificáveis (RNF-001 a RNF-006)

| ID | Categoria | Jornada / Componente Afetado | Métrica e Meta Acordada | Condições e Método de Verificação |
|---|---|---|---|---|
| **RNF-001** | Segurança e Multi-tenancy | Todas as views, APIs, tasks Celery, PDFs e tools de IA | `0` vazamentos entre salões; `403` ou `404` em acessos cruzados ou sem permissão de perfil | Suíte automatizada de testes de isolamento cross-tenant e permissões por papel (`DEC-001`) + inspeção manual |
| **RNF-002** | Desempenho e Concorrência | Consulta de agenda, criação de agendamento e fechamento de comanda/estoque | Tempo de resposta `<= 2s (p95)` até 50 salões simultâneos; `0` *double-bookings* ou saldos negativos sob concorrência | Transações atômicas com bloqueio de linha (`select_for_update`), índices compostos por `(salon_id, start_time)` e testes de concorrência |
| **RNF-003** | Usabilidade, Idioma e Design | Painel interno (Desktop/Mobile) e Página Pública do Cliente (Mobile-first) | Interface 100% em `pt-BR`, fuso `America/Sao_Paulo`, fiel aos tokens da pasta `design_system/` fornecida pelo desenvolvedor | Inspeção visual em larguras Desktop (1366px+) e Mobile (375px–430px) seguindo catálogo extraído do `design_system/` |
| **RNF-004** | Recuperação e Continuidade | PostgreSQL e volumes de mídia em produção (VPS Ubuntu + Docker Swarm) | `RPO <= 24h` (backup diário automatizado) e `RTO <= 2h` (restauração em VPS única) | Execução do procedimento de dump e restore documentado no runbook de operação com medição de tempo pelo usuário |
| **RNF-005** | Privacidade, Segredos e Arquivos | Relatórios PDF, dados de clientes e credenciais de produção | `0` segredos versionados; PDFs servidos apenas após validação de autenticação/tenant; Docker Secrets no Swarm (`CLOUDFLARE_DNS_API_TOKEN`, DB, LLM) | Verificação de `.env.example`, configuração de Docker Secrets e tentativa de acesso anônimo/cruzado a endpoints de relatórios |
| **RNF-006** | Manutenibilidade, Docs e Demo | Documentação viva (`docs/` com MkDocs + Mermaid) e carga de demonstração | Documentação atualizada a cada sprint; comando `seed_demo_data` populando múltiplos salões e cenários temporais | Execução local do comando de carga sintética e renderização do MkDocs com diagramas Mermaid |

---

## 5. Matriz de Rastreabilidade Preliminar

| Requisito | Decisões Associadas | Módulo / App Candidato | Forma de Evidência Prevista |
|---|---|---|---|
| `RF-001`, `RF-002` | `DEC-001`, `DEC-002`, `DEC-003` | `base`, `accounts`, `salons` | Testes de autenticação/vínculo de salão e telas de expediente |
| `RF-003`, `RF-004` | `DEC-002`, `DEC-003` | `catalog`, `clients` | Testes de regra de comissão por profissional e isolamento de clientes |
| `RF-005`, `RF-006` | `DEC-001`, `DEC-002` | `scheduling` | Testes automatizados de colisão de horário e prazo de cancelamento público |
| `RF-007`, `RF-008`, `RF-009` | `DEC-001`, `DEC-002`, `DEC-003` | `orders`, `inventory`, `finance` | Testes transacionais de pagamento -> comissão + baixa de estoque sem saldo negativo |
| `RF-010`, `RF-011`, `RF-012`, `RF-013` | `DEC-001`, `DEC-002`, `DEC-003` | `notifications`, `reports`, `ai_assistant`, `fiscal` | Testes de idempotência Celery, proteção de PDF, escopo de tools IA e registro fiscal |
