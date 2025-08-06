# app/api/mensura/services/cardapio_service.py
from typing import List, Optional
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
        # 1) Valida empresa
        empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Empresa não encontrada")

        # 2) Pega todas as categorias (já com parent carregado via relationship)
        categorias = self.repo_cardapio.listar_categorias()

        resultado: List[CategoriaDeliveryOut] = []
        for cat in categorias:
            # 3) Extrai slug do pai, se existir
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
        # valida empresa
        empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Empresa não encontrada")

        # vitrine filtrada por categoria
        vitrines = self.repo_cardapio.listar_vitrines(empresa_id)
        vitrines_cat = [v for v in vitrines if v.cod_categoria == cod_categoria]

        # produtos agrupados por vitrine
        produtos_por_vitrine = (
            self.repo_cardapio
                .listar_vitrines_com_produtos_empresa_categoria(
                    empresa_id,
                    cod_categoria
                )
        )

        resultado: List[VitrineComProdutosResponse] = []
        for vitrine in vitrines_cat:
            produtos_dto = []
            for prod in produtos_por_vitrine.get(vitrine.id, []):
                produtos_dto.append(
                    ProdutoEmpMiniDTO(
                        empresa=prod.empresa,
                        cod_barras=prod.cod_barras,
                        preco_venda=float(prod.preco_venda),
                        vitrine_id=prod.vitrine_id,
                        produto=ProdutoMiniDTO(
                            id=prod.produto.id,
                            descricao=prod.produto.descricao,
                            imagem=prod.produto.imagem,
                            cod_categoria=prod.produto.cod_categoria,
                        ),
                    )
                )

            resultado.append(
                VitrineComProdutosResponse(
                    id=vitrine.id,
                    titulo=vitrine.titulo,
                    produtos=produtos_dto
                )
            )

        return resultado
