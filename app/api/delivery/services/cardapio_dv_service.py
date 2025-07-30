from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.delivery.repositories.cardapio_dv_repo import CardapioRepository
from app.api.mensura.repositories.empresa_repository import EmpresaRepository
from app.api.delivery.schemas.cardapio__dv_schema import (
     ProdutoEmpMiniDTO, ProdutoMiniDTO
)
from app.api.delivery.schemas.cardapio__dv_schema import VitrineComProdutosResponse
from app.api.delivery.schemas.categoria_dv_schema import CategoriaDeliveryOut


class CardapioService:
    def __init__(self, db: Session, is_home: bool = False):
        self.repo_cardapio = CardapioRepository(db)
        self.repo_empresa = EmpresaRepository(db)

    def listar_cardapio(self, empresa_id: int) -> List[CategoriaDeliveryOut]:
        # VALIDAÇÃO EMPRESA
        empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")

        categorias = self.repo_cardapio.listar_categorias()
        resultado: List[CategoriaDeliveryOut] = []

        for cat in categorias:
            resp = CategoriaDeliveryOut(
                id=cat.id,
                slug=cat.slug,
                slug_pai=cat.slug_pai,
                label=cat.descricao,
                imagem=cat.imagem,
                href=cat.href,
                posicao=cat.posicao,
            )
            resultado.append(resp)

        return resultado


    def buscar_vitrines_com_produtos(self, empresa_id: int, cod_categoria: int) -> List[VitrineComProdutosResponse]:
        empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")

        vitrines = self.repo_cardapio.listar_vitrines(empresa_id)
        vitrines_cat = [v for v in vitrines if v.cod_categoria == cod_categoria]

        produtos_por_vitrine = self.repo_cardapio.listar_vitrines_com_produtos_empresa_categoria(
            empresa_id, cod_categoria
        )

        resultado: List[VitrineComProdutosResponse] = []
        for vitrine in vitrines_cat:
            produtos_dto = [
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
                for prod in produtos_por_vitrine.get(vitrine.id, [])
            ]

            resultado.append(VitrineComProdutosResponse(
                id=vitrine.id,
                titulo=vitrine.titulo,
                produtos=produtos_dto
            ))

        return resultado






