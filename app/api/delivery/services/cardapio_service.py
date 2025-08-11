from __future__ import annotations
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.delivery.repositories.cardapio_dv_repo import CardapioRepository
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.delivery.schemas.cardapio_dv_schema import (
    ProdutoEmpMiniDTO,
    ProdutoMiniDTO,
    VitrineComProdutosResponse,
    CategoriaMiniSchema,
)

class CardapioService:
    def __init__(self, db: Session):
        self.repo_cardapio = CardapioRepository(db)
        self.repo_empresa = EmpresaRepository(db)

    def listar_categorias(self, empresa_id: int, only_home: bool = False) -> List[CategoriaMiniSchema]:
        if not self.repo_empresa.get_empresa_by_id(empresa_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")
        cats = self.repo_cardapio.listar_categorias(only_home=only_home)
        return [
            CategoriaMiniSchema(
                id=c.id,
                slug=c.slug,
                parent_id=c.parent_id,
                descricao=c.descricao,
                posicao=c.posicao,
                is_home=c.is_home,
                imagem=c.imagem,
                href=f"/categoria/{c.slug}"  # derivado
            )
            for c in cats
        ]

    def vitrines_com_produtos(self, empresa_id: int, cod_categoria: int) -> List[VitrineComProdutosResponse]:
        if not self.repo_empresa.get_empresa_by_id(empresa_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

        produtos_por_vitrine = self.repo_cardapio.listar_vitrines_com_produtos_empresa_categoria(empresa_id, cod_categoria)
        vitrines_cat = self.repo_cardapio.listar_vitrines_por_categoria(cod_categoria)

        resultado: List[VitrineComProdutosResponse] = []
        for vitrine in vitrines_cat:
            produtos_dto = [
                ProdutoEmpMiniDTO(
                    empresa_id=p.empresa_id,
                    cod_barras=p.cod_barras,
                    preco_venda=float(p.preco_venda),
                    vitrine_id=p.vitrine_id,
                    disponivel=p.disponivel,
                    produto=ProdutoMiniDTO(
                        cod_barras=p.produto.cod_barras,
                        descricao=p.produto.descricao,
                        imagem=p.produto.imagem,
                        cod_categoria=p.produto.cod_categoria,
                        ativo=p.produto.ativo,
                        unidade_medida=p.produto.unidade_medida,
                    ),
                )
                for p in produtos_por_vitrine.get(vitrine.id, [])
            ]
            resultado.append(
                VitrineComProdutosResponse(
                    id=vitrine.id, titulo=vitrine.titulo, slug=vitrine.slug, ordem=vitrine.ordem, produtos=produtos_dto
                )
            )
        return resultado
