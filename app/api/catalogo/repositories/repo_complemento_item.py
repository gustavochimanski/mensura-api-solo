"""Repository para vínculos de itens (produto/receita/combo) dentro de complementos."""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.api.catalogo.models.model_complemento import ComplementoModel
from app.api.catalogo.models.model_complemento_vinculo_item import ComplementoVinculoItemModel
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel


class ComplementoItemRepository:
    """Operações CRUD sobre complemento_vinculo_item (itens = produto/receita/combo)."""

    def __init__(self, db: Session):
        self.db = db

    def buscar_por_id(
        self,
        vinculo_id: int,
        carregar_entidades: bool = True,
    ) -> Optional[ComplementoVinculoItemModel]:
        """Busca um vínculo por ID."""
        q = self.db.query(ComplementoVinculoItemModel).filter_by(id=vinculo_id)
        if carregar_entidades:
            q = q.options(
                joinedload(ComplementoVinculoItemModel.produto),
                joinedload(ComplementoVinculoItemModel.receita),
                joinedload(ComplementoVinculoItemModel.combo),
                joinedload(ComplementoVinculoItemModel.complemento),
            )
        return q.first()

    def listar_itens_complemento(
        self,
        complemento_id: int,
        apenas_ativos: bool = True,
        empresa_id: Optional[int] = None,
    ) -> List[Tuple[ComplementoVinculoItemModel, int]]:
        """
        Lista os vínculos (itens) de um complemento.

        Returns:
            Lista de (vinculo, ordem). Ordem vem do próprio vinculo.ordem.
        """
        q = (
            self.db.query(ComplementoVinculoItemModel)
            .filter(ComplementoVinculoItemModel.complemento_id == complemento_id)
            .options(
                joinedload(ComplementoVinculoItemModel.produto),
                joinedload(ComplementoVinculoItemModel.receita),
                joinedload(ComplementoVinculoItemModel.combo),
            )
        )
        rows = q.order_by(ComplementoVinculoItemModel.ordem, ComplementoVinculoItemModel.id).all()

        out: List[Tuple[ComplementoVinculoItemModel, int]] = []
        for v in rows:
            if apenas_ativos and not self._ativo(v, empresa_id):
                continue
            out.append((v, int(v.ordem)))
        return out

    def _ativo(self, v: ComplementoVinculoItemModel, _empresa_id: Optional[int]) -> bool:
        return bool(getattr(v, "ativo", True))

    def vincular_itens_complemento(
        self,
        complemento_id: int,
        items: List[dict],
        ordens: Optional[List[int]] = None,
        precos: Optional[List[Optional[Decimal]]] = None,
    ) -> None:
        """
        Substitui os itens do complemento pelos fornecidos.

        Cada item em `items` deve ter exatamente um de:
        produto_cod_barras, receita_id, combo_id.
        """
        comp = self.db.query(ComplementoModel).filter_by(id=complemento_id).first()
        if not comp:
            raise ValueError(f"Complemento {complemento_id} não encontrado")

        # Remove vínculos existentes
        self.db.query(ComplementoVinculoItemModel).filter(
            ComplementoVinculoItemModel.complemento_id == complemento_id
        ).delete(synchronize_session="fetch")
        self.db.flush()

        for i, it in enumerate(items):
            pid = it.get("produto_cod_barras")
            rid = it.get("receita_id")
            cid = it.get("combo_id")
            n = sum(1 for x in (pid, rid, cid) if x is not None)
            if n != 1:
                raise ValueError("Cada item deve ter exatamente um de: produto_cod_barras, receita_id, combo_id")

            ordem = (ordens[i] if ordens and i < len(ordens) else i)
            # Garante que o preço do adicional seja definido no vínculo
            preco = precos[i] if precos and i < len(precos) else None

            vinculo = ComplementoVinculoItemModel(
                complemento_id=complemento_id,
                produto_cod_barras=pid,
                receita_id=rid,
                combo_id=cid,
                ordem=ordem,
                preco_complemento=preco,  # Preço específico do adicional neste complemento
            )
            self.db.add(vinculo)
            # Flush dentro do loop para garantir persistência individual e detecção de erros mais cedo
            self.db.flush()

    def vincular_item_complemento(
        self,
        complemento_id: int,
        *,
        produto_cod_barras: Optional[str] = None,
        receita_id: Optional[int] = None,
        combo_id: Optional[int] = None,
        ordem: Optional[int] = None,
        preco_complemento: Optional[Decimal] = None,
    ) -> ComplementoVinculoItemModel:
        """Adiciona um único item ao complemento (ou atualiza se já existir)."""
        n = sum(1 for x in (produto_cod_barras, receita_id, combo_id) if x is not None)
        if n != 1:
            raise ValueError("Informe exatamente um de: produto_cod_barras, receita_id, combo_id")

        if produto_cod_barras is not None:
            existing = (
                self.db.query(ComplementoVinculoItemModel)
                .filter(
                    ComplementoVinculoItemModel.complemento_id == complemento_id,
                    ComplementoVinculoItemModel.produto_cod_barras == produto_cod_barras,
                )
                .first()
            )
        elif receita_id is not None:
            existing = (
                self.db.query(ComplementoVinculoItemModel)
                .filter(
                    ComplementoVinculoItemModel.complemento_id == complemento_id,
                    ComplementoVinculoItemModel.receita_id == receita_id,
                )
                .first()
            )
        else:
            existing = (
                self.db.query(ComplementoVinculoItemModel)
                .filter(
                    ComplementoVinculoItemModel.complemento_id == complemento_id,
                    ComplementoVinculoItemModel.combo_id == combo_id,
                )
                .first()
            )

        if existing:
            if ordem is not None:
                existing.ordem = ordem
            if preco_complemento is not None:
                existing.preco_complemento = preco_complemento
            self.db.flush()
            return existing

        if ordem is None:
            r = (
                self.db.query(ComplementoVinculoItemModel.ordem)
                .filter(ComplementoVinculoItemModel.complemento_id == complemento_id)
                .order_by(ComplementoVinculoItemModel.ordem.desc())
                .limit(1)
                .scalar()
            )
            ordem = (r + 1) if r is not None else 0

        v = ComplementoVinculoItemModel(
            complemento_id=complemento_id,
            produto_cod_barras=produto_cod_barras,
            receita_id=receita_id,
            combo_id=combo_id,
            ordem=ordem,
            preco_complemento=preco_complemento,
        )
        self.db.add(v)
        self.db.flush()
        return v

    def desvincular_item_complemento(self, complemento_id: int, vinculo_id: int) -> None:
        """Remove o vínculo (por id do vinculo)."""
        self.db.query(ComplementoVinculoItemModel).filter(
            ComplementoVinculoItemModel.complemento_id == complemento_id,
            ComplementoVinculoItemModel.id == vinculo_id,
        ).delete(synchronize_session="fetch")
        self.db.flush()

    def atualizar_preco_item_complemento(
        self,
        complemento_id: int,
        vinculo_id: int,
        preco_complemento: Decimal,
    ) -> None:
        """Atualiza o preço do item dentro do complemento."""
        v = (
            self.db.query(ComplementoVinculoItemModel)
            .filter(
                ComplementoVinculoItemModel.complemento_id == complemento_id,
                ComplementoVinculoItemModel.id == vinculo_id,
            )
            .first()
        )
        if not v:
            raise ValueError(f"Vínculo {vinculo_id} não encontrado no complemento {complemento_id}")
        v.preco_complemento = preco_complemento
        self.db.flush()

    def atualizar_ordem_itens(self, complemento_id: int, item_ordens: List[dict]) -> None:
        """Atualiza a ordem dos itens. item_ordens: [{'item_id': vinculo_id, 'ordem': int}, ...]."""
        for io in item_ordens:
            vid = io.get("item_id")
            ordem = io.get("ordem")
            if vid is None or ordem is None:
                continue
            self.db.query(ComplementoVinculoItemModel).filter(
                ComplementoVinculoItemModel.complemento_id == complemento_id,
                ComplementoVinculoItemModel.id == vid,
            ).update({"ordem": ordem}, synchronize_session="fetch")
        self.db.flush()

    def preco_e_custo_vinculo(
        self,
        v: ComplementoVinculoItemModel,
        empresa_id: int,
    ) -> Tuple[Decimal, Decimal]:
        """Retorna (preco, custo) para o vínculo. Preco usa preco_complemento se definido."""
        preco = v.preco_complemento
        custo = Decimal("0")

        if v.produto_cod_barras and v.produto:
            pe = (
                self.db.query(ProdutoEmpModel)
                .filter(
                    ProdutoEmpModel.empresa_id == empresa_id,
                    ProdutoEmpModel.cod_barras == v.produto_cod_barras,
                )
                .first()
            )
            if pe:
                if preco is None:
                    preco = pe.preco_venda
                custo = pe.custo or Decimal("0")
        elif v.receita_id and v.receita:
            r = v.receita
            if preco is None:
                preco = r.preco_venda
        elif v.combo_id and v.combo:
            c = v.combo
            if preco is None:
                preco = c.preco_total
            custo = c.custo_total or Decimal("0")

        if preco is None:
            preco = Decimal("0")
        return (preco, custo)
