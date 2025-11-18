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

logger = logging.getLogger(__name__)

class NotificationService:
    """Serviço principal de notificações"""
    
    def __init__(
        self,
        notification_repo: NotificationRepository,
        subscription_repo: SubscriptionRepository,
        event_repo: EventRepository
    ):
        self.notification_repo = notification_repo
        self.subscription_repo = subscription_repo
        self.event_repo = event_repo
        self.channel_factory = ChannelFactory()
    
    async def create_notification(self, request: CreateNotificationRequest) -> str:
        """Cria uma nova notificação"""
        try:
            notification_data = {
                "empresa_id": request.empresa_id,
                "user_id": request.user_id,
                "event_type": request.event_type,
                "event_data": request.event_data,
                "title": request.title,
                "message": request.message,
                "channel": request.channel,
                "recipient": request.recipient,
                "priority": request.priority,
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
        
        for channel in request.channels:
            recipient = request.recipients.get(channel)
            if not recipient:
                logger.warning(f"Destinatário não fornecido para canal {channel}")
                continue
            
            try:
                notification_data = {
                    "empresa_id": request.empresa_id,
                    "user_id": request.user_id,
                    "event_type": request.event_type,
                    "event_data": request.event_data,
                    "title": request.title,
                    "message": request.message,
                    "channel": channel,
                    "recipient": recipient,
                    "priority": request.priority
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
            channel = self.channel_factory.create_channel(notification.channel, channel_config)
            
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
        """Busca configuração do canal para a empresa"""
        # Aqui você implementaria a lógica para buscar configurações específicas da empresa
        # Por enquanto, retorna configurações padrão baseadas no canal
        
        default_configs = {
            NotificationChannel.EMAIL: {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "noreply@mensura.com.br",
                "password": "your_password_here",
                "from_email": "noreply@mensura.com.br",
                "from_name": "Sistema Mensura"
            },
            NotificationChannel.WEBHOOK: {
                "timeout": 30,
                "headers": {"Content-Type": "application/json"}
            },
            NotificationChannel.WHATSAPP: {
                "account_sid": "your_twilio_sid",
                "auth_token": "your_twilio_token",
                "from_number": "+1234567890"
            },
            NotificationChannel.PUSH: {
                "server_key": "your_firebase_server_key"
            },
            NotificationChannel.IN_APP: {
                "websocket_manager": websocket_manager
            }
        }
        
        return default_configs.get(channel)
    
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
