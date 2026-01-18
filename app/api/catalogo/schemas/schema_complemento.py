from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, condecimal


# ------ Requests ------
class CriarComplementoRequest(BaseModel):
    empresa_id: int
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    obrigatorio: bool = False
    quantitativo: bool = False
    minimo_itens: Optional[int] = Field(
        None,
        ge=0,
        description="Quantidade mínima de itens que o cliente deve escolher neste complemento (None = sem mínimo específico).",
    )
    maximo_itens: Optional[int] = Field(
        None,
        ge=0,
        description="Quantidade máxima de itens que o cliente pode escolher neste complemento (None = sem limite explícito).",
    )
    ordem: int = 0

    model_config = ConfigDict(from_attributes=True)


class AtualizarComplementoRequest(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    obrigatorio: Optional[bool] = None
    quantitativo: Optional[bool] = None
    minimo_itens: Optional[int] = Field(
        None,
        ge=0,
        description="Quantidade mínima de itens que o cliente deve escolher neste complemento (None = não alterar).",
    )
    maximo_itens: Optional[int] = Field(
        None,
        ge=0,
        description="Quantidade máxima de itens que o cliente pode escolher neste complemento (None = não alterar).",
    )
    ativo: Optional[bool] = None
    ordem: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CriarItemRequest(BaseModel):
    """Request para criar um item de complemento (independente)"""
    empresa_id: int
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    imagem: Optional[str] = Field(None, max_length=255, description="URL pública da imagem do adicional (opcional)")
    preco: condecimal(max_digits=18, decimal_places=2) = Field(default=0)
    custo: condecimal(max_digits=18, decimal_places=2) = Field(default=0)
    ativo: bool = True

    model_config = ConfigDict(from_attributes=True)


class CriarAdicionalRequest(BaseModel):
    """Request para criar um adicional dentro de um complemento (DEPRECADO - usar CriarItemRequest)"""
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    preco: condecimal(max_digits=18, decimal_places=2) = Field(default=0)
    custo: condecimal(max_digits=18, decimal_places=2) = Field(default=0)
    ativo: bool = True
    ordem: int = 0

    model_config = ConfigDict(from_attributes=True)


class AtualizarAdicionalRequest(BaseModel):
    """Request para atualizar um adicional (item) genérico.

    Atenção: para atualizar apenas o preço dentro de um complemento específico,
    use o endpoint dedicado de preço por complemento.
    """
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    imagem: Optional[str] = Field(None, max_length=255, description="URL pública da imagem do adicional (opcional)")
    preco: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    custo: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    ativo: Optional[bool] = None
    ordem: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AtualizarPrecoItemComplementoRequest(BaseModel):
    """Request para atualizar o preço de um item dentro de um complemento específico."""
    preco: condecimal(max_digits=18, decimal_places=2)


# ------ Responses ------
class AdicionalResponse(BaseModel):
    """Response para adicional dentro de um complemento.

    Observação: o campo `preco` representa o preço **efetivo no contexto do complemento**.
    Se existir um preço específico por complemento, ele será retornado aqui; caso contrário,
    será o preço padrão do adicional.
    """
    id: int
    nome: str
    descricao: Optional[str] = None
    imagem: Optional[str] = None
    preco: float
    custo: float
    ativo: bool
    ordem: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplementoResponse(BaseModel):
    """Response para complemento com seus adicionais"""
    id: int
    empresa_id: int
    nome: str
    descricao: Optional[str] = None
    obrigatorio: bool
    quantitativo: bool
    minimo_itens: Optional[int] = Field(
        None,
        description="Mínimo de itens que o cliente deve escolher neste complemento (aplicado só quando > 0).",
    )
    maximo_itens: Optional[int] = Field(
        None,
        description="Máximo de itens que o cliente pode escolher neste complemento (aplicado só quando não nulo).",
    )
    ordem: int
    ativo: bool
    adicionais: List[AdicionalResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplementoResumidoResponse(BaseModel):
    """Versão simplificada para uso em listagens"""
    id: int
    nome: str
    obrigatorio: bool
    quantitativo: bool
    minimo_itens: Optional[int] = None
    maximo_itens: Optional[int] = None
    ordem: int

    model_config = ConfigDict(from_attributes=True)


# ------ Vincular complementos a produtos ------
class VincularComplementosProdutoRequest(BaseModel):
    """Request para vincular múltiplos complementos a um produto"""
    complemento_ids: List[int] = Field(..., description="IDs dos complementos a vincular")
    ordens: Optional[List[int]] = Field(None, description="Ordem de cada complemento (opcional, usa índice se não informado)")


class VincularComplementosProdutoResponse(BaseModel):
    """Response após vincular complementos"""
    produto_cod_barras: str
    complementos_vinculados: List[ComplementoResumidoResponse]
    message: str = "Complementos vinculados com sucesso"

    model_config = ConfigDict(from_attributes=True)


# ------ Vincular complementos a receitas ------
class VincularComplementosReceitaRequest(BaseModel):
    """Request para vincular múltiplos complementos a uma receita"""
    complemento_ids: List[int] = Field(..., description="IDs dos complementos a vincular")
    ordens: Optional[List[int]] = Field(None, description="Ordem de cada complemento (opcional, usa índice se não informado)")


class VincularComplementosReceitaResponse(BaseModel):
    """Response após vincular complementos a uma receita"""
    receita_id: int
    complementos_vinculados: List[ComplementoResumidoResponse]
    message: str = "Complementos vinculados com sucesso"

    model_config = ConfigDict(from_attributes=True)


# ------ Vincular complementos a combos ------
class VincularComplementosComboRequest(BaseModel):
    """Request para vincular múltiplos complementos a um combo"""
    complemento_ids: List[int] = Field(..., description="IDs dos complementos a vincular")
    ordens: Optional[List[int]] = Field(None, description="Ordem de cada complemento (opcional, usa índice se não informado)")


class VincularComplementosComboResponse(BaseModel):
    """Response após vincular complementos a um combo"""
    combo_id: int
    complementos_vinculados: List[ComplementoResumidoResponse]
    message: str = "Complementos vinculados com sucesso"

    model_config = ConfigDict(from_attributes=True)


# ------ Vincular itens a complementos (N:N) ------
class VincularItensComplementoRequest(BaseModel):
    """Request para vincular múltiplos itens a um complemento"""
    item_ids: List[int] = Field(..., description="IDs dos itens a vincular")
    ordens: Optional[List[int]] = Field(None, description="Ordem de cada item (opcional, usa índice se não informado)")
    precos: Optional[List[condecimal(max_digits=18, decimal_places=2)]] = Field(
        None,
        description=(
            "Preços específicos por item neste complemento (alinhados por índice com item_ids). "
            "Se não informado ou posição nula, usa o preço padrão do item."
        ),
    )


class VincularItensComplementoResponse(BaseModel):
    """Response após vincular itens a um complemento"""
    complemento_id: int
    itens_vinculados: List[AdicionalResponse]
    message: str = "Itens vinculados com sucesso"

    model_config = ConfigDict(from_attributes=True)


class VincularItemComplementoRequest(BaseModel):
    """Request para vincular um único item adicional a um complemento"""
    item_id: int = Field(..., description="ID do item adicional a vincular")
    ordem: Optional[int] = Field(None, description="Ordem do item no complemento (opcional)")
    preco_complemento: Optional[condecimal(max_digits=18, decimal_places=2)] = Field(
        None, 
        description="Preço específico do item neste complemento (opcional, sobrescreve o preço padrão)"
    )

    model_config = ConfigDict(from_attributes=True)


class VincularItemComplementoResponse(BaseModel):
    """Response após vincular um item adicional a um complemento"""
    complemento_id: int
    item_vinculado: AdicionalResponse
    message: str = "Item vinculado com sucesso"

    model_config = ConfigDict(from_attributes=True)


class ItemOrdemRequest(BaseModel):
    """Item com ordem para atualização"""
    item_id: int
    ordem: int


class AtualizarOrdemItensRequest(BaseModel):
    """Request para atualizar a ordem dos itens em um complemento
    
    Aceita dois formatos:
    1. item_ids: Lista de IDs na ordem desejada (ordem = índice) - Formato simples
    2. item_ordens: Lista de objetos com item_id e ordem explícita - Formato completo
    """
    item_ids: Optional[List[int]] = Field(None, description="IDs dos itens na ordem desejada (ordem = índice)")
    item_ordens: Optional[List[ItemOrdemRequest]] = Field(None, description="Lista de itens com suas ordens explícitas")
    
    model_config = ConfigDict(from_attributes=True)

