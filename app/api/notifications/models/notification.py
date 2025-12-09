from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Enum, TypeDecorator
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
import uuid

from ....database.db_connection import Base

class EnumValueType(TypeDecorator):
    """TypeDecorator que força o SQLAlchemy a usar o valor do enum, não o nome"""
    impl = String
    cache_ok = True
    
    def __init__(self, enum_class, enum_name=None, schema=None, name=None, *args, **kwargs):
        self.enum_class = enum_class
        # Usa enum_name ou name (ambos são aceitos)
        self.enum_name = enum_name or name
        self.schema = schema
        
        # Remove argumentos que não são válidos para String.__init__()
        # name e schema são específicos do Enum, não do String
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ['name', 'schema']}
        
        # Usa o Enum do SQLAlchemy para validação no banco, mas serializa usando o valor
        # Não cria tipo no banco (create_type=False) e não usa enum nativo (native_enum=False)
        if self.enum_name:
            self.enum_type = Enum(
                enum_class,
                name=self.enum_name,
                schema=self.schema,
                create_type=False,
                native_enum=False
            )
        else:
            self.enum_type = None
        
        # Chama super().__init__() apenas com argumentos válidos para String
        super().__init__(*args, **filtered_kwargs)
    
    def process_bind_param(self, value, dialect):
        """Converte enum para seu valor (string) antes de salvar no banco"""
        if value is None:
            return None
        # Sempre extrai o valor do enum, nunca usa o nome
        if isinstance(value, self.enum_class):
            return value.value.lower()  # Garante minúsculas
        if isinstance(value, str):
            return value.lower()  # Normaliza strings
        # Se for outro tipo de enum (ex: Pydantic), extrai o valor
        if hasattr(value, 'value'):
            return str(value.value).lower()
        # Última tentativa: converte para string e normaliza
        return str(value).lower()
    
    def process_result_value(self, value, dialect):
        """Converte string do banco de volta para enum"""
        if value is None:
            return None
        return self.enum_class(value.lower())

class NotificationStatus(PyEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"

class NotificationChannel(PyEnum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    PUSH = "push"
    WEBHOOK = "webhook"
    IN_APP = "in_app"
    SMS = "sms"
    TELEGRAM = "telegram"

class NotificationPriority(PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class MessageType(PyEnum):
    """Tipos de mensagem para classificação e controle de disparo"""
    MARKETING = "marketing"
    UTILITY = "utility"
    TRANSACTIONAL = "transactional"
    PROMOTIONAL = "promotional"
    ALERT = "alert"
    SYSTEM = "system"
    NEWS = "news"

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": "notifications"}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    
    # Evento que gerou a notificação
    event_type = Column(String, nullable=False, index=True)
    event_data = Column(JSON, nullable=True)
    
    # Conteúdo da notificação
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    # Usa EnumValueType para garantir que o SQLAlchemy sempre use o valor do enum, não o nome
    channel = Column(EnumValueType(NotificationChannel, name='notificationchannel', schema='notifications'), nullable=False, index=True)
    
    # Status e controle
    status = Column(EnumValueType(NotificationStatus, name='notificationstatus', schema='notifications'), default=NotificationStatus.PENDING, index=True)
    priority = Column(EnumValueType(NotificationPriority, name='notificationpriority', schema='notifications'), default=NotificationPriority.NORMAL)
    message_type = Column(EnumValueType(MessageType, name='messagetype', schema='notifications'), nullable=False, index=True, default=MessageType.UTILITY)
    
    # Configurações de entrega
    recipient = Column(String, nullable=False)  # email, phone, webhook_url, etc.
    channel_metadata = Column(JSON, nullable=True)  # configurações específicas do canal
    
    # Controle de tentativas
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_attempt_at = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    
    # Relacionamentos
    logs = relationship("NotificationLog", back_populates="notification", cascade="all, delete-orphan")

class NotificationLog(Base):
    __tablename__ = "notification_logs"
    __table_args__ = {"schema": "notifications"}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    notification_id = Column(String, ForeignKey("notifications.notifications.id"), nullable=False)
    
    status = Column(EnumValueType(NotificationStatus, name='notificationstatus', schema='notifications'), nullable=False)
    message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    notification = relationship("Notification", back_populates="logs")
