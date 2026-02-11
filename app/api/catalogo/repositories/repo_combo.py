from typing import List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.api.catalogo.models.model_combo import ComboModel, ComboItemModel
from app.api.catalogo.models.model_combo_secoes import ComboSecaoModel, ComboSecaoItemModel
from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.models.model_receita import ReceitaModel


class ComboRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, combo_id: int) -> Optional[ComboModel]:
        return (
            self.db.query(ComboModel)
            .options(
                joinedload(ComboModel.secoes).joinedload(ComboSecaoModel.itens).joinedload(ComboSecaoItemModel.produto),
                joinedload(ComboModel.secoes).joinedload(ComboSecaoModel.itens).joinedload(ComboSecaoItemModel.receita),
                joinedload(ComboModel.itens)
            )
            .filter(ComboModel.id == combo_id)
            .first()
        )

    def list_paginado(self, empresa_id: int, offset: int, limit: int, search: Optional[str] = None) -> List[ComboModel]:
        query = (
            self.db.query(ComboModel)
            .options(
                joinedload(ComboModel.secoes).joinedload(ComboSecaoModel.itens).joinedload(ComboSecaoItemModel.produto),
                joinedload(ComboModel.secoes).joinedload(ComboSecaoModel.itens).joinedload(ComboSecaoItemModel.receita),
                joinedload(ComboModel.itens).joinedload(ComboItemModel.produto),
                joinedload(ComboModel.itens).joinedload(ComboItemModel.receita)
            )
            .filter(ComboModel.empresa_id == empresa_id)
        )

        if search and search.strip():
            termo = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    ComboModel.titulo.ilike(termo),
                    ComboModel.descricao.ilike(termo),
                )
            )

        return (
            query
            .order_by(ComboModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_total(self, empresa_id: int, search: Optional[str] = None) -> int:
        query = self.db.query(func.count(ComboModel.id)).filter(ComboModel.empresa_id == empresa_id)

        if search and search.strip():
            termo = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    ComboModel.titulo.ilike(termo),
                    ComboModel.descricao.ilike(termo),
                )
            )

        return int(query.scalar() or 0)

    def criar_combo(
        self,
        *,
        empresa_id: int,
        titulo: str,
        descricao: str,
        preco_total,
        custo_total,
        ativo: bool,
        imagem_url: Optional[str],
        itens: List[dict],
        secoes: List[dict] | None = None,
    ) -> ComboModel:
        combo = ComboModel(
            empresa_id=empresa_id,
            titulo=titulo,
            descricao=descricao,
            preco_total=preco_total,
            custo_total=custo_total,
            ativo=ativo,
            imagem=imagem_url,
        )
        self.db.add(combo)
        self.db.flush()
        # Itens legados — mantém suporte caso enviado
        for it in itens:
            # Valida e cria item (produto ou receita)
            if "produto_cod_barras" in it and it["produto_cod_barras"]:
                prod = self.db.query(ProdutoModel).filter_by(cod_barras=it["produto_cod_barras"]).first()
                if not prod:
                    raise ValueError(f"Produto inexistente: {it['produto_cod_barras']}")
                self.db.add(ComboItemModel(
                    combo_id=combo.id,
                    produto_id=prod.id,
                    produto_cod_barras=it["produto_cod_barras"],
                    receita_id=None,
                    quantidade=it.get("quantidade", 1),
                ))
            elif "receita_id" in it and it["receita_id"]:
                receita = self.db.query(ReceitaModel).filter_by(id=it["receita_id"]).first()
                if not receita:
                    raise ValueError(f"Receita inexistente: {it['receita_id']}")
                self.db.add(ComboItemModel(
                    combo_id=combo.id,
                    produto_cod_barras=None,
                    receita_id=it["receita_id"],
                    quantidade=it.get("quantidade", 1),
                ))
            else:
                raise ValueError("Item deve ter produto_cod_barras ou receita_id")

        # Seções — novo formato
        if secoes:
            for s in secoes:
                sec = ComboSecaoModel(
                    combo_id=combo.id,
                    titulo=s.get("titulo"),
                    descricao=s.get("descricao"),
                    obrigatorio=bool(s.get("obrigatorio", False)),
                    quantitativo=bool(s.get("quantitativo", False)),
                    minimo_itens=int(s.get("minimo_itens", 0)),
                    maximo_itens=int(s.get("maximo_itens", 1)),
                    ordem=int(s.get("ordem", 0)),
                )
                self.db.add(sec)
                self.db.flush()
                for it in s.get("itens", []):
                    if "produto_cod_barras" in it and it["produto_cod_barras"]:
                        prod = self.db.query(ProdutoModel).filter_by(cod_barras=it["produto_cod_barras"]).first()
                        if not prod:
                            raise ValueError(f"Produto inexistente: {it['produto_cod_barras']}")
                        self.db.add(ComboSecaoItemModel(
                            secao_id=sec.id,
                            produto_id=prod.id,
                            produto_cod_barras=it["produto_cod_barras"],
                            receita_id=None,
                            preco_incremental=it.get("preco_incremental", 0),
                            permite_quantidade=bool(it.get("permite_quantidade", False)),
                            quantidade_min=int(it.get("quantidade_min", 1)),
                            quantidade_max=int(it.get("quantidade_max", 1)),
                            ordem=int(it.get("ordem", 0)),
                        ))
                    elif "receita_id" in it and it["receita_id"]:
                        receita = self.db.query(ReceitaModel).filter_by(id=it["receita_id"]).first()
                        if not receita:
                            raise ValueError(f"Receita inexistente: {it['receita_id']}")
                        self.db.add(ComboSecaoItemModel(
                            secao_id=sec.id,
                            produto_cod_barras=None,
                            receita_id=it["receita_id"],
                            preco_incremental=it.get("preco_incremental", 0),
                            permite_quantidade=bool(it.get("permite_quantidade", False)),
                            quantidade_min=int(it.get("quantidade_min", 1)),
                            quantidade_max=int(it.get("quantidade_max", 1)),
                            ordem=int(it.get("ordem", 0)),
                        ))
                    else:
                        raise ValueError("Item da seção deve ter produto_cod_barras ou receita_id")

        self.db.flush()
        return combo

    def atualizar_combo(
        self,
        combo: ComboModel,
        *,
        titulo: Optional[str] = None,
        descricao: Optional[str] = None,
        preco_total=None,
        custo_total=None,
        ativo: Optional[bool] = None,
        imagem_url: Optional[str] = None,
        itens: Optional[List[dict]] = None,
    ) -> ComboModel:
        if titulo is not None:
            combo.titulo = titulo
        if descricao is not None:
            combo.descricao = descricao
        if preco_total is not None:
            combo.preco_total = preco_total
        if custo_total is not None:
            combo.custo_total = custo_total
        if ativo is not None:
            combo.ativo = ativo
        if imagem_url is not None:
            combo.imagem = imagem_url

        if itens is not None:
            # substitui todos os itens legados
            self.db.query(ComboItemModel).filter(ComboItemModel.combo_id == combo.id).delete()
            self.db.flush()
            for it in itens:
                if "produto_cod_barras" in it and it["produto_cod_barras"]:
                    prod = self.db.query(ProdutoModel).filter_by(cod_barras=it["produto_cod_barras"]).first()
                    if not prod:
                        raise ValueError(f"Produto inexistente: {it['produto_cod_barras']}")
                    self.db.add(ComboItemModel(
                        combo_id=combo.id,
                        produto_id=prod.id,
                        produto_cod_barras=it["produto_cod_barras"],
                        receita_id=None,
                        quantidade=it.get("quantidade", 1),
                    ))
                elif "receita_id" in it and it["receita_id"]:
                    receita = self.db.query(ReceitaModel).filter_by(id=it["receita_id"]).first()
                    if not receita:
                        raise ValueError(f"Receita inexistente: {it['receita_id']}")
                    self.db.add(ComboItemModel(
                        combo_id=combo.id,
                        produto_cod_barras=None,
                        receita_id=it["receita_id"],
                        quantidade=it.get("quantidade", 1),
                    ))
                else:
                    raise ValueError("Item deve ter produto_cod_barras ou receita_id")

        # Substitui seções caso informado
        if secoes is not None:
            # remove seções antigas
            self.db.query(ComboSecaoItemModel).filter(ComboSecaoItemModel.secao_id.in_(
                self.db.query(ComboSecaoModel.id).filter(ComboSecaoModel.combo_id == combo.id)
            )).delete(synchronize_session=False)
            self.db.query(ComboSecaoModel).filter(ComboSecaoModel.combo_id == combo.id).delete()
            self.db.flush()
            for s in secoes:
                sec = ComboSecaoModel(
                    combo_id=combo.id,
                    titulo=s.get("titulo"),
                    descricao=s.get("descricao"),
                    obrigatorio=bool(s.get("obrigatorio", False)),
                    quantitativo=bool(s.get("quantitativo", False)),
                    minimo_itens=int(s.get("minimo_itens", 0)),
                    maximo_itens=int(s.get("maximo_itens", 1)),
                    ordem=int(s.get("ordem", 0)),
                )
                self.db.add(sec)
                self.db.flush()
                for it in s.get("itens", []):
                    if "produto_cod_barras" in it and it["produto_cod_barras"]:
                        prod = self.db.query(ProdutoModel).filter_by(cod_barras=it["produto_cod_barras"]).first()
                        if not prod:
                            raise ValueError(f"Produto inexistente: {it['produto_cod_barras']}")
                        self.db.add(ComboSecaoItemModel(
                            secao_id=sec.id,
                            produto_id=prod.id,
                            produto_cod_barras=it["produto_cod_barras"],
                            receita_id=None,
                            preco_incremental=it.get("preco_incremental", 0),
                            permite_quantidade=bool(it.get("permite_quantidade", False)),
                            quantidade_min=int(it.get("quantidade_min", 1)),
                            quantidade_max=int(it.get("quantidade_max", 1)),
                            ordem=int(it.get("ordem", 0)),
                        ))
                    elif "receita_id" in it and it["receita_id"]:
                        receita = self.db.query(ReceitaModel).filter_by(id=it["receita_id"]).first()
                        if not receita:
                            raise ValueError(f"Receita inexistente: {it['receita_id']}")
                        self.db.add(ComboSecaoItemModel(
                            secao_id=sec.id,
                            produto_cod_barras=None,
                            receita_id=it["receita_id"],
                            preco_incremental=it.get("preco_incremental", 0),
                            permite_quantidade=bool(it.get("permite_quantidade", False)),
                            quantidade_min=int(it.get("quantidade_min", 1)),
                            quantidade_max=int(it.get("quantidade_max", 1)),
                            ordem=int(it.get("ordem", 0)),
                        ))
                    else:
                        raise ValueError("Item da seção deve ter produto_cod_barras ou receita_id")

        self.db.flush()
        return combo

    def deletar_combo(self, combo: ComboModel) -> None:
        self.db.delete(combo)
        self.db.flush()

