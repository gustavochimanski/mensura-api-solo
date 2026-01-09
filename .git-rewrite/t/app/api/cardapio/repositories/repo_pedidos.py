from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from starlette import status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.cardapio.models.model_pedido_dv import PedidoDeliveryModel
from app.api.cardapio.models.model_pedido_item_dv import PedidoItemModel
from app.api.cardapio.models.model_pedido_status_historico_dv import PedidoStatusHistoricoModel
from app.api.cadastros.models.model_cupom import CupomDescontoModel
from app.api.cadastros.models.model_endereco_dv import EnderecoModel
from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.api.cardapio.models.model_transacao_pagamento_dv import TransacaoPagamentoModel


class PedidoRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------- Validations / Queries -------------
    def get_cliente(self, telefone: str) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter_by(telefone=telefone).first()

    def get_cliente_by_id(self, id: int) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter(ClienteModel.id == id).first()

    def get_endereco(self, endereco_id: int) -> Optional[EnderecoModel]:
        return self.db.get(EnderecoModel, endereco_id)

    def get_produto_emp(self, empresa_id: int, cod_barras: str) -> Optional[ProdutoEmpModel]:
        return (
            self.db.query(ProdutoEmpModel)
            .options(joinedload(ProdutoEmpModel.produto))
            .filter(
                ProdutoEmpModel.empresa_id == empresa_id,
                ProdutoEmpModel.cod_barras == cod_barras,
            )
            .first()
        )

    def get_cupom(self, cupom_id: int) -> Optional[CupomDescontoModel]:
        return self.db.get(CupomDescontoModel, cupom_id)

    def get_pedido(self, pedido_id: int) -> Optional[PedidoDeliveryModel]:
        return (
            self.db.query(PedidoDeliveryModel)
            .options(
                joinedload(PedidoDeliveryModel.itens),
                joinedload(PedidoDeliveryModel.cliente).joinedload(ClienteModel.enderecos),
                joinedload(PedidoDeliveryModel.endereco),
                joinedload(PedidoDeliveryModel.meio_pagamento),
                joinedload(PedidoDeliveryModel.transacao).joinedload(TransacaoPagamentoModel.meio_pagamento),
                joinedload(PedidoDeliveryModel.transacoes).joinedload(TransacaoPagamentoModel.meio_pagamento),
            )
            .filter(PedidoDeliveryModel.id == pedido_id)
            .first()
        )

    def get_by_cliente_id(self, cliente_id: int) -> list[PedidoDeliveryModel]:
        """Busca todos os pedidos de um cliente específico"""
        return (
            self.db.query(PedidoDeliveryModel)
            .filter(PedidoDeliveryModel.cliente_id == cliente_id)
            .all()
        )

    def list_all_kanban(self, date_filter: date, empresa_id: int = 1, limit: int = 500):
        from app.api.cadastros.schemas.schema_shared_enums import PedidoStatusEnum
        from sqlalchemy import or_, and_
        
        # date_filter é sempre obrigatório
        start_dt = datetime.combine(date_filter, datetime.min.time())
        end_dt = start_dt + timedelta(days=1)
        
        query = self.db.query(PedidoDeliveryModel).filter(PedidoDeliveryModel.empresa_id == empresa_id)
        
        # Busca pedidos criados naquele dia (qualquer status) OU pedidos com status E atualizados naquele dia
        # (mesmo que tenham sido criados em outro dia)
        query = query.filter(
            or_(
                # Pedidos criados naquele dia (qualquer status, incluindo E)
                and_(
                    PedidoDeliveryModel.data_criacao >= start_dt,
                    PedidoDeliveryModel.data_criacao < end_dt
                ),
                # Pedidos com status E atualizados naquele dia (mesmo que criados em outro dia)
                and_(
                    PedidoDeliveryModel.status == PedidoStatusEnum.E.value,
                    PedidoDeliveryModel.data_atualizacao >= start_dt,
                    PedidoDeliveryModel.data_atualizacao < end_dt
                )
            )
        )

        query = query.options(
            joinedload(PedidoDeliveryModel.cliente).joinedload(ClienteModel.enderecos),
            joinedload(PedidoDeliveryModel.endereco),
            joinedload(PedidoDeliveryModel.entregador),
            joinedload(PedidoDeliveryModel.meio_pagamento),
            joinedload(PedidoDeliveryModel.transacao).joinedload(TransacaoPagamentoModel.meio_pagamento),
            joinedload(PedidoDeliveryModel.transacoes).joinedload(TransacaoPagamentoModel.meio_pagamento),
            joinedload(PedidoDeliveryModel.historicos),
        )

        query = query.order_by(PedidoDeliveryModel.data_criacao.desc())

        return query.limit(limit).all()

    # -------------------- Mutations -------------------
    def criar_pedido(
        self,
        *,
        cliente_id: int | None,
        empresa_id: int,
        endereco_id: int | None,
        meio_pagamento_id: int,
        status: str = "I",
        tipo_entrega: str,
        origem: str,
        endereco_snapshot: dict | None = None,
        endereco_geo = None,
    ) -> PedidoDeliveryModel:
        # ⚠️ Setar SOMENTE os campos escalares/FKs aqui; nada de refresh agora
        pedido = PedidoDeliveryModel(
            cliente_id=int(cliente_id) if cliente_id is not None else None,
            empresa_id=empresa_id,
            endereco_id=endereco_id,
            meio_pagamento_id=meio_pagamento_id,
            status=status,
            tipo_entrega=tipo_entrega,
            origem=origem,
            endereco_snapshot=endereco_snapshot,
            endereco_geo=endereco_geo,
            subtotal=Decimal("0"),
            desconto=Decimal("0"),
            taxa_entrega=Decimal("0"),
            taxa_servico=Decimal("0"),
            valor_total=Decimal("0"),
        )
        self.db.add(pedido)
        self.db.flush()  # garante ID do pedido

        # Para criação, não há status anterior, então usa motivo simples
        self.add_status_historico(pedido.id, status, motivo="Pedido criado")
        # ❌ NÃO fazer refresh aqui; evita rehidratar com potencial NULL de triggers/DFs
        return pedido

    def atualizar_totais(
        self,
        pedido: PedidoDeliveryModel,
        *,
        subtotal: Decimal,
        desconto: Decimal,
        taxa_entrega: Decimal,
        taxa_servico: Decimal,
        distancia_km: Optional[Decimal] = None,
    ) -> None:
        pedido.subtotal = subtotal
        pedido.desconto = desconto
        pedido.taxa_entrega = taxa_entrega
        pedido.taxa_servico = taxa_servico
        pedido.valor_total = subtotal - desconto + taxa_entrega + taxa_servico
        if pedido.valor_total < 0:
            pedido.valor_total = Decimal("0")
        pedido.distancia_km = distancia_km
        # Apenas flush — não precisa de refresh
        self.db.flush()

    def add_status_historico(
        self, 
        pedido_id: int, 
        status: str, 
        motivo: str | None = None, 
        observacoes: str | None = None,
        criado_por_id: int | None = None,
        ip_origem: str | None = None,
        user_agent: str | None = None
    ):
        hist = PedidoStatusHistoricoModel(
            pedido_id=pedido_id,
            status=status,
            motivo=motivo,
            observacoes=observacoes,
            criado_por_id=criado_por_id,
            ip_origem=ip_origem,
            user_agent=user_agent,
        )
        self.db.add(hist)

    def _status_para_nome(self, status: str) -> str:
        """Converte código de status para nome simples."""
        mapa = {
            "P": "Pendente",
            "I": "Impressão",
            "R": "Em preparo",
            "S": "Saiu",
            "E": "Entregue",
            "C": "Cancelado",
            "D": "Editado",
            "X": "Editando",
            "A": "Aguardando pagamento",
        }
        return mapa.get(status, status)
    
    def atualizar_status_pedido(self, pedido: PedidoDeliveryModel, novo_status: str, motivo: str | None = None, observacoes: str | None = None, criado_por_id: int | None = None):
        status_anterior = pedido.status
        pedido.status = novo_status
        
        # Formata motivo como transição de status se não fornecido
        if motivo is None:
            status_ant_nome = self._status_para_nome(status_anterior)
            status_novo_nome = self._status_para_nome(novo_status)
            motivo = f"{status_ant_nome} → {status_novo_nome}"
        
        self.add_status_historico(
            pedido.id, 
            novo_status, 
            motivo=motivo,
            observacoes=observacoes,
            criado_por_id=criado_por_id
        )

    def atualizar_status_pedido_com_historico_detalhado(
        self, 
        pedido: PedidoDeliveryModel, 
        novo_status: str, 
        motivo: str | None = None,
        observacoes: str | None = None,
        criado_por_id: int | None = None,
        ip_origem: str | None = None,
        user_agent: str | None = None
    ):
        """Atualiza status do pedido com histórico detalhado em uma única operação"""
        status_anterior = pedido.status
        pedido.status = novo_status
        
        # Formata motivo como transição de status se não fornecido
        if motivo is None:
            status_ant_nome = self._status_para_nome(status_anterior)
            status_novo_nome = self._status_para_nome(novo_status)
            motivo = f"{status_ant_nome} → {status_novo_nome}"
        
        self.add_status_historico(
            pedido_id=pedido.id,
            status=novo_status,
            motivo=motivo,
            observacoes=observacoes,
            criado_por_id=criado_por_id,
            ip_origem=ip_origem,
            user_agent=user_agent
        )

    # ----------------- Transação pagamento -------------
    def criar_transacao_pagamento(
        self,
        *,
        pedido_id: int,
        meio_pagamento_id: int,
        gateway: str,
        metodo: str,
        valor: Decimal,
        moeda: str = "BRL",
        payload_solicitacao: dict | None = None,
        provider_transaction_id: str | None = None,
        qr_code: str | None = None,
        qr_code_base64: str | None = None,
    ) -> TransacaoPagamentoModel:
        tx = TransacaoPagamentoModel(
            pedido_id=pedido_id,
            meio_pagamento_id=meio_pagamento_id,
            gateway=gateway,
            metodo=metodo,
            valor=valor,
            moeda=moeda,
            status="PENDENTE",
            payload_solicitacao=payload_solicitacao,
            provider_transaction_id=provider_transaction_id,
            qr_code=qr_code,
            qr_code_base64=qr_code_base64,
        )
        self.db.add(tx)
        self.db.flush()
        return tx

    def atualizar_transacao_status(
        self,
        tx: TransacaoPagamentoModel,
        *,
        status: str,
        provider_transaction_id: str | None = None,
        payload_retorno: dict | None = None,
        qr_code: str | None = None,
        qr_code_base64: str | None = None,
        timestamp_field: str | None = None,
        payload_solicitacao: dict | None = None,
    ):
        tx.status = status
        if provider_transaction_id is not None:
            tx.provider_transaction_id = provider_transaction_id
        if payload_retorno is not None:
            tx.payload_retorno = payload_retorno
        if qr_code is not None:
            tx.qr_code = qr_code
        if qr_code_base64 is not None:
            tx.qr_code_base64 = qr_code_base64
        if payload_solicitacao is not None:
            tx.payload_solicitacao = payload_solicitacao
        if timestamp_field:
            setattr(tx, timestamp_field, func.now())

    # ---------------- Unit of Work ---------------------
    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    # --------------- ITENS PEDIDO ----------------------
    def get_item_by_id(self, item_id: int) -> Optional[PedidoItemModel]:
        return self.db.get(PedidoItemModel, item_id)

    def adicionar_item(
        self,
        *,
        pedido_id: int,
        cod_barras: str,
        quantidade: int,
        preco_unitario: Decimal,
        observacao: str | None,
        produto_descricao_snapshot: str | None,
        produto_imagem_snapshot: str | None,
        adicionais_snapshot: list | None = None,
    ) -> PedidoItemModel:
        # ⚠️ Evitar passar o objeto pedido E o pedido_id juntos.
        item = PedidoItemModel(
            pedido_id=pedido_id,
            produto_cod_barras=cod_barras,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            observacao=observacao,
            produto_descricao_snapshot=produto_descricao_snapshot,
            produto_imagem_snapshot=produto_imagem_snapshot,
        )
        if adicionais_snapshot:
            item.adicionais_snapshot = adicionais_snapshot
        self.db.add(item)
        self.db.flush()
        return item

    def atualizar_item(
        self,
        item_id: int,
        quantidade: int | None = None,
        observacao: str | None = None
    ) -> PedidoItemModel:
        item = self.get_item_by_id(item_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Item {item_id} não encontrado")
        if quantidade is not None:
            item.quantidade = quantidade
        if observacao is not None:
            item.observacao = observacao
        self.db.flush()
        return item
