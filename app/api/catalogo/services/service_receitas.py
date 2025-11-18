from sqlalchemy.orm import Session
from typing import Optional

from app.api.catalogo.repositories.repo_receitas import ReceitasRepository
from app.api.catalogo.schemas.schema_receitas import (
    IngredienteIn,
    AdicionalIn,
)


class ReceitasService:
    def __init__(self, db: Session):
        self.repo = ReceitasRepository(db)

    # Ingredientes
    def add_ingrediente(self, data: IngredienteIn):
        return self.repo.add_ingrediente(data)

    def list_ingredientes(self, produto_cod_barras: str):
        return self.repo.list_ingredientes(produto_cod_barras)

    def update_ingrediente(self, ingrediente_id: int, quantidade: Optional[float], unidade: Optional[str]):
        return self.repo.update_ingrediente(ingrediente_id, quantidade, unidade)

    def remove_ingrediente(self, ingrediente_id: int):
        return self.repo.remove_ingrediente(ingrediente_id)

    # Adicionais
    def add_adicional(self, data: AdicionalIn):
        return self.repo.add_adicional(data)

    def list_adicionais(self, produto_cod_barras: str):
        return self.repo.list_adicionais(produto_cod_barras)

    def update_adicional(self, adicional_id: int, preco):
        return self.repo.update_adicional(adicional_id, preco)

    def remove_adicional(self, adicional_id: int):
        return self.repo.remove_adicional(adicional_id)

