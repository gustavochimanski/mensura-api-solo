from typing import Optional, List

from pydantic import BaseModel, ConfigDict


class ProdutoListItem(BaseModel):
    # para listagem paginada
    cod_barras: str
    descricao: str
    imagem: Optional[str] = None
    preco_venda: float
    custo: Optional[float] = None
    cod_categoria: int
    label_categoria: str
    disponivel: bool
    exibir_delivery: bool = True

    model_config = ConfigDict(from_attributes=True)

class ProdutosPaginadosResponse(BaseModel):
    data: List[ProdutoListItem]
    total: int
    page: int
    limit: int
    has_more: bool

    model_config = ConfigDict(from_attributes=True)