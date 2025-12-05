from enum import Enum
from typing import List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, ConfigDict, condecimal, Field, field_validator, model_validator

from app.api.cadastros.schemas.schema_meio_pagamento import MeioPagamentoResponse, MeioPagamentoTipoEnum
from app.api.shared.schemas.schema_shared_enums import (
    PedidoStatusEnum,
    TipoEntregaEnum,
    OrigemPedidoEnum,
    PagamentoGatewayEnum,
    PagamentoMetodoEnum,
    PagamentoStatusEnum,
)
from app.api.cadastros.schemas.schema_cliente import ClienteOut
from app.api.cadastros.schemas.schema_endereco import EnderecoOut
from app.api.cadastros.schemas.schema_entregador import EntregadorOut


class EnderecoPedidoDetalhe(BaseModel):
    endereco_selecionado: EnderecoOut | dict | None = None
    outros_enderecos: list[EnderecoOut | dict] = Field(default_factory=list)


from app.api.cadastros.schemas.schema_cupom import CupomOut
from app.api.cardapio.schemas.schema_transacao_pagamento import TransacaoResponse
from app.api.pedidos.schemas.schema_pedido_status_historico import PedidoStatusHistoricoOut
from app.api.empresas.schemas.schema_empresa import EmpresaResponse


class MeioPagamentoKanbanResponse(BaseModel):
    """Schema simplificado para meio de pagamento no kanban (sem timestamps)"""
    id: int
    nome: str
    tipo: MeioPagamentoTipoEnum
    ativo: bool
    model_config = ConfigDict(from_attributes=True)


class PedidoPagamentoResumo(BaseModel):
    status: PagamentoStatusEnum | None = None
    esta_pago: bool = False
    valor: float | None = None
    atualizado_em: datetime | None = None
    meio_pagamento_id: int | None = None
    meio_pagamento_nome: str | None = None
    metodo: PagamentoMetodoEnum | None = None
    gateway: PagamentoGatewayEnum | None = None
    provider_transaction_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ======================================================================
# ============================ ADMIN ===================================
# ======================================================================
class PedidoKanbanResponse(BaseModel):
    id: int
    status: PedidoStatusEnum
    cliente: ClienteOut | None = None
    valor_total: float
    data_criacao: datetime
    observacao_geral: Optional[str] = None
    endereco: str | None = None
    meio_pagamento: Optional[MeioPagamentoKanbanResponse] = None  # Objeto simplificado do meio de pagamento
    entregador: dict | None = None  # {"id": int, "nome": str}
    pagamento: PedidoPagamentoResumo | None = None
    acertado_entregador: bool | None = None
    tempo_entrega_minutos: float | None = None
    troco_para: Optional[float] = None  # Valor do troco (para pagamento em dinheiro)
    tipo_pedido: Optional[str] = None  # "DELIVERY", "MESA", "BALCAO" - para identificar origem
    numero_pedido: Optional[str] = None  # Número do pedido (ex: "PED-001", "M123")
    # Campos para mesa/balcão
    mesa_id: Optional[int] = None  # ID da mesa
    mesa: Optional[dict] = None  # Objeto mesa {"id": int}
    mesa_numero: Optional[str] = None  # Número da mesa (ex: "M12", "12")
    referencia_mesa: Optional[str] = None  # Referência da mesa (ex: "Mesa 12", "M12")
    # Campos alternativos para cliente
    nome_cliente: Optional[str] = None  # Nome do cliente (alternativa ao objeto cliente)
    telefone_cliente: Optional[str] = None  # Telefone do cliente (alternativa ao objeto cliente)
    model_config = ConfigDict(from_attributes=True)


class KanbanAgrupadoResponse(BaseModel):
    """Resposta do kanban agrupada por categoria de pedidos"""
    delivery: List[PedidoKanbanResponse] = Field(default_factory=list, description="Pedidos de delivery")
    balcao: List[PedidoKanbanResponse] = Field(default_factory=list, description="Pedidos de balcão")
    mesas: List[PedidoKanbanResponse] = Field(default_factory=list, description="Pedidos de mesas")


class EditarPedidoRequest(BaseModel):
    meio_pagamento_id: Optional[int] = None
    endereco_id: Optional[int] = None
    cupom_id: Optional[int] = None
    observacao_geral: Optional[str] = None
    troco_para: Optional[condecimal(max_digits=18, decimal_places=2)] = None

class ItemPedidoEditar(BaseModel):
    id: Optional[int] = None           # ID do item já existente no pedido
    produto_cod_barras: Optional[str] = None  # Apenas para adicionar
    quantidade: Optional[int] = None
    observacao: Optional[str] = None
    acao: str  # "novo-item", "atualizar", "remover"

class ModoEdicaoRequest(BaseModel):
    modo_edicao: bool  # True = modo edição (X), False = editado (D)


# ======================================================================
# ============================ CLIENTE =================================
# ======================================================================


class ItemAdicionalRequest(BaseModel):
    """Adicional vinculado a um item do pedido, com quantidade."""
    adicional_id: int
    quantidade: int = Field(ge=1, default=1, description="Quantidade deste adicional para o item")


class ItemPedidoRequest(BaseModel):
    produto_cod_barras: str
    quantidade: int
    observacao: Optional[str] = None

    # Novo formato: adicionais com quantidade
    adicionais: Optional[List[ItemAdicionalRequest]] = Field(
        default=None,
        description="Lista de adicionais do item, com quantidade por adicional",
    )

    # LEGADO: manter por compatibilidade (apenas IDs, quantidade = 1 por adicional)
    adicionais_ids: Optional[List[int]] = Field(
        default=None,
        description="(LEGADO) IDs de adicionais vinculados ao produto; quantidade implícita = 1",
    )


class ReceitaPedidoRequest(BaseModel):
    """
    Item de receita no checkout.

    Referencia apenas o ID da receita (não usa código de barras).
    """
    receita_id: int
    quantidade: int
    observacao: Optional[str] = None

    adicionais: Optional[List[ItemAdicionalRequest]] = Field(
        default=None,
        description="Lista de adicionais vinculados à receita para este item",
    )

    # LEGADO / compat: permite também enviar apenas IDs
    adicionais_ids: Optional[List[int]] = Field(
        default=None,
        description="(LEGADO) IDs de adicionais vinculados à receita; quantidade implícita = 1",
    )


class ComboItemAdicionalPedidoRequest(BaseModel):
    """Mantido apenas para compatibilidade retroativa (NÃO USAR NO NOVO FLUXO)."""
    produto_cod_barras: str
    adicionais: List[ItemAdicionalRequest]


class ComboPedidoRequest(BaseModel):
    combo_id: int
    quantidade: int = Field(ge=1, default=1)
    adicionais: Optional[List[ItemAdicionalRequest]] = Field(
        default=None,
        description="Lista de adicionais aplicados ao combo (por ID, sem usar código de barras)",
    )


class ProdutosPedidoRequest(BaseModel):
    """Agrupa os produtos do checkout (itens, receitas e combos)."""
    itens: List[ItemPedidoRequest] = Field(
        default_factory=list,
        description="Lista de itens (produtos com código de barras)",
    )
    receitas: Optional[List[ReceitaPedidoRequest]] = Field(
        default=None,
        description="Lista de receitas selecionadas no checkout",
    )
    combos: Optional[List[ComboPedidoRequest]] = Field(
        default=None,
        description="Lista de combos opcionais no checkout",
    )

class MeioPagamentoParcialRequest(BaseModel):
    """Define um meio de pagamento com valor parcial"""
    id: Optional[int] = Field(
        default=None,
        description="ID do meio de pagamento (novo campo preferencial)",
    )
    meio_pagamento_id: Optional[int] = Field(
        default=None,
        description="(LEGADO) ID do meio de pagamento; será descontinuado",
    )
    valor: condecimal(max_digits=18, decimal_places=2)

    @model_validator(mode="after")
    def _validar_ids(self):
        # Garante que pelo menos um identificador foi enviado
        if self.id is None and self.meio_pagamento_id is None:
            raise ValueError("Informe 'id' ou 'meio_pagamento_id' para o meio de pagamento.")
        return self

class PreviewCheckoutResponse(BaseModel):
    """Schema de resposta para preview do checkout (sem criar pedido)"""
    subtotal: float
    taxa_entrega: float
    taxa_servico: float
    valor_total: float
    desconto: float
    distancia_km: Optional[float] = None
    empresa_id: Optional[int] = None
    tempo_entrega_minutos: Optional[float] = None


class TipoPedidoCheckoutEnum(str, Enum):
    DELIVERY = "DELIVERY"
    MESA = "MESA"
    BALCAO = "BALCAO"


class FinalizarPedidoRequest(BaseModel):
    empresa_id: Optional[int] = None
    cliente_id: Optional[str] = None  # agora será setado pelo token
    endereco_id: Optional[int] = None  # Opcional para permitir retirada
    meios_pagamento: Optional[List[MeioPagamentoParcialRequest]] = None  # Lista de meios de pagamento
    tipo_entrega: TipoEntregaEnum = TipoEntregaEnum.DELIVERY
    tipo_pedido: TipoPedidoCheckoutEnum = TipoPedidoCheckoutEnum.DELIVERY
    origem: OrigemPedidoEnum = OrigemPedidoEnum.WEB
    observacao_geral: Optional[str] = None
    cupom_id: Optional[int] = None
    troco_para: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    # Novo formato: produtos agrupados
    produtos: Optional[ProdutosPedidoRequest] = Field(
        default=None,
        description="Objeto que agrupa itens, receitas e combos do checkout.",
    )
    # LEGADO: campos diretos na raiz (serão descontinuados)
    itens: Optional[List[ItemPedidoRequest]] = None
    receitas: Optional[List[ReceitaPedidoRequest]] = Field(
        default=None,
        description="(LEGADO) Lista de receitas selecionadas no checkout",
    )
    combos: Optional[List[ComboPedidoRequest]] = Field(
        default=None,
        description="(LEGADO) Lista de combos opcionais no checkout",
    )
    mesa_codigo: Optional[str] = Field(
        default=None,
        description="Código numérico da mesa. Obrigatório quando tipo_pedido=MESA.",
    )
    num_pessoas: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Número de pessoas na mesa. Opcional para pedidos de mesa.",
    )
    
    model_config = ConfigDict(extra="forbid")

    @field_validator("cliente_id", mode="before")
    @classmethod
    def _coagir_cliente_id_para_str(cls, v):
        if v is None or v == "":
            return None
        return str(v)

    @model_validator(mode="after")
    def _ajustar_tipo_e_validar(self):
        # Garante que existe pelo menos UM produto (item normal, receita ou combo),
        # mas não obriga que existam itens "normais". Pode ser só receita ou só combo.
        produtos_payload = getattr(self, "produtos", None)
        itens_novos = produtos_payload.itens if produtos_payload and produtos_payload.itens is not None else []
        receitas_novas = produtos_payload.receitas if produtos_payload and produtos_payload.receitas is not None else []
        combos_novos = produtos_payload.combos if produtos_payload and produtos_payload.combos is not None else []

        itens_legados = self.itens or []
        receitas_legadas = self.receitas or []
        combos_legados = self.combos or []

        if not (itens_novos or receitas_novas or combos_novos or itens_legados or receitas_legadas or combos_legados):
            raise ValueError(
                "É obrigatório informar ao menos um produto em "
                "'produtos.itens', 'produtos.receitas', 'produtos.combos' "
                "ou nos campos legados 'itens', 'receitas', 'combos'."
            )

        if self.tipo_pedido in {TipoPedidoCheckoutEnum.MESA, TipoPedidoCheckoutEnum.BALCAO}:
            # Força tipo_entrega como RETIRADA para fluxos não delivery
            self.tipo_entrega = TipoEntregaEnum.RETIRADA
            if not self.empresa_id:
                raise ValueError("Campo 'empresa_id' é obrigatório para pedidos de mesa ou balcão.")
            if self.tipo_pedido == TipoPedidoCheckoutEnum.MESA and not self.mesa_codigo:
                raise ValueError("Campo 'mesa_codigo' é obrigatório para pedidos de mesa.")
        else:
            self.tipo_entrega = TipoEntregaEnum.DELIVERY
        return self


class ItemPedidoResponse(BaseModel):
    id: int
    produto_cod_barras: Optional[str] = None  # Nullable para suportar combo/receita
    combo_id: Optional[int] = None  # Nullable para suportar produto/receita
    receita_id: Optional[int] = None  # Nullable para suportar produto/combo
    quantidade: int
    preco_unitario: float
    observacao: Optional[str] = None
    produto_descricao_snapshot: Optional[str] = None
    produto_imagem_snapshot: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ProdutoPedidoAdicionalOut(BaseModel):
    adicional_id: Optional[int] = None
    nome: Optional[str] = None
    quantidade: int = 1
    preco_unitario: float = 0.0
    total: float = 0.0


class ProdutoPedidoItemOut(BaseModel):
    item_id: Optional[int] = None
    produto_cod_barras: Optional[str] = None
    descricao: Optional[str] = None
    imagem: Optional[str] = None
    quantidade: int
    preco_unitario: float
    observacao: Optional[str] = None
    adicionais: List[ProdutoPedidoAdicionalOut] = Field(default_factory=list)


class ReceitaPedidoOut(BaseModel):
    item_id: Optional[int] = None
    receita_id: int
    nome: Optional[str] = None
    quantidade: int
    preco_unitario: float
    observacao: Optional[str] = None
    adicionais: List[ProdutoPedidoAdicionalOut] = Field(default_factory=list)


class ComboPedidoOut(BaseModel):
    combo_id: int
    nome: Optional[str] = None
    quantidade: int
    preco_unitario: float
    observacao: Optional[str] = None
    adicionais: List[ProdutoPedidoAdicionalOut] = Field(default_factory=list)


class ProdutosPedidoOut(BaseModel):
    itens: List[ProdutoPedidoItemOut] = Field(default_factory=list)
    receitas: List[ReceitaPedidoOut] = Field(default_factory=list)
    combos: List[ComboPedidoOut] = Field(default_factory=list)

class PedidoResponse(BaseModel):
    id: int
    status: PedidoStatusEnum
    cliente_id: Optional[int] = None
    telefone_cliente: Optional[str] = None
    empresa_id: int
    entregador_id: Optional[int]
    endereco_id: Optional[int]
    meio_pagamento_id: Optional[int] = None
    tipo_entrega: TipoEntregaEnum
    origem: OrigemPedidoEnum
    subtotal: float
    desconto: float
    taxa_entrega: float
    taxa_servico: float
    valor_total: float
    previsao_entrega: Optional[datetime] = None
    distancia_km: Optional[float] = None
    observacao_geral: Optional[str] = None
    troco_para: Optional[float] = None
    cupom_id: Optional[int] = None
    endereco_snapshot: Optional[dict] = None  # Snapshot do endereço no momento do pedido
    endereco_geography: Optional[str] = None  # Ponto geográfico para consultas avançadas
    data_criacao: datetime
    data_atualizacao: datetime
    itens: List[ItemPedidoResponse]
    transacao: Optional[TransacaoResponse] = None
    pagamento: PedidoPagamentoResumo | None = None
    acertado_entregador: bool | None = None
    pago: bool = False
    produtos: ProdutosPedidoOut = Field(default_factory=ProdutosPedidoOut)
    model_config = ConfigDict(from_attributes=True)

class PedidoResponseCompleto(BaseModel):
    id: int
    status: PedidoStatusEnum
    cliente: Optional[ClienteOut] = None
    empresa_id: int
    entregador_id: Optional[int]
    endereco_id: Optional[int]
    meio_pagamento_id: Optional[int] = None
    tipo_entrega: TipoEntregaEnum
    origem: OrigemPedidoEnum
    subtotal: float
    desconto: float
    taxa_entrega: float
    taxa_servico: float
    valor_total: float
    previsao_entrega: Optional[datetime] = None
    distancia_km: Optional[float] = None
    observacao_geral: Optional[str] = None
    troco_para: Optional[float] = None
    cupom_id: Optional[int] = None
    endereco_snapshot: Optional[dict] = None  # Snapshot do endereço no momento do pedido
    endereco_geography: Optional[str] = None  # Ponto geográfico para consultas avançadas
    data_criacao: datetime
    data_atualizacao: datetime
    itens: List[ItemPedidoResponse]
    pagamento: PedidoPagamentoResumo | None = None
    pago: bool = False
    produtos: ProdutosPedidoOut = Field(default_factory=ProdutosPedidoOut)
    model_config = ConfigDict(from_attributes=True)

class PedidoResponseCompletoComEndereco(BaseModel):
    id: int
    status: PedidoStatusEnum
    cliente: Optional[ClienteOut] = None
    endereco: Optional[EnderecoOut] = None
    empresa_id: int
    entregador_id: Optional[int]
    meio_pagamento_id: Optional[int] = None
    tipo_entrega: TipoEntregaEnum
    origem: OrigemPedidoEnum
    subtotal: float
    desconto: float
    taxa_entrega: float
    taxa_servico: float
    valor_total: float
    previsao_entrega: Optional[datetime] = None
    distancia_km: Optional[float] = None
    observacao_geral: Optional[str] = None
    troco_para: Optional[float] = None
    cupom_id: Optional[int] = None
    endereco_snapshot: Optional[dict] = None  # Snapshot do endereço no momento do pedido
    endereco_geography: Optional[str] = None  # Ponto geográfico para consultas avançadas
    data_criacao: datetime
    data_atualizacao: datetime
    itens: List[ItemPedidoResponse]
    pagamento: PedidoPagamentoResumo | None = None
    pago: bool = False
    produtos: ProdutosPedidoOut = Field(default_factory=ProdutosPedidoOut)
    model_config = ConfigDict(from_attributes=True)


class PedidoResponseCompletoTotal(BaseModel):
    id: int
    status: PedidoStatusEnum
    cliente: Optional[ClienteOut] = None
    endereco: Optional[EnderecoPedidoDetalhe] = None
    empresa: Optional[EmpresaResponse] = None
    entregador: Optional[EntregadorOut] = None
    meio_pagamento: Optional[MeioPagamentoResponse] = None
    cupom: Optional[CupomOut] = None
    transacao: Optional[TransacaoResponse] = None
    historicos: List[PedidoStatusHistoricoOut] = Field(default_factory=list)
    tipo_entrega: TipoEntregaEnum
    origem: OrigemPedidoEnum
    subtotal: float
    desconto: float
    taxa_entrega: float
    taxa_servico: float
    valor_total: float
    previsao_entrega: Optional[datetime] = None
    distancia_km: Optional[float] = None
    observacao_geral: Optional[str] = None
    troco_para: Optional[float] = None
    endereco_snapshot: Optional[dict] = None  # Snapshot do endereço no momento do pedido
    endereco_geography: Optional[str] = None  # Ponto geográfico para consultas avançadas
    data_criacao: datetime
    data_atualizacao: datetime
    itens: List[ItemPedidoResponse]
    pagamento: PedidoPagamentoResumo | None = None
    pago: bool = False
    produtos: ProdutosPedidoOut = Field(default_factory=ProdutosPedidoOut)
    model_config = ConfigDict(from_attributes=True)


class PedidoResponseSimplificado(BaseModel):
    """Schema simplificado para listagem de pedidos do cliente"""
    id: int
    status: PedidoStatusEnum
    cliente_nome: str
    cliente_telefone: Optional[str] = None
    subtotal: float
    desconto: float
    taxa_entrega: float
    taxa_servico: float
    valor_total: float
    previsao_entrega: Optional[datetime] = None
    observacao_geral: Optional[str] = None
    troco_para: Optional[float] = None
    endereco_snapshot: Optional[dict] = None
    data_criacao: datetime
    data_atualizacao: datetime
    itens: List[ItemPedidoResponse]
    meio_pagamento_nome: Optional[str] = None
    pagamento: PedidoPagamentoResumo | None = None
    produtos: ProdutosPedidoOut = Field(default_factory=ProdutosPedidoOut)
    model_config = ConfigDict(from_attributes=True)
