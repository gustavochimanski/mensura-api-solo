# app/api/mesas/schemas/schema_mesa_historico.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.api.mesas.models.model_mesa_historico import TipoOperacaoMesa


class MesaHistoricoOut(BaseModel):
    id: int
    mesa_id: int
    cliente_id: Optional[int] = None
    usuario_id: Optional[int] = None
    tipo_operacao: TipoOperacaoMesa
    status_anterior: Optional[str] = None
    status_novo: Optional[str] = None
    descricao: Optional[str] = None
    observacoes: Optional[str] = None
    ip_origem: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    
    # Campos calculados
    tipo_operacao_descricao: str
    resumo_operacao: str
    
    # Campos relacionados
    usuario: Optional[str] = None  # Nome do usuário que executou a operação
    
    model_config = ConfigDict(from_attributes=True)


class HistoricoDaMesaResponse(BaseModel):
    """Resposta com histórico completo da mesa (seguindo padrão do histórico de pedidos)"""
    mesa_id: int
    historicos: List[MesaHistoricoOut]
    
    model_config = ConfigDict(from_attributes=True)


class MesaHistoricoListOut(BaseModel):
    id: int
    mesa_id: int
    tipo_operacao: TipoOperacaoMesa
    tipo_operacao_descricao: str
    resumo_operacao: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MesaHistoricoCreate(BaseModel):
    mesa_id: int
    tipo_operacao: TipoOperacaoMesa
    status_anterior: Optional[str] = None
    status_novo: Optional[str] = None
    descricao: Optional[str] = None
    observacoes: Optional[str] = None
    cliente_id: Optional[int] = None
    usuario_id: Optional[int] = None
    ip_origem: Optional[str] = None
    user_agent: Optional[str] = None
