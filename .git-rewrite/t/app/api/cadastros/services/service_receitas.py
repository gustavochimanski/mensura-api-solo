from sqlalchemy.orm import Session
from typing import Optional

from app.api.cadastros.repositories.repo_receitas import ReceitasRepository
from app.api.cadastros.schemas.schema_receitas import (
    SetDiretivaRequest,
    IngredienteIn,
    AdicionalIn,
)
from app.api.catalogo.models.model_receita import ReceitaModel


class ReceitasService:
    def __init__(self, db: Session):
        self.repo = ReceitasRepository(db)

    # Diretiva
    def set_diretiva(self, cod_barras: str, req: SetDiretivaRequest):
        return self.repo.set_diretiva(cod_barras, req.diretiva)

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
        adicional = self.repo.add_adicional(data)
        # Busca o preço do cadastro para retornar
        adicional.preco = self.repo._buscar_preco_adicional(adicional.adicional_id)
        return adicional

    def list_adicionais(self, produto_cod_barras: str):
        adicionais = self.repo.list_adicionais(produto_cod_barras)
        # Busca o preço do cadastro para cada adicional
        for adicional in adicionais:
            adicional.preco = self.repo._buscar_preco_adicional(adicional.adicional_id)
        return adicionais

    def remove_adicional(self, adicional_id: int):
        return self.repo.remove_adicional(adicional_id)


