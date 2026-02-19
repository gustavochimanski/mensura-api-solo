# app/api/chatbot/schemas/schema_carrinho.py
from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, condecimal
from decimal import Decimal

from app.api.chatbot.models.model_carrinho import TipoEntregaCarrinho


class TipoEntregaCarrinhoEnum(str, Enum):
    """Enum para tipo de entrega do carrinho"""
    DELIVERY = "DELIVERY"
    RETIRADA = "RETIRADA"
    BALCAO = "BALCAO"
    MESA = "MESA"


# ======================================================================
# ==================== SCHEMAS DE REQUEST =============================
# ======================================================================

class ItemAdicionalComplementoCarrinhoRequest(BaseModel):
    """Adicional dentro de um complemento do carrinho"""
    adicional_id: int
    quantidade: int = Field(ge=1, default=1)


class ItemComplementoCarrinhoRequest(BaseModel):
    """Complemento com seus adicionais selecionados no carrinho"""
    complemento_id: int
    adicionais: List[ItemAdicionalComplementoCarrinhoRequest] = Field(default_factory=list)


class ItemCarrinhoRequest(BaseModel):
    """Item de produto no carrinho"""
    produto_cod_barras: str
    quantidade: int = Field(ge=1)
    observacao: Optional[str] = None
    complementos: Optional[List[ItemComplementoCarrinhoRequest]] = Field(default=None)


class ReceitaCarrinhoRequest(BaseModel):
    """Item de receita no carrinho"""
    receita_id: int
    quantidade: int = Field(ge=1)
    observacao: Optional[str] = None
    complementos: Optional[List[ItemComplementoCarrinhoRequest]] = Field(default=None)


class ComboCarrinhoRequest(BaseModel):
    """Item de combo no carrinho"""
    combo_id: int
    quantidade: int = Field(ge=1, default=1)
    complementos: Optional[List[ItemComplementoCarrinhoRequest]] = Field(default=None)


class CriarCarrinhoRequest(BaseModel):
    """Request para criar ou atualizar carrinho"""
    user_id: str = Field(..., description="Telefone do cliente (WhatsApp)")
    empresa_id: int
    tipo_entrega: TipoEntregaCarrinhoEnum
    
    # Itens do carrinho
    itens: Optional[List[ItemCarrinhoRequest]] = Field(default_factory=list)
    receitas: Optional[List[ReceitaCarrinhoRequest]] = Field(default_factory=list)
    combos: Optional[List[ComboCarrinhoRequest]] = Field(default_factory=list)
    
    # Informações adicionais
    endereco_id: Optional[int] = None
    meio_pagamento_id: Optional[int] = None
    cupom_id: Optional[int] = None
    mesa_id: Optional[int] = None
    observacoes: Optional[str] = None
    observacao_geral: Optional[str] = None
    num_pessoas: Optional[int] = None
    troco_para: Optional[condecimal(max_digits=18, decimal_places=2)] = None


class AdicionarItemCarrinhoRequest(BaseModel):
    """Request para adicionar item ao carrinho"""
    user_id: str
    item: Optional[ItemCarrinhoRequest] = None
    receita: Optional[ReceitaCarrinhoRequest] = None
    combo: Optional[ComboCarrinhoRequest] = None


class AtualizarItemCarrinhoRequest(BaseModel):
    """Request para atualizar item do carrinho"""
    item_id: int
    quantidade: Optional[int] = Field(None, ge=1)
    observacao: Optional[str] = None
    complementos: Optional[List[ItemComplementoCarrinhoRequest]] = None


class RemoverItemCarrinhoRequest(BaseModel):
    """Request para remover item do carrinho"""
    item_id: int


# ======================================================================
# ==================== SCHEMAS DE RESPONSE =============================
# ======================================================================

class ItemComplementoAdicionalCarrinhoResponse(BaseModel):
    """Adicional dentro de um complemento do carrinho"""
    id: int
    adicional_id: int
    quantidade: int
    preco_unitario: Decimal
    total: Decimal
    
    model_config = ConfigDict(from_attributes=True)


class ItemComplementoCarrinhoResponse(BaseModel):
    """Complemento com seus adicionais no carrinho"""
    id: int
    complemento_id: int
    total: Decimal
    adicionais: List[ItemComplementoAdicionalCarrinhoResponse] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)


class ItemCarrinhoResponse(BaseModel):
    """Item do carrinho"""
    id: int
    produto_cod_barras: Optional[str] = None
    combo_id: Optional[int] = None
    receita_id: Optional[int] = None
    quantidade: int
    preco_unitario: Decimal
    preco_total: Decimal
    observacao: Optional[str] = None
    produto_descricao_snapshot: Optional[str] = None
    produto_imagem_snapshot: Optional[str] = None
    complementos: List[ItemComplementoCarrinhoResponse] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)


class CarrinhoResponse(BaseModel):
    """Resposta completa do carrinho"""
    id: int
    user_id: str
    empresa_id: int
    tipo_entrega: TipoEntregaCarrinhoEnum
    mesa_id: Optional[int] = None
    cliente_id: Optional[int] = None
    endereco_id: Optional[int] = None
    meio_pagamento_id: Optional[int] = None
    cupom_id: Optional[int] = None
    observacoes: Optional[str] = None
    observacao_geral: Optional[str] = None
    num_pessoas: Optional[int] = None
    subtotal: Decimal
    desconto: Decimal
    taxa_entrega: Decimal
    taxa_servico: Decimal
    valor_total: Decimal
    troco_para: Optional[Decimal] = None
    endereco_snapshot: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    itens: List[ItemCarrinhoResponse] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)


class CarrinhoResumoResponse(BaseModel):
    """Resumo do carrinho (sem itens detalhados)"""
    id: int
    user_id: str
    empresa_id: int
    tipo_entrega: TipoEntregaCarrinhoEnum
    quantidade_itens: int
    valor_total: Decimal
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
