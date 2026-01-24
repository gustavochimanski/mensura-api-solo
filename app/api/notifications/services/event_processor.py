from typing import List, Dict, Any, Optional
import logging
import asyncio
from datetime import datetime

from ..repositories.event_repository import EventRepository
from ..repositories.subscription_repository import SubscriptionRepository
from ..repositories.notification_repository import NotificationRepository
from ..core.event_bus import EventHandler, Event, EventType
from ..models.subscription import NotificationSubscription
from ..models.notification import NotificationChannel, NotificationPriority

logger = logging.getLogger(__name__)

class EventProcessor(EventHandler):
    """Processador de eventos que gera notificações baseadas em assinaturas"""
    
    def __init__(
        self,
        event_repo: EventRepository,
        subscription_repo: SubscriptionRepository,
        notification_repo: NotificationRepository
    ):
        self.event_repo = event_repo
        self.subscription_repo = subscription_repo
        self.notification_repo = notification_repo
    
    async def handle(self, event: Event) -> None:
        """Processa um evento e gera notificações baseadas nas assinaturas"""
        try:
            logger.info(f"Processando evento {event.id} - {event.event_type}")
            
            # Busca assinaturas ativas para este tipo de evento
            subscriptions = self.subscription_repo.get_active_subscriptions(
                event.empresa_id,
                event.event_type
            )
            
            if not subscriptions:
                logger.info(f"Nenhuma assinatura encontrada para evento {event.event_type} da empresa {event.empresa_id}")
                return
            
            # Gera notificações para cada assinatura
            for subscription in subscriptions:
                await self._create_notification_from_subscription(event, subscription)
            
            # Marca evento como processado
            self.event_repo.mark_as_processed(event.id)
            logger.info(f"Evento {event.id} processado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao processar evento {event.id}: {e}")
    
    def can_handle(self, event_type: EventType) -> bool:
        """Sempre pode processar qualquer tipo de evento"""
        return True
    
    async def _create_notification_from_subscription(self, event: Event, subscription: NotificationSubscription):
        """Cria notificação baseada em uma assinatura"""
        try:
            # Verifica filtros se existirem
            if subscription.filters and not self._matches_filters(event, subscription.filters):
                logger.info(f"Evento {event.id} não atende aos filtros da assinatura {subscription.id}")
                return
            
            # Prepara dados da notificação
            title, message = self._generate_notification_content(event, subscription)
            
            # Determina o destinatário baseado na configuração do canal
            recipient = self._get_recipient_from_config(subscription.channel_config, subscription.channel)
            if not recipient:
                logger.warning(f"Destinatário não encontrado para assinatura {subscription.id}")
                return

            # Channel metadata: permite configurar template WhatsApp na própria assinatura (channel_config)
            channel_metadata = None
            try:
                if subscription.channel == "whatsapp":
                    # Convenção: channel_config pode conter "whatsapp" com o contract de mensagem
                    # Ex:
                    # {
                    #   "phone": "5511...",
                    #   "whatsapp": {"mode":"template","template":{"name":"meu_template","language":"pt_BR","body_parameters":[...]} }
                    # }
                    raw = subscription.channel_config or {}
                    if isinstance(raw, dict) and raw.get("whatsapp"):
                        wa_spec = raw.get("whatsapp")
                        # Se for template sem parâmetros explícitos, injeta um body_parameters padrão
                        # com o conteúdo (title/message). Isso permite que templates com 1 variável
                        # funcionem sem precisar repetir configuração por evento.
                        try:
                            if (
                                isinstance(wa_spec, dict)
                                and wa_spec.get("mode") == "template"
                                and isinstance(wa_spec.get("template"), dict)
                            ):
                                tpl = wa_spec["template"]
                                if tpl.get("components") is None and tpl.get("body_parameters") is None:
                                    tpl["body_parameters"] = [f"*{title}*\\n\\n{message}"]
                        except Exception:
                            pass
                        channel_metadata = {"whatsapp": wa_spec}
            except Exception:
                channel_metadata = None

            # Cria e envia a notificação via NotificationService (garante entrega imediata)
            from ..repositories.notification_repository import NotificationRepository
            from ..repositories.subscription_repository import SubscriptionRepository
            from ..repositories.event_repository import EventRepository
            from ..services.notification_service import NotificationService
            from ..schemas.notification_schemas import CreateNotificationRequest, MessageType
            from ..models.notification import NotificationChannel as ModelChannel

            service = NotificationService(
                notification_repo=NotificationRepository(self.notification_repo.db),
                subscription_repo=SubscriptionRepository(self.subscription_repo.db),
                event_repo=EventRepository(self.event_repo.db),
            )

            # Normaliza channel para enum do schema
            channel_enum = ModelChannel(str(subscription.channel).lower())

            # Embute metadados no event_data para rastreio (não existe campo event_metadata no model)
            event_data = dict(event.data or {})
            event_data.setdefault("_notification_meta", {})
            event_data["_notification_meta"].update({"subscription_id": subscription.id, "event_id": event.id})

            notification_id = await service.create_notification(
                CreateNotificationRequest(
                    empresa_id=str(event.empresa_id),
                    user_id=subscription.user_id,
                    event_type=str(event.event_type),
                    event_data=event_data,
                    title=title,
                    message=message,
                    channel=channel_enum,
                    recipient=recipient,
                    priority=self._get_priority_from_event(event),
                    message_type=MessageType.UTILITY,
                    channel_metadata=channel_metadata,
                    max_attempts=3,
                )
            )
            logger.info(f"Notificação criada/enviada: {notification_id} para assinatura {subscription.id}")
            
        except Exception as e:
            logger.error(f"Erro ao criar notificação para assinatura {subscription.id}: {e}")
    
    def _matches_filters(self, event: Event, filters: Dict[str, Any]) -> bool:
        """Verifica se o evento atende aos filtros da assinatura"""
        try:
            for filter_key, filter_value in filters.items():
                if filter_key in event.data:
                    if event.data[filter_key] != filter_value:
                        return False
                else:
                    return False
            return True
        except Exception as e:
            logger.error(f"Erro ao verificar filtros: {e}")
            return False
    
    def _generate_notification_content(self, event: Event, subscription: NotificationSubscription) -> tuple[str, str]:
        """Gera título e mensagem da notificação baseado no evento"""
        event_templates = {
            EventType.PEDIDO_CRIADO: {
                "title": "Novo Pedido Recebido",
                "message": "Um novo pedido foi criado no sistema."
            },
            EventType.PEDIDO_APROVADO: {
                "title": "Pedido Aprovado",
                "message": "Seu pedido foi aprovado e está sendo processado."
            },
            EventType.PEDIDO_REJEITADO: {
                "title": "Pedido Rejeitado",
                "message": "Seu pedido foi rejeitado. Entre em contato para mais informações."
            },
            EventType.ESTOQUE_BAIXO: {
                "title": "Estoque Baixo",
                "message": "Atenção: O estoque de um produto está baixo."
            },
            EventType.PAGAMENTO_APROVADO: {
                "title": "Pagamento Aprovado",
                "message": "Seu pagamento foi aprovado com sucesso."
            },
            EventType.SISTEMA_ERRO: {
                "title": "Erro no Sistema",
                "message": "Ocorreu um erro no sistema que requer atenção."
            }
        }
        
        template = event_templates.get(event.event_type, {
            "title": f"Evento: {event.event_type}",
            "message": "Uma nova atividade foi registrada no sistema."
        })
        
        # Personaliza a mensagem com dados do evento
        title = template["title"]
        message = template["message"]
        
        # Adiciona informações específicas do evento
        if event.data:
            if "pedido_id" in event.data:
                message += f"\nID do Pedido: {event.data['pedido_id']}"
            if "valor_total" in event.data:
                message += f"\nValor: R$ {event.data['valor_total']:.2f}"
            if "produto_nome" in event.data:
                message += f"\nProduto: {event.data['produto_nome']}"
        
        return title, message
    
    def _get_recipient_from_config(self, channel_config: Dict[str, Any], channel: str) -> Optional[str]:
        """Extrai destinatário da configuração do canal"""
        if channel == "email":
            return channel_config.get("email")
        elif channel == "webhook":
            return channel_config.get("webhook_url")
        elif channel == "whatsapp":
            return channel_config.get("phone")
        elif channel == "push":
            return channel_config.get("device_token")
        elif channel == "in_app":
            return channel_config.get("user_id")
        else:
            return None
    
    def _get_priority_from_event(self, event: Event) -> str:
        """Determina prioridade baseada no tipo de evento"""
        high_priority_events = [
            EventType.SISTEMA_ERRO,
            EventType.ESTOQUE_ESGOTADO,
            EventType.PAGAMENTO_REJEITADO
        ]
        
        if event.event_type in high_priority_events:
            return NotificationPriority.HIGH
        elif event.event_type == EventType.PEDIDO_CRIADO:
            return NotificationPriority.NORMAL
        else:
            return NotificationPriority.LOW
