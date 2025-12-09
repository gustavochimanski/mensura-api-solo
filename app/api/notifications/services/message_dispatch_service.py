from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from sqlalchemy.orm import Session

from ..repositories.notification_repository import NotificationRepository
from ..repositories.subscription_repository import SubscriptionRepository
from ..repositories.event_repository import EventRepository
from ..models.notification import MessageType, NotificationChannel, NotificationPriority
from ..schemas.message_dispatch_schemas import (
    DispatchMessageRequest,
    DispatchMessageResponse,
    BulkDispatchRequest
)
from .notification_service import NotificationService
from ..contracts.message_dispatch_service_contract import IMessageDispatchService
from ..contracts.recipient_provider_contract import IRecipientProvider
from ..adapters.recipient_adapters import ClienteRecipientAdapter, CompositeRecipientAdapter

logger = logging.getLogger(__name__)

class MessageDispatchService(IMessageDispatchService):
    """Serviço especializado para disparo de mensagens com tipos determinados"""
    
    def __init__(
        self,
        notification_service: NotificationService,
        db: Optional[Session] = None,
        recipient_provider: Optional[IRecipientProvider] = None
    ):
        self.notification_service = notification_service
        self.notification_repo = notification_service.notification_repo
        self.subscription_repo = notification_service.subscription_repo
        self.event_repo = notification_service.event_repo
        self.db = db or notification_service.notification_repo.db
        
        # Usa o provedor de destinatários fornecido ou cria um padrão
        if recipient_provider:
            self.recipient_provider = recipient_provider
        else:
            # Cria um adaptador composto com ClienteRecipientAdapter por padrão
            cliente_adapter = ClienteRecipientAdapter(self.db)
            self.recipient_provider = CompositeRecipientAdapter([cliente_adapter])
    
    async def dispatch_message(self, request: DispatchMessageRequest) -> DispatchMessageResponse:
        """
        Dispara uma mensagem para um ou mais destinatários através de múltiplos canais
        
        Args:
            request: Dados do disparo de mensagem
            
        Returns:
            Resposta com informações sobre o disparo
        """
        try:
            notification_ids = []
            total_recipients = 0
            channels_used = set()
            
            # Determina lista de destinatários
            recipients = self._build_recipients_list(request)
            total_recipients = len(recipients)
            
            if total_recipients == 0:
                raise ValueError("Nenhum destinatário encontrado")
            
            # Para cada canal, cria notificações para cada destinatário apropriado
            for channel in request.channels:
                channels_used.add(channel)
                
                for recipient_info in recipients:
                    recipient = recipient_info.get('recipient')
                    user_id = recipient_info.get('user_id')
                    
                    if not recipient:
                        continue
                    
                    # Valida se o recipient é apropriado para o canal
                    if channel == NotificationChannel.EMAIL:
                        # Para email, recipient deve ser um email válido
                        if '@' not in recipient:
                            logger.debug(f"Recipient {recipient} não é um email válido, pulando canal email")
                            continue
                    elif channel in [NotificationChannel.WHATSAPP, NotificationChannel.SMS]:
                        # Para WhatsApp/SMS, recipient deve ser um telefone
                        # Remove caracteres não numéricos para validação básica
                        phone_digits = ''.join(filter(str.isdigit, recipient))
                        if len(phone_digits) < 10:
                            logger.debug(f"Recipient {recipient} não parece ser um telefone válido, pulando canal {channel}")
                            continue
                    # Para outros canais (push, webhook, in_app), aceita qualquer recipient
                    
                    # Cria notificação usando o serviço existente
                    from ..schemas.notification_schemas import CreateNotificationRequest
                    
                    notification_request = CreateNotificationRequest(
                        empresa_id=request.empresa_id,
                        user_id=user_id,
                        event_type=request.event_type or f"message_dispatch_{request.message_type.value}",
                        event_data=request.event_data,
                        title=request.title,
                        message=request.message,
                        channel=channel,
                        recipient=recipient,
                        priority=request.priority,
                        message_type=request.message_type,
                        channel_metadata=request.channel_metadata,
                        max_attempts=3
                    )
                    
                    notification_id = await self.notification_service.create_notification(notification_request)
                    notification_ids.append(notification_id)
            
            logger.info(
                f"Mensagem tipo {request.message_type.value} disparada: "
                f"{total_recipients} destinatários, {len(channels_used)} canais, "
                f"{len(notification_ids)} notificações criadas"
            )
            
            return DispatchMessageResponse(
                success=True,
                message_type=request.message_type,
                notification_ids=notification_ids,
                total_recipients=total_recipients,
                channels_used=list(channels_used),
                scheduled=request.scheduled_at is not None,
                scheduled_at=request.scheduled_at
            )
            
        except Exception as e:
            logger.error(f"Erro ao disparar mensagem: {e}")
            raise
    
    def _build_recipients_list(self, request: DispatchMessageRequest) -> List[Dict[str, str]]:
        """
        Constrói lista de destinatários a partir dos dados da requisição
        Usa o provedor de destinatários para buscar informações
        
        Returns:
            Lista de dicionários com 'recipient' e 'user_id'
        """
        recipients = []
        
        # Se há user_ids específicos, busca informações usando o provedor
        if request.user_ids:
            recipient_data_list = self.recipient_provider.get_recipients_by_ids(request.user_ids)
            
            for recipient_data in recipient_data_list:
                user_id = recipient_data.get('user_id') or recipient_data.get('cliente_id')
                
                # Adiciona email se disponível
                if recipient_data.get('email'):
                    recipients.append({
                        "user_id": user_id,
                        "recipient": recipient_data['email']
                    })
                
                # Adiciona telefone se disponível
                if recipient_data.get('phone'):
                    recipients.append({
                        "user_id": user_id,
                        "recipient": recipient_data['phone']
                    })
        
        # Adiciona emails fornecidos diretamente
        if request.recipient_emails:
            for email in request.recipient_emails:
                recipients.append({
                    "user_id": None,
                    "recipient": email
                })
        
        # Adiciona telefones fornecidos diretamente
        if request.recipient_phones:
            for phone in request.recipient_phones:
                recipients.append({
                    "user_id": None,
                    "recipient": phone
                })
        
        return recipients
    
    async def bulk_dispatch(self, request: BulkDispatchRequest) -> DispatchMessageResponse:
        """
        Dispara mensagem em massa baseado em filtros
        
        Args:
            request: Dados do disparo em massa
            
        Returns:
            Resposta com informações sobre o disparo
        """
        try:
            # Busca destinatários baseado nos filtros
            recipients = await self._get_recipients_by_filters(request)
            
            if not recipients:
                raise ValueError("Nenhum destinatário encontrado com os filtros especificados")
            
            # Limita número de destinatários se especificado
            if request.max_recipients and len(recipients) > request.max_recipients:
                recipients = recipients[:request.max_recipients]
                logger.warning(
                    f"Limite de {request.max_recipients} destinatários aplicado. "
                    f"Total encontrado: {len(recipients)}"
                )
            
            # Separa recipients por tipo para criar a requisição corretamente
            user_ids_list = []
            emails_list = []
            phones_list = []
            
            for r in recipients:
                user_id = r.get('user_id')
                email = r.get('email')
                phone = r.get('phone')
                
                if user_id and (email or phone):
                    # Se tem user_id, adiciona aos user_ids
                    # Os emails e phones serão buscados automaticamente
                    if user_id not in user_ids_list:
                        user_ids_list.append(user_id)
                else:
                    # Se não tem user_id, adiciona diretamente
                    if email and email not in emails_list:
                        emails_list.append(email)
                    if phone and phone not in phones_list:
                        phones_list.append(phone)
            
            # Cria requisição de disparo normal
            dispatch_request = DispatchMessageRequest(
                empresa_id=request.empresa_id,
                message_type=request.message_type,
                title=request.title,
                message=request.message,
                user_ids=user_ids_list if user_ids_list else None,
                recipient_emails=emails_list if emails_list else None,
                recipient_phones=phones_list if phones_list else None,
                channels=request.channels,
                priority=request.priority,
                event_type=f"bulk_dispatch_{request.message_type.value}",
                event_data={
                    "filter_by_empresa": request.filter_by_empresa,
                    "filter_by_user_type": request.filter_by_user_type,
                    "filter_by_tags": request.filter_by_tags
                }
            )
            
            return await self.dispatch_message(dispatch_request)
            
        except Exception as e:
            logger.error(f"Erro no disparo em massa: {e}")
            raise
    
    async def _get_recipients_by_filters(self, request: BulkDispatchRequest) -> List[Dict[str, Any]]:
        """
        Busca destinatários baseado nos filtros especificados
        Usa o provedor de destinatários para buscar
        
        Returns:
            Lista de destinatários com suas informações (email, phone, user_id)
        """
        try:
            recipients = self.recipient_provider.get_recipients_by_filters(
                empresa_id=request.empresa_id,
                filter_by_empresa=request.filter_by_empresa,
                filter_by_user_type=request.filter_by_user_type,
                filter_by_tags=request.filter_by_tags
            )
            
            logger.info(
                f"Encontrados {len(recipients)} destinatários com os filtros especificados "
                f"(empresa: {request.filter_by_empresa}, "
                f"tipo: {request.filter_by_user_type}, "
                f"tags: {request.filter_by_tags})"
            )
            
            return recipients
            
        except Exception as e:
            logger.error(f"Erro ao buscar destinatários por filtros: {e}")
            raise
    
    def get_dispatch_stats(
        self,
        empresa_id: str,
        message_type: Optional[MessageType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Obtém estatísticas de disparos de mensagens
        
        Args:
            empresa_id: ID da empresa
            message_type: Tipo de mensagem (opcional)
            start_date: Data inicial (opcional)
            end_date: Data final (opcional)
            
        Returns:
            Dicionário com estatísticas
        """
        try:
            from ..schemas.notification_schemas import NotificationFilter
            
            filters = NotificationFilter(
                empresa_id=empresa_id,
                message_type=message_type,
                created_from=start_date,
                created_to=end_date
            )
            
            notifications = self.notification_repo.filter_notifications(filters, limit=10000, offset=0)
            
            stats = {
                "total": len(notifications),
                "by_status": {},
                "by_channel": {},
                "by_message_type": {}
            }
            
            for notification in notifications:
                # Por status
                status = notification.status.value
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
                
                # Por canal
                channel = notification.channel.value
                stats["by_channel"][channel] = stats["by_channel"].get(channel, 0) + 1
                
                # Por tipo de mensagem
                msg_type = notification.message_type.value
                stats["by_message_type"][msg_type] = stats["by_message_type"].get(msg_type, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de disparo: {e}")
            raise

