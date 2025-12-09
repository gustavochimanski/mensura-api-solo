from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from .notification_schemas import MessageType, NotificationChannel, NotificationPriority

class DispatchMessageRequest(BaseModel):
    """Schema para disparo de mensagens com tipo determinado"""
    empresa_id: str = Field(..., description="ID da empresa")
    message_type: MessageType = Field(..., description="Tipo da mensagem (marketing, utility, transactional, etc)")
    title: str = Field(..., min_length=1, max_length=255, description="Título da mensagem")
    message: str = Field(..., min_length=1, description="Conteúdo da mensagem")
    
    # Destinatários
    user_ids: Optional[List[str]] = Field(None, description="IDs específicos de usuários (opcional)")
    recipient_emails: Optional[List[str]] = Field(None, description="Lista de emails para envio")
    recipient_phones: Optional[List[str]] = Field(None, description="Lista de telefones para WhatsApp/SMS")
    
    # Canais de envio
    channels: List[NotificationChannel] = Field(..., description="Canais para envio da mensagem")
    
    # Configurações opcionais
    priority: NotificationPriority = Field(NotificationPriority.NORMAL, description="Prioridade da mensagem")
    event_type: Optional[str] = Field(None, description="Tipo do evento relacionado (opcional)")
    event_data: Optional[Dict[str, Any]] = Field(None, description="Dados adicionais do evento")
    channel_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados específicos por canal")
    
    # Configurações de agendamento
    scheduled_at: Optional[datetime] = Field(None, description="Data/hora para envio agendado (opcional)")
    
    @field_validator('channels')
    @classmethod
    def validate_channels(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Pelo menos um canal deve ser especificado')
        return v
    
    @model_validator(mode='after')
    def validate_recipients(self):
        """Valida que pelo menos um tipo de destinatário foi fornecido"""
        has_user_ids = self.user_ids and len(self.user_ids) > 0
        has_emails = self.recipient_emails and len(self.recipient_emails) > 0
        has_phones = self.recipient_phones and len(self.recipient_phones) > 0
        
        if not (has_user_ids or has_emails or has_phones):
            raise ValueError('Deve fornecer pelo menos um: user_ids, recipient_emails ou recipient_phones')
        
        return self
    
    @field_validator('message_type')
    @classmethod
    def validate_message_type(cls, v):
        """Validações específicas por tipo de mensagem"""
        if v == MessageType.MARKETING:
            # Mensagens de marketing podem ter restrições adicionais
            pass
        return v

class DispatchMessageResponse(BaseModel):
    """Resposta do disparo de mensagens"""
    success: bool = Field(..., description="Indica se o disparo foi iniciado com sucesso")
    message_type: MessageType = Field(..., description="Tipo da mensagem disparada")
    notification_ids: List[str] = Field(..., description="IDs das notificações criadas")
    total_recipients: int = Field(..., description="Total de destinatários")
    channels_used: List[NotificationChannel] = Field(..., description="Canais utilizados")
    scheduled: bool = Field(False, description="Indica se a mensagem foi agendada")
    scheduled_at: Optional[datetime] = Field(None, description="Data/hora do agendamento")

class BulkDispatchRequest(BaseModel):
    """Schema para disparo em massa de mensagens"""
    empresa_id: str = Field(..., description="ID da empresa")
    message_type: MessageType = Field(..., description="Tipo da mensagem")
    title: str = Field(..., min_length=1, max_length=255, description="Título da mensagem")
    message: str = Field(..., min_length=1, description="Conteúdo da mensagem")
    
    # Filtros para seleção de destinatários
    filter_by_empresa: bool = Field(True, description="Enviar para todos os usuários da empresa")
    filter_by_user_type: Optional[str] = Field(None, description="Filtrar por tipo de usuário")
    filter_by_tags: Optional[List[str]] = Field(None, description="Filtrar por tags")
    
    # Canais
    channels: List[NotificationChannel] = Field(..., description="Canais para envio")
    priority: NotificationPriority = Field(NotificationPriority.NORMAL, description="Prioridade")
    
    # Limites
    max_recipients: Optional[int] = Field(None, ge=1, description="Limite máximo de destinatários")
    
    @field_validator('channels')
    @classmethod
    def validate_channels(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Pelo menos um canal deve ser especificado')
        return v

class MessageDispatchStats(BaseModel):
    """Estatísticas de disparo de mensagens"""
    message_type: MessageType
    total_sent: int = Field(..., description="Total de mensagens enviadas")
    total_failed: int = Field(..., description="Total de mensagens falhadas")
    total_pending: int = Field(..., description="Total de mensagens pendentes")
    by_channel: Dict[str, int] = Field(..., description="Estatísticas por canal")
    created_at: datetime = Field(..., description="Data de criação")

