from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"

class NotificationChannel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    PUSH = "push"
    WEBHOOK = "webhook"
    IN_APP = "in_app"
    SMS = "sms"
    TELEGRAM = "telegram"

class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

# Schemas de Request
class CreateNotificationRequest(BaseModel):
    empresa_id: str = Field(..., description="ID da empresa")
    user_id: Optional[str] = Field(None, description="ID do usuário (opcional)")
    event_type: str = Field(..., description="Tipo do evento que gerou a notificação")
    event_data: Optional[Dict[str, Any]] = Field(None, description="Dados do evento")
    title: str = Field(..., min_length=1, max_length=255, description="Título da notificação")
    message: str = Field(..., min_length=1, description="Mensagem da notificação")
    channel: NotificationChannel = Field(..., description="Canal de notificação")
    recipient: str = Field(..., description="Destinatário da notificação")
    priority: NotificationPriority = Field(NotificationPriority.NORMAL, description="Prioridade da notificação")
    channel_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados específicos do canal")
    max_attempts: int = Field(3, ge=1, le=10, description="Número máximo de tentativas")

class SendNotificationRequest(BaseModel):
    empresa_id: str = Field(..., description="ID da empresa")
    user_id: Optional[str] = Field(None, description="ID do usuário")
    event_type: str = Field(..., description="Tipo do evento")
    event_data: Optional[Dict[str, Any]] = Field(None, description="Dados do evento")
    title: str = Field(..., description="Título da notificação")
    message: str = Field(..., description="Mensagem da notificação")
    channels: List[NotificationChannel] = Field(..., description="Canais para envio")
    recipients: Dict[NotificationChannel, str] = Field(..., description="Destinatários por canal")
    priority: NotificationPriority = Field(NotificationPriority.NORMAL, description="Prioridade")

# Schemas de Response
class NotificationResponse(BaseModel):
    id: str
    empresa_id: str
    user_id: Optional[str]
    event_type: str
    event_data: Optional[Dict[str, Any]]
    title: str
    message: str
    channel: NotificationChannel
    status: NotificationStatus
    priority: NotificationPriority
    recipient: str
    channel_metadata: Optional[Dict[str, Any]]
    attempts: int
    max_attempts: int
    last_attempt_at: Optional[datetime]
    next_retry_at: Optional[datetime]
    created_at: datetime
    sent_at: Optional[datetime]
    failed_at: Optional[datetime]

    class Config:
        from_attributes = True

class NotificationLogResponse(BaseModel):
    id: str
    notification_id: str
    status: NotificationStatus
    message: Optional[str]
    error_details: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationWithLogsResponse(NotificationResponse):
    logs: List[NotificationLogResponse] = []

# Schemas de filtro e paginação
class NotificationFilter(BaseModel):
    empresa_id: Optional[str] = None
    user_id: Optional[str] = None
    event_type: Optional[str] = None
    channel: Optional[NotificationChannel] = None
    status: Optional[NotificationStatus] = None
    priority: Optional[NotificationPriority] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None

class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
