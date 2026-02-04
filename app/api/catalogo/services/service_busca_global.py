"""
Service para busca global de produtos, receitas e combos
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, and_, select, text

from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.catalogo.models.model_receita import ReceitaModel
from app.api.catalogo.models.model_combo import ComboModel
from app.api.catalogo.schemas.schema_busca_global import (
    BuscaGlobalResponse,
    BuscaGlobalItemOut,
)


class BuscaGlobalService:
    # ---- helper: unaccent disponível? (cache por processo) ----
    _unaccent_checked: bool = False
    _has_unaccent_cache: bool = False

    def __init__(self, db: Session):
        self.db = db

    def _has_unaccent(self) -> bool:
        """
        Verifica se a função/extensão `unaccent` está disponível no banco.

        - Em PostgreSQL, depende da extensão `unaccent` estar habilitada.
        - Em outros bancos, esta checagem falha e retorna False (fallback sem unaccent).
        """
        if BuscaGlobalService._unaccent_checked:
            return BuscaGlobalService._has_unaccent_cache
        try:
            # tentativa simples: se existir, retorna 1; se não existir, levanta exceção
            self.db.execute(text("SELECT unaccent(:s)"), {"s": "teste"})
            BuscaGlobalService._has_unaccent_cache = True
        except Exception:
            BuscaGlobalService._has_unaccent_cache = False
        BuscaGlobalService._unaccent_checked = True
        return BuscaGlobalService._has_unaccent_cache

    def _ilike_sem_acento(self, expr, term: str):
        """
        Retorna uma condição ILIKE, removendo acentos quando possível.

        `term` deve vir já com wildcards (`%...%`) quando necessário.
        """
        if self._has_unaccent():
            return func.unaccent(expr).ilike(func.unaccent(term))
        return expr.ilike(term)

    def buscar(
        self,
        empresa_id: int,
        termo: str = "",
        apenas_disponiveis: bool = True,
        apenas_ativos: bool = True,
        limit: int = 50,
        page: int = 1,
    ) -> BuscaGlobalResponse:
        """
        Busca global em produtos, receitas e combos.
        
        Args:
            empresa_id: ID da empresa
            termo: Termo de busca (opcional - se vazio, retorna primeiros itens)
            apenas_disponiveis: Filtrar apenas itens disponíveis (produtos/receitas)
            apenas_ativos: Filtrar apenas itens ativos
            limit: Limite de resultados por tipo (padrão: 50)
            page: Número da página para paginação (padrão: 1)
        """
        termo_lower = termo.lower().strip() if termo else ""
        termo_vazio = not termo_lower
        
        # Normaliza o termo removendo hífens e espaços para busca mais flexível
        # "x bacon" e "x-bacon" se tornam "xbacon"
        termo_normalizado = termo_lower.replace("-", "").replace(" ", "") if termo_lower else ""
        
        # Calcula range para paginação baseada em WHERE
        offset_id = (page - 1) * limit
        max_id = page * limit

        # Busca produtos
        produtos_query = (
            self.db.query(ProdutoModel, ProdutoEmpModel)
            .join(ProdutoEmpModel, ProdutoModel.id == ProdutoEmpModel.produto_id)
            .filter(ProdutoEmpModel.empresa_id == empresa_id)
        )

        if apenas_ativos:
            produtos_query = produtos_query.filter(ProdutoModel.ativo.is_(True))

        if apenas_disponiveis:
            produtos_query = produtos_query.filter(ProdutoEmpModel.disponivel.is_(True), ProdutoEmpModel.preco_venda > 0)

        if termo_vazio:
            # Quando termo vazio, retorna primeiros itens ordenados por created_at
            # Para produtos, usamos ROW_NUMBER() para paginação baseada em WHERE
            # Aplica paginação baseada em WHERE usando subquery com ROW_NUMBER
            # Constrói condições de filtro para a subquery
            subquery_filters = [ProdutoEmpModel.empresa_id == empresa_id]
            if apenas_ativos:
                subquery_filters.append(ProdutoModel.ativo.is_(True))
            if apenas_disponiveis:
                subquery_filters.append(ProdutoEmpModel.disponivel.is_(True))
                subquery_filters.append(ProdutoEmpModel.preco_venda > 0)
            
            subquery = (
                select(
                    ProdutoModel.id,
                    func.row_number().over(
                        order_by=ProdutoModel.created_at.asc()
                    ).label('row_num')
                )
                .select_from(ProdutoModel)
                .join(ProdutoEmpModel, ProdutoModel.id == ProdutoEmpModel.produto_id)
                .where(and_(*subquery_filters))
                .subquery()
            )
            produtos_query = (
                self.db.query(ProdutoModel, ProdutoEmpModel)
                .join(ProdutoEmpModel, ProdutoModel.id == ProdutoEmpModel.produto_id)
                .join(subquery, ProdutoModel.id == subquery.c.id)
                .filter(
                    and_(
                        subquery.c.row_num > offset_id,
                        subquery.c.row_num <= max_id
                    )
                )
                .order_by(ProdutoModel.created_at.asc())
            )
        else:
            # Busca por termo (descrição ou código de barras)
            # Normaliza removendo hífens e espaços de ambos os lados para busca mais flexível
            # "x bacon" encontra "x-bacon" e vice-versa
            term_raw = f"%{termo_lower}%"
            term_norm = f"%{termo_normalizado}%"
            produtos_query = produtos_query.filter(
                or_(
                    self._ilike_sem_acento(
                        func.replace(func.replace(func.lower(ProdutoModel.descricao), "-", ""), " ", ""),
                        term_norm,
                    ),
                    self._ilike_sem_acento(
                        func.replace(func.replace(func.lower(ProdutoModel.cod_barras), "-", ""), " ", ""),
                        term_norm,
                    ),
                    # Também mantém busca original para termos que não tenham hífen/espaço
                    self._ilike_sem_acento(func.lower(ProdutoModel.descricao), term_raw),
                    self._ilike_sem_acento(func.lower(ProdutoModel.cod_barras), term_raw),
                )
            ).order_by(ProdutoModel.created_at.asc())

        produtos_result = produtos_query.limit(limit).all()

        # Busca receitas
        receitas_query = self.db.query(ReceitaModel).filter(
            ReceitaModel.empresa_id == empresa_id
        )

        if apenas_ativos:
            receitas_query = receitas_query.filter(ReceitaModel.ativo.is_(True))

        if apenas_disponiveis:
            receitas_query = receitas_query.filter(ReceitaModel.disponivel.is_(True))

        if termo_vazio:
            # Quando termo vazio, usa WHERE com range de IDs para paginação
            receitas_query = receitas_query.filter(
                and_(
                    ReceitaModel.id > offset_id,
                    ReceitaModel.id <= max_id
                )
            ).order_by(ReceitaModel.id.asc())
        else:
            # Busca por termo (nome ou descrição)
            # Normaliza removendo hífens e espaços de ambos os lados para busca mais flexível
            term_raw = f"%{termo_lower}%"
            term_norm = f"%{termo_normalizado}%"
            condicoes = [
                # Busca normalizada (sem hífen/espaço)
                self._ilike_sem_acento(
                    func.replace(func.replace(func.lower(ReceitaModel.nome), "-", ""), " ", ""),
                    term_norm,
                ),
                # Busca original
                self._ilike_sem_acento(func.lower(ReceitaModel.nome), term_raw),
            ]
            # Adiciona busca na descrição apenas se o campo não for NULL
            condicoes.append(
                and_(
                    ReceitaModel.descricao.isnot(None),
                    self._ilike_sem_acento(
                        func.replace(func.replace(func.lower(ReceitaModel.descricao), "-", ""), " ", ""),
                        term_norm,
                    ),
                )
            )
            condicoes.append(
                and_(
                    ReceitaModel.descricao.isnot(None),
                    self._ilike_sem_acento(func.lower(ReceitaModel.descricao), term_raw),
                )
            )
            receitas_query = receitas_query.filter(or_(*condicoes)).order_by(ReceitaModel.id.asc())

        receitas_result = receitas_query.limit(limit).all()

        # Busca combos
        combos_query = self.db.query(ComboModel).filter(
            ComboModel.empresa_id == empresa_id
        )

        if apenas_ativos:
            combos_query = combos_query.filter(ComboModel.ativo.is_(True))

        if termo_vazio:
            # Quando termo vazio, usa WHERE com range de IDs para paginação
            combos_query = combos_query.filter(
                and_(
                    ComboModel.id > offset_id,
                    ComboModel.id <= max_id
                )
            ).order_by(ComboModel.id.asc())
        else:
            # Busca por termo (título ou descrição)
            # Normaliza removendo hífens e espaços de ambos os lados para busca mais flexível
            term_raw = f"%{termo_lower}%"
            term_norm = f"%{termo_normalizado}%"
            condicoes = []
            # Adiciona busca no título apenas se o campo não for NULL
            condicoes.append(
                and_(
                    ComboModel.titulo.isnot(None),
                    self._ilike_sem_acento(
                        func.replace(func.replace(func.lower(ComboModel.titulo), "-", ""), " ", ""),
                        term_norm,
                    ),
                )
            )
            condicoes.append(
                and_(
                    ComboModel.titulo.isnot(None),
                    self._ilike_sem_acento(func.lower(ComboModel.titulo), term_raw),
                )
            )
            # Descrição sempre existe (não é NULL)
            condicoes.append(
                self._ilike_sem_acento(
                    func.replace(func.replace(func.lower(ComboModel.descricao), "-", ""), " ", ""),
                    term_norm,
                )
            )
            condicoes.append(self._ilike_sem_acento(func.lower(ComboModel.descricao), term_raw))
            combos_query = combos_query.filter(or_(*condicoes)).order_by(ComboModel.id.asc())

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
            quantidade_produtos=total,
            total=total,
        )

