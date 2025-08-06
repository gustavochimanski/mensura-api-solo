# app/api/mensura/services/cardapio_service.py
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.delivery.repositories.cardapio_dv_repo import CardapioRepository
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.delivery.schemas.cardapio__dv_schema import (
    ProdutoEmpMiniDTO,
    ProdutoMiniDTO,
    VitrineComProdutosResponse
)
from app.api.delivery.schemas.categoria_dv_schema import CategoriaDeliveryOut


class CardapioService:
    def __init__(self, db: Session, is_home: bool = False):
        self.repo_cardapio = CardapioRepository(db)
        self.repo_empresa = EmpresaRepository(db)

    def listar_cardapio(self, empresa_id: int) -> List[CategoriaDeliveryOut]:
        empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Empresa não encontrada")

        categorias = self.repo_cardapio.listar_categorias()

        resultado: List[CategoriaDeliveryOut] = []
        for cat in categorias:
            slug_pai = cat.parent.slug if cat.parent else None

            resultado.append(
                CategoriaDeliveryOut(
                    id=cat.id,
                    label=cat.descricao,
                    slug=cat.slug,
                    parent_id=cat.parent_id,
                    slug_pai=slug_pai,
                    imagem=cat.imagem,
                    href=cat.href,
                    posicao=cat.posicao,
                )
            )

        return resultado

    def buscar_vitrines_com_produtos(
        self,
        empresa_id: int,
        cod_categoria: int
    ) -> List[VitrineComProdutosResponse]:
        empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Empresa não encontrada")

        produtos_por_vitrine = self.repo_cardapio.listar_vitrines_com_produtos_empresa_categoria(
            empresa_id,
            cod_categoria
        )

        # ✅ lista todas as vitrines da categoria, mesmo sem produto
        vitrines_cat = self.repo_cardapio.listar_vitrines_por_categoria(cod_categoria)

        resultado: List[VitrineComProdutosResponse] = []
        for vitrine in vitrines_cat:
            produtos_dto = [
                ProdutoEmpMiniDTO(
                    empresa_id=prod.empresa_id,
                    cod_barras=prod.cod_barras,
                    preco_venda=float(prod.preco_venda),
                    vitrine_id=prod.vitrine_id,
                    produto=ProdutoMiniDTO(
                        cod_barras=prod.produto.cod_barras,
                        descricao=prod.produto.descricao,
                        imagem=prod.produto.imagem,
                        cod_categoria=prod.produto.cod_categoria,
                    ),
                )
                for prod in produtos_por_vitrine.get(vitrine.id, [])
            ]

            resultado.append(
                VitrineComProdutosResponse(
                    id=vitrine.id,
                    titulo=vitrine.titulo,
                    slug=vitrine.slug,
                    ordem=vitrine.ordem,
                    produtos=produtos_dto
                )
            )

        return resultado
