from pydantic import BaseModel, ConfigDict, constr
from typing import Optional

# -------- Parceiro --------
class ParceiroIn(BaseModel):
    nome: constr(min_length=1, max_length=100)
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


class ParceiroOut(BaseModel):
    id: int
    nome: str
    ativo: bool

    model_config = ConfigDict(from_attributes=True)


# -------- Banner Parceiro --------
class BannerParceiroIn(BaseModel):
    nome: constr(min_length=1, max_length=100)
    parceiro_id: int
    categoria_id: int
    ativo: bool
    tipo_banner: constr(min_length=1, max_length=1)  # "V" ou "H"
    imagem: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BannerParceiroOut(BaseModel):
    id: int
    nome: str
    parceiro_id: int
    categoria_id: int
    ativo: bool
    tipo_banner: str
    imagem: Optional[str] = None
    parceiro_nome: Optional[str] = None
    href_destino: str

    model_config = ConfigDict(from_attributes=True)
