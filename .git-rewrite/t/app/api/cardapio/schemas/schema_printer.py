from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class TipoPedidoPrinterEnum(str, Enum):
    DELIVERY = "delivery"
    MESA = "mesa"
    BALCAO = "balcao"


class ItemPedidoPrinter(BaseModel):
    descricao: str
    quantidade: int
    preco: float
    observacao: Optional[str] = None


class PedidoParaImpressao(BaseModel):
    id: int
    status: str
    cliente_nome: str
    cliente_telefone: Optional[str] = None
    valor_total: float
    data_criacao: datetime
    endereco: Optional[str] = None
    meio_pagamento_descricao: Optional[str] = None
    observacao_geral: Optional[str] = None
    itens: List[ItemPedidoPrinter]




class RespostaImpressaoPrinter(BaseModel):
    sucesso: bool
    mensagem: str
    numero_pedido: Optional[int] = None

"""
Schemas específicos para comunicação com Printer API
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime


class ItemPedidoPrinter(BaseModel):
    """Item de pedido formatado para impressão"""
    descricao: str = Field(..., description="Descrição do produto")
    quantidade: int = Field(..., ge=1, description="Quantidade do item")
    preco: float = Field(..., ge=0, description="Preço unitário do item")
    observacao: Optional[str] = Field(None, description="Observação específica do item")


class PedidoPrinterRequest(BaseModel):
    """Pedido formatado para envio à Printer API"""
    numero: int = Field(..., ge=1, description="Número do pedido")
    status: str = Field(..., description="Status do pedido")
    cliente: str = Field(..., min_length=1, description="Nome do cliente")
    telefone_cliente: Optional[str] = Field(None, description="Telefone do cliente")
    itens: List[ItemPedidoPrinter] = Field(..., min_items=1, description="Lista de itens do pedido")
    subtotal: float = Field(..., ge=0, description="Subtotal do pedido")
    desconto: float = Field(0, ge=0, description="Valor do desconto")
    taxa_entrega: float = Field(0, ge=0, description="Taxa de entrega")
    taxa_servico: float = Field(0, ge=0, description="Taxa de serviço")
    total: float = Field(..., ge=0, description="Total do pedido")
    tipo_pagamento: str = Field(..., min_length=1, description="Tipo de pagamento")
    troco: Optional[float] = Field(None, ge=0, description="Valor do troco (valor pago - valor total do pedido)")
    observacao_geral: Optional[str] = Field(None, description="Observação geral do pedido")
    endereco: Optional[str] = Field(None, description="Endereço de entrega")
    data_criacao: datetime = Field(..., description="Data de criação do pedido")
    
    @validator('troco')
    def validar_troco_dinheiro(cls, v, values):
        tipo_pagamento = values.get('tipo_pagamento', '').upper()
        if tipo_pagamento == 'DINHEIRO' and v is None:
            # Para pagamento em dinheiro, o troco pode ser None se não foi informado o valor pago
            # Isso será tratado no service
            pass
        if v is not None and v < 0:
            raise ValueError('Troco não pode ser negativo')
        return v


class RespostaImpressaoPrinter(BaseModel):
    """Resposta da operação de impressão da Printer API"""
    sucesso: bool = Field(..., description="Se a impressão foi bem-sucedida")
    mensagem: str = Field(..., description="Mensagem de resultado")
    numero_pedido: Optional[int] = Field(None, description="Número do pedido impresso")
    timestamp: Optional[datetime] = Field(None, description="Timestamp da impressão")


class PedidoParaImpressao(BaseModel):
    """Pedido formatado para impressão com dados completos"""
    id: int = Field(..., description="ID do pedido")
    status: str = Field(..., description="Status do pedido")
    cliente_nome: str = Field(..., description="Nome do cliente")
    cliente_telefone: Optional[str] = Field(None, description="Telefone do cliente")
    valor_total: float = Field(..., description="Valor total do pedido")
    data_criacao: datetime = Field(..., description="Data de criação")
    endereco: Optional[str] = Field(None, description="Endereço do pedido")
    meio_pagamento_descricao: Optional[str] = Field(None, description="Descrição do meio de pagamento")
    observacao_geral: Optional[str] = Field(None, description="Observação geral")
    itens: List[ItemPedidoPrinter] = Field(..., description="Itens do pedido")


class DadosEmpresaPrinter(BaseModel):
    """Dados da empresa para impressão"""
    cnpj: Optional[str] = Field(None, description="CNPJ da empresa")
    endereco: Optional[str] = Field(None, description="Endereço completo da empresa")
    telefone: Optional[str] = Field(None, description="Telefone da empresa")


class PedidoPendenteImpressaoResponse(BaseModel):
    """Resposta formatada para pedidos pendentes de impressão"""
    numero: int = Field(..., description="Número do pedido")
    status: str = Field(..., description="Status do pedido")
    cliente: str = Field(..., description="Nome do cliente")
    telefone_cliente: Optional[str] = Field(None, description="Telefone do cliente")
    itens: List[ItemPedidoPrinter] = Field(..., description="Lista de itens do pedido")
    subtotal: float = Field(..., description="Subtotal do pedido")
    desconto: float = Field(0, description="Valor do desconto")
    taxa_entrega: float = Field(0, description="Taxa de entrega")
    taxa_servico: float = Field(0, description="Taxa de serviço")
    total: float = Field(..., description="Valor total do pedido")
    tipo_pagamento: str = Field(..., description="Tipo de pagamento")
    troco: Optional[float] = Field(None, description="Valor do troco (valor pago - valor total do pedido)")
    observacao_geral: Optional[str] = Field(None, description="Observação geral do pedido")
    endereco: Optional[str] = Field(None, description="Endereço de entrega")
    data_criacao: datetime = Field(..., description="Data de criação do pedido")
    empresa: DadosEmpresaPrinter = Field(..., description="Dados da empresa")
    tipo_pedido: TipoPedidoPrinterEnum = Field(..., description="Tipo do pedido: delivery, mesa ou balcao")


class PedidosPendentesPrinterResponse(BaseModel):
    """Resposta agrupada com pedidos pendentes por canal."""
    delivery: List[PedidoPendenteImpressaoResponse] = Field(default_factory=list, description="Pedidos pendentes de impressão do delivery")
    mesa: List[PedidoPendenteImpressaoResponse] = Field(default_factory=list, description="Pedidos pendentes de impressão das mesas")
    balcao: List[PedidoPendenteImpressaoResponse] = Field(default_factory=list, description="Pedidos pendentes de impressão do balcão")