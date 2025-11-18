from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime

# Schemas de Request
class CreateSubscriptionRequest(BaseModel):
    empresa_id: str = Field(..., description="ID da empresa")
    user_id: Optional[str] = Field(None, description="ID do usuário (opcional para configuração global)")
    event_type: str = Field(..., description="Tipo do evento a ser monitorado")
    channel: str = Field(..., description="Canal de notificação")
    channel_config: Dict[str, Any] = Field(..., description="Configurações do canal")
    active: bool = Field(True, description="Se a assinatura está ativa")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filtros para envio da notificação")

    @validator('channel_config')
    def validate_channel_config(cls, v, values):
        channel = values.get('channel')
        if not channel:
            return v
            
        # Validações específicas por canal
        if channel == 'email':
            if 'email' not in v:
                raise ValueError("Email é obrigatório para canal email")
        elif channel == 'webhook':
            if 'webhook_url' not in v:
                raise ValueError("webhook_url é obrigatório para canal webhook")
        elif channel == 'whatsapp':
            if 'phone' not in v:
                raise ValueError("phone é obrigatório para canal whatsapp")
        elif channel == 'push':
            if 'device_token' not in v:
                raise ValueError("device_token é obrigatório para canal push")
        
        return v

class UpdateSubscriptionRequest(BaseModel):
    channel_config: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None
    filters: Optional[Dict[str, Any]] = None

# Schemas de Response
class SubscriptionResponse(BaseModel):
    id: str
    empresa_id: str
    user_id: Optional[str]
    event_type: str
    channel: str
    channel_config: Dict[str, Any]
    active: bool
    filters: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SubscriptionListResponse(BaseModel):
    subscriptions: List[SubscriptionResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

# Schemas de filtro
class SubscriptionFilter(BaseModel):
    empresa_id: Optional[str] = None
    user_id: Optional[str] = None
    event_type: Optional[str] = None
    channel: Optional[str] = None
    active: Optional[bool] = None
