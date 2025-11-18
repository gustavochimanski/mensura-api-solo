import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType
from aio_pika.abc import AbstractIncomingMessage

logger = logging.getLogger(__name__)

class RabbitMQClient:
    """Cliente RabbitMQ para sistema de notificações"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        username: str = "guest",
        password: str = "guest",
        virtual_host: str = "/"
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.virtual_host = virtual_host
        
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchanges: Dict[str, aio_pika.Exchange] = {}
        self.queues: Dict[str, aio_pika.Queue] = {}
        
        self._running = False
        self._consumers: Dict[str, Callable] = {}
    
    async def connect(self):
        """Conecta ao RabbitMQ"""
        try:
            # Na URL AMQP, o vhost já começa com uma barra, então remover a barra inicial se existir
            # Exemplo: /mensura -> mensura (o RabbitMQ automaticamente adiciona /)
            vhost = self.virtual_host.lstrip('/') if self.virtual_host != '/' else ''
            
            connection_url = f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/{vhost}"
            self.connection = await aio_pika.connect_robust(connection_url)
            self.channel = await self.connection.channel()
            
            # Configura QoS para processar uma mensagem por vez
            await self.channel.set_qos(prefetch_count=1)
            
            logger.info(f"Conectado ao RabbitMQ em {self.host}:{self.port}")
            self._running = True
            
        except Exception as e:
            logger.error(f"Erro ao conectar ao RabbitMQ: {e}")
            raise
    
    async def disconnect(self):
        """Desconecta do RabbitMQ"""
        try:
            self._running = False
            
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            
            logger.info("Desconectado do RabbitMQ")
            
        except Exception as e:
            logger.error(f"Erro ao desconectar do RabbitMQ: {e}")
    
    async def create_exchange(
        self,
        name: str,
        exchange_type: ExchangeType = ExchangeType.TOPIC,
        durable: bool = True
    ) -> aio_pika.Exchange:
        """Cria um exchange"""
        try:
            exchange = await self.channel.declare_exchange(
                name=name,
                type=exchange_type,
                durable=durable
            )
            self.exchanges[name] = exchange
            logger.info(f"Exchange '{name}' criado")
            return exchange
            
        except Exception as e:
            logger.error(f"Erro ao criar exchange '{name}': {e}")
            raise
    
    async def create_queue(
        self,
        name: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False
    ) -> aio_pika.Queue:
        """Cria uma queue"""
        try:
            queue = await self.channel.declare_queue(
                name=name,
                durable=durable,
                exclusive=exclusive,
                auto_delete=auto_delete
            )
            self.queues[name] = queue
            logger.info(f"Queue '{name}' criada")
            return queue
            
        except Exception as e:
            logger.error(f"Erro ao criar queue '{name}': {e}")
            raise
    
    async def bind_queue_to_exchange(
        self,
        queue_name: str,
        exchange_name: str,
        routing_key: str
    ):
        """Vincula uma queue a um exchange com routing key"""
        try:
            queue = self.queues.get(queue_name)
            exchange = self.exchanges.get(exchange_name)
            
            if not queue or not exchange:
                raise ValueError(f"Queue '{queue_name}' ou Exchange '{exchange_name}' não encontrado")
            
            await queue.bind(exchange, routing_key)
            logger.info(f"Queue '{queue_name}' vinculada ao exchange '{exchange_name}' com routing key '{routing_key}'")
            
        except Exception as e:
            logger.error(f"Erro ao vincular queue '{queue_name}' ao exchange '{exchange_name}': {e}")
            raise
    
    async def publish_message(
        self,
        exchange_name: str,
        routing_key: str,
        message: Dict[str, Any],
        priority: int = 0,
        delivery_mode: DeliveryMode = DeliveryMode.PERSISTENT
    ) -> bool:
        """Publica uma mensagem"""
        try:
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                raise ValueError(f"Exchange '{exchange_name}' não encontrado")
            
            # Adiciona timestamp à mensagem
            message["timestamp"] = datetime.utcnow().isoformat()
            message["message_id"] = f"{routing_key}_{datetime.utcnow().timestamp()}"
            
            # Serializa a mensagem
            message_body = json.dumps(message, ensure_ascii=False).encode()
            
            # Cria a mensagem
            rabbit_message = Message(
                message_body,
                delivery_mode=delivery_mode,
                priority=priority,
                content_type="application/json"
            )
            
            # Publica a mensagem
            await exchange.publish(rabbit_message, routing_key=routing_key)
            
            logger.info(f"Mensagem publicada no exchange '{exchange_name}' com routing key '{routing_key}'")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao publicar mensagem: {e}")
            return False
    
    async def consume_messages(
        self,
        queue_name: str,
        callback: Callable[[Dict[str, Any]], None],
        auto_ack: bool = False
    ):
        """Consome mensagens de uma queue"""
        try:
            queue = self.queues.get(queue_name)
            if not queue:
                raise ValueError(f"Queue '{queue_name}' não encontrada")
            
            # Registra o callback
            self._consumers[queue_name] = callback
            
            # Inicia o consumo
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    if not self._running:
                        break
                    
                    try:
                        # Processa a mensagem
                        async with message.process():
                            # Deserializa a mensagem
                            message_data = json.loads(message.body.decode())
                            
                            # Chama o callback
                            await callback(message_data)
                            
                            if not auto_ack:
                                message.ack()
                                
                    except Exception as e:
                        logger.error(f"Erro ao processar mensagem: {e}")
                        if not auto_ack:
                            message.nack(requeue=True)
            
        except Exception as e:
            logger.error(f"Erro ao consumir mensagens da queue '{queue_name}': {e}")
            raise
    
    async def setup_notification_system(self):
        """Configura o sistema de notificações no RabbitMQ"""
        try:
            # Cria exchanges
            await self.create_exchange("notifications", ExchangeType.TOPIC)
            await self.create_exchange("events", ExchangeType.TOPIC)
            await self.create_exchange("dead_letter", ExchangeType.DIRECT)
            
            # Cria queues principais
            await self.create_queue("notifications.email")
            await self.create_queue("notifications.whatsapp")
            await self.create_queue("notifications.webhook")
            await self.create_queue("notifications.push")
            await self.create_queue("notifications.in_app")
            
            # Cria queue para eventos
            await self.create_queue("events.processor")
            
            # Cria queue de dead letter
            await self.create_queue("notifications.failed", durable=True)
            
            # Vincula queues aos exchanges
            await self.bind_queue_to_exchange("notifications.email", "notifications", "notification.email")
            await self.bind_queue_to_exchange("notifications.whatsapp", "notifications", "notification.whatsapp")
            await self.bind_queue_to_exchange("notifications.webhook", "notifications", "notification.webhook")
            await self.bind_queue_to_exchange("notifications.push", "notifications", "notification.push")
            await self.bind_queue_to_exchange("notifications.in_app", "notifications", "notification.in_app")
            
            await self.bind_queue_to_exchange("events.processor", "events", "event.*")
            
            # Configura dead letter
            await self.bind_queue_to_exchange("notifications.failed", "dead_letter", "failed")
            
            logger.info("Sistema de notificações configurado no RabbitMQ")
            
        except Exception as e:
            logger.error(f"Erro ao configurar sistema de notificações: {e}")
            raise
    
    async def publish_notification(
        self,
        channel: str,
        notification_data: Dict[str, Any]
    ) -> bool:
        """Publica uma notificação"""
        routing_key = f"notification.{channel}"
        return await self.publish_message("notifications", routing_key, notification_data)
    
    async def publish_event(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """Publica um evento"""
        routing_key = f"event.{event_type}"
        return await self.publish_message("events", routing_key, event_data)
    
    async def start_consumers(self):
        """Inicia todos os consumidores"""
        try:
            tasks = []
            
            # Consumidor para processamento de eventos
            if "events.processor" in self.queues:
                task = asyncio.create_task(
                    self.consume_messages("events.processor", self._handle_event)
                )
                tasks.append(task)
            
            # Consumidores para notificações por canal
            for channel in ["email", "whatsapp", "webhook", "push", "in_app"]:
                queue_name = f"notifications.{channel}"
                if queue_name in self.queues:
                    task = asyncio.create_task(
                        self.consume_messages(queue_name, self._handle_notification)
                    )
                    tasks.append(task)
            
            # Aguarda todas as tarefas
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Erro ao iniciar consumidores: {e}")
            raise
    
    async def _handle_event(self, event_data: Dict[str, Any]):
        """Processa eventos"""
        try:
            logger.info(f"Processando evento: {event_data.get('event_type')}")
            # Aqui você implementaria a lógica de processamento de eventos
            # Por exemplo, chamar o EventProcessor
            
        except Exception as e:
            logger.error(f"Erro ao processar evento: {e}")
    
    async def _handle_notification(self, notification_data: Dict[str, Any]):
        """Processa notificações"""
        try:
            logger.info(f"Processando notificação: {notification_data.get('channel')}")
            # Aqui você implementaria a lógica de processamento de notificações
            # Por exemplo, chamar o NotificationService
            
        except Exception as e:
            logger.error(f"Erro ao processar notificação: {e}")
    
    def is_connected(self) -> bool:
        """Verifica se está conectado"""
        return self.connection is not None and not self.connection.is_closed
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Retorna informações da conexão"""
        return {
            "host": self.host,
            "port": self.port,
            "virtual_host": self.virtual_host,
            "connected": self.is_connected(),
            "exchanges": list(self.exchanges.keys()),
            "queues": list(self.queues.keys())
        }

# Instância global do cliente RabbitMQ
rabbitmq_client: Optional[RabbitMQClient] = None

async def get_rabbitmq_client() -> RabbitMQClient:
    """Retorna a instância global do cliente RabbitMQ"""
    global rabbitmq_client
    
    if rabbitmq_client is None:
        # Configurações do RabbitMQ (podem vir de variáveis de ambiente)
        import os
        from app.config.settings import RABBITMQ_CONFIG
        
        rabbitmq_client = RabbitMQClient(
            host=os.getenv("RABBITMQ_HOST", RABBITMQ_CONFIG['host']),
            port=int(os.getenv("RABBITMQ_PORT", RABBITMQ_CONFIG['port'])),
            username=os.getenv("RABBITMQ_USERNAME", RABBITMQ_CONFIG['username']),
            password=os.getenv("RABBITMQ_PASSWORD", RABBITMQ_CONFIG['password']),
            virtual_host=os.getenv("RABBITMQ_VHOST", RABBITMQ_CONFIG['virtual_host'])
        )
        
        await rabbitmq_client.connect()
        await rabbitmq_client.setup_notification_system()
    
    return rabbitmq_client

async def close_rabbitmq_client():
    """Fecha a conexão com RabbitMQ"""
    global rabbitmq_client
    
    if rabbitmq_client:
        await rabbitmq_client.disconnect()
        rabbitmq_client = None
