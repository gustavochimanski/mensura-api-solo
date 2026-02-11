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
                    quantidade=i.quantidade,
                    preco_incremental=getattr(i, "preco_incremental", None),
                    permite_quantidade=getattr(i, "permite_quantidade", None),
                    quantidade_min=getattr(i, "quantidade_min", None),
                    quantidade_max=getattr(i, "quantidade_max", None),
                ) for i in combo.itens
            ],
            secoes=[
                {
                    "id": s.id,
                    "titulo": s.titulo,
                    "descricao": s.descricao,
                    "obrigatorio": s.obrigatorio,
                    "quantitativo": s.quantitativo,
                    "minimo_itens": s.minimo_itens,
                    "maximo_itens": s.maximo_itens,
                    "ordem": getattr(s, "ordem", 0),
                    "itens": [
                        {
                            "id": it.id,
                            "produto_cod_barras": it.produto_cod_barras,
                            "receita_id": it.receita_id,
                            "preco_incremental": float(it.preco_incremental),
                            "permite_quantidade": it.permite_quantidade,
                            "quantidade_min": it.quantidade_min,
                            "quantidade_max": it.quantidade_max,
                            "ordem": getattr(it, "ordem", 0),
                        } for it in s.itens
                    ],
                } for s in combo.secoes
            ],
        )

