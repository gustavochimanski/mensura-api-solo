from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from app.utils.database_utils import now_trimmed
from sqlalchemy import DateTime
from pydantic import ConfigDict


class ChatbotConfigModel(Base):
    """Modelo para configurações do chatbot por empresa"""
    __tablename__ = "chatbot_configs"
    __table_args__ = (
        Index("idx_chatbot_config_empresa", "empresa_id"),
        Index("idx_chatbot_config_ativo", "ativo"),
        {"schema": "chatbot"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relacionamentos
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="RESTRICT"), nullable=False, unique=True)
    empresa = relationship("EmpresaModel", backref="chatbot_config")
    
    # Configurações básicas
    nome = Column(String(100), nullable=False, default="Assistente Virtual")  # Nome do chatbot
    personalidade = Column(Text, nullable=True)  # Descrição da personalidade do chatbot
    
    # Configurações de pedidos
    aceita_pedidos_whatsapp = Column(Boolean, default=True, nullable=False)  # Se aceita fazer pedidos pelo WhatsApp
    link_redirecionamento = Column(String(500), nullable=True)  # Link para redirecionar quando não aceita pedidos
    
    # Configurações adicionais
    mensagem_boas_vindas = Column(Text, nullable=True)  # Mensagem de boas-vindas personalizada
    mensagem_redirecionamento = Column(Text, nullable=True)  # Mensagem quando redireciona para link
    ativo = Column(Boolean, default=True, nullable=False)  # Se a configuração está ativa
    
    # Timestamps
    created_at = Column(DateTime, default=now_trimmed, nullable=False)
    updated_at = Column(DateTime, default=now_trimmed, onupdate=now_trimmed, nullable=False)

    model_config = ConfigDict(from_attributes=True)
