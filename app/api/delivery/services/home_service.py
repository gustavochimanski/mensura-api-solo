from __future__ import annotations
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.delivery.repositories.repo_home_dv import HomeRepository
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.delivery.schemas.home_dv_schema import (
    ProdutoEmpMiniDTO,
    ProdutoMiniDTO,
    VitrineComProdutosResponse,
    CategoriaMiniSchema,
    HomeResponse,
)

class HomeService:
    def __init__(self, db: Session):
        self.repo_home = HomeRepository(db)
        self.repo_empresa = EmpresaRepository(db)

    # --- usado internamente ---
    def _map_categorias(self, cats) -> List[CategoriaMiniSchema]:
        return [
            CategoriaMiniSchema(
                id=c.id,
                slug=c.slug,
                parent_id=c.parent_id,
                slug_pai=(c.parent.slug if c.parent else None),
                descricao=c.descricao,
                posicao=c.posicao,
                imagem=c.imagem,
                label=c.descricao,
                href=f"/categoria/{c.slug}",
            )
            for c in cats
        ]

    def listar_categorias(self, empresa_id: int, only_home: bool = False) -> List[CategoriaMiniSchema]:
        if not self.repo_empresa.get_empresa_by_id(empresa_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")
        cats = self.repo_home.listar_categorias(only_home=only_home)
        return self._map_categorias(cats)

    def montar_home(self, empresa_id: int, only_home: bool = False) -> HomeResponse:
        """
        Home completa: categorias (raízes quando only_home=True) + vitrines de home (is_home=True) com produtos.
        """
        if not self.repo_empresa.get_empresa_by_id(empresa_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

        # Categorias
        cats = self._map_categorias(self.repo_home.listar_categorias(only_home=only_home))

        # Vitrines de Home
        vitrines = self.repo_home.listar_vitrines_home()
        vitrine_ids = [v.id for v in vitrines]
        produtos_por_vitrine = self.repo_home.listar_produtos_por_vitrine_ids(empresa_id, vitrine_ids)

        vitrines_resp: List[VitrineComProdutosResponse] = []
        for v in vitrines:
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
                for p in produtos_por_vitrine.get(v.id, [])
            ]

            vitrines_resp.append(
                VitrineComProdutosResponse(
                    id=v.id,
                    titulo=v.titulo,
                    slug=v.slug,
                    ordem=v.ordem,
                    is_home=bool(v.is_home),
                    produtos=produtos_dto,
                    cod_categoria=v.cod_categoria
                )
            )

        return HomeResponse(categorias=cats, vitrines=vitrines_resp)

    def vitrines_com_produtos(self, empresa_id: int, cod_categoria: int) -> List[VitrineComProdutosResponse]:
        if not self.repo_empresa.get_empresa_by_id(empresa_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

        produtos_por_vitrine = self.repo_home.listar_vitrines_com_produtos_empresa_categoria(empresa_id, cod_categoria)
        vitrines_cat = self.repo_home.listar_vitrines_por_categoria(cod_categoria)

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
                    id=vitrine.id,
                    titulo=vitrine.titulo,
                    slug=vitrine.slug,
                    ordem=vitrine.ordem,
                    is_home=bool(vitrine.is_home),
                    produtos=produtos_dto,
                    cod_categoria=vitrine.cod_categoria
                )
            )
        return resultado
