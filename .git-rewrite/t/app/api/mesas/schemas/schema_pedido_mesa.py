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


class StatusPedidoMesaEnum(str, Enum):
    """Status de pedidos de mesa alinhados ao fluxo de delivery (sem o status 'S')."""

    PENDENTE = "P"
    IMPRESSAO = "I"
    PREPARANDO = "R"
    ENTREGUE = "E"
    CANCELADO = "C"
    EDITADO = "D"
    EM_EDICAO = "X"
    AGUARDANDO_PAGAMENTO = "A"


class PedidoMesaItemIn(BaseModel):
    produto_cod_barras: constr(min_length=1)
    quantidade: int = Field(ge=1, default=1)
    observacao: Optional[constr(max_length=255)] = None
    adicionais: Optional[List[ItemAdicionalRequest]] = Field(
        default=None,
        description="Lista de adicionais selecionados para o item",
    )
    adicionais_ids: Optional[List[int]] = Field(
        default=None,
        description="(LEGADO) IDs de adicionais vinculados ao produto",
    )


class PedidoMesaCreate(BaseModel):
    empresa_id: int = Field(..., description="ID da empresa dona da mesa/pedido")
    mesa_id: int = Field(
        ...,
        description="Código numérico da mesa (número real). O sistema buscará a mesa pelo código (campo 'codigo'), não pelo ID."
    )
    cliente_id: Optional[int] = None
    observacoes: Optional[constr(max_length=500)] = None
    num_pessoas: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Número de pessoas na mesa; opcional. Informe quando desejar registrar o total de pessoas atendidas."
    )
    itens: Optional[List[PedidoMesaItemIn]] = None
    produtos: Optional[ProdutosPedidoRequest] = Field(
        default=None,
        description="Objeto estruturado de produtos (itens/receitas/combos) vindo do checkout",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Criar pedido com num_pessoas",
                    "value": {
                        "mesa_id": 1,
                        "cliente_id": 123,
                        "num_pessoas": 4,
                        "observacoes": "sem cebola",
                        "itens": [
                            {"produto_cod_barras": "789...", "quantidade": 2}
                        ]
                    }
                },
                {
                    "summary": "Criar pedido sem num_pessoas (opcional)",
                    "value": {
                        "mesa_id": 1,
                        "observacoes": "água com gás",
                        "itens": [
                            {"produto_cod_barras": "123...", "quantidade": 1}
                        ]
                    }
                }
            ]
        }
    )


class PedidoMesaItemOut(BaseModel):
    id: int
    produto_cod_barras: str
    quantidade: int
    preco_unitario: float
    observacao: Optional[str] = None
    produto_descricao_snapshot: Optional[str] = None
    produto_imagem_snapshot: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PedidoMesaOut(BaseModel):
    id: int
    empresa_id: int
    numero_pedido: str
    mesa_id: int
    cliente_id: Optional[int]
    num_pessoas: Optional[int]
    status: StatusPedidoMesaEnum
    status_descricao: str
    observacoes: Optional[str] = None
    valor_total: float
    itens: List[PedidoMesaItemOut] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    produtos: ProdutosPedidoOut = Field(default_factory=ProdutosPedidoOut)

    model_config = ConfigDict(from_attributes=True)


class AdicionarItemRequest(PedidoMesaItemIn):
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
    status: StatusPedidoMesaEnum


class FecharContaMesaRequest(BaseModel):
    """Payload para fechar a conta do pedido informando pagamento."""
    meio_pagamento_id: Optional[int] = None
    troco_para: Optional[float] = None


class AtualizarObservacoesRequest(BaseModel):
    """Payload para atualizar as observações do pedido."""
    observacoes: Optional[constr(max_length=500)] = Field(
        default=None,
        description="Observações do pedido. Pode ser None para limpar as observações."
    )


