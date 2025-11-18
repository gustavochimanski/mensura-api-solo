from sqlalchemy import Column, String, Boolean, JSON, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class NotificationSubscription(Base):
    __tablename__ = "notification_subscriptions"
    __table_args__ = {"schema": "notifications"}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)  # null = configuração global da empresa
    
    # Evento que será monitorado
    event_type = Column(String, nullable=False, index=True)
    
    # Canal de notificação
    channel = Column(String, nullable=False, index=True)
    
    # Configurações do canal
    channel_config = Column(JSON, nullable=False)  # {email: "user@email.com", webhook_url: "https://..."}
    
    # Controle de ativação
    active = Column(Boolean, default=True, index=True)
    
    # Filtros opcionais
    filters = Column(JSON, nullable=True)  # condições para enviar a notificação
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índices compostos para performance
    __table_args__ = (
        Index('idx_empresa_event_channel', 'empresa_id', 'event_type', 'channel'),
        Index('idx_user_event_channel', 'user_id', 'event_type', 'channel'),
    )
