from __future__ import annotations

from decimal import Decimal
from typing import Optional, List
from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.mesas.models.model_mesa import MesaModel
from app.api.mesas.models.model_pedido_mesa import PedidoMesaModel, StatusPedidoMesa

OPEN_STATUS_PEDIDO_MESA = [
    StatusPedidoMesa.PENDENTE.value,
    StatusPedidoMesa.IMPRESSAO.value,
    StatusPedidoMesa.PREPARANDO.value,
    StatusPedidoMesa.EDITADO.value,
    StatusPedidoMesa.EM_EDICAO.value,
    StatusPedidoMesa.AGUARDANDO_PAGAMENTO.value,
]
from app.api.mesas.models.model_pedido_mesa_item import PedidoMesaItemModel
from app.api.catalogo.contracts.produto_contract import IProdutoContract, ProdutoEmpDTO


class PedidoMesaRepository:
    def __init__(self, db: Session, produto_contract: IProdutoContract | None = None):
        self.db = db
        self.produto_contract = produto_contract

    # ------------ Helpers ------------
    def _calc_total(self, pedido: PedidoMesaModel) -> Decimal:
        return sum((item.preco_unitario or Decimal("0")) * (item.quantidade or 0) for item in pedido.itens) or Decimal("0")

    def _refresh_total(self, pedido: PedidoMesaModel) -> PedidoMesaModel:
        pedido.valor_total = self._calc_total(pedido)
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    # ------------ CRUD Pedido ------------
    def get(self, pedido_id: int) -> PedidoMesaModel:
        pedido = (
            self.db.query(PedidoMesaModel)
            .options(joinedload(PedidoMesaModel.itens))
            .filter(PedidoMesaModel.id == pedido_id)
            .first()
        )
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        return pedido

    def list_abertos_by_mesa(self, mesa_id: int, *, empresa_id: int | None = None) -> list[PedidoMesaModel]:
        query = (
            self.db.query(PedidoMesaModel)
            .options(joinedload(PedidoMesaModel.itens))
            .filter(
                PedidoMesaModel.mesa_id == mesa_id,
                PedidoMesaModel.status.in_(OPEN_STATUS_PEDIDO_MESA)
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoMesaModel.empresa_id == empresa_id)
        return query.order_by(PedidoMesaModel.created_at.desc()).all()

    def get_aberto_mais_recente(self, mesa_id: int, *, empresa_id: int | None = None) -> Optional[PedidoMesaModel]:
        query = (
            self.db.query(PedidoMesaModel)
            .filter(
                PedidoMesaModel.mesa_id == mesa_id,
                PedidoMesaModel.status.in_(OPEN_STATUS_PEDIDO_MESA)
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoMesaModel.empresa_id == empresa_id)
        return query.order_by(PedidoMesaModel.created_at.desc()).first()

    def list_abertos_all(self, *, empresa_id: int | None = None) -> list[PedidoMesaModel]:
        query = (
            self.db.query(PedidoMesaModel)
            .options(joinedload(PedidoMesaModel.itens))
            .filter(PedidoMesaModel.status.in_(OPEN_STATUS_PEDIDO_MESA))
        )
        if empresa_id is not None:
            query = query.filter(PedidoMesaModel.empresa_id == empresa_id)
        return query.order_by(PedidoMesaModel.created_at.desc()).all()

    def list_finalizados_by_mesa(
        self,
        mesa_id: int,
        data_filtro: Optional[date] = None,
        *,
        empresa_id: int | None = None,
    ) -> list[PedidoMesaModel]:
        """Lista todos os pedidos finalizados (ENTREGUE) de uma mesa, opcionalmente filtrando por data"""
        query = (
            self.db.query(PedidoMesaModel)
            .options(joinedload(PedidoMesaModel.itens))
            .filter(
                PedidoMesaModel.mesa_id == mesa_id,
                PedidoMesaModel.status == StatusPedidoMesa.ENTREGUE.value
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoMesaModel.empresa_id == empresa_id)
        
        # Filtro por data se fornecido
        if data_filtro is not None:
            data_inicio = datetime.combine(data_filtro, datetime.min.time())
            data_fim = datetime.combine(data_filtro, datetime.max.time())
            query = query.filter(
                PedidoMesaModel.created_at >= data_inicio,
                PedidoMesaModel.created_at <= data_fim
            )
        
        return query.order_by(PedidoMesaModel.created_at.desc()).all()

    def list_by_cliente_id(
        self,
        cliente_id: int,
        skip: int = 0,
        limit: int = 50,
        *,
        empresa_id: int | None = None,
    ) -> list[PedidoMesaModel]:
        """Lista todos os pedidos de um cliente específico"""
        query = (
            self.db.query(PedidoMesaModel)
            .options(
                joinedload(PedidoMesaModel.itens),
                joinedload(PedidoMesaModel.mesa),
                joinedload(PedidoMesaModel.cliente)
            )
            .filter(PedidoMesaModel.cliente_id == cliente_id)
        )
        if empresa_id is not None:
            query = query.filter(PedidoMesaModel.empresa_id == empresa_id)
        return (
            query
            .order_by(PedidoMesaModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(
        self,
        *,
        mesa_id: int,
        empresa_id: int,
        cliente_id: Optional[int],
        observacoes: Optional[str],
        num_pessoas: Optional[int],
    ) -> PedidoMesaModel:
        mesa = (
            self.db.query(MesaModel)
            .filter(
                MesaModel.id == mesa_id,
                MesaModel.empresa_id == empresa_id,
            )
            .first()
        )
        if not mesa:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa não encontrada")

        # número simples: M{mesa_id}-{sequencial curto}
        seq = (
            self.db.query(PedidoMesaModel)
            .filter(
                PedidoMesaModel.mesa_id == mesa_id,
                PedidoMesaModel.empresa_id == empresa_id,
            )
            .count()
            or 0
        ) + 1
        numero = f"{mesa.numero}-{seq:03d}"

        pedido = PedidoMesaModel(
            empresa_id=empresa_id,
            mesa_id=mesa_id,
            cliente_id=cliente_id,
            numero_pedido=numero,
            observacoes=observacoes,
            num_pessoas=num_pessoas,
            status=StatusPedidoMesa.IMPRESSAO.value,  # Converte enum para valor string
        )
        self.db.add(pedido)
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    # ------------ Itens ------------
    def add_item(
        self,
        pedido_id: int,
        *,
        produto_cod_barras: str,
        quantidade: int,
        observacao: Optional[str],
    ) -> PedidoMesaModel:
        pedido = self.get(pedido_id)

        descricao_snapshot = None
        imagem_snapshot = None
        preco_unitario = Decimal("0")

        pe_dto: ProdutoEmpDTO | None = None
        if self.produto_contract is not None:
            pe_dto = self.produto_contract.obter_produto_emp_por_cod(pedido.empresa_id, produto_cod_barras)
            if not pe_dto:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")
            if not pe_dto.disponivel or not (pe_dto.produto and bool(pe_dto.produto.ativo)):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Produto indisponível")
            preco_unitario = Decimal(str(pe_dto.preco_venda or 0))
            if pe_dto.produto:
                descricao_snapshot = pe_dto.produto.descricao
                imagem_snapshot = pe_dto.produto.imagem
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Contrato de produto não configurado")

        item = PedidoMesaItemModel(
            pedido_id=pedido.id,
            produto_cod_barras=produto_cod_barras,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            observacao=observacao,
            produto_descricao_snapshot=descricao_snapshot,
            produto_imagem_snapshot=imagem_snapshot,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        return self._refresh_total(pedido)

    def remove_item(self, pedido_id: int, item_id: int) -> PedidoMesaModel:
        pedido = self.get(pedido_id)
        item = (
            self.db.query(PedidoMesaItemModel)
            .filter(PedidoMesaItemModel.id == item_id, PedidoMesaItemModel.pedido_id == pedido_id)
            .first()
        )
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Item não encontrado")
        self.db.delete(item)
        self.db.commit()
        return self._refresh_total(pedido)

    # ------------ Fluxo Pedido ------------
    def cancelar(self, pedido_id: int) -> PedidoMesaModel:
        pedido = self.get(pedido_id)
        pedido.status = StatusPedidoMesa.CANCELADO.value  # Converte enum para valor string
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def confirmar(self, pedido_id: int) -> PedidoMesaModel:
        pedido = self.get(pedido_id)
        pedido.status = StatusPedidoMesa.IMPRESSAO.value  # Converte enum para valor string
        self.db.commit()
        self.db.refresh(pedido)
        # garante total atualizado de acordo com itens
        return self._refresh_total(pedido)

    def fechar_conta(self, pedido_id: int) -> PedidoMesaModel:
        pedido = self.get(pedido_id)
        pedido.status = StatusPedidoMesa.ENTREGUE.value  # Converte enum para valor string
        self.db.commit()
        self.db.refresh(pedido)
        return self._refresh_total(pedido)

    def reabrir(self, pedido_id: int) -> PedidoMesaModel:
        pedido = self.get(pedido_id)
        # Compara com valores string do banco
        status_atual = pedido.status if isinstance(pedido.status, str) else pedido.status.value if hasattr(pedido.status, 'value') else str(pedido.status)
        if status_atual != StatusPedidoMesa.CANCELADO.value and status_atual != StatusPedidoMesa.ENTREGUE.value:
            return pedido
        # Sempre reabre para PENDENTE
        pedido.status = StatusPedidoMesa.PENDENTE.value  # Converte enum para valor string
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def atualizar_status(self, pedido_id: int, novo_status) -> PedidoMesaModel:
        """Atualiza o status do pedido com valor fornecido (enum ou string)."""
        pedido = self.get(pedido_id)
        if hasattr(novo_status, "value"):
            valor_status = novo_status.value
        else:
            valor_status = str(novo_status)
        pedido.status = valor_status
        self.db.commit()
        self.db.refresh(pedido)
        return pedido


