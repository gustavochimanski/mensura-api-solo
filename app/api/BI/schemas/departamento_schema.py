from pydantic import BaseModel
from decimal import Decimal


class VendasPorDepartamento(BaseModel):
    departamento: str  # agora é nome
    total_vendas: Decimal
