from pydantic import BaseModel


class VendasPorDepartamento(BaseModel):
    departamento: str  # agora é nome
    total_vendas: float
