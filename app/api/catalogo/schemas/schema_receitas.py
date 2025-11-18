from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, constr


class IngredienteIn(BaseModel):
    produto_cod_barras: constr(min_length=1)
    ingrediente_cod_barras: constr(min_length=1)
    quantidade: Optional[float] = None
    unidade: Optional[constr(max_length=10)] = None


class IngredienteOut(BaseModel):
    id: int
    produto_cod_barras: str
    ingrediente_cod_barras: str
    quantidade: Optional[float] = None
    unidade: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class AdicionalIn(BaseModel):
    produto_cod_barras: constr(min_length=1)
    adicional_cod_barras: constr(min_length=1)
    preco: Optional[Decimal] = None


class AdicionalOut(BaseModel):
    id: int
    produto_cod_barras: str
    adicional_cod_barras: str
    preco: Optional[Decimal] = None
    model_config = ConfigDict(from_attributes=True)

