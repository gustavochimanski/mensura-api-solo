# app/api/delivery/schemas/schema_parceiros.py
from pydantic import BaseModel, ConfigDict, constr
from typing import Optional, List

# -------- Parceiro --------
class ParceiroIn(BaseModel):
    nome: constr(min_length=1, max_length=100)
    ativo: bool

    model_config = ConfigDict(from_attributes=True)

class ParceiroOut(BaseModel):
    id: int
    nome: str
    ativo: bool
    categoria_destino: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

# -------- Banner Parceiro --------
class BannerParceiroIn(BaseModel):
    nome: constr(min_length=1, max_length=100)
    parceiro_id: int
    imagem: Optional[str] = None
    categoria_destino: int
    ativo: bool
    tipo_banner: constr(min_length=1, max_length=1)  # V ou H

    model_config = ConfigDict(from_attributes=True)

class BannerParceiroOut(BaseModel):
    id: int
    nome: str
    parceiro_id: int
    imagem: Optional[str] = None
    tipo_banner: str
    ativo: bool
    parceiro_nome: Optional[str] = None
    href_destino: str

    model_config = ConfigDict(from_attributes=True)
