from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import asyncio

from ..repositories.notification_repository import NotificationRepository
from ..repositories.subscription_repository import SubscriptionRepository
from ..repositories.event_repository import EventRepository
from ..channels.channel_factory import ChannelFactory
from ..core.websocket_manager import websocket_manager
from ..core.event_bus import EventHandler, Event, EventType
from ..models.notification import NotificationStatus, NotificationChannel, NotificationPriority
from ..schemas.notification_schemas import CreateNotificationRequest, SendNotificationRequest
from ..contracts.notification_service_contract import INotificationService
from ..contracts.channel_config_provider_contract import IChannelConfigProvider
from ..adapters.channel_config_adapters import DefaultChannelConfigAdapter

logger = logging.getLogger(__name__)

class NotificationService(INotificationService):
    """Serviço principal de notificações"""
    
    def __init__(
        self,
        notification_repo: NotificationRepository,
        subscription_repo: SubscriptionRepository,
        event_repo: EventRepository,
        channel_config_provider: Optional[IChannelConfigProvider] = None
    ):
        self.notification_repo = notification_repo
        self.subscription_repo = subscription_repo
        self.event_repo = event_repo
        self.channel_factory = ChannelFactory()
        self.channel_config_provider = channel_config_provider or DefaultChannelConfigAdapter()
    
    async def create_notification(self, request: CreateNotificationRequest) -> str:
        """Cria uma nova notificação"""
        try:
            # Extrai os valores dos enums para garantir compatibilidade com SQLAlchemy
            # Isso previne problemas de serialização onde o nome do enum é usado em vez do valor
            channel_value = request.channel.value if hasattr(request.channel, 'value') else str(request.channel)
            priority_value = request.priority.value if hasattr(request.priority, 'value') else str(request.priority)
            message_type_value = request.message_type.value if hasattr(request.message_type, 'value') else str(request.message_type)
            
            notification_data = {
                "empresa_id": request.empresa_id,
                "user_id": request.user_id,
                "event_type": request.event_type,
                "event_data": request.event_data,
                "title": request.title,
                "message": request.message,
                "channel": channel_value, 
                "recipient": request.recipient,
                "priority": priority_value,  # Passa o valor do enum, não o enum em si
                "message_type": message_type_value,  # Passa o valor do enum, não o enum em si
                "channel_metadata": request.channel_metadata,
                "max_attempts": request.max_attempts
            }
            
            notification = self.notification_repo.create(notification_data)
            logger.info(f"Notificação criada: {notification.id}")
            
            # Processa a notificação imediatamente
            await self._process_notification(notification)
            
            return notification.id
        except Exception as e:
            logger.error(f"Erro ao criar notificação: {e}")
            raise
    
    async def send_notification(self, request: SendNotificationRequest) -> List[str]:
        """Envia notificação para múltiplos canais"""
        notification_ids = []
        
        # Extrai os valores dos enums uma vez para reutilizar
        priority_value = request.priority.value if hasattr(request.priority, 'value') else str(request.priority)
        message_type_value = request.message_type.value if hasattr(request.message_type, 'value') else str(request.message_type)
        
        for channel in request.channels:
            recipient = request.recipients.get(channel)
            if not recipient:
                logger.warning(f"Destinatário não fornecido para canal {channel}")
                continue
            
            try:
                # Extrai o valor do enum do canal
                channel_value = channel.value if hasattr(channel, 'value') else str(channel)
                
                notification_data = {
                    "empresa_id": request.empresa_id,
                    "user_id": request.user_id,
                    "event_type": request.event_type,
                    "event_data": request.event_data,
                    "title": request.title,
                    "message": request.message,
                    "channel": channel_value,  # Passa o valor do enum, não o enum em si
                    "recipient": recipient,
                    "priority": priority_value,  # Passa o valor do enum, não o enum em si
                    "message_type": message_type_value  # Passa o valor do enum, não o enum em si
                }
                
                notification = self.notification_repo.create(notification_data)
                notification_ids.append(notification.id)
                
                # Processa a notificação
                await self._process_notification(notification)
                
            except Exception as e:
                logger.error(f"Erro ao criar notificação para canal {channel}: {e}")
        
        return notification_ids
    
    async def _process_notification(self, notification):
        """Processa uma notificação enviando pelo canal apropriado"""
        try:
            # Busca configuração do canal
            channel_config = self._get_channel_config(notification.empresa_id, notification.channel)
            if not channel_config:
                logger.error(f"Configuração não encontrada para canal {notification.channel}")
                self._mark_notification_failed(notification.id, "Configuração do canal não encontrada")
                return
            
            # Cria instância do canal
            # Converte o enum para string (valor) antes de passar para o factory
            channel_type = notification.channel.value if hasattr(notification.channel, 'value') else str(notification.channel)
            channel = self.channel_factory.create_channel(channel_type, channel_config)
            
            # Envia a notificação
            result = await channel.send(
                recipient=notification.recipient,
                title=notification.title,
                message=notification.message,
                channel_metadata=notification.channel_metadata
            )
            
            if result.success:
                self.notification_repo.update_status(
                    notification.id,
                    NotificationStatus.SENT,
                    attempts=notification.attempts + 1
                )
                self.notification_repo.add_log(
                    notification.id,
                    NotificationStatus.SENT,
                    result.message,
                    {"external_id": result.external_id}
                )
                logger.info(f"Notificação {notification.id} enviada com sucesso")
            else:
                self._handle_notification_failure(notification, result.message, result.error_details)
                
        except Exception as e:
            logger.error(f"Erro ao processar notificação {notification.id}: {e}")
            self._handle_notification_failure(notification, str(e))
    
    def _get_channel_config(self, empresa_id: str, channel: NotificationChannel) -> Optional[Dict[str, Any]]:
        """Busca configuração do canal para a empresa usando o provedor de configuração"""
        config = self.channel_config_provider.get_channel_config(empresa_id, channel)
        
        # Se não encontrou configuração específica, usa a padrão
        if not config:
            config = self.channel_config_provider.get_default_channel_config(channel)
        
        # Adiciona websocket_manager para canal in_app se necessário
        if channel == NotificationChannel.IN_APP and config:
            config["websocket_manager"] = websocket_manager
        
        return config
    
    def _handle_notification_failure(self, notification, error_message: str, error_details: Optional[Dict[str, Any]] = None):
        """Trata falha no envio de notificação"""
        if notification.attempts + 1 >= notification.max_attempts:
            # Máximo de tentativas atingido
            self.notification_repo.update_status(
                notification.id,
                NotificationStatus.FAILED,
                attempts=notification.attempts + 1
            )
            self.notification_repo.add_log(
                notification.id,
                NotificationStatus.FAILED,
                f"Falha definitiva: {error_message}",
                error_details
            )
            logger.error(f"Notificação {notification.id} falhou definitivamente após {notification.attempts + 1} tentativas")
        else:
            # Agenda nova tentativa
            self.notification_repo.increment_attempts(notification.id)
            self.notification_repo.add_log(
                notification.id,
                NotificationStatus.RETRYING,
                f"Tentativa {notification.attempts + 1} falhou: {error_message}",
                error_details
            )
            logger.warning(f"Notificação {notification.id} falhou, será tentada novamente")
    
    def _mark_notification_failed(self, notification_id: str, error_message: str):
        """Marca notificação como falhada"""
        self.notification_repo.update_status(notification_id, NotificationStatus.FAILED)
        self.notification_repo.add_log(notification_id, NotificationStatus.FAILED, error_message)
    
    async def process_pending_notifications(self, limit: int = 50):
        """Processa notificações pendentes"""
        pending_notifications = self.notification_repo.get_pending_notifications(limit)
        
        for notification in pending_notifications:
            await self._process_notification(notification)
            # Pequena pausa entre processamentos para não sobrecarregar
            await asyncio.sleep(0.1)
    
    async def retry_failed_notifications(self, limit: int = 50):
        """Tenta reenviar notificações que falharam"""
        failed_notifications = self.notification_repo.get_failed_notifications(limit=limit)
        
        for notification in failed_notifications:
            await self._process_notification(notification)
            await asyncio.sleep(0.1)
    
    def get_notification_by_id(self, notification_id: str):
        """Busca notificação por ID"""
        return self.notification_repo.get_by_id(notification_id)
    
    def get_notifications_by_empresa(self, empresa_id: str, limit: int = 100, offset: int = 0):
        """Busca notificações por empresa"""
        return self.notification_repo.get_by_empresa(empresa_id, limit, offset)
    
    def get_notification_logs(self, notification_id: str):
        """Busca logs de uma notificação"""
        return self.notification_repo.get_logs(notification_id)
