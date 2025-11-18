from __future__ import annotations

from decimal import Decimal
from typing import Optional, List
from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.mesas.models.model_mesa import MesaModel
from app.api.balcao.models.model_pedido_balcao import PedidoBalcaoModel, StatusPedidoBalcao
from app.api.balcao.models.model_pedido_balcao_item import PedidoBalcaoItemModel
from app.api.balcao.models.model_pedido_balcao_historico import PedidoBalcaoHistoricoModel, TipoOperacaoPedidoBalcao
from app.api.catalogo.contracts.produto_contract import IProdutoContract, ProdutoEmpDTO


OPEN_STATUS_PEDIDO_BALCAO = [
    StatusPedidoBalcao.PENDENTE.value,
    StatusPedidoBalcao.IMPRESSAO.value,
    StatusPedidoBalcao.PREPARANDO.value,
    StatusPedidoBalcao.EDITADO.value,
    StatusPedidoBalcao.EM_EDICAO.value,
    StatusPedidoBalcao.AGUARDANDO_PAGAMENTO.value,
]


class PedidoBalcaoRepository:
    def __init__(self, db: Session, produto_contract: IProdutoContract | None = None):
        self.db = db
        self.produto_contract = produto_contract

    # ------------ Helpers ------------
    def _calc_total(self, pedido: PedidoBalcaoModel) -> Decimal:
        return sum((item.preco_unitario or Decimal("0")) * (item.quantidade or 0) for item in pedido.itens) or Decimal("0")

    def _refresh_total(self, pedido: PedidoBalcaoModel) -> PedidoBalcaoModel:
        pedido.valor_total = self._calc_total(pedido)
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    # ------------ CRUD Pedido ------------
    def get(self, pedido_id: int) -> PedidoBalcaoModel:
        pedido = (
            self.db.query(PedidoBalcaoModel)
            .options(joinedload(PedidoBalcaoModel.itens))
            .filter(PedidoBalcaoModel.id == pedido_id)
            .first()
        )
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        return pedido

    def list_abertos_by_mesa(self, mesa_id: int, *, empresa_id: Optional[int] = None) -> list[PedidoBalcaoModel]:
        """Lista pedidos abertos de balcão associados a uma mesa específica"""
        query = (
            self.db.query(PedidoBalcaoModel)
            .options(joinedload(PedidoBalcaoModel.itens))
            .filter(
                PedidoBalcaoModel.mesa_id == mesa_id,
                PedidoBalcaoModel.status.in_(OPEN_STATUS_PEDIDO_BALCAO)
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoBalcaoModel.empresa_id == empresa_id)
        return query.order_by(PedidoBalcaoModel.created_at.desc()).all()

    def list_abertos_all(self, *, empresa_id: Optional[int] = None) -> list[PedidoBalcaoModel]:
        query = (
            self.db.query(PedidoBalcaoModel)
            .options(joinedload(PedidoBalcaoModel.itens))
            .filter(
                PedidoBalcaoModel.status.in_(OPEN_STATUS_PEDIDO_BALCAO)
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoBalcaoModel.empresa_id == empresa_id)
        return query.order_by(PedidoBalcaoModel.created_at.desc()).all()

    def list_finalizados(self, data_filtro: date, *, empresa_id: Optional[int] = None) -> list[PedidoBalcaoModel]:
        """Lista todos os pedidos finalizados (ENTREGUE), filtrando por data (obrigatório)"""
        from sqlalchemy import or_, and_
        
        # data_filtro é sempre obrigatório
        data_inicio = datetime.combine(data_filtro, datetime.min.time())
        data_fim = datetime.combine(data_filtro, datetime.max.time())
        
        query = (
            self.db.query(PedidoBalcaoModel)
            .options(joinedload(PedidoBalcaoModel.itens))
            .filter(PedidoBalcaoModel.status == StatusPedidoBalcao.ENTREGUE.value)
        )

        if empresa_id is not None:
            query = query.filter(PedidoBalcaoModel.empresa_id == empresa_id)
        
        # Busca pedidos criados naquele dia OU pedidos entregues naquele dia
        # (mesmo que tenham sido criados em outro dia)
        query = query.filter(
            or_(
                # Pedidos criados naquele dia
                and_(
                    PedidoBalcaoModel.created_at >= data_inicio,
                    PedidoBalcaoModel.created_at <= data_fim
                ),
                # Pedidos entregues naquele dia (baseado em updated_at quando status = E)
                and_(
                    PedidoBalcaoModel.updated_at >= data_inicio,
                    PedidoBalcaoModel.updated_at <= data_fim
                )
            )
        )
        
        return query.order_by(PedidoBalcaoModel.created_at.desc()).all()

    def list_by_cliente_id(self, cliente_id: int, *, empresa_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> list[PedidoBalcaoModel]:
        """Lista todos os pedidos de um cliente específico"""
        query = (
            self.db.query(PedidoBalcaoModel)
            .options(
                joinedload(PedidoBalcaoModel.itens),
                joinedload(PedidoBalcaoModel.mesa),
                joinedload(PedidoBalcaoModel.cliente)
            )
            .filter(PedidoBalcaoModel.cliente_id == cliente_id)
        )
        if empresa_id is not None:
            query = query.filter(PedidoBalcaoModel.empresa_id == empresa_id)
        return (
            query
            .order_by(PedidoBalcaoModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(
        self,
        *,
        empresa_id: int,
        mesa_id: Optional[int],
        cliente_id: int,
        observacoes: Optional[str],
    ) -> PedidoBalcaoModel:
        # Valida mesa se informada
        if mesa_id is not None:
            mesa = self.db.query(MesaModel).filter(MesaModel.id == mesa_id).first()
            if not mesa:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa não encontrada")
            if mesa.empresa_id != empresa_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mesa não pertence à empresa informada")

        # Gera número único de pedido: BAL-{sequencial} por empresa
        seq = (
            self.db.query(PedidoBalcaoModel)
            .filter(PedidoBalcaoModel.empresa_id == empresa_id)
            .count()
            + 1
        )
        numero = f"BAL-{seq:06d}"

        pedido = PedidoBalcaoModel(
            empresa_id=empresa_id,
            mesa_id=mesa_id,
            cliente_id=cliente_id,
            numero_pedido=numero,
            observacoes=observacoes,
            status=StatusPedidoBalcao.IMPRESSAO.value,
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
    ) -> PedidoBalcaoModel:
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
            # Fallback legado: mantém comportamento anterior mínimo (sem depender de modelos de cadastros)
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Contrato de produto não configurado")

        item = PedidoBalcaoItemModel(
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

    def remove_item(self, pedido_id: int, item_id: int) -> PedidoBalcaoModel:
        pedido = self.get(pedido_id)
        item = (
            self.db.query(PedidoBalcaoItemModel)
            .filter(PedidoBalcaoItemModel.id == item_id, PedidoBalcaoItemModel.pedido_id == pedido_id)
            .first()
        )
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Item não encontrado")
        self.db.delete(item)
        self.db.commit()
        return self._refresh_total(pedido)

    # ------------ Fluxo Pedido ------------
    def cancelar(self, pedido_id: int) -> PedidoBalcaoModel:
        pedido = self.get(pedido_id)
        pedido.status = StatusPedidoBalcao.CANCELADO.value
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def confirmar(self, pedido_id: int) -> PedidoBalcaoModel:
        pedido = self.get(pedido_id)
        pedido.status = StatusPedidoBalcao.IMPRESSAO.value
        self.db.commit()
        self.db.refresh(pedido)
        return self._refresh_total(pedido)

    def fechar_conta(self, pedido_id: int) -> PedidoBalcaoModel:
        pedido = self.get(pedido_id)
        pedido.status = StatusPedidoBalcao.ENTREGUE.value
        self.db.commit()
        self.db.refresh(pedido)
        return self._refresh_total(pedido)

    def reabrir(self, pedido_id: int) -> PedidoBalcaoModel:
        pedido = self.get(pedido_id)
        status_atual = (
            pedido.status
            if isinstance(pedido.status, str)
            else pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)
        )
        if status_atual != StatusPedidoBalcao.CANCELADO.value and status_atual != StatusPedidoBalcao.ENTREGUE.value:
            return pedido
        pedido.status = StatusPedidoBalcao.IMPRESSAO.value
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def atualizar_status(self, pedido_id: int, novo_status) -> PedidoBalcaoModel:
        """Atualiza o status do pedido (aceita enum ou string)."""
        pedido = self.get(pedido_id)
        if hasattr(novo_status, "value"):
            status_value = novo_status.value
        else:
            status_value = str(novo_status)
        pedido.status = status_value
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def commit(self):
        """Commite a transação"""
        self.db.commit()

    # ------------ Histórico ------------
    def add_historico(
        self,
        pedido_id: int,
        tipo_operacao: TipoOperacaoPedidoBalcao,
        status_anterior: str | None = None,
        status_novo: str | None = None,
        descricao: str | None = None,
        observacoes: str | None = None,
        cliente_id: int | None = None,
        usuario_id: int | None = None,
        ip_origem: str | None = None,
        user_agent: str | None = None
    ):
        """Adiciona um registro ao histórico do pedido de balcão"""
        status_anterior_value = (
            status_anterior.value
            if hasattr(status_anterior, "value")
            else status_anterior
        )
        status_novo_value = (
            status_novo.value
            if hasattr(status_novo, "value")
            else status_novo
        )

        historico = PedidoBalcaoHistoricoModel(
            pedido_id=pedido_id,
            cliente_id=cliente_id,
            usuario_id=usuario_id,
            tipo_operacao=tipo_operacao.value if hasattr(tipo_operacao, "value") else tipo_operacao,
            status_anterior=status_anterior_value,
            status_novo=status_novo_value,
            descricao=descricao,
            observacoes=observacoes,
            ip_origem=ip_origem,
            user_agent=user_agent
        )
        self.db.add(historico)

    def get_historico(self, pedido_id: int, limit: int = 100) -> list[PedidoBalcaoHistoricoModel]:
        """Busca histórico de um pedido"""
        return (
            self.db.query(PedidoBalcaoHistoricoModel)
            .options(joinedload(PedidoBalcaoHistoricoModel.usuario))
            .filter(PedidoBalcaoHistoricoModel.pedido_id == pedido_id)
            .order_by(PedidoBalcaoHistoricoModel.created_at.desc())
            .limit(limit)
            .all()
        )

