---
versao: 1.0.0
data_editorial: 2026-11-13
tipo: catalogo_design_system
projeto: SPS (Sistema Para Salões)
estado: aprovado_na_sprint_05
origem_referencia: "sps/design_system/refs/design-system.html"
---

# Catálogo Visual e Tokens do Design System — SPS (Sistema Para Salões)

## 1. Inventário e Auditoria de Segurança de `sps/design_system/refs/`

Em cumprimento à tarefa `S05-T01` e às diretrizes de [`design_system_fornecido_pelo_desenvolvedor.md`](../../../guia_desenvolvimento_ia/08_design_system/design_system_fornecido_pelo_desenvolvedor.md), todos os arquivos presentes em `sps/design_system/refs/` foram inspecionados antes de qualquer alteração nos templates do produto:

| Arquivo em `sps/design_system/refs/` | Tamanho | Natureza Técnica | Decisão de Aproveitamento e Segurança |
|---|---|---|---|
| `design-system.html` | `46,5 KB` | Catálogo HTML estruturado (Seções `00` a `09`: Shell, Tipografia, Cores, Navegação, Dados, UI, Layout e Ícones). | **Fonte Primária de Tokens:** Tokens de cor, tipografia, espaçamento, cartões, tabelas, badges e shell extraídos fielmente. Scripts de telemetria/iframe externos descartados. |
| `index.html` | `12,1 KB` | Captura original da aplicação de referência (*Auth Portal*). | **Fonte Complementar:** Confirma a estrutura real do shell lateral (`w-64`), cabeçalho superior (`header`) e tabela de sessões/eventos. |
| `css2` | `2,9 KB` | Folha `@font-face` da família tipográfica `Inter` (`400`, `500`, `600`, `700`). | **Aproveitado Conceitualmente:** Família `Inter` definida como fonte primária na pilha `font-sans` com fallback seguro de sistema (`system-ui, -apple-system, sans-serif`). |
| `main-BsXTeVfQ.css` | `94,3 KB` | Bundle CSS da ferramenta de prototipação Aura. | **Não Incluído Diretamente:** Contém regras proprietárias do editor externo; substituído por folha limpa do produto (`sps/static/css/sps-design-system.css`). |
| `main-DLZ6GWhB.js` | `1.106 KB` | Bundle JavaScript da plataforma Aura (`aura.build`). | **Rejeitado (Segurança):** Contém código de aplicação terceira, chamadas remotas e instrumentação alheia ao SPS. |
| `iconify-icon.min.js` | `40,1 KB` | Web Component Iconify. | **Não Necessário:** A própria referência utiliza SVGs inline (`20x20`, `stroke="currentColor"`, `stroke-width="2"`), eliminando dependência de runtime JS externo. |
| `logo-aura-gray.svg` | `1,0 KB` | Logotipo da ferramenta geradora. | **Descartado:** Substituído pelo emblema institucional violeta do **SPS** (`w-8 h-8 bg-violet-600 rounded-md`). |

### Registro de Segurança sobre Scripts e Recursos Externos
Durante a inspeção de `index.html` e `design-system.html`, foram identificados scripts de comunicação com `46mjiy.aura.build`, URLs de mídia em `hoirqrkdgbmvpwutwuwj.supabase.co` e imagens externas (`images.unsplash.com`, `cdn.tailwindcss.com`). Conforme regra explícita do guia (*"Revise scripts recebidos antes de executar. Uma página de referência pode conter analytics, chamadas externas ou operações de outra aplicação que não pertencem ao produto"*), **nenhum script externo, CDN dinâmico ou chamada a domínios terceiros foi copiado para os templates Django do SPS**. Todo o Design System foi consolidado localmente em [`sps/static/css/sps-design-system.css`](../../static/css/sps-design-system.css).

---

## 2. Tokens de Cores Extraídos da Referência (Seção 02)

A referência define um **Tema Claro Corporativo (Light Mode)** de alto contraste, com superfície neutra fria (`Gray`) e cor de destaque primária em **Violeta (`Violet 600`)**.

### 2.1 Superfícies e Fundos
| Token / Classe CSS | Hexadecimal | RGB | Papel Visual no SPS |
|---|---|---|---|
| `bg-gray-50` (`--sps-bg-app`) | `#f9fafb` | `rgb(249, 250, 251)` | Fundo geral da aplicação (`body`), cabeçalhos de tabela (`thead`) e caixas de apoio. |
| `bg-white` (`--sps-bg-surface`) | `#ffffff` | `rgb(255, 255, 255)` | Superfície principal de cartões (`cards`), barra lateral (`sidebar`), cabeçalho (`header`) e corpo de tabelas (`tbody`). |
| `bg-violet-50` (`--sps-bg-accent-subtle`) | `#f5f3ff` | `rgb(245, 243, 255)` | Fundo de item de navegação ativo, destaque suave de horário selecionado e banners informativos da marca. |

### 2.2 Marca e Ações Primárias
| Token / Classe CSS | Hexadecimal | RGB | Papel Visual no SPS |
|---|---|---|---|
| `bg-violet-600` (`--sps-primary`) | `#7c3aed` | `rgb(124, 58, 237)` | Botão primário (`CTA`), emblema do logotipo, indicadores principais e seleção ativa no agendamento público. |
| `hover:bg-violet-700` (`--sps-primary-hover`) | `#6d28d9` | `rgb(109, 40, 217)` | Estado `hover`/`focus` de botões primários e texto de navegação ativa (`text-violet-700`). |
| `text-violet-600` | `#7c3aed` | `rgb(124, 58, 237)` | Links de ação em tabelas e cabeçalhos de seção (`hover:text-violet-900` `#4c1d95`). |

### 2.3 Hierarquia de Texto e Bordas
| Token / Classe CSS | Hexadecimal | Papel Visual no SPS |
|---|---|---|
| `text-gray-900` (`--sps-text-primary`) | `#111827` | Títulos de página (`h1`/`h2`), valores de KPIs, nomes de clientes/serviços e células principais. |
| `text-gray-700` (`--sps-text-secondary`) | `#374151` | Rótulos de formulário (`label`), links inativos da navegação lateral e textos de apoio densos. |
| `text-gray-500` (`--sps-text-muted`) | `#6b7280` | Subtítulos, metadados secundários, cabeçalhos de tabela em caixa alta (`uppercase`) e dicas de campo. |
| `border-gray-200` (`--sps-border`) | `#e5e7eb` | Divisórias estruturais de `1px solid` (sidebar, header, linhas de tabela `divide-y` e bordas de cartão). |

### 2.4 Cores Semânticas e Pílulas de Status
| Estado Semântico | Classes na Referência | Fundo (`Hex`) | Texto (`Hex`) | Aplicação no Domínio SPS |
|---|---|---|---|---|
| **Sucesso / Ativo / Confirmado** | `bg-green-100 text-green-800` | `#dcfce7` | `#166534` | Agendamento `confirmado`/`concluido`, serviço ativo, mensagem de sucesso. |
| **Aviso / Pendente / Agendado** | `bg-yellow-100 text-yellow-800` | `#fef9c3` | `#854d0e` | Agendamento `agendado` (aguardando confirmação), feriado parcial, alerta preventivo. |
| **Em Atendimento / Destaque** *(Extensão)* | `bg-violet-100 text-violet-800` | `#ede9fe` | `#5b21b6` | Agendamento `em_atendimento` e perfil do usuário logado. |
| **Erro / Cancelado / Falta** *(Extensão)* | `bg-red-100 text-red-800` | `#fee2e2` | `#991b1b` | Agendamento `cancelado`/`nao_compareceu`, bloqueio de agenda e erros de validação. |

---

## 3. Tipografia e Escala Hierárquica (Seção 01)

- **Família Primária (`font-sans`):** `'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`.
- **Família Monoespaçada (`font-mono`):** `'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` (usada para tokens públicos, códigos fiscais CNPJ/IBGE/LC 116 e horários).

| Nível Tipográfico | Classes Equivalentes | Tamanho / Peso / Entrelinha | Uso Padronizado no SPS |
|---|---|---|---|
| **Page Title (`H1`)** | `text-xl font-semibold text-gray-900` | `20px` (`1.25rem`) / `600` / `28px` | Título principal no cabeçalho superior (`header`) e no topo do portal público `/s/<slug>/`. |
| **Section Heading (`H2`)** | `text-lg font-medium text-gray-900 mb-4` | `18px` (`1.125rem`) / `500` / `28px` | Títulos de cartões, blocos de formulário e seções de listagem. |
| **Metric KPI Value** | `text-3xl font-semibold text-gray-900` | `30px` (`1.875rem`) / `600` / `36px` | Indicadores numéricos em destaque (total de agendamentos, duração estimada, valor total). |
| **Table Header** | `text-xs font-medium text-gray-500 uppercase tracking-wider` | `12px` (`0.75rem`) / `500` / `16px` (`+0.05em`) | Cabeçalhos de colunas em todas as tabelas operacionais (`thead`). |
| **Body Primary** | `text-sm text-gray-900` | `14px` (`0.875rem`) / `400`–`500` / `20px` | Conteúdo padrão de células, descrições e textos operacionais. |
| **Body Secondary / Muted** | `text-sm text-gray-500` / `text-xs text-gray-500` | `14px` ou `12px` / `400` / `20px` | Observações, textos de ajuda (`help_text`), e-mails secundários e carimbos de data/hora. |

---

## 4. Layout, Application Shell e Responsividade (Seções 00, 03 e 07)

### 4.1 Application Shell Interno (`sps/templates/base.html`)
Reproduz a arquitetura exata da Seção `00` de `design-system.html`:
1. **Container Raiz:** `flex h-screen bg-gray-50 font-sans` (com fallback responsivo em telas menores).
2. **Barra Lateral Esquerda (`Sidebar` — Desktop `>= 768px`):**
   - Largura fixa `w-64` (`256px`), fundo `bg-white`, borda direita `border-r border-gray-200`.
   - Topo (`p-6`): Emblema `w-8 h-8 bg-violet-600 rounded-md flex items-center justify-center text-white font-bold` (`S`) + nome `SPS Salões` (`text-xl font-semibold text-gray-800`).
   - Navegação (`nav class="mt-6 px-6 space-y-1"`): Links com ícone SVG `w-5 h-5 mr-3`, espaçamento `px-3 py-2 text-sm font-medium rounded-md`, estado ativo em `bg-violet-50 text-violet-700` e estado padrão em `text-gray-700 hover:bg-gray-100`.
   - Rodapé de Perfil (`px-6 pt-6 mt-6 border-t border-gray-200`): Avatar em iniciais violeta, nome completo (`text-sm font-medium text-gray-700`), papel + salão (`text-xs text-gray-500`) e botão de encerramento de sessão (`Sair`).
3. **Área Principal Direita (`Main Area`):**
   - `flex-1 flex flex-col overflow-hidden`.
   - Cabeçalho Superior (`header class="bg-white border-b border-gray-200"` com `px-6 py-3 flex items-center justify-between`): exibe o título da seção, atalho para o link público do salão (`/s/<slug>/`) e ação primária contextual.
   - Conteúdo Rolável (`main class="flex-1 overflow-y-auto p-6"`): container centralizado (`max-w-7xl mx-auto space-y-6`) para mensagens de feedback, cartões e tabelas.

### 4.2 Portal Público de Autoagendamento (`sps/templates/public_base.html`)
Projetado para clientes finais acessando `/s/<slug_salao>/` em **smartphones (`360px`–`430px`)** ou **desktop (`1280px+`)**:
- Cabeçalho limpo `bg-white border-b border-gray-200` com emblema violeta, nome fantasia do salão (`trade_name`), telefone/endereço e selo de antecedência mínima de cancelamento (`cancellation_min_hours`).
- Container responsivo `max-w-4xl mx-auto px-4 py-6 sm:px-6` com cartões `bg-white rounded-lg shadow p-6`, grade de serviços selecionáveis com soma clara de tempo/valor e grade de botões de horários livres (`slots`).

---

## 5. Catálogo de Componentes Padronizados (Seções 05, 06 e Extensões Propostas)

### 5.1 Componentes Extraídos Diretamente da Referência
1. **Botão Primário (`btn-primary`):** `px-4 py-2 bg-violet-600 text-white rounded-md text-sm font-medium hover:bg-violet-700 transition-colors`.
2. **Card de Conteúdo / KPI (`sps-card`):** `bg-white rounded-lg shadow p-6` (`box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)`).
3. **Tabela de Dados (`sps-table-container` / `sps-table`):**
   - Wrapper: `bg-white shadow rounded-lg overflow-hidden`.
   - Tabela: `min-w-full divide-y divide-gray-200`, cabeçalho `bg-gray-50` com células `px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider` e corpo `bg-white divide-y divide-gray-200` com células `px-6 py-4 whitespace-nowrap text-sm`.
4. **Pílula de Status (`sps-badge`):** `px-2 inline-flex text-xs leading-5 font-semibold rounded-full`.
5. **Ícones SVG Inline (`20x20`):** Traço `stroke="currentColor"`, `stroke-width="2"`, `stroke-linecap="round"`, `stroke-linejoin="round"`.

### 5.2 Extensões Propostas para Lacunas da Referência (`design-system.html`)
A Seção `04` de `design-system.html` registra explicitamente *"Nenhum formulário tradicional (inputs de texto, selects, checkboxes) está visível na captura atual"*. Para atender aos fluxos reais do SPS mantendo 100% de coerência estética com os tokens `Violet 600` e `Gray 50–900`, foram propostas e implementadas as seguintes extensões:

| Componente Proposto | Especificação Visual Baseada nos Tokens | Onde é Utilizado |
|---|---|---|
| **Inputs, Selects e Textareas** | Borda `1px solid #d1d5db` (`gray-300`), raio `6px` (`rounded-md`), padding `0.5rem 0.75rem`, texto `14px #111827`, foco com anel violeta `border-color: #7c3aed; box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.18)`. | Todos os formulários internos e formulário público `/s/<slug>/`. |
| **Seletores de Múltiplos Serviços (Checkboxes em Card)** | Item interativo `border border-gray-200 rounded-md p-3 hover:border-violet-600 hover:bg-violet-50`, exibindo nome do serviço, duração em minutos e preço em `R$`. | Autoagendamento público (`S05-T02`) e criação/remarcação interna de agendamento. |
| **Grade de Horários Livres (`Slot Pills`)** | Botões selecionáveis `px-3 py-2 text-sm font-mono font-medium rounded-md border border-violet-200 bg-violet-50 text-violet-700 hover:bg-violet-600 hover:text-white`. | Consulta de horários reais calculados pelo `AvailabilityService` em `/s/<slug>/`. |
| **Botões Secundário e Perigo (`Danger`)** | Secundário: `bg-white border border-gray-300 text-gray-700 hover:bg-gray-50`; Perigo: `bg-red-600 text-white hover:bg-red-700` (`#dc2626`). | Ações de "Voltar/Limpar", exclusão de bloqueios e confirmação de cancelamento de agendamento (`S05-T03`). |
| **Navegação Mobile Responsiva (`< 768px`)** | Barra superior compacta com links horizontais roláveis (`overflow-x-auto`) quando a `sidebar` de `256px` é recolhida em telas de celular. | Uso da agenda e portal público em dispositivos móveis (`RNF-003`). |

---

## 6. Mapeamento de Aplicação nos Templates do Produto

| Template | Layout Base | Componentes Aplicados na `Sprint 05` |
|---|---|---|
| [`sps/templates/base.html`](../../templates/base.html) | Shell Interno (`00`) | Sidebar `w-64`, navegação com ícones SVG, header superior, alertas semânticos e estilização automática de tabelas/formulários. |
| [`sps/templates/public_base.html`](../../templates/public_base.html) | Shell Público | Header institucional do salão, container mobile-first `max-w-4xl`, rodapé de transparência de regras de cancelamento. |
| [`sps/templates/scheduling/public_booking.html`](../../templates/scheduling/public_booking.html) | `public_base.html` | Seleção de múltiplos serviços, filtro de profissional/data com horários livres reais (`AvailabilityService`) e confirmação de agendamento (`RF-006`). |
| [`sps/templates/scheduling/public_appointment_detail.html`](../../templates/scheduling/public_appointment_detail.html) | `public_base.html` | Comprovante público com `public_token`, pílula de status, resumo de serviços/valores e formulário de cancelamento condicionado ao prazo mínimo (`RF-006`). |
| [`sps/templates/scheduling/appointment_list.html`](../../templates/scheduling/appointment_list.html) | `base.html` | Filtros diário/semanal, pílulas de horários livres, tabela de agendamentos com badges semânticos e link para o portal público do salão. |
| [`sps/templates/base/home.html`](../../templates/base/home.html) | `base.html` | Painel inicial com cartões de acesso rápido no padrão `bg-white rounded-lg shadow p-6` e atalho para a página pública `/s/<slug>/`. |

---

## 7. Biblioteca de Ícones SVG Inline (Seção 09) e Variáveis CSS (`:root`)

### 7.1 Padrão de Ícones Vetoriais Extraídos
A Seção `09` de `design-system.html` padroniza ícones vetoriais SVG inline com `viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`, `stroke-width="2"`, `stroke-linecap="round"` e `stroke-linejoin="round"`:

| Ícone | Path SVG (`d="..."`) | Uso no SPS |
|---|---|---|
| **Dashboard / Visão Geral** | `M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6` | Item "Início / Visão Geral" na barra lateral. |
| **Agenda / Relógio** | `M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z` | Item "Agenda Inteligente", horários livres e bloqueios de agenda. |
| **Clientes / Equipe** | `M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z` | Itens "Clientes" e "Equipe de Profissionais". |
| **Catálogo / Serviços** | `M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z` | Itens "Catálogo de Serviços", "Regras de Comissão" e conformidade fiscal. |
| **Configurações / Salão** | `M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z` | Item "Configurações e Fiscal" e expediente do salão. |

### 7.2 Contrato de Variáveis CSS (`sps/static/css/sps-design-system.css`)
```css
:root {
  --sps-bg-app: #f9fafb;          /* gray-50 */
  --sps-bg-surface: #ffffff;      /* white */
  --sps-bg-accent-subtle: #f5f3ff;/* violet-50 */
  --sps-primary: #7c3aed;         /* violet-600 */
  --sps-primary-hover: #6d28d9;   /* violet-700 */
  --sps-text-primary: #111827;    /* gray-900 */
  --sps-text-secondary: #374151;  /* gray-700 */
  --sps-text-muted: #6b7280;      /* gray-500 */
  --sps-border: #e5e7eb;          /* gray-200 */
  --sps-radius-md: 0.375rem;      /* 6px */
  --sps-radius-lg: 0.5rem;        /* 8px */
  --sps-shadow-card: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1);
}
```

