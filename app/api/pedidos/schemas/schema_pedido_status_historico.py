from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, constr
from app.api.cadastros.schemas.schema_shared_enums import PedidoStatusEnum

class AlterarStatusPedidoRequest(BaseModel):
    pedido_id: int
    status: PedidoStatusEnum
    motivo: Optional[str] = None
    observacoes: Optional[str] = None
    criado_por: Optional[constr(max_length=60)] = None
    ip_origem: Optional[constr(max_length=45)] = None
    user_agent: Optional[constr(max_length=500)] = None

class AlterarStatusPedidoBody(BaseModel):
    status: PedidoStatusEnum
    motivo: Optional[str] = None
    observacoes: Optional[str] = None
    criado_por: Optional[constr(max_length=60)] = None
    ip_origem: Optional[constr(max_length=45)] = None
    user_agent: Optional[constr(max_length=500)] = None

class PedidoStatusHistoricoOut(BaseModel):
    """
    Schema de histórico de pedidos compatível com modelo unificado.
    
    Mantém compatibilidade com histórico simples (status) e detalhado (tipo_operacao).
    """
    id: int
    pedido_id: int
    status: Optional[PedidoStatusEnum] = None  # Pode ser None se for histórico detalhado sem status
    status_anterior: Optional[PedidoStatusEnum] = None  # Status anterior (modelo unificado)
    status_novo: Optional[PedidoStatusEnum] = None  # Status novo (modelo unificado)
    tipo_operacao: Optional[str] = None  # Tipo de operação (modelo unificado)
    descricao: Optional[str] = None  # Descrição da operação (modelo unificado)
    motivo: Optional[str] = None
    observacoes: Optional[str] = None
    criado_em: datetime
    criado_por: Optional[str] = None
    usuario_id: Optional[int] = None  # ID do usuário (modelo unificado)
    cliente_id: Optional[int] = None  # ID do cliente (modelo unificado)
    ip_origem: Optional[str] = None
    user_agent: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
    
    def model_post_init(self, __context):
        """Garante compatibilidade: se status não está preenchido, usa status_novo ou status_anterior."""
        if self.status is None:
            if self.status_novo is not None:
                self.status = self.status_novo
            elif self.status_anterior is not None:
                self.status = self.status_anterior

class HistoricoDoPedidoResponse(BaseModel):
    pedido_id: int
    historicos: List[PedidoStatusHistoricoOut]

    model_config = ConfigDict(from_attributes=True)

