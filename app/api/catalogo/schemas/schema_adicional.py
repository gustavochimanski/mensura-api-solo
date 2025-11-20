from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, condecimal


# ------ Requests ------
class CriarAdicionalRequest(BaseModel):
    empresa_id: int
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    preco: condecimal(max_digits=18, decimal_places=2) = Field(default=0)
    custo: condecimal(max_digits=18, decimal_places=2) = Field(default=0)
    ativo: bool = True
    obrigatorio: bool = False
    permite_multipla_escolha: bool = True
    ordem: int = 0

    model_config = ConfigDict(from_attributes=True)


class AtualizarAdicionalRequest(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    descricao: Optional[str] = Field(None, max_length=255)
    preco: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    custo: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    ativo: Optional[bool] = None
    obrigatorio: Optional[bool] = None
    permite_multipla_escolha: Optional[bool] = None
    ordem: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ------ Responses ------
class AdicionalResponse(BaseModel):
    id: int
    empresa_id: int
    nome: str
    descricao: Optional[str] = None
    preco: float
    custo: float
    ativo: bool
    obrigatorio: bool
    permite_multipla_escolha: bool
    ordem: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdicionalResumidoResponse(BaseModel):
    """Versão simplificada para uso em listagens de produtos"""
    id: int
    nome: str
    preco: float
    obrigatorio: bool
    permite_multipla_escolha: bool

    model_config = ConfigDict(from_attributes=True)


# ------ Vincular adicionais a produtos ------
class VincularAdicionaisProdutoRequest(BaseModel):
    """Request para vincular múltiplos adicionais a um produto"""
    adicional_ids: List[int] = Field(..., description="IDs dos adicionais a vincular")


class VincularAdicionaisProdutoResponse(BaseModel):
    """Response após vincular adicionais"""
    produto_cod_barras: str
    adicionais_vinculados: List[AdicionalResumidoResponse]
    message: str = "Adicionais vinculados com sucesso"

    model_config = ConfigDict(from_attributes=True)

