# home_service.py
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.api.delivery.repositories.repo_home_dv import HomeRepository
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.delivery.schemas.home_dv_schema import (
    ProdutoEmpMiniDTO, ProdutoMiniDTO, VitrineComProdutosResponse,
    CategoriaMiniSchema, HomeResponse,
)

def _build_cat_href(slug: str, slug_pai: str | None) -> str:
    return f"/categoria/{slug_pai}/{slug}" if slug_pai else f"/categoria/{slug}"

class HomeService:
    def __init__(self, db: Session):
        self.repo_home = HomeRepository(db)
        self.repo_empresa = EmpresaRepository(db)

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
                href=_build_cat_href(c.slug, c.parent.slug if c.parent else None),  # <- ajustado
            )
            for c in cats
        ]

    def montar_home(self, empresa_id: int, is_home: bool) -> HomeResponse:
        if not self.repo_empresa.get_empresa_by_id(empresa_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

        # Categorias
        cats = self._map_categorias(self.repo_home.listar_categorias(is_home=is_home))

        # Vitrines (já com categoria + parent carregados)
        vitrines = self.repo_home.listar_vitrines(is_home=is_home)
        vitrine_ids = [v.id for v in vitrines]
        produtos_map = self.repo_home.listar_produtos_por_vitrine_ids(empresa_id, vitrine_ids)

        vitrines_resp: List[VitrineComProdutosResponse] = []
        for v in vitrines:
            # 👇 categoria “principal” (1ª do vínculo) para compat
            cat0 = v.categorias[0] if v.categorias else None
            slug = cat0.slug if cat0 else None
            slug_pai = cat0.parent.slug if (cat0 and cat0.parent) else None
            href_categoria = _build_cat_href(slug, slug_pai) if slug else None

            produtos_dto = [
                ProdutoEmpMiniDTO(
                    empresa_id=p.empresa_id,
                    cod_barras=p.cod_barras,
                    preco_venda=float(p.preco_venda),
                    vitrine_id=v.id,  # 👈 vitrine do CONTEXTO
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
                for p in produtos_map.get(v.id, [])
            ]

            vitrines_resp.append(
                VitrineComProdutosResponse(
                    id=v.id,
                    titulo=v.titulo,
                    slug=v.slug,
                    ordem=v.ordem,
                    cod_categoria=(cat0.id if cat0 else None),  # 👈 compat
                    is_home=bool(v.is_home),
                    produtos=produtos_dto,
                    href_categoria=href_categoria,
                )
            )
        return HomeResponse(categorias=cats, vitrines=vitrines_resp)

    def vitrines_com_produtos(self, empresa_id: int, cod_categoria: int, is_home: bool) -> List[VitrineComProdutosResponse]:
        if not self.repo_empresa.get_empresa_by_id(empresa_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

        # produtos de vitrines somente da categoria informada
        produtos_map = self.repo_home.listar_vitrines_com_produtos_empresa_categoria(empresa_id, cod_categoria)

        # vitrines vinculadas à categoria (opcionalmente só as de home)
        vitrines_cat = self.repo_home.listar_vitrines_por_categoria(cod_categoria, is_home=is_home)

        out: List[VitrineComProdutosResponse] = []
        for v in vitrines_cat:
            # ⚠️ Use a categoria DO FILTRO, não a primeira da lista
            cat_match = next((c for c in v.categorias if c.id == cod_categoria), None)
            # Fallback (não deveria acontecer porque filtramos por categoria)
            cat_ref = cat_match or (v.categorias[0] if v.categorias else None)

            slug = cat_ref.slug if cat_ref else None
            slug_pai = cat_ref.parent.slug if (cat_ref and cat_ref.parent) else None
            href_categoria = _build_cat_href(slug, slug_pai) if slug else None

            produtos_dto = [
                ProdutoEmpMiniDTO(
                    empresa_id=p.empresa_id,
                    cod_barras=p.cod_barras,
                    preco_venda=float(p.preco_venda),
                    vitrine_id=v.id,
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
                for p in produtos_map.get(v.id, [])
            ]

            out.append(
                VitrineComProdutosResponse(
                    id=v.id,
                    titulo=v.titulo,
                    slug=v.slug,
                    ordem=v.ordem,
                    # ✅ aqui garantimos coerência com o filtro
                    cod_categoria=cod_categoria,
                    is_home=bool(v.is_home),
                    produtos=produtos_dto,
                    href_categoria=href_categoria,
                )
            )
        return out

