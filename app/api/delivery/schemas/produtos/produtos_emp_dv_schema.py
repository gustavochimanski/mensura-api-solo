from pydantic import BaseModel, ConfigDict
from typing import Optional

# Mantemos um DTO simples para usos internos fora da API HTTP, se necessário.
class ProdutoEmpDTO(BaseModel):
    empresa_id: int
    cod_barras: str
    preco_venda: float
    custo: Optional[float] = None
    vitrine_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
