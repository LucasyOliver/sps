from typing import TypedDict
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from langgraph.graph import END, START, StateGraph
from accounts.models import UserRoleChoices
from ai_assistant.models import (
    ALLOWED_ASSISTANT_ROLES,
    AssistantChatMessage,
    AssistantChatSession,
    MessageSenderChoices,
)
from ai_assistant.tools import build_authorized_tools


class AssistantGraphState(TypedDict):
    prompt: str
    requested_tool_names: list[str]
    invoked_tools: list[str]
    tool_outputs: dict
    blocked_gestor_only: bool
    final_answer: str


class LLMFactory:
    """
    Fábrica de configuração de modelo LLM parametrizada por .env (S09-T01, RF-012).
    Mantém compatibilidade com `modelo_llm = a_definir` sem exigir chave externa no MVP.
    """

    @staticmethod
    def get_configured_model_name() -> str:
        model_name = (getattr(settings, 'LLM_MODEL', '') or '').strip()
        return model_name or 'a_definir'

    @staticmethod
    def has_external_provider_configured() -> bool:
        model_name = LLMFactory.get_configured_model_name()
        api_key = (getattr(settings, 'LLM_API_KEY', '') or '').strip()
        return bool(model_name and model_name != 'a_definir' and api_key)


class SalonAssistantOrchestrator:
    """
    Orquestrador LangGraph do Assistente Gerencial Interno (S09-T03, RF-012, SEC-G).
    Constrói um StateGraph onde `salon_id` e `user_role` são fixados por closure no
    servidor autenticado, impedindo vazamento cross-tenant mesmo sob prompt injection.
    """

    def __init__(self, *, salon_id: int, user_role: str):
        if user_role not in ALLOWED_ASSISTANT_ROLES:
            raise PermissionDenied(
                'Apenas Gestor e Recepcionista possuem permissão para utilizar o Assistente Gerencial de IA.'
            )
        self.salon_id = int(salon_id)
        self.user_role = user_role
        self.authorized_tools = build_authorized_tools(
            salon_id=self.salon_id,
            user_role=self.user_role,
        )
        self.compiled_graph = self._build_graph()

    def _route_intent_node(self, state: AssistantGraphState) -> dict:
        text = (state.get('prompt') or '').lower()
        requested = []
        blocked_gestor = False

        if any(
            kw in text
            for kw in (
                'faturamento',
                'receita',
                'comiss',
                'financeiro',
                'lucro',
                'ticket',
                'caixa',
            )
        ):
            if self.user_role == UserRoleChoices.GESTOR:
                requested.append('get_revenue_and_commissions_summary')
            else:
                blocked_gestor = True

        if any(
            kw in text
            for kw in ('agenda', 'horário', 'horario', 'atendimento', 'hoje', 'amanhã', 'amanha', 'vago')
        ):
            requested.append('get_salon_agenda_summary')

        if any(
            kw in text
            for kw in ('estoque', 'produto', 'insumo', 'reposição', 'reposicao', 'mínimo', 'minimo', 'baixo')
        ):
            requested.append('get_low_stock_products')

        if any(
            kw in text
            for kw in ('cliente', 'inativo', 'sumido', '60 dias', 'ausente', 'retorno')
        ):
            requested.append('get_inactive_clients')

        if not requested and not blocked_gestor:
            requested.append('get_salon_agenda_summary')
            requested.append('get_low_stock_products')
            if self.user_role == UserRoleChoices.GESTOR:
                requested.append('get_revenue_and_commissions_summary')

        return {
            'requested_tool_names': requested,
            'blocked_gestor_only': blocked_gestor,
        }

    def _execute_tools_node(self, state: AssistantGraphState) -> dict:
        outputs = {}
        invoked = []
        for tool_name in state.get('requested_tool_names', []):
            bound_tool = self.authorized_tools.get(tool_name)
            if bound_tool is None:
                continue
            outputs[tool_name] = bound_tool.invoke({})
            invoked.append(tool_name)
        return {
            'invoked_tools': invoked,
            'tool_outputs': outputs,
        }

    def _synthesize_response_node(self, state: AssistantGraphState) -> dict:
        outputs = state.get('tool_outputs', {})
        sections = []

        if state.get('blocked_gestor_only'):
            sections.append(
                'Aviso de permissão: indicadores globais de faturamento e comissões são '
                'exclusivos do perfil Gestor. Como Recepcionista, você pode consultar '
                'agenda, alertas de estoque e clientes inativos.'
            )

        rev = outputs.get('get_revenue_and_commissions_summary')
        if rev:
            sections.append(
                f'Resumo Financeiro ({rev["salon_name"]}): Faturamento Bruto R$ {rev["gross_revenue"]} | '
                f'Faturamento Líquido R$ {rev["net_revenue"]} ({rev["paid_orders_count"]} comandas pagas; '
                f'Ticket médio R$ {rev["average_ticket"]}) | Comissões pendentes: '
                f'R$ {rev["commissions_pending_total"]} | Comissões pagas: R$ {rev["commissions_paid_total"]}.'
            )

        agenda = outputs.get('get_salon_agenda_summary')
        if agenda:
            appts = agenda['active_appointments']
            if appts:
                details = '; '.join(
                    f'{a["start_time"]}-{a["end_time"]} {a["client_name"]} com {a["professional_name"]}'
                    for a in appts[:8]
                )
                sections.append(
                    f'Agenda ({agenda["salon_name"]} em {agenda["reference_date"]}): '
                    f'{agenda["active_appointments_count"]} agendamento(s) ativo(s) ({details}).'
                )
            else:
                sections.append(
                    f'Agenda ({agenda["salon_name"]} em {agenda["reference_date"]}): '
                    f'Nenhum agendamento ativo registrado para a data.'
                )

        stock = outputs.get('get_low_stock_products')
        if stock:
            if stock['low_stock_count'] > 0:
                prod_list = ', '.join(
                    f'{p["name"]} (saldo {p["current_stock"]}/{p["min_stock_alert"]} {p["unit"]})'
                    for p in stock['products']
                )
                sections.append(
                    f'Estoque Crítico ({stock["salon_name"]}): {stock["low_stock_count"]} produto(s) '
                    f'abaixo ou no limite mínimo: {prod_list}.'
                )
            else:
                sections.append(
                    f'Estoque ({stock["salon_name"]}): Todos os produtos ativos estão acima do estoque mínimo.'
                )

        inactive = outputs.get('get_inactive_clients')
        if inactive:
            if inactive['inactive_clients_count'] > 0:
                cli_list = ', '.join(
                    f'{c["full_name"]} ({c["last_appointment_at"]})'
                    for c in inactive['clients'][:10]
                )
                sections.append(
                    f'Clientes sem agendamento recente ({inactive["salon_name"]}): '
                    f'{inactive["inactive_clients_count"]} cliente(s): {cli_list}.'
                )
            else:
                sections.append(
                    f'Clientes ({inactive["salon_name"]}): Nenhum cliente inativo acima de '
                    f'{inactive["days_inactive_threshold"]} dias.'
                )

        model_tag = LLMFactory.get_configured_model_name()
        sections.append(f'[Modelo configurado: {model_tag}]')
        return {'final_answer': '\n\n'.join(sections)}

    def _build_graph(self):
        workflow = StateGraph(AssistantGraphState)
        workflow.add_node('route_intent', self._route_intent_node)
        workflow.add_node('execute_tools', self._execute_tools_node)
        workflow.add_node('synthesize_response', self._synthesize_response_node)

        workflow.add_edge(START, 'route_intent')
        workflow.add_edge('route_intent', 'execute_tools')
        workflow.add_edge('execute_tools', 'synthesize_response')
        workflow.add_edge('synthesize_response', END)
        return workflow.compile()

    def invoke(self, prompt: str) -> dict:
        initial_state: AssistantGraphState = {
            'prompt': prompt,
            'requested_tool_names': [],
            'invoked_tools': [],
            'tool_outputs': {},
            'blocked_gestor_only': False,
            'final_answer': '',
        }
        return self.compiled_graph.invoke(initial_state)


class AssistantChatService:
    """Serviço de gerenciamento de sessões e mensagens do Assistente de IA (S09-T01, S09-T04)."""

    @staticmethod
    def get_or_create_active_session(*, salon, user, session_id: int | None = None) -> AssistantChatSession:
        if (
            salon is None
            or user is None
            or user.salon_id != salon.id
            or user.role not in ALLOWED_ASSISTANT_ROLES
        ):
            raise PermissionDenied(
                'Usuário sem permissão para acessar o Assistente Gerencial Interno.'
            )

        qs = AssistantChatSession.objects.for_salon(salon).filter(
            user=user,
            is_active=True,
        )
        if session_id is not None:
            session = qs.filter(pk=session_id).first()
            if session is None:
                raise PermissionDenied('Sessão de chat inexistente ou pertencente a outro usuário/salão.')
            return session

        session = qs.first()
        if session is not None:
            return session

        session = AssistantChatSession(
            salon=salon,
            user=user,
            title='Consulta Operacional e Gerencial',
            llm_model_snapshot=LLMFactory.get_configured_model_name(),
        )
        session.full_clean()
        session.save()
        return session

    @classmethod
    def send_user_message(
        cls,
        *,
        salon,
        user,
        session: AssistantChatSession,
        prompt: str,
    ) -> AssistantChatMessage:
        if (
            salon is None
            or user is None
            or user.salon_id != salon.id
            or user.role not in ALLOWED_ASSISTANT_ROLES
        ):
            raise PermissionDenied(
                'Apenas Gestor e Recepcionista do salão podem enviar mensagens ao Assistente de IA.'
            )
        if session is None or session.salon_id != salon.id or session.user_id != user.id:
            raise PermissionDenied('Sessão de chat inválida para este usuário e salão.')

        prompt_clean = (prompt or '').strip()
        if not prompt_clean:
            raise ValidationError({'prompt': 'Digite uma pergunta para o assistente.'})

        user_msg = AssistantChatMessage(
            salon=salon,
            session=session,
            sender_role=MessageSenderChoices.USER,
            content=prompt_clean,
        )
        user_msg.full_clean()
        user_msg.save()

        orchestrator = SalonAssistantOrchestrator(
            salon_id=salon.id,
            user_role=user.role,
        )
        result = orchestrator.invoke(prompt_clean)

        assistant_msg = AssistantChatMessage(
            salon=salon,
            session=session,
            sender_role=MessageSenderChoices.ASSISTANT,
            content=result['final_answer'],
            invoked_tools=result['invoked_tools'],
        )
        assistant_msg.full_clean()
        assistant_msg.save()

        session.llm_model_snapshot = LLMFactory.get_configured_model_name()
        session.save(update_fields=['llm_model_snapshot', 'updated_at'])
        return assistant_msg
