from typing import List
from collections import defaultdict

from app.api.mensura.repositories.cardapio.CardapioRepository import CardapioRepository
from app.api.mensura.schemas.delivery.cardapio.cardapio_schema import (
    CardapioCategProdutosResponse, ProdutoEmpMiniDTO, ProdutoMiniDTO, VitrineConfigSchema
)

class CardapioService:
    def __init__(self, repository: CardapioRepository):
        self.repository = repository

    def listar_cardapio(self, cod_empresa: int) -> List[CardapioCategProdutosResponse]:
        itens_emp = self.repository.listar_produtos_emp(cod_empresa)
        categorias = self.repository.listar_categorias()
        vitrines = self.repository.listar_vitrines(cod_empresa)

        produtos_por_cat: dict[int, List[ProdutoEmpMiniDTO]] = defaultdict(list)
        for ie in itens_emp:
            base = ie.produto
            if not base:
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
                produto=prod_mini
            )
            produtos_por_cat[base.cod_categoria].append(emp_mini)

        vitrines_schema = [VitrineConfigSchema.model_validate(v) for v in vitrines]

        resultado: List[CardapioCategProdutosResponse] = []
        for cat in categorias:
            lista_prod = produtos_por_cat.get(cat.id, [])

            vitrines_para_cat = [v for v in vitrines_schema if v.cod_categoria == cat.id]

            resp = CardapioCategProdutosResponse(
                id=cat.id,
                slug=cat.slug,
                slug_pai=cat.slug_pai,
                descricao=cat.descricao,
                imagem=cat.imagem,
                destacar_em_slug=getattr(cat, "destacar_em_slug", None),
                href=cat.href,
                produtos=lista_prod,
                vitrines=vitrines_para_cat,
            )
            resultado.append(resp)

        return resultado

    def buscar_produtos_por_vitrine(
            self, cod_empresa: int, cod_categoria: int, subcategoria_id: int
    ) -> List[ProdutoEmpMiniDTO]:
        itens_emp = self.repository.listar_produtos_emp_por_categoria_e_sub(
            cod_empresa, cod_categoria, subcategoria_id
        )

        resultado: List[ProdutoEmpMiniDTO] = []

        for ie in itens_emp:
            base = ie.produto
            if not base:
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
            resultado.append(emp_mini)

        return resultado

