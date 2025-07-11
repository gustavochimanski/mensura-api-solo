# app/schemas/produtosDelivery/produtos_schema.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class ProdutoEmpDTO(BaseModel):
    empresa: int
    cod_barras: str
    preco_venda: float
    custo: Optional[float]
    subcategoria_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)