from __future__ import annotations

from sqlalchemy.orm import Session

from app.api.catalogo.contracts.combo_contract import IComboContract, ComboMiniDTO, ComboItemDTO
from app.api.catalogo.repositories.repo_combo import ComboRepository


class ComboAdapter(IComboContract):
    def __init__(self, db: Session):
        self.repo = ComboRepository(db)

    def buscar_por_id(self, combo_id: int) -> ComboMiniDTO | None:
        combo = self.repo.get_by_id(combo_id)
        if not combo or not combo.ativo:
            return None
        return ComboMiniDTO(
            id=combo.id,
            empresa_id=combo.empresa_id,
            titulo=combo.titulo,
            preco_total=combo.preco_total,
            ativo=combo.ativo,
            itens=[
                ComboItemDTO(
                    produto_cod_barras=i.produto_cod_barras,
                    receita_id=i.receita_id,
                    quantidade=i.quantidade
                ) for i in combo.itens
            ],
        )

