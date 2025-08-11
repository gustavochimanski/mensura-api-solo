from pydantic import BaseModel, ConfigDict, constr
from typing import Optional

class CriarVitrineRequest(BaseModel):
    cod_categoria: Optional[int] = None  # alinhar ao model (FK int)
    titulo: constr(min_length=1, max_length=100)
    ordem: int = 1
    is_home: bool  # property derivada

    model_config = ConfigDict(from_attributes=True)

class CriarVitrineResponse(BaseModel):
    id: int
    cod_categoria: int
    titulo: str
    slug: str
    ordem: int
    is_home: bool  # property derivada

    model_config = ConfigDict(from_attributes=True)

class VitrineOut(BaseModel):
    id: int
    cod_categoria: int
    titulo: str
    slug: str
    ordem: int
    is_home: bool  # property derivada

    model_config = ConfigDict(from_attributes=True)

class AtualizarVitrineRequest(BaseModel):
    cod_categoria: Optional[int] = None
    titulo: Optional[constr(min_length=1, max_length=100)] = None
    ordem: Optional[int] = None
    is_home: bool  # property derivada