from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import asyncio

from ..core.rabbitmq_client import get_rabbitmq_client
from ..core.event_bus import EventType
from ..channels.channel_factory import ChannelFactory
from ..repositories.notification_repository import NotificationRepository
from ..repositories.subscription_repository import SubscriptionRepository
from ..repositories.event_repository import EventRepository

logger = logging.getLogger(__name__)

class RabbitMQNotificationService:
    """Serviço de notificações usando RabbitMQ"""
    
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
        self._rabbitmq_client = None
        self._running = False
    
    async def initialize(self):
        """Inicializa o serviço com RabbitMQ"""
        try:
            self._rabbitmq_client = await get_rabbitmq_client()
            self._running = True
            logger.info("RabbitMQNotificationService inicializado")
        except Exception as e:
            logger.error(f"Erro ao inicializar RabbitMQNotificationService: {e}")
            raise
    
    async def start_consumers(self):
        """Inicia consumidores RabbitMQ para notificações"""
        if not self._running:
            await self.initialize()
        
        try:
            # Inicia consumidores para cada canal
            tasks = []
            
            for channel in ["email", "whatsapp", "webhook", "push", "in_app"]:
                task = asyncio.create_task(
                    self._consume_notifications(channel)
                )
                tasks.append(task)
            
            # Aguarda todas as tarefas
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Erro ao iniciar consumidores de notificações: {e}")
            raise
    
    async def _consume_notifications(self, channel: str):
        """Consome notificações de um canal específico"""
        try:
            queue_name = f"notifications.{channel}"
            
            async def process_notification(notification_data: Dict[str, Any]):
                await self._process_notification(notification_data, channel)
            
            await self._rabbitmq_client.consume_messages(queue_name, process_notification)
            
        except Exception as e:
            logger.error(f"Erro ao consumir notificações do canal {channel}: {e}")
    
    async def _process_notification(self, notification_data: Dict[str, Any], channel: str):
        """Processa uma notificação"""
        try:
            notification_id = notification_data.get("id")
            if not notification_id:
                logger.error("ID da notificação não encontrado")
                return
            
            # Busca a notificação no banco
            notification = self.notification_repo.get_by_id(notification_id)
            if not notification:
                logger.error(f"Notificação {notification_id} não encontrada")
                return
            
            # Verifica se já foi processada
            if notification.status != "pending":
                logger.info(f"Notificação {notification_id} já foi processada")
                return
            
            # Busca configuração do canal
            channel_config = self._get_channel_config(notification.empresa_id, channel)
            if not channel_config:
                logger.error(f"Configuração não encontrada para canal {channel}")
                await self._mark_notification_failed(notification_id, f"Configuração do canal {channel} não encontrada")
                return
            
            # Cria instância do canal
            channel_instance = self.channel_factory.create_channel(channel, channel_config)
            
            # Envia a notificação
            result = await channel_instance.send(
                recipient=notification.recipient,
                title=notification.title,
                message=notification.message,
                channel_metadata=notification.channel_metadata
            )
            
            if result.success:
                # Marca como enviada
                self.notification_repo.update_status(
                    notification_id,
                    "sent",
                    attempts=notification.attempts + 1
                )
                self.notification_repo.add_log(
                    notification_id,
                    "sent",
                    result.message,
                    {"external_id": result.external_id}
                )
                logger.info(f"Notificação {notification_id} enviada com sucesso via {channel}")
            else:
                # Trata falha
                await self._handle_notification_failure(notification, result.message, result.error_details)
                
        except Exception as e:
            logger.error(f"Erro ao processar notificação {notification_data.get('id')}: {e}")
            await self._handle_notification_failure(
                notification_data.get('id'),
                str(e),
                {"exception": str(e)}
            )
    
    async def send_notification(
        self,
        empresa_id: str,
        user_id: Optional[str],
        event_type: str,
        title: str,
        message: str,
        channel: str,
        recipient: str,
        priority: str = "normal",
        channel_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Envia notificação via RabbitMQ"""
        try:
            if not self._rabbitmq_client:
                await self.initialize()
            
            # Cria notificação no banco
            notification_data = {
                "empresa_id": empresa_id,
                "user_id": user_id,
                "event_type": event_type,
                "title": title,
                "message": message,
                "channel": channel,
                "recipient": recipient,
                "priority": priority,
                "channel_metadata": channel_metadata or {}
            }
            
            notification = self.notification_repo.create(notification_data)
            
            # Prepara dados para RabbitMQ
            rabbitmq_data = {
                "id": notification.id,
                "empresa_id": empresa_id,
                "user_id": user_id,
                "event_type": event_type,
                "title": title,
                "message": message,
                "channel": channel,
                "recipient": recipient,
                "priority": priority,
                "channel_metadata": channel_metadata or {},
                "created_at": notification.created_at.isoformat()
            }
            
            # Publica no RabbitMQ
            success = await self._rabbitmq_client.publish_notification(
                channel=channel,
                notification_data=rabbitmq_data
            )
            
            if success:
                logger.info(f"Notificação {notification.id} publicada no RabbitMQ")
                return notification.id
            else:
                logger.error(f"Falha ao publicar notificação {notification.id} no RabbitMQ")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao enviar notificação: {e}")
            raise
    
    async def send_bulk_notifications(
        self,
        empresa_id: str,
        event_type: str,
        title: str,
        message: str,
        channels: List[str],
        recipients: Dict[str, str],
        priority: str = "normal",
        channel_metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Envia notificações em lote via RabbitMQ"""
        try:
            notification_ids = []
            
            for channel in channels:
                recipient = recipients.get(channel)
                if not recipient:
                    logger.warning(f"Destinatário não fornecido para canal {channel}")
                    continue
                
                notification_id = await self.send_notification(
                    empresa_id=empresa_id,
                    user_id=None,
                    event_type=event_type,
                    title=title,
                    message=message,
                    channel=channel,
                    recipient=recipient,
                    priority=priority,
                    channel_metadata=channel_metadata
                )
                
                if notification_id:
                    notification_ids.append(notification_id)
            
            return notification_ids
            
        except Exception as e:
            logger.error(f"Erro ao enviar notificações em lote: {e}")
            raise
    
    def _get_channel_config(self, empresa_id: str, channel: str) -> Optional[Dict[str, Any]]:
        """Busca configuração do canal para a empresa"""
        # Aqui você implementaria a lógica para buscar configurações específicas da empresa
        # Por enquanto, retorna configurações padrão baseadas no canal
        
        default_configs = {
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "noreply@mensura.com.br",
                "password": "your_password_here",
                "from_email": "noreply@mensura.com.br",
                "from_name": "Sistema Mensura"
            },
            "webhook": {
                "timeout": 30,
                "headers": {"Content-Type": "application/json"}
            },
            "whatsapp": {
                "account_sid": "your_twilio_sid",
                "auth_token": "your_twilio_token",
                "from_number": "+1234567890"
            },
            "push": {
                "server_key": "your_firebase_server_key"
            },
            "in_app": {
                "websocket_manager": None  # Será injetado pelo sistema
            }
        }
        
        return default_configs.get(channel)
    
    async def _handle_notification_failure(self, notification, error_message: str, error_details: Optional[Dict[str, Any]] = None):
        """Trata falha no envio de notificação"""
        if isinstance(notification, str):
            # Se for string, é o ID
            notification_id = notification
            notification = self.notification_repo.get_by_id(notification_id)
        
        if not notification:
            return
        
        if notification.attempts + 1 >= notification.max_attempts:
            # Máximo de tentativas atingido
            self.notification_repo.update_status(
                notification.id,
                "failed",
                attempts=notification.attempts + 1
            )
            self.notification_repo.add_log(
                notification.id,
                "failed",
                f"Falha definitiva: {error_message}",
                error_details
            )
            logger.error(f"Notificação {notification.id} falhou definitivamente após {notification.attempts + 1} tentativas")
        else:
            # Agenda nova tentativa
            self.notification_repo.increment_attempts(notification.id)
            self.notification_repo.add_log(
                notification.id,
                "retrying",
                f"Tentativa {notification.attempts + 1} falhou: {error_message}",
                error_details
            )
            logger.warning(f"Notificação {notification.id} falhou, será tentada novamente")
    
    async def _mark_notification_failed(self, notification_id: str, error_message: str):
        """Marca notificação como falhada"""
        self.notification_repo.update_status(notification_id, "failed")
        self.notification_repo.add_log(notification_id, "failed", error_message)
    
    async def get_notification_status(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """Busca status de uma notificação"""
        try:
            notification = self.notification_repo.get_by_id(notification_id)
            if not notification:
                return None
            
            logs = self.notification_repo.get_logs(notification_id)
            
            return {
                "id": notification.id,
                "status": notification.status,
                "attempts": notification.attempts,
                "max_attempts": notification.max_attempts,
                "created_at": notification.created_at.isoformat(),
                "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
                "failed_at": notification.failed_at.isoformat() if notification.failed_at else None,
                "logs": [
                    {
                        "status": log.status,
                        "message": log.message,
                        "created_at": log.created_at.isoformat(),
                        "error_details": log.error_details
                    }
                    for log in logs
                ]
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar status da notificação {notification_id}: {e}")
            return None
    
    async def retry_failed_notifications(self, limit: int = 50) -> int:
        """Tenta reenviar notificações que falharam"""
        try:
            failed_notifications = self.notification_repo.get_failed_notifications(limit=limit)
            retried_count = 0
            
            for notification in failed_notifications:
                try:
                    # Prepara dados para reenvio
                    rabbitmq_data = {
                        "id": notification.id,
                        "empresa_id": notification.empresa_id,
                        "user_id": notification.user_id,
                        "event_type": notification.event_type,
                        "title": notification.title,
                        "message": notification.message,
                        "channel": notification.channel,
                        "recipient": notification.recipient,
                        "priority": notification.priority,
                        "channel_metadata": notification.channel_metadata,
                        "created_at": notification.created_at.isoformat()
                    }
                    
                    # Publica no RabbitMQ para reprocessamento
                    success = await self._rabbitmq_client.publish_notification(
                        channel=notification.channel,
                        notification_data=rabbitmq_data
                    )
                    
                    if success:
                        retried_count += 1
                        logger.info(f"Notificação {notification.id} enviada para reprocessamento")
                    
                except Exception as e:
                    logger.error(f"Erro ao reenviar notificação {notification.id}: {e}")
            
            logger.info(f"Reenviadas {retried_count} notificações falhadas")
            return retried_count
            
        except Exception as e:
            logger.error(f"Erro ao reenviar notificações falhadas: {e}")
            return 0
    
    async def get_rabbitmq_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do RabbitMQ"""
        try:
            if not self._rabbitmq_client:
                await self.initialize()
            
            return self._rabbitmq_client.get_connection_info()
            
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas do RabbitMQ: {e}")
            return {}
    
    async def stop(self):
        """Para o serviço"""
        self._running = False
        logger.info("RabbitMQNotificationService parado")
