from typing import Optional, List

from pydantic import BaseModel, ConfigDict

from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field, condecimal, constr
from typing import Optional, List

# ------ Requests de criação/edição ------
class CriarNovoProdutoRequest(BaseModel):
    # ProdutoDeliveryModel
    cod_barras: constr(min_length=1)
    descricao: constr(min_length=1, max_length=255)
    imagem: Optional[str] = None
    data_cadastro: Optional[date] = None
    ativo: bool = True
    unidade_medida: Optional[constr(max_length=10)] = None
    cod_categoria: Optional[int] = None  # Agora opcional - categoria do ERP

    # ProdutoEmpDeliveryModel (já cria o vínculo com a empresa)
    empresa_id: int
    preco_venda: condecimal(max_digits=18, decimal_places=2) = Field(..., gt=0)
    custo: Optional[condecimal(max_digits=18, decimal_places=5)] = None
    sku_empresa: Optional[constr(max_length=60)] = None
    disponivel: bool = True
    exibir_delivery: bool = True

    model_config = ConfigDict(from_attributes=True)



class AtualizarProdutoRequest(BaseModel):
    descricao: Optional[constr(max_length=255)] = None
    cod_categoria: Optional[int] = None  # Categoria do ERP (opcional)
    imagem: Optional[str] = None
    ativo: Optional[bool] = None
    unidade_medida: Optional[constr(max_length=10)] = None

    # campos de produto da empresa (opcionais)
    preco_venda: Optional[condecimal(max_digits=18, decimal_places=2)] = None
    custo: Optional[condecimal(max_digits=18, decimal_places=5)] = None
    vitrine_id: Optional[int] = None
    sku_empresa: Optional[constr(max_length=60)] = None
    disponivel: Optional[bool] = None
    exibir_delivery: bool = True

# ------ DTOs / Responses ------
class ProdutoBaseDTO(BaseModel):
    cod_barras: str
    descricao: str
    imagem: Optional[str] = None
    cod_categoria: Optional[int] = None   # Categoria do ERP (opcional)
    ativo: bool
    unidade_medida: Optional[str] = None
    exibir_delivery: bool = True

    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProdutoEmpDTO(BaseModel):
    empresa_id: int
    cod_barras: str
    preco_venda: float
    custo: Optional[float] = None
    vitrine_id: Optional[int] = None
    sku_empresa: Optional[str] = None
    disponivel: bool
    exibir_delivery: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CriarNovoProdutoResponse(BaseModel):
    produto: ProdutoBaseDTO
    produto_emp: ProdutoEmpDTO

    model_config = ConfigDict(from_attributes=True)


class ProdutoListItem(BaseModel):
    cod_barras: str
    descricao: str
    imagem: Optional[str] = None
    preco_venda: float
    custo: Optional[float] = None
    cod_categoria: Optional[int] = None    # Categoria do ERP (opcional)
    label_categoria: Optional[str] = None  # Nome da categoria (opcional)
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