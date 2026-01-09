"""
Repository unificado para pedidos.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, List
from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.api.pedidos.models.model_pedido import PedidoModel, TipoPedido, StatusPedido
from app.api.pedidos.models.model_pedido_item import PedidoUnificadoItemModel
from app.api.pedidos.models.model_pedido_historico import PedidoHistoricoModel
from app.api.mesas.models.model_mesa import MesaModel
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.pedidos.utils.helpers import enum_value


# Status considerados "abertos" (não finalizados)
OPEN_STATUS_PEDIDO = [
    StatusPedido.PENDENTE.value,
    StatusPedido.IMPRESSAO.value,
    StatusPedido.PREPARANDO.value,
    StatusPedido.SAIU_PARA_ENTREGA.value,
    StatusPedido.EDITADO.value,
    StatusPedido.EM_EDICAO.value,
    StatusPedido.AGUARDANDO_PAGAMENTO.value,
]


class PedidoRepository:
    """Repository unificado para todos os tipos de pedidos."""
    
    def __init__(self, db: Session, produto_contract: IProdutoContract | None = None):
        self.db = db
        self.produto_contract = produto_contract

    # ------------ Helpers ------------
    def _calc_subtotal(self, pedido: PedidoModel) -> Decimal:
        """Calcula o subtotal do pedido baseado nos itens."""
        return sum(
            (item.preco_unitario or Decimal("0")) * (item.quantidade or 0)
            for item in pedido.itens
        ) or Decimal("0")

    def _calc_total(self, pedido: PedidoModel) -> Decimal:
        """Calcula o total do pedido incluindo descontos e taxas."""
        subtotal = self._calc_subtotal(pedido)
        desconto = pedido.desconto or Decimal("0")
        taxa_entrega = pedido.taxa_entrega or Decimal("0")
        taxa_servico = pedido.taxa_servico or Decimal("0")
        total = subtotal - desconto + taxa_entrega + taxa_servico
        return total if total > 0 else Decimal("0")

    def _refresh_totals(self, pedido: PedidoModel) -> PedidoModel:
        """Recalcula e atualiza os valores do pedido."""
        pedido.subtotal = self._calc_subtotal(pedido)
        pedido.valor_total = self._calc_total(pedido)
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def _gerar_numero_pedido(self, tipo_pedido: str, empresa_id: int) -> str:
        """Gera número único de pedido baseado no tipo."""
        prefixos = {
            TipoPedido.MESA.value: "MESA",
            TipoPedido.BALCAO.value: "BAL",
            TipoPedido.DELIVERY.value: "DEL",
        }
        prefixo = prefixos.get(tipo_pedido, "PED")
        
        # Conta pedidos existentes do mesmo tipo e empresa
        seq = (
            self.db.query(PedidoModel)
            .filter(
                PedidoModel.empresa_id == empresa_id,
                PedidoModel.tipo_pedido == tipo_pedido
            )
            .count()
            + 1
        )
        return f"{prefixo}-{seq:06d}"

    # ------------ CRUD Pedido ------------
    def get(self, pedido_id: int) -> PedidoModel:
        """Busca um pedido por ID com todos os relacionamentos."""
        pedido = (
            self.db.query(PedidoModel)
            .options(
                joinedload(PedidoModel.itens),
                joinedload(PedidoModel.mesa),
                joinedload(PedidoModel.cliente),
                joinedload(PedidoModel.endereco),
                joinedload(PedidoModel.entregador),
                joinedload(PedidoModel.empresa)
            )
            .filter(PedidoModel.id == pedido_id)
            .first()
        )
        if not pedido:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        return pedido

    def get_by_numero(self, numero_pedido: str, empresa_id: int) -> Optional[PedidoModel]:
        """Busca um pedido pelo número e empresa."""
        return (
            self.db.query(PedidoModel)
            .options(joinedload(PedidoModel.itens))
            .filter(
                PedidoModel.numero_pedido == numero_pedido,
                PedidoModel.empresa_id == empresa_id
            )
            .first()
        )

    def list_by_tipo(
        self,
        tipo_pedido: str,
        *,
        empresa_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[PedidoModel]:
        """Lista pedidos filtrados por tipo."""
        query = (
            self.db.query(PedidoModel)
            .options(joinedload(PedidoModel.itens))
            .filter(PedidoModel.tipo_pedido == tipo_pedido)
        )
        
        if empresa_id is not None:
            query = query.filter(PedidoModel.empresa_id == empresa_id)
        
        if status is not None:
            query = query.filter(PedidoModel.status == status)
        
        return (
            query
            .order_by(PedidoModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_abertos(
        self,
        *,
        empresa_id: Optional[int] = None,
        tipo_pedido: Optional[str] = None
    ) -> List[PedidoModel]:
        """Lista todos os pedidos abertos."""
        query = (
            self.db.query(PedidoModel)
            .options(joinedload(PedidoModel.itens))
            .filter(PedidoModel.status.in_(OPEN_STATUS_PEDIDO))
        )
        
        if empresa_id is not None:
            query = query.filter(PedidoModel.empresa_id == empresa_id)
        
        if tipo_pedido is not None:
            query = query.filter(PedidoModel.tipo_pedido == tipo_pedido)
        
        return query.order_by(PedidoModel.created_at.desc()).all()

    def list_abertos_by_mesa(
        self,
        mesa_id: int,
        *,
        empresa_id: Optional[int] = None
    ) -> List[PedidoModel]:
        """Lista pedidos abertos associados a uma mesa específica."""
        query = (
            self.db.query(PedidoModel)
            .options(joinedload(PedidoModel.itens))
            .filter(
                PedidoModel.mesa_id == mesa_id,
                PedidoModel.status.in_(OPEN_STATUS_PEDIDO)
            )
        )
        
        if empresa_id is not None:
            query = query.filter(PedidoModel.empresa_id == empresa_id)
        
        return query.order_by(PedidoModel.created_at.desc()).all()

    def list_finalizados(
        self,
        data_filtro: date,
        *,
        empresa_id: Optional[int] = None,
        tipo_pedido: Optional[str] = None
    ) -> List[PedidoModel]:
        """Lista pedidos finalizados (ENTREGUE) filtrando por data."""
        data_inicio = datetime.combine(data_filtro, datetime.min.time())
        data_fim = datetime.combine(data_filtro, datetime.max.time())
        
        query = (
            self.db.query(PedidoModel)
            .options(joinedload(PedidoModel.itens))
            .filter(PedidoModel.status == StatusPedido.ENTREGUE.value)
        )
        
        if empresa_id is not None:
            query = query.filter(PedidoModel.empresa_id == empresa_id)
        
        if tipo_pedido is not None:
            query = query.filter(PedidoModel.tipo_pedido == tipo_pedido)
        
        # Busca pedidos criados ou finalizados naquele dia
        query = query.filter(
            or_(
                and_(
                    PedidoModel.created_at >= data_inicio,
                    PedidoModel.created_at <= data_fim
                ),
                and_(
                    PedidoModel.updated_at >= data_inicio,
                    PedidoModel.updated_at <= data_fim
                )
            )
        )
        
        return query.order_by(PedidoModel.created_at.desc()).all()

    def list_by_cliente(
        self,
        cliente_id: int,
        *,
        empresa_id: Optional[int] = None,
        tipo_pedido: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[PedidoModel]:
        """Lista pedidos de um cliente específico."""
        query = (
            self.db.query(PedidoModel)
            .options(
                joinedload(PedidoModel.itens),
                joinedload(PedidoModel.mesa),
                joinedload(PedidoModel.cliente)
            )
            .filter(PedidoModel.cliente_id == cliente_id)
        )
        
        if empresa_id is not None:
            query = query.filter(PedidoModel.empresa_id == empresa_id)
        
        if tipo_pedido is not None:
            query = query.filter(PedidoModel.tipo_pedido == tipo_pedido)
        
        return (
            query
            .order_by(PedidoModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, **data) -> PedidoModel:
        """Cria um novo pedido."""
        tipo_pedido = data.get("tipo_pedido")
        empresa_id = data.get("empresa_id")
        
        if not tipo_pedido or not empresa_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tipo_pedido e empresa_id são obrigatórios"
            )
        
        # Validações específicas por tipo
        if tipo_pedido == TipoPedido.MESA.value:
            if not data.get("mesa_id"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="mesa_id é obrigatório para pedidos de mesa"
                )
            # Valida se a mesa existe
            mesa = self.db.query(MesaModel).filter(MesaModel.id == data["mesa_id"]).first()
            if not mesa:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mesa não encontrada")
            if mesa.empresa_id != empresa_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mesa não pertence à empresa informada"
                )
        
        if tipo_pedido == TipoPedido.DELIVERY.value:
            if not data.get("endereco_id"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="endereco_id é obrigatório para pedidos de delivery"
                )
        
        # Gera número do pedido
        numero_pedido = self._gerar_numero_pedido(tipo_pedido, empresa_id)
        
        # Define status inicial
        if "status" not in data:
            data["status"] = StatusPedido.PENDENTE.value
        
        pedido = PedidoModel(
            numero_pedido=numero_pedido,
            **data
        )
        
        self.db.add(pedido)
        self.db.commit()
        self.db.refresh(pedido)
        
        return pedido

    def update(self, pedido_id: int, **data) -> PedidoModel:
        """Atualiza um pedido existente."""
        pedido = self.get(pedido_id)
        
        for key, value in data.items():
            if hasattr(pedido, key) and value is not None:
                setattr(pedido, key, value)
        
        self.db.commit()
        self.db.refresh(pedido)
        
        # Recalcula totais se necessário
        if any(key in data for key in ["desconto", "taxa_entrega", "taxa_servico"]):
            pedido = self._refresh_totals(pedido)
        
        return pedido

    # ------------ Itens ------------
    def add_item(self, pedido_id: int, **data) -> PedidoModel:
        """Adiciona um item ao pedido."""
        pedido = self.get(pedido_id)
        
        # Valida se o pedido pode ser editado
        if pedido.status in (StatusPedido.CANCELADO.value, StatusPedido.ENTREGUE.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível adicionar itens a um pedido fechado/cancelado"
            )
        
        quantidade = data.get("quantidade", 1)
        preco_unitario = Decimal(str(data.get("preco_unitario", 0)))
        preco_total = preco_unitario * quantidade
        
        # Garante que nome está presente (obrigatório no modelo)
        nome = data.get("nome", "Item")
        
        # Prepara dados do item, excluindo campos já tratados
        item_data = {
            "pedido_id": pedido.id,
            "nome": nome,
            "quantidade": quantidade,
            "preco_unitario": preco_unitario,
            "preco_total": preco_total,
        }
        
        # Adiciona campos opcionais se presentes
        optional_fields = ["produto_cod_barras", "combo_id", "descricao", "observacoes", "adicionais"]
        for field in optional_fields:
            if field in data:
                item_data[field] = data[field]
        
        item = PedidoUnificadoItemModel(**item_data)
        
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        
        return self._refresh_totals(pedido)

    def remove_item(self, pedido_id: int, item_id: int) -> PedidoModel:
        """Remove um item do pedido."""
        pedido = self.get(pedido_id)
        
        # Valida se o pedido pode ser editado
        if pedido.status in (StatusPedido.CANCELADO.value, StatusPedido.ENTREGUE.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível remover itens de um pedido fechado/cancelado"
            )
        
        item = (
            self.db.query(PedidoUnificadoItemModel)
            .filter(
                PedidoUnificadoItemModel.id == item_id,
                PedidoUnificadoItemModel.pedido_id == pedido_id
            )
            .first()
        )
        
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado")
        
        self.db.delete(item)
        self.db.commit()
        
        return self._refresh_totals(pedido)

    # ------------ Fluxo Pedido ------------
    def atualizar_status(self, pedido_id: int, novo_status: str) -> PedidoModel:
        """Atualiza o status do pedido."""
        pedido = self.get(pedido_id)
        
        status_value = enum_value(novo_status)
        pedido.status = status_value
        
        self.db.commit()
        self.db.refresh(pedido)
        
        return pedido

    def cancelar(self, pedido_id: int) -> PedidoModel:
        """Cancela um pedido."""
        return self.atualizar_status(pedido_id, StatusPedido.CANCELADO.value)

    def finalizar(self, pedido_id: int) -> PedidoModel:
        """Finaliza um pedido (marca como entregue)."""
        return self.atualizar_status(pedido_id, StatusPedido.ENTREGUE.value)

    def commit(self):
        """Commite a transação."""
        self.db.commit()

    # ------------ Histórico ------------
    def add_historico(
        self,
        pedido_id: int,
        status_anterior: Optional[str] = None,
        status_novo: Optional[str] = None,
        observacao: Optional[str] = None,
        usuario_id: Optional[int] = None
    ) -> PedidoHistoricoModel:
        """Adiciona um registro ao histórico do pedido."""
        historico = PedidoHistoricoModel(
            pedido_id=pedido_id,
            status_anterior=status_anterior,
            status_novo=status_novo or StatusPedido.PENDENTE.value,
            observacao=observacao,
            usuario_id=usuario_id
        )
        
        self.db.add(historico)
        return historico

    def get_historico(self, pedido_id: int, limit: int = 100) -> List[PedidoHistoricoModel]:
        """Busca histórico de um pedido."""
        return (
            self.db.query(PedidoHistoricoModel)
            .options(joinedload(PedidoHistoricoModel.usuario))
            .filter(PedidoHistoricoModel.pedido_id == pedido_id)
            .order_by(PedidoHistoricoModel.created_at.desc())
            .limit(limit)
            .all()
        )

