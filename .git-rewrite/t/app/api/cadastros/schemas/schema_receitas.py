from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, constr


class SetDiretivaRequest(BaseModel):
    diretiva: Optional[constr(max_length=4)] = None  # Ex.: "RC"


class IngredienteIn(BaseModel):
    produto_cod_barras: constr(min_length=1)
    ingrediente_cod_barras: constr(min_length=1)
    quantidade: Optional[float] = None
    unidade: Optional[constr(max_length=10)] = None


class IngredienteOut(BaseModel):
    id: int
    receita_id: int
    ingrediente_id: int
    quantidade: Optional[float] = None
    # Dados do ingrediente
    ingrediente_nome: Optional[str] = None
    ingrediente_descricao: Optional[str] = None
    ingrediente_unidade_medida: Optional[str] = None
    ingrediente_custo: Optional[Decimal] = None
    # Para compatibilidade com o schema antigo
    produto_cod_barras: Optional[str] = None  # Será preenchido com o receita_id como string
    ingrediente_cod_barras: Optional[str] = None  # Será preenchido com o ingrediente_id como string
    unidade: Optional[str] = None  # Alias para ingrediente_unidade_medida
    model_config = ConfigDict(from_attributes=True)


class AdicionalIn(BaseModel):
    produto_cod_barras: constr(min_length=1)  # receita_id como string para compatibilidade
    adicional_id: int


class AdicionalOut(BaseModel):
    id: int
    produto_cod_barras: str  # receita_id como string para compatibilidade
    adicional_id: int
    preco: Optional[Decimal] = None
    model_config = ConfigDict(from_attributes=True)


