from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from starlette import status
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session, joinedload, defer, selectinload

from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.pedidos.models.model_pedido_unificado import (
    PedidoUnificadoModel,
    TipoPedido,
    StatusPedido,
)
from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
from app.api.pedidos.models.model_pedido_historico_unificado import (
    PedidoHistoricoUnificadoModel,
    TipoOperacaoPedido,
)
from app.api.cadastros.models.model_cupom import CupomDescontoModel
from app.api.cadastros.models.model_endereco_dv import EnderecoModel
from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.api.cardapio.models.model_transacao_pagamento_dv import TransacaoPagamentoModel
from app.api.catalogo.contracts.produto_contract import IProdutoContract, ProdutoEmpDTO


# Status abertos para balcão e mesa (mesmos valores)
OPEN_STATUS_PEDIDO_BALCAO_MESA = [
    StatusPedido.PENDENTE.value,
    StatusPedido.IMPRESSAO.value,
    StatusPedido.PREPARANDO.value,
    StatusPedido.EDITADO.value,
    StatusPedido.EM_EDICAO.value,
    StatusPedido.AGUARDANDO_PAGAMENTO.value,
]


class PedidoRepository:
    def __init__(self, db: Session, produto_contract: IProdutoContract | None = None):
        self.db = db
        self.produto_contract = produto_contract

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

    def get_pedido(self, pedido_id: int, tipo_pedido: TipoPedido | None = None) -> Optional[PedidoUnificadoModel]:
        """Busca um pedido por ID. Se tipo_pedido for fornecido, filtra por tipo."""
        query = (
            self.db.query(PedidoUnificadoModel)
            .options(
                joinedload(PedidoUnificadoModel.itens),
                joinedload(PedidoUnificadoModel.cliente).joinedload(ClienteModel.enderecos),
                joinedload(PedidoUnificadoModel.endereco),
                joinedload(PedidoUnificadoModel.meio_pagamento),
                joinedload(PedidoUnificadoModel.transacao).joinedload(TransacaoPagamentoModel.meio_pagamento),
                joinedload(PedidoUnificadoModel.transacoes).joinedload(TransacaoPagamentoModel.meio_pagamento),
            )
            .filter(PedidoUnificadoModel.id == pedido_id)
        )
        if tipo_pedido:
            query = query.filter(PedidoUnificadoModel.tipo_pedido == tipo_pedido.value)
        return query.first()
    
    def get(self, pedido_id: int, tipo_pedido: TipoPedido) -> PedidoUnificadoModel:
        """Busca um pedido por ID e tipo, lança exceção se não encontrar."""
        pedido = self.get_pedido(pedido_id, tipo_pedido)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        return pedido

    def get_by_cliente_id(self, cliente_id: int) -> list[PedidoUnificadoModel]:
        """Busca todos os pedidos de um cliente específico"""
        return (
            self.db.query(PedidoUnificadoModel)
            .filter(
                PedidoUnificadoModel.tipo_pedido == TipoPedido.DELIVERY.value,
                PedidoUnificadoModel.cliente_id == cliente_id
            )
            .all()
        )

    def list_all_kanban(self, date_filter: date, empresa_id: int = 1, limit: int = 500):
        from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum
        from sqlalchemy import or_, and_
        
        # date_filter é sempre obrigatório
        start_dt = datetime.combine(date_filter, datetime.min.time())
        end_dt = start_dt + timedelta(days=1)
        
        query = self.db.query(PedidoUnificadoModel).filter(
            PedidoUnificadoModel.empresa_id == empresa_id,
            PedidoUnificadoModel.tipo_pedido == TipoPedido.DELIVERY.value
        )
        
        # Busca pedidos criados naquele dia (qualquer status) OU pedidos com status E atualizados naquele dia
        # (mesmo que tenham sido criados em outro dia)
        query = query.filter(
            or_(
                # Pedidos criados naquele dia (qualquer status, incluindo E)
                and_(
                    PedidoUnificadoModel.created_at >= start_dt,
                    PedidoUnificadoModel.created_at < end_dt
                ),
                # Pedidos com status E atualizados naquele dia (mesmo que criados em outro dia)
                and_(
                    PedidoUnificadoModel.status == PedidoStatusEnum.E.value,
                    PedidoUnificadoModel.updated_at >= start_dt,
                    PedidoUnificadoModel.updated_at < end_dt
                )
            )
        )

        query = query.options(
            joinedload(PedidoUnificadoModel.cliente).joinedload(ClienteModel.enderecos),
            joinedload(PedidoUnificadoModel.endereco),
            joinedload(PedidoUnificadoModel.entregador),
            joinedload(PedidoUnificadoModel.meio_pagamento),
            joinedload(PedidoUnificadoModel.transacao).joinedload(TransacaoPagamentoModel.meio_pagamento),
            joinedload(PedidoUnificadoModel.transacoes).joinedload(TransacaoPagamentoModel.meio_pagamento),
            selectinload(PedidoUnificadoModel.historico).defer(PedidoHistoricoUnificadoModel.tipo_operacao),
        )

        query = query.order_by(PedidoUnificadoModel.created_at.desc())

        return query.limit(limit).all()

    # -------------------- Mutations -------------------
    # -------------------- Helpers para cálculos -------------------
    def _calc_item_total(self, item: PedidoItemUnificadoModel) -> Decimal:
        """Calcula o total de um item incluindo adicionais."""
        total = (item.preco_unitario or Decimal("0")) * (item.quantidade or 0)
        adicionais_snapshot = getattr(item, "adicionais_snapshot", None) or []
        for adicional in adicionais_snapshot:
            try:
                adicional_total = (
                    adicional.get("total")
                    if isinstance(adicional, dict)
                    else getattr(adicional, "total", 0)
                )
            except AttributeError:
                adicional_total = 0
            total += Decimal(str(adicional_total or 0))
        return total

    def _calc_total(self, pedido: PedidoUnificadoModel) -> Decimal:
        """Calcula o total do pedido somando todos os itens e seus adicionais."""
        total = Decimal("0")
        for item in pedido.itens:
            item_total = self._calc_item_total(item)
            total += item_total
        return total

    def _refresh_total(self, pedido: PedidoUnificadoModel) -> PedidoUnificadoModel:
        """Recalcula e atualiza o valor_total do pedido."""
        pedido.valor_total = self._calc_total(pedido)
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

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
    ) -> PedidoUnificadoModel:
        """Cria um pedido de delivery (mantido para compatibilidade)."""
        return self.criar_pedido_delivery(
            cliente_id=cliente_id,
            empresa_id=empresa_id,
            endereco_id=endereco_id,
            meio_pagamento_id=meio_pagamento_id,
            status=status,
            tipo_entrega=tipo_entrega,
            origem=origem,
            endereco_snapshot=endereco_snapshot,
            endereco_geo=endereco_geo,
        )

    def criar_pedido_delivery(
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
    ) -> PedidoUnificadoModel:
        """Cria um pedido de delivery."""
        # Gera número único de pedido: DV-{sequencial} por empresa
        seq = (
            self.db.query(PedidoUnificadoModel)
            .filter(
                PedidoUnificadoModel.empresa_id == empresa_id,
                PedidoUnificadoModel.tipo_pedido == TipoPedido.DELIVERY.value
            )
            .count()
            + 1
        )
        numero = f"DV-{seq:06d}"
        
        pedido = PedidoUnificadoModel(
            tipo_pedido=TipoPedido.DELIVERY.value,
            empresa_id=empresa_id,
            cliente_id=int(cliente_id) if cliente_id is not None else None,
            endereco_id=endereco_id,
            meio_pagamento_id=meio_pagamento_id,
            numero_pedido=numero,
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
        self.db.flush()
        self.add_status_historico(pedido.id, status, motivo="Pedido criado")
        return pedido

    def criar_pedido_balcao(
        self,
        *,
        empresa_id: int,
        mesa_id: Optional[int],
        cliente_id: int,
        observacoes: Optional[str],
    ) -> PedidoUnificadoModel:
        """Cria um pedido de balcão."""
        # Valida mesa se informada
        if mesa_id is not None:
            mesa = self.db.query(MesaModel).filter(MesaModel.id == mesa_id).first()
            if not mesa:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa não encontrada")
            if mesa.empresa_id != empresa_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mesa não pertence à empresa informada")

        # Gera número único de pedido: BAL-{sequencial} por empresa
        seq = (
            self.db.query(PedidoUnificadoModel)
            .filter(
                PedidoUnificadoModel.empresa_id == empresa_id,
                PedidoUnificadoModel.tipo_pedido == TipoPedido.BALCAO.value
            )
            .count()
            + 1
        )
        numero = f"BAL-{seq:06d}"

        pedido = PedidoUnificadoModel(
            tipo_pedido=TipoPedido.BALCAO.value,
            empresa_id=empresa_id,
            mesa_id=mesa_id,
            cliente_id=cliente_id,
            numero_pedido=numero,
            observacoes=observacoes,
            status=StatusPedido.IMPRESSAO.value,
            subtotal=Decimal("0"),
            desconto=Decimal("0"),
            taxa_entrega=Decimal("0"),
            taxa_servico=Decimal("0"),
            valor_total=Decimal("0"),
        )
        self.db.add(pedido)
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def criar_pedido_mesa(
        self,
        *,
        mesa_id: int,
        empresa_id: int,
        cliente_id: Optional[int],
        observacoes: Optional[str],
        num_pessoas: Optional[int],
    ) -> PedidoUnificadoModel:
        """Cria um pedido de mesa."""
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

        # número simples: {mesa.numero}-{sequencial curto}
        seq = (
            self.db.query(PedidoUnificadoModel)
            .filter(
                PedidoUnificadoModel.tipo_pedido == TipoPedido.MESA.value,
                PedidoUnificadoModel.mesa_id == mesa_id,
                PedidoUnificadoModel.empresa_id == empresa_id,
            )
            .count()
            or 0
        ) + 1
        numero = f"{mesa.numero}-{seq:03d}"

        pedido = PedidoUnificadoModel(
            tipo_pedido=TipoPedido.MESA.value,
            empresa_id=empresa_id,
            mesa_id=mesa_id,
            cliente_id=cliente_id,
            numero_pedido=numero,
            observacoes=observacoes,
            num_pessoas=num_pessoas,
            status=StatusPedido.IMPRESSAO.value,
            subtotal=Decimal("0"),
            desconto=Decimal("0"),
            taxa_entrega=Decimal("0"),
            taxa_servico=Decimal("0"),
            valor_total=Decimal("0"),
        )
        self.db.add(pedido)
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def atualizar_totais(
        self,
        pedido: PedidoUnificadoModel,
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
        hist = PedidoHistoricoUnificadoModel(
            pedido_id=pedido_id,
            status_novo=status,
            motivo=motivo,
            observacoes=observacoes,
            usuario_id=criado_por_id,
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
    
    def atualizar_status_pedido(self, pedido: PedidoUnificadoModel, novo_status: str, motivo: str | None = None, observacoes: str | None = None, criado_por_id: int | None = None):
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
        pedido: PedidoUnificadoModel, 
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
    def get_item_by_id(self, item_id: int) -> Optional[PedidoItemUnificadoModel]:
        return self.db.get(PedidoItemUnificadoModel, item_id)

    def adicionar_item(
        self,
        *,
        pedido_id: int,
        cod_barras: str | None = None,
        receita_id: int | None = None,
        combo_id: int | None = None,
        quantidade: int,
        preco_unitario: Decimal,
        observacao: str | None,
        produto_descricao_snapshot: str | None = None,
        produto_imagem_snapshot: str | None = None,
        adicionais_snapshot: list | None = None,
    ) -> PedidoItemUnificadoModel:
        """
        Adiciona um item ao pedido. Suporta produto (cod_barras), receita (receita_id) ou combo (combo_id).
        Apenas um dos três campos deve ser preenchido.
        """
        # Valida que apenas um tipo está preenchido
        tipos_preenchidos = sum([
            cod_barras is not None,
            receita_id is not None,
            combo_id is not None
        ])
        if tipos_preenchidos != 1:
            raise ValueError("Exatamente um dos campos (cod_barras, receita_id, combo_id) deve ser preenchido")
        
        # Calcula preco_total
        preco_total = preco_unitario * Decimal(str(quantidade))
        
        # ⚠️ Evitar passar o objeto pedido E o pedido_id juntos.
        item = PedidoItemUnificadoModel(
            pedido_id=pedido_id,
            produto_cod_barras=cod_barras,
            receita_id=receita_id,
            combo_id=combo_id,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            preco_total=preco_total,
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
    ) -> PedidoItemUnificadoModel:
        item = self.get_item_by_id(item_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Item {item_id} não encontrado")
        if quantidade is not None:
            item.quantidade = quantidade
            # Recalcula preco_total se quantidade mudou
            item.preco_total = item.preco_unitario * Decimal(str(quantidade))
        if observacao is not None:
            item.observacao = observacao
        self.db.flush()
        return item

    # -------------------- Métodos específicos para produtos, receitas e combos -------------------
    def adicionar_item_produto(
        self,
        *,
        pedido_id: int,
        cod_barras: str,
        quantidade: int,
        preco_unitario: Decimal,
        observacao: str | None,
        produto_descricao_snapshot: str | None = None,
        produto_imagem_snapshot: str | None = None,
        adicionais_snapshot: list | None = None,
    ) -> PedidoItemUnificadoModel:
        """Adiciona um item de produto ao pedido."""
        return self.adicionar_item(
            pedido_id=pedido_id,
            cod_barras=cod_barras,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            observacao=observacao,
            produto_descricao_snapshot=produto_descricao_snapshot,
            produto_imagem_snapshot=produto_imagem_snapshot,
            adicionais_snapshot=adicionais_snapshot,
        )

    def adicionar_item_receita(
        self,
        *,
        pedido_id: int,
        receita_id: int,
        quantidade: int,
        preco_unitario: Decimal,
        observacao: str | None,
        adicionais_snapshot: list | None = None,
    ) -> PedidoItemUnificadoModel:
        """Adiciona um item de receita ao pedido."""
        return self.adicionar_item(
            pedido_id=pedido_id,
            receita_id=receita_id,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            observacao=observacao,
            adicionais_snapshot=adicionais_snapshot,
        )

    def adicionar_item_combo(
        self,
        *,
        pedido_id: int,
        combo_id: int,
        quantidade: int,
        preco_unitario: Decimal,
        observacao: str | None,
        adicionais_snapshot: list | None = None,
    ) -> PedidoItemUnificadoModel:
        """Adiciona um item de combo ao pedido."""
        return self.adicionar_item(
            pedido_id=pedido_id,
            combo_id=combo_id,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            observacao=observacao,
            adicionais_snapshot=adicionais_snapshot,
        )

    # -------------------- Métodos unificados para balcão e mesa -------------------
    def add_item(
        self,
        pedido_id: int,
        *,
        produto_cod_barras: str | None = None,
        receita_id: int | None = None,
        combo_id: int | None = None,
        quantidade: int,
        observacao: Optional[str],
        preco_unitario: Optional[Decimal] = None,
        produto_descricao_snapshot: Optional[str] = None,
        produto_imagem_snapshot: Optional[str] = None,
        adicionais_snapshot: list | None = None,
    ) -> PedidoUnificadoModel:
        """Adiciona um item ao pedido (balcão ou mesa). Busca preço automaticamente se for produto."""
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

        # Valida que apenas um tipo está preenchido
        tipos_preenchidos = sum([
            produto_cod_barras is not None,
            receita_id is not None,
            combo_id is not None
        ])
        if tipos_preenchidos != 1:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Exatamente um dos campos (produto_cod_barras, receita_id, combo_id) deve ser preenchido"
            )

        descricao_snapshot = produto_descricao_snapshot
        imagem_snapshot = produto_imagem_snapshot
        
        # Se não foi fornecido preço unitário, busca do produto
        if preco_unitario is None:
            if produto_cod_barras:
                if self.produto_contract is not None:
                    pe_dto = self.produto_contract.obter_produto_emp_por_cod(pedido.empresa_id, produto_cod_barras)
                    if not pe_dto:
                        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")
                    if not pe_dto.disponivel or not (pe_dto.produto and bool(pe_dto.produto.ativo)):
                        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Produto indisponível")
                    preco_unitario = Decimal(str(pe_dto.preco_venda or 0))
                    if pe_dto.produto:
                        descricao_snapshot = descricao_snapshot or pe_dto.produto.descricao
                        imagem_snapshot = imagem_snapshot or pe_dto.produto.imagem
                else:
                    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Contrato de produto não configurado")
            else:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "preco_unitario é obrigatório para receitas e combos"
                )

        # Usa o método adicionar_item unificado
        self.adicionar_item(
            pedido_id=pedido_id,
            cod_barras=produto_cod_barras,
            receita_id=receita_id,
            combo_id=combo_id,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            observacao=observacao,
            produto_descricao_snapshot=descricao_snapshot,
            produto_imagem_snapshot=imagem_snapshot,
            adicionais_snapshot=adicionais_snapshot,
        )
        self.db.commit()
        return self._refresh_total(pedido)

    def remove_item(self, pedido_id: int, item_id: int) -> PedidoUnificadoModel:
        """Remove um item do pedido e recalcula o total."""
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        item = (
            self.db.query(PedidoItemUnificadoModel)
            .filter(PedidoItemUnificadoModel.id == item_id, PedidoItemUnificadoModel.pedido_id == pedido_id)
            .first()
        )
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Item não encontrado")
        self.db.delete(item)
        self.db.commit()
        return self._refresh_total(pedido)

    # -------------------- Métodos de status para balcão e mesa -------------------
    def cancelar(self, pedido_id: int) -> PedidoUnificadoModel:
        """Cancela um pedido (balcão ou mesa)."""
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        pedido.status = StatusPedido.CANCELADO.value
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def confirmar(self, pedido_id: int) -> PedidoUnificadoModel:
        """Confirma um pedido (balcão ou mesa) mudando status para IMPRESSAO."""
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        pedido.status = StatusPedido.IMPRESSAO.value
        self.db.commit()
        self.db.refresh(pedido)
        return self._refresh_total(pedido)

    def fechar_conta(self, pedido_id: int) -> PedidoUnificadoModel:
        """Fecha a conta de um pedido (balcão ou mesa) mudando status para ENTREGUE."""
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        pedido.status = StatusPedido.ENTREGUE.value
        self.db.commit()
        self.db.refresh(pedido)
        return self._refresh_total(pedido)

    def reabrir(self, pedido_id: int, novo_status: str = StatusPedido.PENDENTE.value) -> PedidoUnificadoModel:
        """Reabre um pedido cancelado ou entregue."""
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        status_atual = (
            pedido.status
            if isinstance(pedido.status, str)
            else pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)
        )
        if status_atual != StatusPedido.CANCELADO.value and status_atual != StatusPedido.ENTREGUE.value:
            return pedido
        pedido.status = novo_status
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def atualizar_status(self, pedido_id: int, novo_status) -> PedidoUnificadoModel:
        """Atualiza o status do pedido (aceita enum ou string)."""
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        if hasattr(novo_status, "value"):
            status_value = novo_status.value
        else:
            status_value = str(novo_status)
        pedido.status = status_value
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    # -------------------- Métodos de listagem para balcão e mesa -------------------
    def list_abertos_by_mesa(self, mesa_id: int, tipo_pedido: TipoPedido, *, empresa_id: Optional[int] = None) -> list[PedidoUnificadoModel]:
        """Lista pedidos abertos de balcão ou mesa associados a uma mesa específica"""
        query = (
            self.db.query(PedidoUnificadoModel)
            .options(joinedload(PedidoUnificadoModel.itens))
            .filter(
                PedidoUnificadoModel.tipo_pedido == tipo_pedido.value,
                PedidoUnificadoModel.mesa_id == mesa_id,
                PedidoUnificadoModel.status.in_(OPEN_STATUS_PEDIDO_BALCAO_MESA)
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoUnificadoModel.empresa_id == empresa_id)
        return query.order_by(PedidoUnificadoModel.created_at.desc()).all()

    def list_abertos_all(self, tipo_pedido: TipoPedido, *, empresa_id: Optional[int] = None) -> list[PedidoUnificadoModel]:
        """Lista todos os pedidos abertos de balcão ou mesa"""
        query = (
            self.db.query(PedidoUnificadoModel)
            .options(joinedload(PedidoUnificadoModel.itens))
            .filter(
                PedidoUnificadoModel.tipo_pedido == tipo_pedido.value,
                PedidoUnificadoModel.status.in_(OPEN_STATUS_PEDIDO_BALCAO_MESA)
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoUnificadoModel.empresa_id == empresa_id)
        return query.order_by(PedidoUnificadoModel.created_at.desc()).all()

    def get_aberto_mais_recente(self, mesa_id: int, tipo_pedido: TipoPedido, *, empresa_id: int | None = None) -> Optional[PedidoUnificadoModel]:
        """Busca o pedido aberto mais recente de uma mesa (apenas para tipo MESA)"""
        query = (
            self.db.query(PedidoUnificadoModel)
            .filter(
                PedidoUnificadoModel.tipo_pedido == tipo_pedido.value,
                PedidoUnificadoModel.mesa_id == mesa_id,
                PedidoUnificadoModel.status.in_(OPEN_STATUS_PEDIDO_BALCAO_MESA)
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoUnificadoModel.empresa_id == empresa_id)
        return query.order_by(PedidoUnificadoModel.created_at.desc()).first()

    def list_finalizados(self, tipo_pedido: TipoPedido, data_filtro: Optional[date] = None, *, empresa_id: Optional[int] = None, mesa_id: Optional[int] = None) -> list[PedidoUnificadoModel]:
        """Lista pedidos finalizados (ENTREGUE) de balcão ou mesa"""
        query = (
            self.db.query(PedidoUnificadoModel)
            .options(joinedload(PedidoUnificadoModel.itens))
            .filter(
                PedidoUnificadoModel.tipo_pedido == tipo_pedido.value,
                PedidoUnificadoModel.status == StatusPedido.ENTREGUE.value
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoUnificadoModel.empresa_id == empresa_id)
        if mesa_id is not None:
            query = query.filter(PedidoUnificadoModel.mesa_id == mesa_id)
        
        # Filtro por data se fornecido
        if data_filtro is not None:
            data_inicio = datetime.combine(data_filtro, datetime.min.time())
            data_fim = datetime.combine(data_filtro, datetime.max.time())
            query = query.filter(
                or_(
                    and_(
                        PedidoUnificadoModel.created_at >= data_inicio,
                        PedidoUnificadoModel.created_at <= data_fim
                    ),
                    and_(
                        PedidoUnificadoModel.updated_at >= data_inicio,
                        PedidoUnificadoModel.updated_at <= data_fim
                    )
                )
            )
        
        return query.order_by(PedidoUnificadoModel.created_at.desc()).all()

    def list_by_cliente_id(self, cliente_id: int, tipo_pedido: TipoPedido, *, empresa_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> list[PedidoUnificadoModel]:
        """Lista pedidos de um cliente específico por tipo"""
        query = (
            self.db.query(PedidoUnificadoModel)
            .options(
                joinedload(PedidoUnificadoModel.itens),
                joinedload(PedidoUnificadoModel.mesa),
                joinedload(PedidoUnificadoModel.cliente)
            )
            .filter(
                PedidoUnificadoModel.tipo_pedido == tipo_pedido.value,
                PedidoUnificadoModel.cliente_id == cliente_id
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoUnificadoModel.empresa_id == empresa_id)
        return (
            query
            .order_by(PedidoUnificadoModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    # -------------------- Histórico unificado -------------------
    def add_historico(
        self,
        pedido_id: int,
        tipo_operacao: TipoOperacaoPedido,
        status_anterior: str | None = None,
        status_novo: str | None = None,
        descricao: str | None = None,
        observacoes: str | None = None,
        cliente_id: int | None = None,
        usuario_id: int | None = None,
        ip_origem: str | None = None,
        user_agent: str | None = None
    ):
        """Adiciona um registro ao histórico do pedido"""
        # Busca o pedido para obter o tipo_pedido (DELIVERY, MESA, BALCAO)
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise ValueError(f"Pedido {pedido_id} não encontrado")
        
        tipo_pedido_value = pedido.tipo_pedido.value if hasattr(pedido.tipo_pedido, "value") else pedido.tipo_pedido
        
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

        historico = PedidoHistoricoUnificadoModel(
            pedido_id=pedido_id,
            cliente_id=cliente_id,
            usuario_id=usuario_id,
            tipo_pedido=tipo_pedido_value,  # DELIVERY, MESA ou BALCAO
            tipo_operacao=tipo_operacao.value if hasattr(tipo_operacao, "value") else tipo_operacao,  # PEDIDO_CRIADO, STATUS_ALTERADO, etc
            status_anterior=status_anterior_value,
            status_novo=status_novo_value,
            descricao=descricao,
            observacoes=observacoes,
            ip_origem=ip_origem,
            user_agent=user_agent
        )
        self.db.add(historico)

    def get_historico(self, pedido_id: int, limit: int = 100) -> list[PedidoHistoricoUnificadoModel]:
        """Busca histórico de um pedido"""
        return (
            self.db.query(PedidoHistoricoUnificadoModel)
            .options(joinedload(PedidoHistoricoUnificadoModel.usuario))
            .filter(PedidoHistoricoUnificadoModel.pedido_id == pedido_id)
            .order_by(PedidoHistoricoUnificadoModel.created_at.desc())
            .limit(limit)
            .all()
        )
