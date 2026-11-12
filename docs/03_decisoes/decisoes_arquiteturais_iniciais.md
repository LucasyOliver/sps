---
versao: 1.0.0
data_editorial: 2026-11-12
tipo: registro_de_decisoes
projeto: SPS (Sistema Para Salões)
estado: aprovado_na_descoberta
---

# Decisões arquiteturais iniciais do SPS (Sistema Para Salões)

## Objetivo deste documento

Registrar de forma auditável as decisões arquiteturais e de governança tomadas pelo
desenvolvedor durante as etapas de confirmação da stack e descoberta de requisitos do
**SPS (Sistema Para Salões)**. Conforme o guia operacional, toda divergência consciente
em relação ao baseline original ou definição estrutural que impacte múltiplos módulos
deve possuir contexto, alternativas consideradas, consequências e rastreabilidade para
requisitos e sprints.

---

## DEC-001: Política de validação com testes automatizados para fluxos críticos

```text
Identificador: DEC-001
Título específico: Adoção de testes automatizados para fluxos críticos além da verificação manual
Situação: aprovada
Data: 2026-11-12
Responsável pela decisão: Desenvolvedor
Requisitos que motivam a escolha: RNF-001, RNF-002, RNF-006, RF-005, RF-007, RF-008, RF-009, RF-012
Contexto e restrições:
  O prompt bruto histórico do estudo de referência (SCSI) continha a diretriz "Não implementar
  testes", apoiando-se exclusivamente em revisão manual. Contudo, o módulo de confirmação da
  stack e o módulo de critérios de aceite recomendam discutir explicitamente a automação para
  riscos críticos em sistemas multi-tenant transacionais. O SPS opera múltiplos salões isolados,
  com regras concorrentes de agenda, cálculo de comissões condicionado ao pagamento de comandas,
  baixa de estoque e ferramentas de IA que consultam dados organizacionais.
Opções consideradas:
  1. Manter a política original do baseline sem nenhum teste automatizado.
  2. Implementar testes automatizados focados nos fluxos de alto risco (isolamento entre salões,
     permissões por perfil, conflito de horário na agenda, cálculo de comissão no fechamento da
     comanda, bloqueio de estoque negativo e escopo de tenant nas tools de IA), mantendo a
     verificação manual obrigatória ao fim de cada sprint.
  3. Exigir cobertura automatizada exaustiva de interface e código (100% de cobertura) em todas
     as views e templates.
Decisão adotada:
  Opção 2 — Incluir testes automatizados direcionados aos fluxos críticos de negócio e segurança,
  preservando a revisão e verificação manual obrigatória de cada sprint.
Motivo:
  Reduzir o risco de regressão silenciosa em regras financeiras, concorrência de horários e
  isolamento multi-tenant sem burocratizar o desenvolvimento com testes artificiais de layout.
Consequências favoráveis:
  - Evidência reproduzível de que um salão não acessa nem altera registros de outro salão.
  - Validação determinística da geração de comissões (percentual específico do profissional vs
    percentual padrão do serviço) no momento exato do pagamento da comanda.
  - Detecção imediata de regressões em bloqueios de conflito de agenda e saldo de estoque.
Custos e limitações:
  - Acréscimo controlado de tarefas de teste nas sprints de domínio e segurança.
  - Necessidade de manter os testes atualizados quando regras de negócio mudarem.
Riscos e mitigação:
  - Risco: Testes superficiais que apenas repetem a implementação sem testar casos de borda.
  - Mitigação: Exigir nos critérios de aceite de cada sprint cenários explícitos de acesso
    negado (cross-tenant e perfil sem permissão) e entradas conflitantes.
Arquivos e sprints afetados:
  - `docs/01_planejamento/prompt_inicial_do_projeto.md`
  - `docs/01_planejamento/prompt_refinado_do_projeto.md`
  - `docs/01_planejamento/prd_do_projeto.md`
  - Sprints de fundação multi-tenant, agenda, comandas/caixa, estoque e assistente de IA.
Evidência de aprovação:
  Confirmado pelo desenvolvedor na Etapa 1 (Confirmação Preliminar da Stack, resposta A5).
Condição para reavaliar:
  Se o tempo de execução da suíte crítica comprometer o ciclo de revisão local da sprint.
Decisão que substitui, se houver:
  Substitui a cláusula padrão "Não implementar testes" do template histórico do baseline.
```

---

## DEC-002: Modelo multi-tenant com vínculo único de usuário interno por salão

```text
Identificador: DEC-002
Título específico: Arquitetura multi-tenant compartilhada com vínculo fixo de usuário por salão
Situação: aprovada
Data: 2026-11-12
Responsável pela decisão: Desenvolvedor
Requisitos que motivam a escolha: RF-001, RF-002, RF-004, RNF-001, RNF-005
Contexto e restrições:
  O SPS será oferecido no modelo SaaS para múltiplos salões de beleza independentes. Durante a
  descoberta (Rodada 2 e Rodada 4), avaliou-se como usuários internos (Proprietário/Gestor,
  Recepcionista e Profissional/Especialista) e Clientes Finais se relacionam com cada organização
  (Salão).
Opções consideradas:
  1. Usuário interno vinculado a múltiplos salões via tabela N:N (`Membership`) e clientes com
     conta global compartilhada entre salões.
  2. Usuário interno vinculado a múltiplos salões via tabela N:N, com cadastro de clientes
     isolado por salão.
  3. Cada usuário interno pertence a um único salão fixo (exceto o Superadmin SaaS da plataforma),
     e o cadastro de clientes, serviços, agenda, comandas, caixa e estoque pertence isoladamente
     a cada salão.
Decisão adotada:
  Opção 3 — Vínculo direto e fixo de cada usuário interno a um único salão (`salon_id` no modelo
  de usuário ou perfil operacional 1:1 vinculado ao salão), com isolamento estrito de clientes e
  demais entidades operacionais por salão.
Motivo:
  Reflete a realidade operacional dos salões alvo do MVP, simplifica a experiência de autenticação
  (sem necessidade de tela intermediária de troca de organização no login), reduz a superfície de
  erro em filtros de autorização e garante privacidade da carteira de clientes de cada salão.
Consequências favoráveis:
  - Determinação imediata do `salon` ativo a partir do `request.user` autenticado.
  - Isolamento claro para queries ORM, tarefas Celery, relatórios PDF e tools do LangChain.
  - Clientes agendando pelo link público `/s/<slug_salao>/` têm seus registros vinculados
    exclusivamente àquele salão, evitando vazamento de carteira entre concorrentes.
Custos e limitações:
  - Caso um mesmo profissional trabalhe em dois salões distintos na plataforma no futuro, precisará
    de credenciais (e-mails) distintas no MVP ou de uma migração planejada para vínculo N:N.
Riscos e mitigação:
  - Risco: Esquecimento de filtro por `salon` em listagens, detalhes ou relatórios.
  - Mitigação: Uso de mixins/managers base obrigatórios em `base` e cobertura pela suíte de
    isolamento prevista na DEC-001.
Arquivos e sprints afetados:
  - App `accounts` / `salons` e `base` (mixins de tenant e permissões).
  - Todas as apps de domínio (`catalog`, `clients`, `scheduling`, `orders`, `finance`, `inventory`,
    `reports`, `ai_assistant`).
Evidência de aprovação:
  Confirmado pelo desenvolvedor na Etapa 1 (resposta A2) e Etapa 3 (resposta A1).
Condição para reavaliar:
  Demanda comprovada de redes de franquias onde um mesmo gestor ou profissional alterne entre
  múltiplas unidades com um único login.
Decisão que substitui, se houver:
  Não aplicável (decisão fundacional do projeto).
```

---

## DEC-003: Preparação estrutural e desacoplamento para futura emissão de notas fiscais

```text
Identificador: DEC-003
Título específico: Preparação de dados e contratos fiscais sem acoplamento de emissão no MVP
Situação: aprovada
Data: 2026-11-12
Responsável pela decisão: Desenvolvedor
Requisitos que motivam a escolha: RF-001, RF-003, RF-004, RF-007, RF-008, RF-009, RF-013
Contexto e restrições:
  Em salões de beleza no Brasil, a operação envolve prestação de serviços (sujeita a NFS-e
  municipal e regras como a Lei do Salão-Parceiro, quando aplicável) e venda de produtos de
  estoque (sujeita a NFC-e/NF-e estadual). Integrar diretamente dezenas de prefeituras e SEFAZ
  já no primeiro lançamento atrasaria o MVP e exigiria credenciais/certificados digitais A1 que
  nem todos os salões possuem no primeiro dia. Contudo, refatorar modelos financeiros e de
  comanda depois que o sistema já está em produção gera alto custo de migração.
Opções consideradas:
  1. Ignorar completamente qualquer aspecto fiscal no MVP e remodelar tabelas no futuro.
  2. Tornar a integração com API externa de NFS-e/NFC-e obrigatória e bloqueante para fechar
     comandas já no MVP.
  3. Preparar a estrutura de dados (campos fiscais no Salão, Cliente, Serviço, Produto e Comanda)
     e definir uma camada/contrato de integração assíncrona desacoplada (status fiscal, histórico
     de eventos fiscais e payload padronizado), mantendo o conector externo como evolução futura.
Decisão adotada:
  Opção 3 — Modelagem preparada para emissão fiscal desde o MVP (RF-013), com integração efetiva
  com provedor/gateway fiscal externo classificada como evolução futura planejada.
Motivo:
  Permite que os salões cadastrem desde o início CNPJ, Inscrição Municipal, regime tributário,
  CPF/CNPJ do cliente, códigos de serviço/NCM e fechem comandas gerando um registro de intenção/
  documento fiscal (`FiscalDocumentRecord`) pronto para ser processado por um worker Celery
  quando o adaptador do provedor fiscal for ativado, sem exigir migrations destrutivas futuras.
Consequências favoráveis:
  - Banco de dados e formulários já contemplam os metadados necessários para NFS-e (serviços) e
    NFC-e (produtos vendidos na comanda), inclusive separação entre valor do serviço e retenção/
    parceria quando parametrizado.
  - Arquitetura pronta para disparo assíncrono via Celery (idempotente por comanda) sem travar o
    fechamento do caixa na recepção.
Custos e limitações:
  - Campos fiscais no cadastro de clientes e catálogo devem ser opcionais ou configuráveis por
    salão no MVP para não engessar agendamentos rápidos de balcão.
Riscos e mitigação:
  - Risco: Desenvolvedor ou usuário confundir "preparação estrutural fiscal" com "emissão homologada
    junto à prefeitura/SEFAZ" no MVP.
  - Mitigação: Explicitar na interface e no PRD que o estado fiscal padrão no MVP é
    `nao_emitida` / `aguardando_integracao_futura` e registrar a emissão externa nas exclusões
    do MVP.
Arquivos e sprints afetados:
  - `docs/01_planejamento/requisitos_do_projeto.md` (RF-001, RF-003, RF-004, RF-007, RF-008, RF-013)
  - Modelagem dos apps `salons`, `clients`, `catalog`, `inventory`, `orders` e `finance`.
Evidência de aprovação:
  Solicitado explicitamente pelo desenvolvedor ao aprovar o plano de descoberta ("Sobre o manual
  de RF e RNF deixe preparado para uma futura integração de emissão de notas fiscais").
Condição para reavaliar:
  Quando o provedor/gateway fiscal (ex.: Focus NFe, eNotas, PlugNotas, Nuvem Fiscal) for escolhido
  para implementação da sprint de integração fiscal.
Decisão que substitui, se houver:
  Não aplicável.
```

---

## Resumo de Rastreabilidade das Decisões

| ID | Título Resumido | Situação | Impacto Principal |
|---|---|---|---|
| `DEC-001` | Testes automatizados para fluxos críticos + revisão manual | Aprovada | Sprints de domínio, segurança e aceite |
| `DEC-002` | Multi-tenant por salão com vínculo único de usuário interno | Aprovada | Autenticação, permissões e isolamento ORM |
| `DEC-003` | Preparação estrutural para futura emissão de notas fiscais | Aprovada | Modelos de Salão, Cliente, Catálogo, Estoque e Comanda |
