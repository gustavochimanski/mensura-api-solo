"""
Schemas Pydantic para o módulo de chatbot
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# ==================== CHAT ====================

class Message(BaseModel):
    """Mensagem no chat"""
    role: str  # "user" ou "assistant"
    content: str


class ChatRequest(BaseModel):
    """Requisição de chat"""
    messages: List[Message]
    model: Optional[str] = "llama3.1:8b"
    temperature: Optional[float] = 0.7
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    """Resposta do chat"""
    response: str
    model: str


# ==================== PROMPTS ====================

class PromptCreate(BaseModel):
    """Criação de prompt"""
    key: str
    name: str
    content: str


class PromptUpdate(BaseModel):
    """Atualização de prompt"""
    name: str
    content: str


class PromptResponse(BaseModel):
    """Resposta de prompt"""
    id: int
    key: str
    name: str
    content: str
    is_default: bool
    empresa_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== CONVERSAS ====================

class ConversationCreate(BaseModel):
    """Criação de conversa"""
    session_id: Optional[str] = None
    user_id: str
    prompt_key: str
    model: str
    empresa_id: Optional[int] = None


class MessageCreate(BaseModel):
    """Criação de mensagem"""
    role: str
    content: str


class ConversationResponse(BaseModel):
    """Resposta de conversa"""
    id: int
    session_id: str
    user_id: str
    prompt_key: str
    model: str
    empresa_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Resposta de mensagem"""
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== NOTIFICAÇÕES ====================

class OrderNotificationRequest(BaseModel):
    """Requisição de notificação de pedido"""
    order_type: str  # cardapio, mesa, balcao
    client_name: str
    client_phone: str
    order_id: int
    items: str
    total: str
    address: Optional[str] = None  # Para delivery
    table_number: Optional[int] = None  # Para mesa
    estimated_time: Optional[str] = None  # Para delivery
    preparation_time: Optional[str] = None  # Para balcão


class NotificationResponse(BaseModel):
    """Resposta de notificação"""
    success: bool
    message: str
    data: Optional[dict] = None


# ==================== CONFIGURAÇÕES WHATSAPP ====================

class WhatsAppConfigUpdate(BaseModel):
    """Atualização de configuração do WhatsApp"""
    access_token: str
    phone_number_id: str
    business_account_id: str
    api_version: Optional[str] = "v22.0"
    send_mode: Optional[str] = "api"
    coexistence_enabled: Optional[bool] = False


class WhatsAppConfigResponse(BaseModel):
    """Resposta de configuração do WhatsApp"""
    access_token: str
    phone_number_id: str
    business_account_id: str
    api_version: str
    send_mode: str
    coexistence_enabled: bool
