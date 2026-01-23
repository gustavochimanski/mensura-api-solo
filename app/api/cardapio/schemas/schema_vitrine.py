from pydantic import BaseModel, ConfigDict, constr
from typing import Optional

class CriarVitrineRequest(BaseModel):
    cod_categoria: Optional[int] = None  # Agora opcional
    titulo: constr(min_length=1, max_length=100)
    is_home: bool = False  # mapeia para tipo_exibica
    model_config = ConfigDict(from_attributes=True)

class AtualizarVitrineRequest(BaseModel):
    cod_categoria: Optional[int] = None
    titulo: Optional[constr(min_length=1, max_length=100)] = None
    ordem: Optional[int] = None
    is_home: Optional[bool] = None

class VitrineOut(BaseModel):
    id: int
    cod_categoria: Optional[int] = None  # Agora opcional
    titulo: str
    slug: str
    ordem: int
    is_home: bool
    model_config = ConfigDict(from_attributes=True)
