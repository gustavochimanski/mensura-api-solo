from pydantic import BaseModel


class VendasPorDepartamento(BaseModel):
    departamento: str
    total_vendas: float

class VendasPorEmpresaComDepartamentos(BaseModel):
    empresa: str
    departamentos: list[VendasPorDepartamento]
