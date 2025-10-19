from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


# ------ Requests de criação/edição ------
class CriarCategoriaRequest(BaseModel):
    descricao: str = Field(..., min_length=1, max_length=100, description="Descrição da categoria")
    parent_id: Optional[int] = Field(None, description="ID da categoria pai (para subcategorias)")
    ativo: bool = Field(True, description="Status ativo/inativo da categoria")

    model_config = ConfigDict(from_attributes=True)


class AtualizarCategoriaRequest(BaseModel):
    descricao: Optional[str] = Field(None, min_length=1, max_length=100, description="Descrição da categoria")
    parent_id: Optional[int] = Field(None, description="ID da categoria pai (para subcategorias)")
    ativo: Optional[bool] = Field(None, description="Status ativo/inativo da categoria")

    model_config = ConfigDict(from_attributes=True)


# ------ DTOs / Responses ------
class CategoriaBaseDTO(BaseModel):
    id: int
    descricao: str
    ativo: bool
    parent_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoriaComFilhosDTO(CategoriaBaseDTO):
    children: List['CategoriaComFilhosDTO'] = []

    model_config = ConfigDict(from_attributes=True)


class CategoriaListItem(BaseModel):
    id: int
    descricao: str
    ativo: bool
    parent_id: Optional[int] = None
    parent_descricao: Optional[str] = None
    total_filhos: int = 0

    model_config = ConfigDict(from_attributes=True)


class CategoriasPaginadasResponse(BaseModel):
    data: List[CategoriaListItem]
    total: int
    page: int
    limit: int
    has_more: bool

    model_config = ConfigDict(from_attributes=True)


class CategoriaResponse(BaseModel):
    categoria: CategoriaBaseDTO

    model_config = ConfigDict(from_attributes=True)


class CategoriaArvoreResponse(BaseModel):
    categorias: List[CategoriaComFilhosDTO]

    model_config = ConfigDict(from_attributes=True)


# Resolve forward reference
CategoriaComFilhosDTO.model_rebuild()
