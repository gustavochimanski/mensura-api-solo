from sqlalchemy.orm import Session
from typing import Optional, List

from app.api.catalogo.repositories.repo_receitas import ReceitasRepository
from app.api.catalogo.schemas.schema_receitas import (
    ReceitaIngredienteIn,
    AdicionalIn,
    ReceitaIn,
    ReceitaUpdate,
)


class ReceitasService:
    def __init__(self, db: Session):
        self.repo = ReceitasRepository(db)

    # Receitas - CRUD completo
    def create_receita(self, data: ReceitaIn):
        return self.repo.create_receita(data)

    def get_receita(self, receita_id: int):
        return self.repo.get_receita_by_id(receita_id)

    def list_receitas(self, empresa_id: Optional[int] = None, ativo: Optional[bool] = None):
        return self.repo.list_receitas(empresa_id=empresa_id, ativo=ativo)

    def update_receita(self, receita_id: int, data: ReceitaUpdate):
        return self.repo.update_receita(receita_id, data)

    def delete_receita(self, receita_id: int):
        return self.repo.delete_receita(receita_id)

    # Ingredientes (vinculação a receitas)
    def add_ingrediente(self, data: ReceitaIngredienteIn):
        return self.repo.add_ingrediente(data)

    def list_ingredientes(self, receita_id: int):
        return self.repo.list_ingredientes(receita_id)

    def update_ingrediente(self, receita_ingrediente_id: int, quantidade: Optional[float]):
        return self.repo.update_ingrediente(receita_ingrediente_id, quantidade)

    def remove_ingrediente(self, receita_ingrediente_id: int):
        return self.repo.remove_ingrediente(receita_ingrediente_id)

    # Adicionais
    def add_adicional(self, data: AdicionalIn):
        return self.repo.add_adicional(data)

    def list_adicionais(self, receita_id: int):
        return self.repo.list_adicionais(receita_id)

    def update_adicional(self, adicional_id: int, preco):
        return self.repo.update_adicional(adicional_id, preco)

    def remove_adicional(self, adicional_id: int):
        return self.repo.remove_adicional(adicional_id)

