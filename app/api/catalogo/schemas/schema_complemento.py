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
    permite_multipla_escolha: bool = True
    ordem: int = 0

    model_config = ConfigDict(from_attributes=True)


class AtualizarComplementoRequest(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    obrigatorio: Optional[bool] = None
    quantitativo: Optional[bool] = None
    permite_multipla_escolha: Optional[bool] = None
    ativo: Optional[bool] = None
    ordem: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CriarAdicionalRequest(BaseModel):
    """Request para criar um adicional dentro de um complemento"""
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    preco: condecimal(max_digits=18, decimal_places=2) = Field(default=0)
    custo: condecimal(max_digits=18, decimal_places=2) = Field(default=0)
    ativo: bool = True
    ordem: int = 0

    model_config = ConfigDict(from_attributes=True)


class AtualizarAdicionalRequest(BaseModel):
    """Request para atualizar um adicional dentro de um complemento"""
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    preco: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    custo: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    ativo: Optional[bool] = None
    ordem: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ------ Responses ------
class AdicionalResponse(BaseModel):
    """Response para adicional dentro de um complemento"""
    id: int
    nome: str
    descricao: Optional[str] = None
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
    permite_multipla_escolha: bool
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
    permite_multipla_escolha: bool
    ordem: int

    model_config = ConfigDict(from_attributes=True)


# ------ Vincular complementos a produtos ------
class VincularComplementosProdutoRequest(BaseModel):
    """Request para vincular múltiplos complementos a um produto"""
    complemento_ids: List[int] = Field(..., description="IDs dos complementos a vincular")


class VincularComplementosProdutoResponse(BaseModel):
    """Response após vincular complementos"""
    produto_cod_barras: str
    complementos_vinculados: List[ComplementoResumidoResponse]
    message: str = "Complementos vinculados com sucesso"

    model_config = ConfigDict(from_attributes=True)

