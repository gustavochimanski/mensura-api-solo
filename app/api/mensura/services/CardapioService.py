from typing import List
from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.mensura.repositories.cardapio.CardapioRepository import CardapioRepository
from app.api.mensura.repositories.empresaRepository import EmpresaRepository
from app.api.mensura.schemas.delivery.cardapio.cardapio_schema import (
     ProdutoEmpMiniDTO, ProdutoMiniDTO, VitrineComProdutosResponse
)
from app.api.mensura.schemas.delivery.categorias.categoria_schema import CategoriaDeliveryOut


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

    from app.api.mensura.schemas.delivery.cardapio.cardapio_schema import VitrineComProdutosResponse

    def buscar_vitrines_com_produtos(
            self, empresa_id: int, cod_categoria: int
    ) -> List[VitrineComProdutosResponse]:
        # VALIDAÇÃO EMPRESA
        empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")

        vitrines = self.repo_cardapio.listar_vitrines(empresa_id)
        produtos = self.repo_cardapio.listar_produtos_emp(empresa_id)

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

    def buscar_vitrines_home(self, empresa_id: int) -> List[VitrineComProdutosResponse]:
        from collections import defaultdict

        empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")

        categorias = self.repo_cardapio.listar_categorias()
        vitrines = self.repo_cardapio.listar_vitrines(empresa_id)
        produtos = self.repo_cardapio.listar_produtos_emp(empresa_id)

        # Agrupa produtos por vitrine_id
        produtos_por_vitrine: dict[int, List[ProdutoEmpMiniDTO]] = defaultdict(list)
        for ie in produtos:
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
            produtos_por_vitrine[ie.subcategoria_id].append(emp_mini)

        # Categorias raiz (slug_pai vazio ou None)
        categorias_raiz = [cat for cat in categorias if not cat.slug_pai]

        resultado: List[VitrineComProdutosResponse] = []

        for categoria in categorias_raiz:
            # Pega a primeira vitrine da categoria
            vitrine = next((v for v in vitrines if v.cod_categoria == categoria.id), None)
            if not vitrine:
                continue

            produtos_da_vitrine = produtos_por_vitrine.get(vitrine.id, [])
            if not produtos_da_vitrine:
                continue

            resultado.append(VitrineComProdutosResponse(
                id=categoria.id,
                titulo=categoria.descricao,
                produtos=produtos_da_vitrine[:3]
            ))

        return resultado


