---
versao: 1.0.0
data_editorial: 2026-11-12
tipo: prompt_bruto_do_projeto
projeto: SPS (Sistema Para Salões)
estado: preenchido_para_refinamento
origem_template: "../../guia_desenvolvimento_ia/04_prompts_e_prd/prompt_inicial_bruto_parametrizavel.md"
---

# Prompt Inicial Bruto Preenchido — SPS (Sistema Para Salões)

## Registro de Preenchimento e Parâmetros

- **Projeto:** SPS (Sistema Para Salões) — Slug: `sps`
- **Stack confirmada:** Python `3.13.6`, Django `5.2 LTS`, PostgreSQL, Celery, RabbitMQ, Redis, `dj-celery-panel`, LangChain, LangGraph, ReportLab, PyPDF, MkDocs (com Mermaid), Docker Compose e Docker Swarm + Traefik + Cloudflare.
- **Decisões incorporadas:** `DEC-001` (testes automatizados para fluxos críticos + revisão manual), `DEC-002` (multi-tenant por salão com vínculo único de usuário interno) e `DEC-003` (preparação estrutural para futura emissão de notas fiscais NFS-e/NFC-e).
- **Parâmetros pendentes mantidos explícitos:** `dominio_principal = a_definir`, `registry_imagem = a_definir`, `arquivo_design_system = a_definir`, `modelo_llm = a_definir`.

---

## Texto do Prompt Inicial Bruto

````text
Vou desenvolver SPS (Sistema Para Salões), para centralizar e profissionalizar a
gestão operacional, financeira, de estoque e de agendamento de salões de beleza
independentes em modelo SaaS multi-tenant, com a stack aprovada: Python 3.13.6,
Django 5.2 LTS e componentes confirmados do baseline.

# TECH SPECS DO SISTEMA
- Use a versão Python 3.13.6 validada para este projeto e Django 5.2 LTS.
- Ambiente virtual em .venv na raiz do projeto (pasta sps/).
- requirements.txt sempre atualizado na raiz do projeto.
- Arquitetura de tenant: Multi-tenant compartilhado com isolamento estrito por
organização (DEC-002). Organização significa "salão" (Salon) neste produto.
Cada usuário interno (gestor, recepcionista, profissional) pertence a um único
salão fixo (além do superadmin_saas da plataforma). Clientes, catálogo de
serviços, agenda, comandas, caixa, comissões, estoque e documentos fiscais
pertencem isoladamente a cada salão. Proteja todos os arquivos privados e PDFs
validando autenticação e pertencimento ao salão.
- O sistema de autenticação será o sistema nativo de usuários e autenticação do
Django.
- Sistema de disparo de emails usando o próprio sistema de emails do Django,
configurando os dados de email no .env -> settings.py.
- O login usa e-mail. Defina o usuário customizado e AUTH_USER_MODEL antes
das primeiras migrations de um projeto novo; não reinicialize dados existentes.
- As entidades/domains do sistema devem ser separadas em apps do Django,
para isolar as responsabilidades.
- O código deve ser simples, sempre usar aspas simples e seguir os padrões da
PEP08.
- O código do projeto deve ser em inglês.
- Apps do Django devem ficar na raiz do projeto.
- O pacote de configuração principal do Django deve se chamar core.
Um pacote de configuração não é automaticamente um app instalado.
- O app com recursos base e compartilhados do projeto deve se chamar "base".
- Toda informação da interface deve usar português brasileiro.
Fuso de negócio confirmado: America/Sao_Paulo.
- Toda tabela/model deve ter os campos created_at e updated_at.
- Política de validação e testes (DEC-001): em substituição consciente à regra
original de não implementar testes, o projeto DEVE implementar testes
automatizados para os fluxos críticos (isolamento multi-tenant entre salões,
permissões por perfil, bloqueio de conflito de horário na agenda, cálculo de
comissão apenas no fechamento/pagamento da comanda, bloqueio de saldo negativo
de estoque e escopo de tenant nas tools de IA), mantendo a verificação manual
obrigatória ao final de cada sprint.
- Credenciais de desenvolvimento ficam em .env local e são lidas pelo
settings.py. Produção usa configuração e secrets separados, conforme o runbook.
- Mantenha apenas 1 arquivo settings.py do Django.
- Use banco de dados PostgreSQL no sistema.
- Use Docker e Docker Compose localmente. O baseline de produção usa Docker
Swarm em VPS com DNS Cloudflare. Destino para dominio_principal (a_definir),
registrando qualquer adaptação aprovada antes de gerar comandos de deploy.
- Para execução de tarefas pesadas assíncronas/em segundo plano, use o Celery
integrado ao Django (envio de e-mails de confirmação/cancelamento, lembretes
de agendamento, tarefas futuras de integração fiscal e processamento de IA
quando aplicável).
- Use RabbitMQ como sistema de mensageria do Celery.
- Use a biblioteca dj-celery-panel para visualização das tasks do Celery no
admin do Django.
- Os serviços Docker devem ser: o app django, postgresql do app, celery worker,
celery beat, rabbitmq para o celery, traefik como web server/load balancer.
- Use um serviço Redis adicional no stack como result backend do Celery e cache
do app, além do RabbitMQ que é o broker.
- Registry: a_definir (ex.: ghcr.io). Publicação da imagem e deploy são
executados pelo usuário conforme runbook revisado; Git/GitHub nunca são
executados pela IA. O deploy Swarm deve prever autenticação de pull quando a
imagem for privada.
- Defina persistência para PostgreSQL, Redis, RabbitMQ, media e certificados.
A estratégia de staticfiles deve ser decidida explicitamente antes do deploy.
- No baseline, use redes traefik_public, sps_internal e sps_egress. A primeira
atende ingresso HTTP; a segunda usa internal: true; a terceira atende serviços
que precisam acessar APIs externas. App e Traefik compartilham a rede de
ingresso. Banco, broker e Redis não publicam portas na internet. Worker/beat
usam as redes necessárias às suas tarefas.
- Para TLS wildcard, inclua domínio raiz e wildcard no certificado e use DNS-01.
No Cloudflare, valide permissões de leitura da zona e edição de DNS limitadas
à zona necessária.
- O token da API do Cloudflare nunca deve ficar em texto puro no compose/stack
nem no .env versionado. Ele deve ser armazenado como um Docker Secret do Swarm
(nome do secret: CLOUDFLARE_DNS_API_TOKEN) e lido pelo Traefik via convenção de
arquivo CF_DNS_API_TOKEN_FILE=/run/secrets/CLOUDFLARE_DNS_API_TOKEN. As demais
credenciais sensíveis de produção também devem preferir Docker Secrets.
- Separe .env de desenvolvimento e configuração de produção. Não versione
segredos. Use leitura compatível com arquivos de Docker Secrets quando adotados.
- ALLOWED_HOSTS e CSRF_TRUSTED_ORIGINS devem ser lidos do .env como listas
separadas por vírgula (via django-environ).
- Em produção (DEBUG=False), como o TLS é terminado no Traefik e o app recebe
HTTP interno com o header X-Forwarded-Proto, o settings.py deve configurar
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https') para evitar loop de
redirect atrás do proxy, e isentar a rota de healthcheck do redirect HTTPS via
SECURE_REDIRECT_EXEMPT, conforme rota realmente implementada.
- Diferencie liveness leve de readiness de dependências; implemente esperas
limitadas e retry para dependências necessárias e crie o comando wait_for_db
antes de referenciá-lo em entrypoints.
- Worker e beat não executam migrations nem collectstatic.
- Planeje scripts/deploy.sh sem chamadas Git/GH, diretas ou indiretas.
- Planeje backup de PostgreSQL e media com retenção e restauração verificada.
- Sempre que possível, o projeto deve usar Class Based Views, classes,
funções e recursos nativos do Django.
- Caso use signals no projeto, eles devem ficar em um arquivo signals.py
dentro da app correspondente do signal.
- Use Reportlab e PyPDF para relatórios em PDF (extrato de comissões,
fechamento de caixa e movimentação de estoque).
- Pasta docs/ no sistema com toda a documentação sempre atualizada do sistema,
com MKDocs para servir a documentação online, incluindo suporte a renderizar
mermaid das documentações.
- Um django command (seed_demo_data) que faz uma carga inicial de dados fakes
no sistema, cobrindo múltiplos salões, profissionais, serviços, agendamentos em
diversas datas, comandas pagas, comissões, estoque e registros fiscais
preparatórios, visando fazer demonstrações do sistema.
- O desenvolvedor fornecerá design_system/ antes da sprint de interface/frontend
(arquivo_design_system: a_definir). Não invente componentes existentes nem
busque outro design silenciosamente.
- Para o Assistente Gerencial Interno de IA, use LangChain e LangGraph conforme
stack aprovada. Modelo de IA (modelo_llm): a_definir, lido via variável de
ambiente no .env e sujeito à verificação de disponibilidade e acesso.

# REQUISITOS FUNCIONAIS DO SISTEMA
- RF-001: Gestão de Salões (Tenants), horários de funcionamento por dia da
semana, feriados, antecedência mínima de cancelamento público e metadados
fiscais do salão (CNPJ, IM, IE, Regime Tributário, código IBGE e indicador de
Salão-Parceiro).
- RF-002: Autenticação por e-mail (AUTH_USER_MODEL customizado antes da 1ª
migration) e gestão de equipe por salão (vínculo fixo de 1 salão por usuário
interno nos perfis gestor, recepcionista e profissional, além do superadmin_saas
global), incluindo expediente individual e bloqueios de agenda do profissional.
- RF-003: Catálogo de serviços por salão com duração em minutos, preço base,
status, profissionais habilitados, comissão padrão do serviço (%), exceção de
comissão específica por (profissional, serviço) e metadados fiscais opcionais
de serviço (código de serviço LC 116, CNAE, alíquota ISS referencial).
- RF-004: Cadastro e histórico de clientes isolado por salão, com prevenção de
duplicidade no mesmo salão e campos fiscais opcionais para tomador de nota
fiscal (CPF/CNPJ e endereço completo).
- RF-005: Agenda inteligente interna suportando múltiplos serviços no mesmo
agendamento (somando durações e valores), com validação transacional estrita
contra conflitos de horário por profissional, respeito ao expediente/bloqueios e
estados (agendado, confirmado, em_atendimento, concluido, cancelado,
nao_compareceu).
- RF-006: Autoagendamento e cancelamento público pelo cliente via link do salão
(/s/<slug_salao>/), exibindo horários reais disponíveis para os serviços
selecionados e permitindo cancelamento pelo cliente apenas dentro da
antecedência mínima configurada pelo salão.
- RF-007: Comandas de atendimento vinculadas a agendamento ou avulsas, suportando
múltiplos serviços executados (por um ou mais profissionais) e venda de produtos
do estoque, com controle de descontos e estados (aberta, fechada_paga, cancelada).
- RF-008: Controle de estoque de produtos isolado por salão (venda e consumo
interno), com baixa automática ao fechar comanda, registro de entradas, consumo
interno e ajustes, alerta de estoque mínimo, bloqueio de venda quando saldo for
insuficiente e metadados fiscais opcionais de produto (NCM, CEST, CFOP, origem
e alíquotas referenciais).
- RF-009: Caixa diário (abertura, entradas, saídas, fechamento e múltiplas formas
de pagamento) e geração automática de comissões dos profissionais exclusivamente
no momento em que a comanda é fechada/paga no caixa (aplicando percentual
específico do profissional no serviço ou, na falta deste, o percentual padrão
do serviço), com reversão atômica em caso de estorno.
- RF-010: Notificações e lembretes assíncronos por e-mail nativo do Django via
Celery, RabbitMQ e Redis (confirmação, cancelamento e lembrete periódico via
Celery Beat) com controle de idempotência.
- RF-011: Dashboard gerencial do salão e exportação de relatórios privados em
PDF com ReportLab/PyPDF (comissões por profissional/período, fechamento de caixa
e estoque), protegidos por validação de tenant e perfil.
- RF-012: Assistente Gerencial Interno de IA (LangChain + LangGraph) para gestor
e recepcionista consultarem indicadores de agenda, faturamento, comissões,
clientes inativos e alertas de estoque do próprio salão, com tools restritas ao
salon_id da sessão autenticada.
- RF-013: Preparação estrutural e contrato desacoplado (FiscalDocumentRecord +
FiscalGatewayAdapter stub) para futura integração de emissão de notas fiscais
(NFS-e para serviços, incluindo rateio de Salão-Parceiro quando aplicável, e
NFC-e para produtos vendidos na comanda), consolidando os snapshots fiscais no
fechamento da comanda sem bloquear o MVP com chamadas externas à SEFAZ/Prefeitura.

# REQUISITOS NÃO FUNCIONAIS DO SISTEMA
- RNF-001 (Segurança e Multi-tenancy): Isolamento absoluto entre salões em
queries, views, relatórios PDF, tasks Celery e tools de IA (403/404 em acessos
indevidos), validado por testes automatizados (DEC-001).
- RNF-002 (Desempenho e Concorrência): Páginas de agenda e comanda respondendo
em até 2s (p95) para carga de até 50 salões simultâneos; bloqueio transacional
contra double-booking de agenda e saldo negativo de estoque.
- RNF-003 (Usabilidade e Design): Interface em pt-BR (America/Sao_Paulo),
responsiva para Desktop (recepção/gestão) e Mobile (profissionais e agendamento
público do cliente), seguindo design_system/ fornecido pelo desenvolvedor.
- RNF-004 (Recuperação): Backup diário automatizado (RPO <= 24h) e restauração
documentada em VPS única em até 2h (RTO <= 2h).
- RNF-005 (Privacidade e Segredos): Nenhum segredo versionado; uso de Docker
Secrets no Swarm; relatórios PDF e arquivos privados inacessíveis sem validação
de autenticação e tenant.
- RNF-006 (Documentação e Demonstração): Documentação viva em docs/ servida via
MkDocs com Mermaid e comando seed_demo_data cobrindo múltiplos cenários.

# TAREFA
Gere o PRD desse projeto (Product Requirement Document), em formato de arquivo
markdown modularizado em docs/01_planejamento/, incluindo visão, escopo, RF/RNF,
arquitetura multi-tenant, preparação fiscal desacoplada, guia de deploy em VPS
Ubuntu com Docker Swarm/Traefik/Cloudflare DNS-01 e sprints detalhadas em
checklist, respeitando todas as decisões registradas.

# IMPORTANTE
O SCSI é referência de arquitetura e estudo, não de requisitos do meu produto.
Antes de gerar o PRD definitivo, conclua o refinamento deste prompt e minha
revisão do texto. Depois de gerar o PRD, peça minha revisão e aprovação.
Não escreva código de negócio antes dessa aprovação.
Execute uma sprint por solicitação. Revise, corrija e entregue para minha
ação manual de Git/GitHub. Não execute nenhum comando ou ação nesses serviços.
````
