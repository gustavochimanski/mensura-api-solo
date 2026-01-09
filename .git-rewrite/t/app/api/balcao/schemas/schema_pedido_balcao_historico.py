# app/api/balcao/schemas/schema_pedido_balcao_historico.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.api.balcao.models.model_pedido_balcao_historico import TipoOperacaoPedidoBalcao


class PedidoBalcaoHistoricoOut(BaseModel):
    id: int
    pedido_id: int
    cliente_id: Optional[int] = None
    usuario_id: Optional[int] = None
    tipo_operacao: TipoOperacaoPedidoBalcao
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


class HistoricoPedidoBalcaoResponse(BaseModel):
    """Resposta com histórico completo do pedido de balcão"""
    pedido_id: int
    historicos: List[PedidoBalcaoHistoricoOut]
    
    model_config = ConfigDict(from_attributes=True)


class PedidoBalcaoHistoricoListOut(BaseModel):
    id: int
    pedido_id: int
    tipo_operacao: TipoOperacaoPedidoBalcao
    tipo_operacao_descricao: str
    resumo_operacao: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PedidoBalcaoHistoricoCreate(BaseModel):
    pedido_id: int
    tipo_operacao: TipoOperacaoPedidoBalcao
    status_anterior: Optional[str] = None
    status_novo: Optional[str] = None
    descricao: Optional[str] = None
    observacoes: Optional[str] = None
    cliente_id: Optional[int] = None
    usuario_id: Optional[int] = None
    ip_origem: Optional[str] = None
    user_agent: Optional[str] = None

