from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session

from app.api.catalogo.contracts.receitas_contract import (
    IReceitasContract,
    ProdutoIngredienteDTO,
    ProdutoAdicionalDTO,
    ReceitaMiniDTO,
)
from app.api.catalogo.repositories.repo_receitas import ReceitasRepository


class ReceitasAdapter(IReceitasContract):
    def __init__(self, db: Session):
        self.repo = ReceitasRepository(db)

    def listar_ingredientes_por_produto(self, produto_cod_barras: str) -> List[ProdutoIngredienteDTO]:
        itens = self.repo.list_ingredientes(produto_cod_barras)
        return [
            ProdutoIngredienteDTO(
                id=i.id,
                produto_cod_barras=i.produto_cod_barras,
                ingrediente_cod_barras=i.ingrediente_cod_barras,
                quantidade=float(i.quantidade) if i.quantidade is not None else None,
                unidade=i.unidade,
            )
            for i in itens
        ]

    def listar_adicionais_por_produto(self, produto_cod_barras: str) -> List[ProdutoAdicionalDTO]:
        itens = self.repo.list_adicionais(produto_cod_barras)
        return [
            ProdutoAdicionalDTO(
                id=i.id,
                produto_cod_barras=i.produto_cod_barras,
                adicional_cod_barras=i.adicional_cod_barras,
                preco=float(i.preco) if i.preco is not None else None,
            )
            for i in itens
        ]

    def obter_receita_por_id(self, receita_id: int) -> Optional[ReceitaMiniDTO]:
        """Obtém uma receita por ID."""
        receita = self.repo.get_receita_by_id(receita_id)
        if not receita or not receita.ativo:
            return None
        return ReceitaMiniDTO(
            id=receita.id,
            empresa_id=receita.empresa_id,
            nome=receita.nome,
            preco_venda=receita.preco_venda,
            ativo=receita.ativo,
            disponivel=receita.disponivel,
        )

