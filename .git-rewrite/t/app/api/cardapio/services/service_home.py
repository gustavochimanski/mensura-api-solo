from __future__ import annotations
from typing import List, Optional
from sqlalchemy.orm import Session

from app.api.cardapio.schemas.schema_home import (
    HomeResponse,
    VitrineComProdutosResponse,
    CategoryPageResponse,
    CategoriaMiniSchema,
    ProdutoEmpMiniDTO,
    ProdutoMiniDTO,
    ComboMiniDTO,
    ReceitaMiniDTO,
)
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.catalogo.repositories.repo_adicional import AdicionalRepository

from app.api.cardapio.repositories.repo_home import HomeRepository
from app.api.cardapio.contracts.vitrine_contract import IVitrineContract


class HomeService:
    def __init__(self, db: Session, vitrine_contract: IVitrineContract | None = None):
        self.db = db
        self.repo = HomeRepository(db)
        self.repo_adicional = AdicionalRepository(db)
        self.vitrine_contract = vitrine_contract

    def _produto_emp_to_dto(self, prod_emp: ProdutoEmpModel) -> ProdutoEmpMiniDTO:
        """Converte ProdutoEmpModel para ProdutoEmpMiniDTO"""
        # Busca adicionais vinculados ao produto com todas as configurações
        adicionais = None
        try:
            adicionais_list = self.repo_adicional.listar_por_produto(prod_emp.cod_barras, apenas_ativos=True)
            if adicionais_list:
                adicionais = [
                    {
                        "id": a.id,
                        "descricao": a.nome,
                        "preco": float(a.preco),
                        "obrigatorio": a.obrigatorio,
                        "permite_multipla_escolha": a.permite_multipla_escolha,
                        "ordem": a.ordem,
                        "ativo": a.ativo,
                    }
                    for a in adicionais_list
                ]
        except Exception:
            pass
        
        # Cria o DTO do produto com adicionais dentro
        # Cria um dicionário manualmente excluindo 'adicionais' do relacionamento do modelo
        # pois o relacionamento retorna objetos AdicionalModel, não dicionários
        produto_data = {
            "cod_barras": prod_emp.produto.cod_barras,
            "descricao": prod_emp.produto.descricao,
            "imagem": prod_emp.produto.imagem,
            "cod_categoria": None,  # ProdutoModel não tem este campo
            "ativo": prod_emp.produto.ativo,
            "unidade_medida": prod_emp.produto.unidade_medida,
            "adicionais": adicionais,
        }
        produto_dto = ProdutoMiniDTO(**produto_data)
        
        return ProdutoEmpMiniDTO(
            empresa_id=prod_emp.empresa_id,
            cod_barras=prod_emp.cod_barras,
            preco_venda=float(prod_emp.preco_venda),
            vitrine_id=None,  # Será preenchido pelo método que chama
            disponivel=prod_emp.disponivel,
            produto=produto_dto,
        )

    def _montar_vitrine_response(
        self, vitrine, produtos: List[ProdutoEmpModel], combos=None, receitas=None
    ) -> VitrineComProdutosResponse:
        """Monta VitrineComProdutosResponse a partir de uma vitrine e seus produtos, combos e receitas"""
        # Pega a primeira categoria da vitrine (se houver)
        cod_categoria = None
        href_categoria = None
        if vitrine.categorias:
            primeira_cat = vitrine.categorias[0]
            cod_categoria = primeira_cat.id
            href_categoria = primeira_cat.href
        
        produtos_dto = [self._produto_emp_to_dto(prod) for prod in produtos]
        
        # Converte combos para DTO (combos já vem do contract como ComboVitrineDTO)
        combos_dto = None
        if combos:
            combos_dto = [
                ComboMiniDTO(
                    id=c.id,
                    empresa_id=c.empresa_id,
                    titulo=c.titulo,
                    descricao=c.descricao,
                    preco_total=float(c.preco_total),
                    imagem=c.imagem,
                    ativo=c.ativo,
                    vitrine_id=c.vitrine_id or vitrine.id,
                )
                for c in combos
            ]
        
        # Converte receitas para DTO (receitas já vem do contract como ReceitaVitrineDTO)
        receitas_dto = None
        if receitas:
            receitas_dto = [
                ReceitaMiniDTO(
                    id=r.id,
                    empresa_id=r.empresa_id,
                    nome=r.nome,
                    descricao=r.descricao,
                    preco_venda=float(r.preco_venda),
                    imagem=r.imagem,
                    vitrine_id=r.vitrine_id or vitrine.id,
                    disponivel=r.disponivel,
                    ativo=r.ativo,
                )
                for r in receitas
            ]
        
        return VitrineComProdutosResponse(
            id=vitrine.id,
            titulo=vitrine.titulo,
            slug=vitrine.slug,
            ordem=vitrine.ordem,
            produtos=produtos_dto,
            combos=combos_dto,
            receitas=receitas_dto,
            is_home=vitrine.is_home,
            cod_categoria=cod_categoria,
            href_categoria=href_categoria,
        )

    def montar_home(self, empresa_id: int, is_home: Optional[bool] = None) -> HomeResponse:
        """Monta a resposta da home com categorias e vitrines"""
        # Busca categorias
        categorias = self.repo.listar_categorias(is_home=is_home if is_home is not None else False)
        categorias_dto = [
            CategoriaMiniSchema.model_validate(cat, from_attributes=True)
            for cat in categorias
        ]
        
        # Busca vitrines
        vitrines = self.repo.listar_vitrines(is_home=is_home if is_home is not None else False)
        vitrine_ids = [v.id for v in vitrines]
        
        # Busca produtos por vitrine
        produtos_por_vitrine = self.repo.listar_produtos_por_vitrine_ids(
            empresa_id=empresa_id,
            vitrine_ids=vitrine_ids
        )
        
        # Busca combos e receitas por vitrine (se contract disponível)
        combos_por_vitrine = {}
        receitas_por_vitrine = {}
        if self.vitrine_contract and vitrine_ids:
            combos_por_vitrine = self.vitrine_contract.listar_combos_por_vitrine_ids(
                empresa_id=empresa_id,
                vitrine_ids=vitrine_ids
            )
            receitas_por_vitrine = self.vitrine_contract.listar_receitas_por_vitrine_ids(
                empresa_id=empresa_id,
                vitrine_ids=vitrine_ids
            )
        
        # Monta vitrines com produtos, combos e receitas
        vitrines_response = []
        for vitrine in vitrines:
            produtos = produtos_por_vitrine.get(vitrine.id, [])
            combos = combos_por_vitrine.get(vitrine.id, [])
            receitas = receitas_por_vitrine.get(vitrine.id, [])
            vitrines_response.append(
                self._montar_vitrine_response(vitrine, produtos, combos=combos, receitas=receitas)
            )
        
        return HomeResponse(
            categorias=categorias_dto,
            vitrines=vitrines_response,
        )

    def vitrines_com_produtos(
        self, empresa_id: int, cod_categoria: int
    ) -> List[VitrineComProdutosResponse]:
        """Retorna vitrines com produtos de uma categoria específica"""
        # Busca vitrines da categoria
        vitrines = self.repo.listar_vitrines_por_categoria(categoria_id=cod_categoria)
        vitrine_ids = [v.id for v in vitrines]
        
        # Busca produtos por vitrine (filtrados pela categoria)
        produtos_por_vitrine = self.repo.listar_vitrines_com_produtos_empresa_categoria(
            empresa_id=empresa_id,
            categoria_id=cod_categoria
        )
        
        # Busca combos e receitas por vitrine (se contract disponível)
        combos_por_vitrine = {}
        receitas_por_vitrine = {}
        if self.vitrine_contract and vitrine_ids:
            combos_por_vitrine = self.vitrine_contract.listar_combos_por_vitrine_categoria(
                empresa_id=empresa_id,
                categoria_id=cod_categoria
            )
            receitas_por_vitrine = self.vitrine_contract.listar_receitas_por_vitrine_categoria(
                empresa_id=empresa_id,
                categoria_id=cod_categoria
            )
        
        # Monta resposta
        resultado = []
        for vitrine in vitrines:
            produtos = produtos_por_vitrine.get(vitrine.id, [])
            combos = combos_por_vitrine.get(vitrine.id, [])
            receitas = receitas_por_vitrine.get(vitrine.id, [])
            resultado.append(
                self._montar_vitrine_response(vitrine, produtos, combos=combos, receitas=receitas)
            )
        
        return resultado

    def resolve_categoria_id_por_slug(self, slug: str) -> int:
        """Resolve o ID de uma categoria pelo slug"""
        categoria = self.repo.get_categoria_by_slug(slug)
        if not categoria:
            raise ValueError(f"Categoria com slug '{slug}' não encontrada")
        return categoria.id

    def categoria_page(self, empresa_id: int, slug: str) -> CategoryPageResponse:
        """Monta a página de uma categoria com subcategorias e vitrines"""
        # Busca categoria pelo slug
        categoria = self.repo.get_categoria_by_slug(slug)
        if not categoria:
            raise ValueError(f"Categoria com slug '{slug}' não encontrada")
        
        categoria_dto = CategoriaMiniSchema.model_validate(categoria, from_attributes=True)
        
        # Busca subcategorias
        subcategorias = self.repo.listar_subcategorias(parent_id=categoria.id)
        subcategorias_dto = [
            CategoriaMiniSchema.model_validate(sub, from_attributes=True)
            for sub in subcategorias
        ]
        
        # Busca vitrines da categoria
        vitrines = self.repo.listar_vitrines_por_categoria(categoria_id=categoria.id)
        vitrine_ids = [v.id for v in vitrines]
        
        # Busca produtos por vitrine
        produtos_por_vitrine = self.repo.listar_vitrines_com_produtos_empresa_categoria(
            empresa_id=empresa_id,
            categoria_id=categoria.id
        )
        
        # Busca combos e receitas por vitrine (se contract disponível)
        combos_por_vitrine = {}
        receitas_por_vitrine = {}
        if self.vitrine_contract and vitrine_ids:
            combos_por_vitrine = self.vitrine_contract.listar_combos_por_vitrine_categoria(
                empresa_id=empresa_id,
                categoria_id=categoria.id
            )
            receitas_por_vitrine = self.vitrine_contract.listar_receitas_por_vitrine_categoria(
                empresa_id=empresa_id,
                categoria_id=categoria.id
            )
        
        vitrines_response = []
        for vitrine in vitrines:
            produtos = produtos_por_vitrine.get(vitrine.id, [])
            combos = combos_por_vitrine.get(vitrine.id, [])
            receitas = receitas_por_vitrine.get(vitrine.id, [])
            vitrines_response.append(
                self._montar_vitrine_response(vitrine, produtos, combos=combos, receitas=receitas)
            )
        
        # Busca vitrines das subcategorias (filho)
        vitrines_filho = []
        if subcategorias:
            subcategoria_ids = [sub.id for sub in subcategorias]
            # Busca a primeira vitrine de cada subcategoria
            vitrines_por_subcat = self.repo.listar_primeiras_vitrines_por_categorias(subcategoria_ids)
            
            for subcat_id, vitrine in vitrines_por_subcat.items():
                produtos = self.repo.listar_vitrines_com_produtos_empresa_categoria(
                    empresa_id=empresa_id,
                    categoria_id=subcat_id
                ).get(vitrine.id, [])
                
                # Busca combos e receitas para subcategoria
                combos_sub = {}
                receitas_sub = {}
                if self.vitrine_contract:
                    combos_sub = self.vitrine_contract.listar_combos_por_vitrine_categoria(
                        empresa_id=empresa_id,
                        categoria_id=subcat_id
                    )
                    receitas_sub = self.vitrine_contract.listar_receitas_por_vitrine_categoria(
                        empresa_id=empresa_id,
                        categoria_id=subcat_id
                    )
                
                combos_vit = combos_sub.get(vitrine.id, [])
                receitas_vit = receitas_sub.get(vitrine.id, [])
                vitrines_filho.append(
                    self._montar_vitrine_response(vitrine, produtos, combos=combos_vit, receitas=receitas_vit)
                )
        
        return CategoryPageResponse(
            categoria=categoria_dto,
            subcategorias=subcategorias_dto,
            vitrines=vitrines_response,
            vitrines_filho=vitrines_filho,
        )

