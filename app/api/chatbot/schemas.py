from pydantic import BaseModel
from typing import Optional, Any


class ProductQueryOut(BaseModel):
    cod_barras: str
    descricao: str
    preco_venda: Optional[float]
    imagem: Optional[str]
    disponivel: Optional[bool]


class TaxaRequest(BaseModel):
    empresa_id: int
    endereco: dict
    tipo_entrega: str = "DELIVERY"


class TaxaResponse(BaseModel):
    taxa_entrega: float
    taxa_servico: float
    distancia_km: Optional[float]
    tempo_estimado_min: Optional[int]


class CadastroRequest(BaseModel):
    nome: str
    telefone: str
    email: Optional[str] = None


class ResumoRequest(BaseModel):
    pedido_id: int
    empresa_id: Optional[int] = None
    phone_number: Optional[str] = None

