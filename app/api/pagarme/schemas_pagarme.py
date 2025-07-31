from pydantic import BaseModel, Field
from typing import Optional

class PagamentoRequest(BaseModel):
    pedido_id: int = Field(..., description="ID do pedido a ser pago")
    metodo_pagamento: str = Field(..., description="boleto, credit_card ou pix")
    token_cartao: Optional[str] = Field(None, description="Token do cartão (se for crédito)")


class PagamentoResponse(BaseModel):
    status: str
    transaction_id: str
    boleto_url: Optional[str] = None
    pix_qr_code_url: Optional[str] = None
