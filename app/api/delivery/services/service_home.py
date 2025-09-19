# service_home.py
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.api.delivery.repositories.repo_home import HomeRepository
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.delivery.schemas.schema_home import (
    ProdutoEmpMiniDTO, ProdutoMiniDTO, VitrineComProdutosResponse,
    CategoriaMiniSchema, HomeResponse, CategoryPageResponse,  # <-- add CategoryPageResponse
)

def _build_cat_href(slug: str, slug_pai: str | None) -> str:
    return f"/categoria/{slug_pai}/{slug}" if slug_pai else f"/categoria/{slug}"

class HomeService:
    def __init__(self, db: Session):
        self.repo_home = HomeRepository(db)
        self.repo_empresa = EmpresaRepository(db)

    # util: resolve ID por slug (reuso no router antigo)
    def resolve_categoria_id_por_slug(self, slug: str) -> int:
        cat = self.repo_home.get_categoria_by_slug(slug)
        if not cat:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria não encontrada")
        return cat.id

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
                href=_build_cat_href(c.slug, c.parent.slug if c.parent else None),
            )
            for c in cats
        ]

    def montar_home(self, empresa_id: int, is_home: bool) -> HomeResponse:
        # ... (igual ao seu código atual) ...
        # (sem mudanças aqui)
        # return HomeResponse(categorias=cats, vitrines=vitrines_resp)
        #  (mantido)
        if not self.repo_empresa.get_empresa_by_id(empresa_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

        cats = self._map_categorias(self.repo_home.listar_categorias(is_home=is_home))
        vitrines = self.repo_home.listar_vitrines(is_home=is_home)
        vitrine_ids = [v.id for v in vitrines]
        produtos_map = self.repo_home.listar_produtos_por_vitrine_ids(empresa_id, vitrine_ids)

        vitrines_resp: List[VitrineComProdutosResponse] = []
        for v in vitrines:
            cat0 = v.categorias[0] if v.categorias else None
            slug = cat0.slug if cat0 else None
            slug_pai = cat0.parent.slug if (cat0 and cat0.parent) else None
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
                        cod_categoria=None,  # ProdutoModel não possui cod_categoria
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
                    cod_categoria=(cat0.id if cat0 else None),
                    is_home=bool(v.is_home),
                    produtos=produtos_dto,
                    href_categoria=href_categoria,
                )
            )
        return HomeResponse(categorias=cats, vitrines=vitrines_resp)

    def vitrines_com_produtos(self, empresa_id: int, cod_categoria: int) -> List[VitrineComProdutosResponse]:
        # ... (igual ao seu código atual) ...
        if not self.repo_empresa.get_empresa_by_id(empresa_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

        produtos_map = self.repo_home.listar_vitrines_com_produtos_empresa_categoria(empresa_id, cod_categoria)
        vitrines_cat = self.repo_home.listar_vitrines_por_categoria(cod_categoria)

        out: List[VitrineComProdutosResponse] = []
        for v in vitrines_cat:
            cat_match = next((c for c in v.categorias if c.id == cod_categoria), None)
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
                        cod_categoria=None,  # ProdutoModel não possui cod_categoria
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
                    cod_categoria=cod_categoria,
                    is_home=bool(v.is_home),
                    produtos=produtos_dto,
                    href_categoria=href_categoria,
                )
            )
        return out

    # 🆕 NOVO: página de categoria por slug (categoria + subcategorias + vitrines)
    def categoria_page(self, empresa_id: int, slug: str) -> CategoryPageResponse:
        if not self.repo_empresa.get_empresa_by_id(empresa_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

        cat = self.repo_home.get_categoria_by_slug(slug)
        if not cat:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria não encontrada")

        categoria = self._map_categorias([cat])[0]
        subcats = self._map_categorias(self.repo_home.listar_subcategorias(cat.id))

        # vitrines da própria categoria (já existente)
        vitrines = self.vitrines_com_produtos(empresa_id, cat.id)

        # --- novo: pegar 1ª vitrine (posicao == 1) para cada subcategoria em batch ---
        subcat_ids = [s.id for s in subcats]
        primeiras_vitrines_map = self.repo_home.listar_primeiras_vitrines_por_categorias(subcat_ids)
        # coletar ids únicos para buscar produtos de uma só vez
        vitrine_ids = list({v.id for v in primeiras_vitrines_map.values()})
        produtos_por_vitrine = self.repo_home.listar_produtos_por_vitrine_ids(empresa_id, vitrine_ids)

        vitrines_filho: List[VitrineComProdutosResponse] = []
        for sc in subcats:
            vit = primeiras_vitrines_map.get(sc.id)  # VitrinesModel ou None
            if not vit:
                # se a subcategoria não tem vitrine com posicao==1, pulamos
                continue

            produtos_dto = [
                ProdutoEmpMiniDTO(
                    empresa_id=p.empresa_id,
                    cod_barras=p.cod_barras,
                    preco_venda=float(p.preco_venda),
                    vitrine_id=vit.id,
                    disponivel=p.disponivel,
                    produto=ProdutoMiniDTO(
                        cod_barras=p.produto.cod_barras,
                        descricao=p.produto.descricao,
                        imagem=p.produto.imagem,
                        cod_categoria=None,  # ProdutoModel não possui cod_categoria
                        ativo=p.produto.ativo,
                        unidade_medida=p.produto.unidade_medida,
                    ),
                )
                for p in produtos_por_vitrine.get(vit.id, [])
            ]

            href_categoria = _build_cat_href(sc.slug, sc.slug_pai)

            vitrines_filho.append(
                VitrineComProdutosResponse(
                    id=vit.id,
                    titulo=vit.titulo,
                    slug=vit.slug,
                    ordem=vit.ordem,
                    cod_categoria=sc.id,
                    is_home=bool(vit.is_home),
                    produtos=produtos_dto,
                    href_categoria=href_categoria,
                )
            )

        return CategoryPageResponse(
            categoria=categoria,
            subcategorias=subcats,
            vitrines=vitrines,
            vitrines_filho=vitrines_filho,
        )

