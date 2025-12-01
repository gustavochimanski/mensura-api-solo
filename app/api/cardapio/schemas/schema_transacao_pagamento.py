from datetime import datetime
from typing import Optional, Any, Dict

from pydantic import BaseModel, ConfigDict

from app.api.shared.schemas.schema_shared_enums import (
    PagamentoGatewayEnum,
    PagamentoMetodoEnum,
    PagamentoStatusEnum,
)


class TransacaoBase(BaseModel):
    pedido_id: int
    gateway: PagamentoGatewayEnum
    metodo: PagamentoMetodoEnum
    valor: float
    moeda: str = "BRL"


class TransacaoCreateRequest(TransacaoBase):
    payload_solicitacao: Optional[Dict[str, Any]] = None
    provider_transaction_id: Optional[str] = None
    qr_code: Optional[str] = None
    qr_code_base64: Optional[str] = None


class TransacaoResponse(TransacaoBase):
    id: int
    status: PagamentoStatusEnum
    provider_transaction_id: Optional[str]
    qr_code: Optional[str]
    qr_code_base64: Optional[str]
    payload_solicitacao: Optional[dict]
    payload_retorno: Optional[dict]
    autorizado_em: Optional[datetime]
    pago_em: Optional[datetime]
    cancelado_em: Optional[datetime]
    estornado_em: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConsultarTransacaoResponse(BaseModel):
    status: PagamentoStatusEnum
    provider_transaction_id: Optional[str]
    payload: Dict[str, Any]
    qr_code: Optional[str]
    qr_code_base64: Optional[str]


class TransacaoStatusUpdateRequest(BaseModel):
    status: PagamentoStatusEnum
    provider_transaction_id: Optional[str] = None
    payload_retorno: Optional[Dict[str, Any]] = None
    qr_code: Optional[str] = None
    qr_code_base64: Optional[str] = None
