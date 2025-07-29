from pydantic import BaseModel, ConfigDict, constr
from typing import Optional

class CriarVitrineRequest(BaseModel):
    cod_categoria: Optional[int]
    titulo: constr(min_length=1, max_length=100)
    ordem: int

    model_config = ConfigDict(from_attributes=True)

class CriarVitrineResponse(BaseModel):
    id: int
    cod_categoria: int
    titulo: str
    slug: str
    ordem: int

    model_config = ConfigDict(from_attributes=True)