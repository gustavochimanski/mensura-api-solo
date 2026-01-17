from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class ChatbotConfigBase(BaseModel):
    """Schema base para configuração do chatbot"""
    nome: str = Field(..., min_length=1, max_length=100, description="Nome do chatbot")
    personalidade: Optional[str] = Field(None, description="Descrição da personalidade do chatbot")
    aceita_pedidos_whatsapp: bool = Field(True, description="Se aceita fazer pedidos pelo WhatsApp")
    link_redirecionamento: Optional[str] = Field(None, max_length=500, description="Link para redirecionar quando não aceita pedidos")
    mensagem_boas_vindas: Optional[str] = Field(None, description="Mensagem de boas-vindas personalizada")
    mensagem_redirecionamento: Optional[str] = Field(None, description="Mensagem quando redireciona para link")
    ativo: bool = Field(True, description="Se a configuração está ativa")


class ChatbotConfigCreate(ChatbotConfigBase):
    """Schema para criar uma nova configuração do chatbot"""
    empresa_id: int = Field(..., gt=0, description="ID da empresa")


class ChatbotConfigUpdate(BaseModel):
    """Schema para atualizar uma configuração do chatbot"""
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    personalidade: Optional[str] = None
    aceita_pedidos_whatsapp: Optional[bool] = None
    link_redirecionamento: Optional[str] = Field(None, max_length=500)
    mensagem_boas_vindas: Optional[str] = None
    mensagem_redirecionamento: Optional[str] = None
    ativo: Optional[bool] = None


class ChatbotConfigResponse(BaseModel):
    """Schema de resposta para configuração do chatbot"""
    id: int
    empresa_id: int
    nome: str
    personalidade: Optional[str] = None
    aceita_pedidos_whatsapp: bool
    link_redirecionamento: Optional[str] = None
    mensagem_boas_vindas: Optional[str] = None
    mensagem_redirecionamento: Optional[str] = None
    ativo: bool
    created_at: datetime
    updated_at: datetime
    
    # Informações adicionais
    empresa_nome: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
