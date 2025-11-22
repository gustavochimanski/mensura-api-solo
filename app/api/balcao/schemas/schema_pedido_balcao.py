from __future__ import annotations

from enum import Enum
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, constr, model_validator

from app.api.cardapio.schemas.schema_pedido import (
    ItemAdicionalRequest,
    ProdutosPedidoRequest,
    ProdutosPedidoOut,
)


class StatusPedidoBalcaoEnum(str, Enum):
    """Status de pedidos de balcão alinhados ao fluxo de delivery (sem o status 'S')."""

    PENDENTE = "P"
    IMPRESSAO = "I"
    PREPARANDO = "R"
    ENTREGUE = "E"
    CANCELADO = "C"
    EDITADO = "D"
    EM_EDICAO = "X"
    AGUARDANDO_PAGAMENTO = "A"


class PedidoBalcaoItemIn(BaseModel):
    produto_cod_barras: constr(min_length=1)
    quantidade: int = Field(ge=1, default=1)
    observacao: Optional[constr(max_length=255)] = None
    adicionais: Optional[List[ItemAdicionalRequest]] = Field(
        default=None,
        description="Lista de adicionais do item",
    )
    adicionais_ids: Optional[List[int]] = Field(
        default=None,
        description="(LEGADO) IDs de adicionais vinculados ao produto",
    )


class PedidoBalcaoCreate(BaseModel):
    empresa_id: int = Field(
        ...,
        description="ID da empresa responsável pelo pedido de balcão."
    )
    mesa_id: Optional[int] = Field(
        None,
        description="Código numérico da mesa (opcional). Se informado, o sistema buscará a mesa pelo código."
    )
    cliente_id: Optional[int] = None
    observacoes: Optional[constr(max_length=500)] = None
    itens: Optional[List[PedidoBalcaoItemIn]] = None
    produtos: Optional[ProdutosPedidoRequest] = Field(
        default=None,
        description="Objeto estruturado de produtos (itens/receitas/combos)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Criar pedido de balcão sem mesa",
                    "value": {
                        "cliente_id": 123,
                        "observacoes": "Para viagem",
                        "itens": [
                            {"produto_cod_barras": "789...", "quantidade": 2}
                        ]
                    }
                },
                {
                    "summary": "Criar pedido de balcão com mesa (opcional)",
                    "value": {
                        "mesa_id": 1,
                        "observacoes": "Balcão",
                        "itens": [
                            {"produto_cod_barras": "123...", "quantidade": 1}
                        ]
                    }
                }
            ]
        }
    )


class PedidoBalcaoItemOut(BaseModel):
    id: int
    produto_cod_barras: str
    quantidade: int
    preco_unitario: float
    observacao: Optional[str] = None
    produto_descricao_snapshot: Optional[str] = None
    produto_imagem_snapshot: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PedidoBalcaoOut(BaseModel):
    id: int
    empresa_id: int
    numero_pedido: str
    mesa_id: Optional[int] = None
    cliente_id: Optional[int]
    status: StatusPedidoBalcaoEnum
    status_descricao: str
    observacoes: Optional[str] = None
    valor_total: float
    itens: List[PedidoBalcaoItemOut] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    produtos: ProdutosPedidoOut = Field(default_factory=ProdutosPedidoOut)

    model_config = ConfigDict(from_attributes=True)


class AdicionarItemRequest(PedidoBalcaoItemIn):
    pass


class AdicionarProdutoGenericoRequest(BaseModel):
    """
    Schema genérico para adicionar qualquer tipo de produto (item normal, receita ou combo).
    O sistema identifica automaticamente o tipo baseado nos campos preenchidos.
    
    **Regras de identificação:**
    - Se `produto_cod_barras` estiver presente → Item normal (produto)
    - Se `receita_id` estiver presente → Receita
    - Se `combo_id` estiver presente → Combo
    
    **Validação:** Apenas um dos campos (produto_cod_barras, receita_id, combo_id) deve ser informado.
    """
    # Item normal (produto com código de barras)
    produto_cod_barras: Optional[constr(min_length=1)] = Field(
        default=None,
        description="Código de barras do produto (para itens normais)"
    )
    
    # Receita
    receita_id: Optional[int] = Field(
        default=None,
        description="ID da receita (para receitas)"
    )
    
    # Combo
    combo_id: Optional[int] = Field(
        default=None,
        description="ID do combo (para combos)"
    )
    
    # Campos comuns
    quantidade: int = Field(ge=1, default=1, description="Quantidade do item")
    observacao: Optional[constr(max_length=255)] = Field(
        default=None,
        description="Observação específica do item"
    )
    adicionais: Optional[List[ItemAdicionalRequest]] = Field(
        default=None,
        description="Lista de adicionais do item (com quantidade por adicional)"
    )
    adicionais_ids: Optional[List[int]] = Field(
        default=None,
        description="(LEGADO) IDs de adicionais vinculados; quantidade implícita = 1"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Adicionar produto normal",
                    "value": {
                        "produto_cod_barras": "7891234567890",
                        "quantidade": 2,
                        "observacao": "Bem passado",
                        "adicionais": [
                            {"adicional_id": 10, "quantidade": 1}
                        ]
                    }
                },
                {
                    "summary": "Adicionar receita",
                    "value": {
                        "receita_id": 5,
                        "quantidade": 1,
                        "observacao": "Sem pimenta",
                        "adicionais": [
                            {"adicional_id": 20, "quantidade": 2}
                        ]
                    }
                },
                {
                    "summary": "Adicionar combo",
                    "value": {
                        "combo_id": 3,
                        "quantidade": 2,
                        "adicionais": [
                            {"adicional_id": 25, "quantidade": 1}
                        ]
                    }
                }
            ]
        }
    )
    
    @model_validator(mode="after")
    def _validar_tipo_produto(self):
        """Valida que exatamente um tipo de produto foi informado"""
        tipos_informados = sum([
            self.produto_cod_barras is not None,
            self.receita_id is not None,
            self.combo_id is not None,
        ])
        
        if tipos_informados == 0:
            raise ValueError(
                "É obrigatório informar um dos campos: 'produto_cod_barras', 'receita_id' ou 'combo_id'"
            )
        
        if tipos_informados > 1:
            raise ValueError(
                "Informe apenas um tipo de produto: 'produto_cod_barras', 'receita_id' ou 'combo_id'"
            )
        
        return self


class RemoverItemResponse(BaseModel):
    ok: bool
    pedido_id: int
    valor_total: float


class AtualizarStatusPedidoRequest(BaseModel):
    status: StatusPedidoBalcaoEnum


class FecharContaBalcaoRequest(BaseModel):
    """Payload para fechar a conta do pedido informando pagamento."""
    meio_pagamento_id: Optional[int] = None
    troco_para: Optional[float] = None

