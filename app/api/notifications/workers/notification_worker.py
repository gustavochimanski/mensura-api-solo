"""
Worker para processar notificações do RabbitMQ
"""

import asyncio
import logging
import sys
import os
from typing import Dict, Any

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from app.api.notifications.core.rabbitmq_client import get_rabbitmq_client
from app.api.notifications.channels.channel_factory import ChannelFactory
from ....database.db_connection import get_db
from app.api.notifications.repositories.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)

class NotificationWorker:
    """Worker para processar notificações do RabbitMQ"""
    
    def __init__(self):
        self.rabbitmq_client = None
        self.channel_factory = ChannelFactory()
        self.db = None
        self.notification_repo = None
        self._running = False
    
    async def initialize(self):
        """Inicializa o worker"""
        try:
            # Conecta ao RabbitMQ
            self.rabbitmq_client = await get_rabbitmq_client()
            
            # Conecta ao banco de dados
            self.db = next(get_db())
            self.notification_repo = NotificationRepository(self.db)
            
            logger.info("NotificationWorker inicializado")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar NotificationWorker: {e}")
            raise
    
    async def start(self):
        """Inicia o worker"""
        if not self.rabbitmq_client:
            await self.initialize()
        
        self._running = True
        logger.info("NotificationWorker iniciado")
        
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
            logger.error(f"Erro no NotificationWorker: {e}")
            self._running = False
            raise
    
    async def stop(self):
        """Para o worker"""
        self._running = False
        logger.info("NotificationWorker parado")
    
    async def _consume_notifications(self, channel: str):
        """Consome notificações de um canal específico"""
        try:
            queue_name = f"notifications.{channel}"
            
            async def process_notification(notification_data: Dict[str, Any]):
                await self._process_notification(notification_data, channel)
            
            await self.rabbitmq_client.consume_messages(queue_name, process_notification)
            
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
    
    def _get_channel_config(self, empresa_id: str, channel: str) -> Dict[str, Any]:
        """Busca configuração do canal para a empresa"""
        # Configurações padrão (em produção, buscar do banco de dados)
        default_configs = {
            "email": {
                "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
                "smtp_port": int(os.getenv("SMTP_PORT", 587)),
                "username": os.getenv("SMTP_USERNAME", "noreply@mensura.com.br"),
                "password": os.getenv("SMTP_PASSWORD", "your_password"),
                "from_email": os.getenv("SMTP_FROM_EMAIL", "noreply@mensura.com.br"),
                "from_name": os.getenv("SMTP_FROM_NAME", "Sistema Mensura")
            },
            "webhook": {
                "timeout": int(os.getenv("WEBHOOK_TIMEOUT", 30)),
                "headers": {"Content-Type": "application/json"}
            },
            "whatsapp": {
                "account_sid": os.getenv("TWILIO_ACCOUNT_SID", "your_twilio_sid"),
                "auth_token": os.getenv("TWILIO_AUTH_TOKEN", "your_twilio_token"),
                "from_number": os.getenv("TWILIO_WHATSAPP_NUMBER", "+1234567890")
            },
            "push": {
                "server_key": os.getenv("FIREBASE_SERVER_KEY", "your_firebase_server_key")
            },
            "in_app": {
                "websocket_manager": None  # Será injetado pelo sistema
            }
        }
        
        return default_configs.get(channel, {})
    
    async def _handle_notification_failure(self, notification, error_message: str, error_details: Dict[str, Any] = None):
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

async def main():
    """Função principal do worker"""
    worker = NotificationWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Recebido sinal de interrupção")
    except Exception as e:
        logger.error(f"Erro no worker: {e}")
    finally:
        await worker.stop()

if __name__ == "__main__":
    # Configura logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Executa o worker
    asyncio.run(main())
