from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
import uuid

Base = declarative_base()

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
    channel = Column(Enum(NotificationChannel), nullable=False, index=True)
    
    # Status e controle
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING, index=True)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)
    message_type = Column(Enum(MessageType), nullable=False, index=True, default=MessageType.UTILITY)
    
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
    
    status = Column(Enum(NotificationStatus), nullable=False)
    message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    notification = relationship("Notification", back_populates="logs")
