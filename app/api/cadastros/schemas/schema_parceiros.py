"""
Schemas de Parceiros
Centralizado no schema de cadastros
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, constr
from typing import List, Optional

# Importação direta para evitar problemas com forward references no OpenAPI
from app.api.cadastros.schemas.schema_cupom import CupomParceiroOut


# Banner Parceiro (definido primeiro para ser usado em ParceiroOut)
class BannerParceiroIn(BaseModel):
    nome: constr(min_length=1, max_length=100)
    parceiro_id: int
    categoria_id: Optional[int] = None
    link_redirecionamento: Optional[str] = None
    ativo: bool
    tipo_banner: constr(min_length=1, max_length=1)  # "V" ou "H"
    imagem: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class BannerParceiroOut(BaseModel):
    id: int
    nome: str
    ativo: bool
    tipo_banner: str
    imagem: Optional[str]
    categoria_id: Optional[int] = None
    link_redirecionamento: Optional[str] = None
    href_destino: str
    model_config = ConfigDict(from_attributes=True)


# Parceiro DTOs
class ParceiroIn(BaseModel):
    nome: constr(min_length=1, max_length=100)
    ativo: bool
    model_config = ConfigDict(from_attributes=True)


class ParceiroOut(BaseModel):
    id: int
    nome: str
    ativo: bool
    banners: List[BannerParceiroOut] = []
    model_config = ConfigDict(from_attributes=True)


# Parceiro Completo com Banners e Cupons
class ParceiroCompletoOut(BaseModel):
    id: int
    nome: str
    ativo: bool
    telefone: Optional[str]
    cupons: List[CupomParceiroOut] = []
    banners: List[BannerParceiroOut] = []
    model_config = ConfigDict(from_attributes=True)
