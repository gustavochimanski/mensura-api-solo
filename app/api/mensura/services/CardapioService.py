from typing import List
from collections import defaultdict

from app.api.mensura.repositories.cardapio.CardapioRepository import CardapioRepository
from app.api.mensura.schemas.delivery.cardapio.cardapio_schema import (
     ProdutoEmpMiniDTO, ProdutoMiniDTO, VitrineConfigSchema, VitrineComProdutosResponse
)
from app.api.mensura.schemas.delivery.categorias.categoria_schema import CategoriaDeliveryOut


class CardapioService:
    def __init__(self, repository: CardapioRepository):
        self.repository = repository

    def listar_cardapio(self, empresa_id: int) -> List[CategoriaDeliveryOut]:
        categorias = self.repository.listar_categorias()
        vitrines = self.repository.listar_vitrines(empresa_id)

        vitrines_schema = [VitrineConfigSchema.model_validate(v) for v in vitrines]

        resultado: List[CategoriaDeliveryOut] = []
        for cat in categorias:

            vitrines_para_cat = [v for v in vitrines_schema if v.cod_categoria == cat.id]

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

    from app.api.mensura.schemas.delivery.cardapio.cardapio_schema import VitrineComProdutosResponse

    def buscar_vitrines_com_produtos(
            self, cod_empresa: int, cod_categoria: int
    ) -> List[VitrineComProdutosResponse]:
        vitrines = self.repository.listar_vitrines(cod_empresa)
        produtos = self.repository.listar_produtos_emp(cod_empresa)

        # Filtrar vitrines da categoria desejada
        vitrines_cat = [v for v in vitrines if v.cod_categoria == cod_categoria]

        # Agrupar produtos por subcategoria_id
        produtos_por_sub: dict[int, List[ProdutoEmpMiniDTO]] = defaultdict(list)

        for ie in produtos:
            base = ie.produto
            if not base or base.cod_categoria != cod_categoria:
                continue

            prod_mini = ProdutoMiniDTO(
                id=base.id,
                descricao=base.descricao,
                imagem=base.imagem,
                cod_categoria=base.cod_categoria,
            )
            emp_mini = ProdutoEmpMiniDTO(
                empresa=ie.empresa,
                cod_barras=ie.cod_barras,
                preco_venda=float(ie.preco_venda),
                subcategoria_id=ie.subcategoria_id,
                produto=prod_mini,
            )
            produtos_por_sub[ie.subcategoria_id].append(emp_mini)

        # Construir a resposta
        resultado: List[VitrineComProdutosResponse] = []
        for vitrine in vitrines_cat:
            resultado.append(VitrineComProdutosResponse(
                id=vitrine.id,
                titulo=vitrine.titulo,
                produtos=produtos_por_sub.get(vitrine.id, [])
            ))

        return resultado
