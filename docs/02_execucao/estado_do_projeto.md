---
versao: 1.0.0
data_editorial: 2026-11-12
tipo: registro_de_estado
projeto: SPS (Sistema Para Salões)
estado: aguardando_acao_git_do_usuario
---

# Estado do Projeto e Passagens de Etapa — SPS (Sistema Para Salões)

## 1. Finalidade deste Registro

Manter a fonte única de verdade sobre a etapa atual do **SPS (Sistema Para Salões)**,
as decisões efetivamente aprovadas pelo desenvolvedor, as verificações técnicas
realizadas no ambiente local e a próxima ação permitida dentro do workflow. Nenhuma
sessão da IA deve avançar para geração de PRD ou implementação de sprints sem conferir
este arquivo e respeitar as condições de passagem.

---

## 2. Registro Estruturado de Estado Atual

```json
{
  "nome_projeto": "SPS (Sistema Para Salões)",
  "slug_projeto": "sps",
  "etapa_atual": "aguardando_acao_git_do_usuario",
  "versao_prd": "1.0.0",
  "aprovacao_prd": {
    "aprovado": true,
    "autor": "desenvolvedor",
    "data": "2026-11-12",
    "evidencia": "Aprovo o PRD versao 1.0.0 do SPS e solicito a execucao exclusiva da Sprint 01."
  },
  "preparacao_tecnica": {
    "stack_confirmada": true,
    "ferramentas_verificadas": true,
    "venv_criada": true
  },
  "sprint_solicitada": "Sprint 08",
  "sprint_em_execucao": null,
  "bloqueios": [],
  "ultima_entrega": "Sprint 08 concluida, revisada e verificada (50 testes automatizados aprovados; Celery, dj-celery-panel, notifications e reports com PDF entregues; evidencias em docs/02_execucao/evidencias_da_sprint_008.md).",
  "git_executado_pela_ia": false,
  "acao_git_informada_pelo_usuario": "usuario_solicitou_sprint_08_recomendacao_de_commit_mantida",
  "proxima_acao_permitida": "revisao_e_commit_pelo_usuario_ou_solicitacao_da_sprint_09"
}
```

---

## 3. Inventário do Ambiente Local Verificado

Conforme diretriz de [`instalacao_python_docker_git_github_cli.md`](../../guia_desenvolvimento_ia/02_stack_e_preparacao/instalacao_python_docker_git_github_cli.md),
foi realizada inspeção somente-leitura de Python e Docker (sem executar nenhum comando
de Git ou GitHub CLI):

```text
Sistema operacional e versão: Windows (PowerShell)
Arquitetura: 64-bit
Terminal utilizado: PowerShell
Python disponível e caminho: Python 3.13.6 (C:\Users\lucas\AppData\Local\Programs\Python\Python313\python.exe)
Python aprovado para o projeto: Python 3.13.6
Django aprovado para o projeto: Django 5.2 LTS
Docker Engine ou Docker Desktop: Ausente no PATH atual (C:\Program Files\Docker não encontrado)
Docker Compose disponível: Pendente de instalação/ativação do Docker Desktop pelo desenvolvedor
Git: Sob controle e confirmação exclusiva do usuário (não consultado pela IA)
GitHub CLI: Sob controle e confirmação exclusiva do usuário (não consultado pela IA)
Pendências de instalação local: Instalar/ativar Docker Desktop no Windows antes da sprint de infraestrutura/containers
```

---

## 4. Histórico de Passagens de Etapa

| Data | Etapa Anterior | Nova Etapa | Evidência / Decisão do Desenvolvedor |
|---|---|---|---|
| `2026-11-12` | `ideia_recebida` | `stack_em_confirmacao` | Solicitação inicial para sistema de salão de beleza seguindo `guia_de_entrada_para_ia.md`. |
| `2026-11-12` | `stack_em_confirmacao` | `requisitos_em_descoberta` | Confirmação de replicação do baseline (`Python 3.13.6`, `Django 5.2 LTS`, PostgreSQL, Celery, RabbitMQ, Redis, LangChain/LangGraph, Docker) com testes automatizados para fluxos críticos (`DEC-001`). |
| `2026-11-12` | `requisitos_em_descoberta` | `prompt_em_refinamento` | Definição do nome `SPS (Sistema Para Salões)`, fechamento das Rodadas 1 a 5 de RF/RNF, inclusão da preparação estrutural para emissão de notas fiscais (`DEC-003` / `RF-013`) e escolha do Refinamento Assistido (Caminho B). |
| `2026-11-12` | `prompt_em_refinamento` | `aguardando_revisao_prd` | Desenvolvedor aprovou o prompt refinado ("Aprovado, gerar o PRD") e o PRD modular `v1.0.0` foi gerado em `sps/docs/01_planejamento/`. |
| `2026-11-12` | `aguardando_revisao_prd` | `sprint_em_execucao` | Desenvolvedor aprovou o PRD `v1.0.0` e solicitou explicitamente a `Sprint 01`. |
| `2026-11-12` | `sprint_em_execucao` | `aguardando_acao_git_do_usuario` | `Sprint 01` implementada, revisada e verificada com 12 testes automatizados aprovados ([`evidencias_da_sprint_001.md`](evidencias_da_sprint_001.md)). |
| `2026-11-12` | `aguardando_acao_git_do_usuario` | `aguardando_acao_git_do_usuario` | Desenvolvedor solicitou `Sprint 02` ("Execute a sprint 02"); `Sprint 02` implementada, revisada e verificada com 21 testes automatizados aprovados ([`evidencias_da_sprint_002.md`](evidencias_da_sprint_002.md)). |
| `2026-11-12` | `aguardando_acao_git_do_usuario` | `aguardando_acao_git_do_usuario` | Desenvolvedor solicitou `Sprint 03` ("Pode iniciar a sprint 03"); `Sprint 03` implementada, revisada e verificada com 26 testes automatizados aprovados ([`evidencias_da_sprint_003.md`](evidencias_da_sprint_003.md)). |
| `2026-11-13` | `aguardando_acao_git_do_usuario` | `aguardando_acao_git_do_usuario` | Desenvolvedor solicitou `Sprint 04` ("Pode iniciar a sprint 04"); `Sprint 04` implementada, revisada e verificada com 30 testes automatizados aprovados ([`evidencias_da_sprint_004.md`](evidencias_da_sprint_004.md)). |
| `2026-11-13` | `aguardando_acao_git_do_usuario` | `aguardando_acao_git_do_usuario` | Desenvolvedor forneceu `sps/design_system/refs/` e solicitou `Sprint 05`; `Sprint 05` implementada, revisada e verificada com 34 testes automatizados aprovados ([`evidencias_da_sprint_005.md`](evidencias_da_sprint_005.md)). |
| `2026-11-13` | `aguardando_acao_git_do_usuario` | `aguardando_acao_git_do_usuario` | Desenvolvedor solicitou `Sprint 06`; `Sprint 06` implementada, revisada e verificada com 41 testes automatizados aprovados ([`evidencias_da_sprint_006.md`](evidencias_da_sprint_006.md)). |
| `2026-11-18` | `aguardando_acao_git_do_usuario` | `aguardando_acao_git_do_usuario` | Desenvolvedor solicitou `Sprint 07`; `Sprint 07` implementada, revisada e verificada com 46 testes automatizados aprovados ([`evidencias_da_sprint_007.md`](evidencias_da_sprint_007.md)). |
| `2026-11-18` | `aguardando_acao_git_do_usuario` | `aguardando_acao_git_do_usuario` | Desenvolvedor solicitou `Sprint 08`; `Sprint 08` implementada, revisada e verificada com 50 testes automatizados aprovados ([`evidencias_da_sprint_008.md`](evidencias_da_sprint_008.md)). |

---

## 5. Mapa dos Documentos Ativos do Projeto (`sps/`)

| Caminho do Arquivo | Situação | Papel no Workflow |
|---|---|---|
| [`sps/parametros_do_projeto.json`](../../parametros_do_projeto.json) | Atualizado | Parâmetros editáveis, variáveis `a_definir` (`null`) e flags de controle. |
| [`sps/docs/01_planejamento/requisitos_do_projeto.md`](../01_planejamento/requisitos_do_projeto.md) | Aprovado | Fichas completas de `RF-001` a `RF-013` e `RNF-001` a `RNF-006` com critérios de aceite. |
| [`sps/docs/01_planejamento/prompt_inicial_do_projeto.md`](../01_planejamento/prompt_inicial_do_projeto.md) | Preenchido | Cópia do prompt inicial bruto parametrizado para o SPS. |
| [`sps/docs/01_planejamento/prompt_refinado_do_projeto.md`](../01_planejamento/prompt_refinado_do_projeto.md) | Aprovado | Prompt Refinado aprovado pelo desenvolvedor em `2026-11-12`. |
| [`sps/docs/01_planejamento/prd_do_projeto.md`](../01_planejamento/prd_do_projeto.md) | `prd_aprovado` | Documento central e índice do PRD `v1.0.0` (aprovado em `2026-11-12`). |
| [`sps/docs/01_planejamento/arquitetura_dados_e_seguranca_prd.md`](../01_planejamento/arquitetura_dados_e_seguranca_prd.md) | `prd_aprovado` | Arquitetura Django, modelagem conceitual completa (incluindo fiscal), transações e IA. |
| [`sps/docs/01_planejamento/guia_deploy_vps_swarm_e_operacao_prd.md`](../01_planejamento/guia_deploy_vps_swarm_e_operacao_prd.md) | `prd_aprovado` | Guia passo a passo de deploy em VPS Ubuntu com Docker Swarm, Traefik e Cloudflare DNS-01. |
| [`sps/docs/01_planejamento/sprints_de_implementacao_prd.md`](../01_planejamento/sprints_de_implementacao_prd.md) | `Sprints 01-08 [x]` | Planejamento das 10 sprints com checklists (`Sprints 01 a 08` concluídas). |
| [`sps/docs/01_planejamento/catalogo_design_system.md`](../01_planejamento/catalogo_design_system.md) | Aprovado | Catálogo visual extraído de `sps/design_system/refs/` com auditoria de segurança e tokens. |
| [`sps/docs/03_decisoes/decisoes_arquiteturais_iniciais.md`](../03_decisoes/decisoes_arquiteturais_iniciais.md) | Aprovado | Registro formal de `DEC-001` (Testes), `DEC-002` (Multi-tenant) e `DEC-003` (Fiscal). |
| [`sps/docs/02_execucao/evidencias_da_sprint_001.md`](evidencias_da_sprint_001.md) | Concluído | Evidências, revisão, correção e suíte de 12 testes da `Sprint 01`. |
| [`sps/docs/02_execucao/evidencias_da_sprint_002.md`](evidencias_da_sprint_002.md) | Concluído | Evidências, revisão, correção e suíte acumulada de 21 testes da `Sprint 02`. |
| [`sps/docs/02_execucao/evidencias_da_sprint_003.md`](evidencias_da_sprint_003.md) | Concluído | Evidências, revisão, correção e suíte acumulada de 26 testes da `Sprint 03`. |
| [`sps/docs/02_execucao/evidencias_da_sprint_004.md`](evidencias_da_sprint_004.md) | Concluído | Evidências, revisão, correção e suíte acumulada de 30 testes da `Sprint 04`. |
| [`sps/docs/02_execucao/evidencias_da_sprint_005.md`](evidencias_da_sprint_005.md) | Concluído | Evidências, revisão, correção e suíte acumulada de 34 testes da `Sprint 05`. |
| [`sps/docs/02_execucao/evidencias_da_sprint_006.md`](evidencias_da_sprint_006.md) | Concluído | Evidências, revisão, correção e suíte acumulada de 41 testes da `Sprint 06`. |
| [`sps/docs/02_execucao/evidencias_da_sprint_007.md`](evidencias_da_sprint_007.md) | Concluído | Evidências, revisão, correção e suíte acumulada de 46 testes da `Sprint 07`. |
| [`sps/docs/02_execucao/evidencias_da_sprint_008.md`](evidencias_da_sprint_008.md) | Concluído | Evidências, revisão, correção e suíte acumulada de 50 testes da `Sprint 08`. |
| [`sps/docs/02_execucao/estado_do_projeto.md`](estado_do_projeto.md) | Atualizado | Controle de estado, inventário local e próxima ação permitida. |

---

## 6. Resumo de Decisões Firmes vs. Parâmetros `a_definir`

### Decisões Firmes Aprovadas
1. **Identidade do Produto:** `SPS (Sistema Para Salões)` — diretório raiz do produto em `sps/`.
2. **Arquitetura Multi-tenant (`DEC-002`):** Isolamento estrito por `Salon`. Cada usuário interno (`gestor`, `recepcionista`, `profissional`) pertence a 1 salão fixo; `superadmin_saas` atua no escopo global da plataforma; clientes pertencem isoladamente a cada salão.
3. **Agendamento Híbrido e Prevenção de Conflitos (`RF-005`, `RF-006`):** Suporte a múltiplos serviços no mesmo agendamento (soma de tempos e valores), validação atômica contra colisão de horários do profissional e cancelamento público condicionado à antecedência mínima configurada pelo salão.
4. **Comandas, Caixa e Comissões (`RF-007`, `RF-009`):** Comissões geradas exclusivamente quando a comanda é fechada/paga no caixa, respeitando percentual específico por `(profissional, servico)` ou percentual padrão do serviço.
5. **Estoque de Produtos (`RF-008`):** Isolado por salão, com baixa automática na venda em comanda, lançamentos de consumo interno/ajuste, alerta de estoque mínimo e bloqueio de saldo negativo.
6. **Preparação para Notas Fiscais (`DEC-003`, `RF-013`):** Metadados fiscais em Salão, Profissional, Cliente, Serviço e Produto + geração de `FiscalDocumentRecord` e contrato `FiscalGatewayAdapter` no fechamento da comanda, mantendo transmissão externa como evolução futura.
7. **Qualidade (`DEC-001`):** Testes automatizados obrigatórios para os fluxos críticos + revisão manual por sprint.

### Parâmetros Mantidos como `a_definir`
- `modelo_llm`: `a_definir` (configurável via `.env` para o Assistente Gerencial Interno em `LangChain`/`LangGraph`).
- `dominio_principal` e `registry_imagem`: `a_definir` (serão fixados antes da execução do runbook de deploy em VPS).

---

## 7. Condições de Passagem de Etapa no Ciclo de Vida do SPS

| Estado do Workflow | Condição de Entrada | Saída Necessária para Avançar | Situação no SPS |
|---|---|---|---|
| `ideia_recebida` | Pedido inicial do sistema para salões | Primeiras perguntas de stack e escopo | Concluído |
| `stack_em_confirmacao` | Baseline e restrições discutidos | Escolha registrada pelo desenvolvedor | Concluído |
| `requisitos_em_descoberta` | Rodadas 1 a 5 de RF e RNF | Lacunas impeditivas resolvidas e documentadas | Concluído |
| `prompt_em_refinamento` | Prompt bruto preenchido e proposta assistida gerada | Revisão do `prompt_refinado_do_projeto.md` pelo desenvolvedor | Concluído |
| `prompt_revisado` | Prompt refinado conferido e aceito | Solicitação explícita para gerar o PRD | Concluído |
| `aguardando_revisao_prd` | PRD modular gerado em `docs/01_planejamento/` | Revisão e aprovação explícita de versão identificada do PRD | Concluído (`v1.0.0`) |
| `prd_aprovado` | Versão e evidência de aceite registradas | Solicitação explícita da Sprint 01 | Concluído |
| `sprint_em_execucao` | Sprint específica solicitada pelo desenvolvedor | Implementação restrita ao escopo da sprint | Concluído (`Sprint 01`) |
| `sprint_em_revisao` | Código e testes da sprint executados | Evidências documentadas e falhas corrigidas | Concluído (`Sprint 01`) |
| `aguardando_acao_git_do_usuario` | Sprint revisada e entregue | Desenvolvedor realiza commit/push (ou decide adiar) | **Etapa Atual** |

---

## 8. Protocolo de Retomada e Encerramento de Sessão para o SPS

### Prompt de Retomada de Sessão
```text
Retome o projeto SPS (Sistema Para Salões) lendo sps/docs/02_execucao/estado_do_projeto.md,
sps/parametros_do_projeto.json e os documentos vigentes em sps/docs/01_planejamento/.
Confira a última aprovação registrada e se há alguma sprint explicitamente solicitada.
Inspecione os arquivos relevantes sem executar nenhum comando de Git ou GitHub.
Resuma: etapa atual, decisões firmes (DEC-001 a DEC-003), pendências (a_definir) e próxima
ação permitida. Continue apenas o escopo já autorizado pelo desenvolvedor.
```

### Prompt de Encerramento de Sessão
```text
Atualize sps/docs/02_execucao/estado_do_projeto.md e sps/parametros_do_projeto.json com o
que realmente foi realizado e verificado nesta sessão.
Separe verificações executadas, não executadas e impedidas.
Liste decisões pendentes e identifique a próxima ação que cabe ao desenvolvedor.
Não realize operações de Git/GitHub e não inicie outra etapa ou sprint sem solicitação.
```

---

## 9. Checklist de Passagem para a Próxima Etapa (`aguardando_acao_git_do_usuario` -> `Sprint 09`)

- [x] Pasta do produto (`sps/`) criada separadamente da pasta do guia (`guia_desenvolvimento_ia/`).
- [x] Todos os módulos Markdown em `sps/docs/` possuem entre 150 e 400 linhas.
- [x] PRD `v1.0.0` aprovado explicitamente pelo desenvolvedor.
- [x] `Sprints 01 a 08` implementadas, revisadas e verificadas com 50 testes automatizados aprovados ([`evidencias_da_sprint_008.md`](evidencias_da_sprint_008.md)).
- [x] Nenhum comando `git` ou `gh` foi executado pela IA (`git_executado_pela_ia: false`).
- [ ] **Próximo passo do desenvolvedor:** Revisar a entrega da `Sprint 08`, realizar manualmente o commit/push no Git/GitHub (ou optar por adiar) e solicitar explicitamente a execução da `Sprint 09`.
