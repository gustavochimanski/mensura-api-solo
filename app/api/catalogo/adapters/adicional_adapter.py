from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from app.api.catalogo.contracts.adicional_contract import IAdicionalContract, AdicionalDTO
from app.api.catalogo.repositories.repo_adicional import AdicionalRepository


class AdicionalAdapter(IAdicionalContract):
    def __init__(self, db: Session):
        self.repo = AdicionalRepository(db)

    def listar_por_produto(self, cod_barras: str, apenas_ativos: bool = True) -> List[AdicionalDTO]:
        itens = self.repo.listar_por_produto(cod_barras, apenas_ativos=apenas_ativos)
        return [
            AdicionalDTO(
                id=i.id,
                nome=i.nome,
                preco=i.preco,
                obrigatorio=i.obrigatorio,
            )
            for i in itens
        ]

    def buscar_por_ids_para_produto(self, cod_barras: str, adicional_ids: List[int]) -> List[AdicionalDTO]:
        vinculados = self.repo.listar_por_produto(cod_barras, apenas_ativos=True)
        ids_set = set(adicional_ids or [])
        filtrados = [i for i in vinculados if i.id in ids_set]
        return [
            AdicionalDTO(
                id=i.id,
                nome=i.nome,
                preco=i.preco,
                obrigatorio=i.obrigatorio,
            )
            for i in filtrados
        ]

