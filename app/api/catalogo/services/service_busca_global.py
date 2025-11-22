"""
Service para busca global de produtos, receitas e combos
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.catalogo.models.model_receita import ReceitaModel
from app.api.catalogo.models.model_combo import ComboModel
from app.api.catalogo.schemas.schema_busca_global import (
    BuscaGlobalResponse,
    BuscaGlobalItemOut,
)


class BuscaGlobalService:
    def __init__(self, db: Session):
        self.db = db

    def buscar(
        self,
        empresa_id: int,
        termo: str,
        apenas_disponiveis: bool = True,
        apenas_ativos: bool = True,
        limit: int = 50,
    ) -> BuscaGlobalResponse:
        """
        Busca global em produtos, receitas e combos.
        
        Args:
            empresa_id: ID da empresa
            termo: Termo de busca (busca em nome/descrição/código de barras)
            apenas_disponiveis: Filtrar apenas itens disponíveis (produtos/receitas)
            apenas_ativos: Filtrar apenas itens ativos
            limit: Limite de resultados por tipo (padrão: 50)
        """
        termo_lower = termo.lower().strip()
        if not termo_lower:
            return BuscaGlobalResponse(
                produtos=[],
                receitas=[],
                combos=[],
                total=0,
            )

        # Busca produtos
        produtos_query = (
            self.db.query(ProdutoModel, ProdutoEmpModel)
            .join(ProdutoEmpModel, ProdutoModel.cod_barras == ProdutoEmpModel.cod_barras)
            .filter(ProdutoEmpModel.empresa_id == empresa_id)
        )

        if apenas_ativos:
            produtos_query = produtos_query.filter(ProdutoModel.ativo.is_(True))

        if apenas_disponiveis:
            produtos_query = produtos_query.filter(ProdutoEmpModel.disponivel.is_(True))

        # Busca por termo (descrição ou código de barras)
        produtos_query = produtos_query.filter(
            or_(
                ProdutoModel.descricao.ilike(f"%{termo_lower}%"),
                ProdutoModel.cod_barras.ilike(f"%{termo_lower}%"),
            )
        )

        produtos_result = produtos_query.limit(limit).all()

        # Busca receitas
        receitas_query = self.db.query(ReceitaModel).filter(
            ReceitaModel.empresa_id == empresa_id
        )

        if apenas_ativos:
            receitas_query = receitas_query.filter(ReceitaModel.ativo.is_(True))

        if apenas_disponiveis:
            receitas_query = receitas_query.filter(ReceitaModel.disponivel.is_(True))

        # Busca por termo (nome ou descrição)
        receitas_query = receitas_query.filter(
            or_(
                ReceitaModel.nome.ilike(f"%{termo_lower}%"),
                ReceitaModel.descricao.ilike(f"%{termo_lower}%"),
            )
        )

        receitas_result = receitas_query.limit(limit).all()

        # Busca combos
        combos_query = self.db.query(ComboModel).filter(
            ComboModel.empresa_id == empresa_id
        )

        if apenas_ativos:
            combos_query = combos_query.filter(ComboModel.ativo.is_(True))

        # Busca por termo (título ou descrição)
        combos_query = combos_query.filter(
            or_(
                ComboModel.titulo.ilike(f"%{termo_lower}%"),
                ComboModel.descricao.ilike(f"%{termo_lower}%"),
            )
        )

        combos_result = combos_query.limit(limit).all()

        # Converte para schema unificado
        produtos_out = []
        for produto, produto_emp in produtos_result:
            produtos_out.append(
                BuscaGlobalItemOut(
                    tipo="produto",
                    id=produto.cod_barras,
                    cod_barras=produto.cod_barras,
                    nome=produto.descricao,
                    descricao=produto.descricao,
                    imagem=produto.imagem,
                    preco=float(produto_emp.preco_venda),
                    preco_venda=float(produto_emp.preco_venda),
                    disponivel=produto_emp.disponivel,
                    ativo=produto.ativo,
                    empresa_id=empresa_id,
                )
            )

        receitas_out = []
        for receita in receitas_result:
            receitas_out.append(
                BuscaGlobalItemOut(
                    tipo="receita",
                    id=receita.id,
                    receita_id=receita.id,
                    nome=receita.nome,
                    descricao=receita.descricao,
                    imagem=receita.imagem,
                    preco=float(receita.preco_venda),
                    preco_venda=float(receita.preco_venda),
                    disponivel=receita.disponivel,
                    ativo=receita.ativo,
                    empresa_id=empresa_id,
                )
            )

        combos_out = []
        for combo in combos_result:
            combos_out.append(
                BuscaGlobalItemOut(
                    tipo="combo",
                    id=combo.id,
                    combo_id=combo.id,
                    nome=combo.titulo or combo.descricao,
                    titulo=combo.titulo,
                    descricao=combo.descricao,
                    imagem=combo.imagem,
                    preco=float(combo.preco_total),
                    preco_total=float(combo.preco_total),
                    disponivel=None,  # Combos não têm campo disponivel
                    ativo=combo.ativo,
                    empresa_id=empresa_id,
                )
            )

        total = len(produtos_out) + len(receitas_out) + len(combos_out)

        return BuscaGlobalResponse(
            produtos=produtos_out,
            receitas=receitas_out,
            combos=combos_out,
            total=total,
        )

