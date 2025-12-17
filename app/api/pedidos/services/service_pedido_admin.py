from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.pedidos.models.model_pedido_unificado import (
    PedidoUnificadoModel,
    TipoEntrega,
)
from app.api.pedidos.models.model_pedido_historico_unificado import (
    PedidoHistoricoUnificadoModel,
)
from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.pedidos.schemas import (
    HistoricoDoPedidoResponse,
    KanbanAgrupadoResponse,
    PedidoCreateRequest,
    PedidoEntregadorRequest,
    PedidoFecharContaRequest,
    PedidoItemMutationAction,
    PedidoItemMutationRequest,
    PedidoObservacaoPatchRequest,
    PedidoResponse,
    PedidoResponseCompleto,
    PedidoResponseCompletoTotal,
    PedidoStatusPatchRequest,
    PedidoUpdateRequest,
)
from app.api.pedidos.schemas.schema_pedido import (
    ItemPedidoRequest,
    ItemPedidoEditar,
    TipoPedidoCheckoutEnum,
)
from app.api.pedidos.schemas.schema_pedido_status_historico import PedidoStatusHistoricoOut
from app.api.pedidos.services.service_pedido import PedidoService
from app.api.pedidos.services.service_pedidos_balcao import (
    PedidoBalcaoService,
    PedidoBalcaoCreate,
    FecharContaBalcaoRequest,
    AtualizarStatusPedidoRequest as BalcaoStatusRequest,
)
from app.api.pedidos.services.service_pedidos_mesa import (
    PedidoMesaService,
    PedidoMesaCreate,
    AtualizarObservacoesRequest as MesaObservacoesRequest,
    AtualizarStatusPedidoRequest as MesaStatusRequest,
    FecharContaMesaRequest,
)
from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum, TipoEntregaEnum


class PedidoAdminService:
    """
    Fachada para operações de pedidos no contexto admin unificado.
    Delegamos comportamentos específicos para os services legados e expomos
    uma interface única para o router unificado.
    """

    def __init__(
        self,
        db: Session,
        pedido_service: PedidoService,
        mesa_service: PedidoMesaService,
        balcao_service: PedidoBalcaoService,
    ) -> None:
        self.db = db
        self.pedido_service = pedido_service
        self.mesa_service = mesa_service
        self.balcao_service = balcao_service
        self.repo = PedidoRepository(db)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _get_pedido(self, pedido_id: int) -> PedidoUnificadoModel:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        return pedido

    def _to_tipo_entrega_enum(self, tipo: TipoEntrega | str | TipoEntregaEnum) -> TipoEntregaEnum:
        if isinstance(tipo, TipoEntregaEnum):
            return tipo
        if isinstance(tipo, TipoEntrega):
            return TipoEntregaEnum(tipo.value)
        return TipoEntregaEnum(str(tipo))

    def _build_pedido_response(self, pedido: PedidoUnificadoModel) -> PedidoResponse:
        return self.pedido_service.response_builder.build_pedido_response(pedido)

    # ------------------------------------------------------------------ #
    # Listagem e consulta
    # ------------------------------------------------------------------ #
    def listar_pedidos(
        self,
        *,
        empresa_id: Optional[int] = None,
        tipos: Optional[Iterable[TipoEntregaEnum]] = None,
        status_list: Optional[Iterable[PedidoStatusEnum]] = None,
        cliente_id: Optional[int] = None,
        mesa_id: Optional[int] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[PedidoResponse]:
        query = self.db.query(PedidoUnificadoModel)

        if empresa_id:
            query = query.filter(PedidoUnificadoModel.empresa_id == empresa_id)

        if tipos:
            tipos_str = [self._to_tipo_entrega_enum(t).value for t in tipos]
            query = query.filter(PedidoUnificadoModel.tipo_entrega.in_(tipos_str))

        if status_list:
            status_values = [status.value for status in status_list]
            query = query.filter(PedidoUnificadoModel.status.in_(status_values))

        if cliente_id:
            query = query.filter(PedidoUnificadoModel.cliente_id == cliente_id)

        if mesa_id:
            query = query.filter(PedidoUnificadoModel.mesa_id == mesa_id)

        if data_inicio:
            query = query.filter(PedidoUnificadoModel.created_at >= datetime.combine(data_inicio, datetime.min.time()))

        if data_fim:
            query = query.filter(PedidoUnificadoModel.created_at <= datetime.combine(data_fim, datetime.max.time()))

        pedidos = (
            query.order_by(PedidoUnificadoModel.created_at.desc())
            .offset(skip)
            .limit(min(limit, 200))
            .all()
        )
        return [self._build_pedido_response(p) for p in pedidos]

    def listar_kanban(
        self,
        *,
        empresa_id: int,
        date_filter: date,
        limit: int = 500,
    ) -> KanbanAgrupadoResponse:
        return self.pedido_service.list_all_kanban(
            date_filter=date_filter,
            empresa_id=empresa_id,
            limit=limit,
        )

    def obter_pedido(self, pedido_id: int) -> PedidoResponseCompletoTotal:
        pedido = self.pedido_service.get_pedido_by_id_completo_total(pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido com ID {pedido_id} não encontrado",
            )
        return pedido

    def obter_historico(self, pedido_id: int) -> HistoricoDoPedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(
                status=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido com ID {pedido_id} não encontrado",
            )

        historicos = (
            self.db.query(PedidoHistoricoUnificadoModel)
            .filter(PedidoHistoricoUnificadoModel.pedido_id == pedido_id)
            .order_by(PedidoHistoricoUnificadoModel.created_at.desc())
            .all()
        )

        historico_out = [
            PedidoStatusHistoricoOut(
                id=h.id,
                pedido_id=h.pedido_id,
                status=h.status_novo or h.status_anterior,
                status_anterior=h.status_anterior,
                status_novo=h.status_novo,
                tipo_operacao=h.tipo_operacao.value if hasattr(h.tipo_operacao, "value") else h.tipo_operacao,
                descricao=h.descricao,
                motivo=h.motivo,
                observacoes=h.observacoes,
                criado_em=h.created_at,
                criado_por=h.usuario.username if h.usuario and hasattr(h.usuario, "username") else None,
                usuario_id=h.usuario_id,
                cliente_id=h.cliente_id,
                ip_origem=h.ip_origem,
                user_agent=h.user_agent,
            )
            for h in historicos
        ]

        return HistoricoDoPedidoResponse(pedido_id=pedido_id, historicos=historico_out)

    # ------------------------------------------------------------------ #
    # Criação e atualização
    # ------------------------------------------------------------------ #
    async def criar_pedido(
        self,
        payload: PedidoCreateRequest,
        *,
        user_id: Optional[int] = None,
    ) -> PedidoResponseCompleto:
        tipo = payload.tipo_pedido
        if tipo == TipoPedidoCheckoutEnum.DELIVERY:
            cliente_id = payload.cliente_id
            if cliente_id is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "cliente_id é obrigatório para criação de pedidos de delivery via admin.",
                )
            created = await self.pedido_service.finalizar_pedido(payload, cliente_id=cliente_id)
            pedido_atualizado = self.repo.get_pedido(created.id)
            return self.pedido_service.response_builder.pedido_to_response_completo(pedido_atualizado)

        itens_payload = payload.produtos.itens if payload.produtos and payload.produtos.itens is not None else (
            payload.itens or []
        )

        if tipo == TipoPedidoCheckoutEnum.MESA:
            if payload.empresa_id is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "empresa_id é obrigatório para pedidos de mesa.")
            if payload.mesa_codigo is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "mesa_codigo é obrigatório para pedidos de mesa.")
            mesa_payload = PedidoMesaCreate(
                empresa_id=payload.empresa_id,
                mesa_id=int(payload.mesa_codigo),
                cliente_id=payload.cliente_id,
                observacoes=payload.observacao_geral,
                num_pessoas=payload.num_pessoas,
                itens=[
                    ItemPedidoRequest(
                        produto_cod_barras=item.produto_cod_barras,
                        quantidade=item.quantidade,
                        observacao=item.observacao,
                    )
                    for item in itens_payload
                ],
            )
            return self.mesa_service.criar_pedido(mesa_payload)

        if tipo == TipoPedidoCheckoutEnum.BALCAO:
            if payload.empresa_id is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "empresa_id é obrigatório para pedidos de balcão.")

            mesa_codigo = None
            if payload.mesa_codigo is not None:
                try:
                    mesa_codigo = int(str(payload.mesa_codigo))
                except (TypeError, ValueError):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código da mesa inválido.")

            balcao_payload = PedidoBalcaoCreate(
                empresa_id=payload.empresa_id,
                mesa_id=mesa_codigo,
                cliente_id=payload.cliente_id,
                observacoes=payload.observacao_geral,
                itens=[
                    ItemPedidoRequest(
                        produto_cod_barras=item.produto_cod_barras,
                        quantidade=item.quantidade,
                        observacao=item.observacao,
                    )
                    for item in itens_payload
                ],
            )
            return self.balcao_service.criar_pedido(balcao_payload)

        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Tipo de pedido '{tipo}' não suportado para criação via admin.",
        )

    def atualizar_pedido(self, pedido_id: int, payload: PedidoUpdateRequest) -> PedidoResponseCompleto:
        pedido = self._get_pedido(pedido_id)
        tipo = self._to_tipo_entrega_enum(pedido.tipo_entrega)

        # Atualizações comuns via PedidoService
        self.pedido_service.editar_pedido_parcial(pedido_id, payload)

        if payload.cliente_id is not None:
            pedido.cliente_id = payload.cliente_id
        if payload.pagamentos:
            pedido.pagamentos_snapshot = [
                {
                    "id": pag.id or pag.meio_pagamento_id,
                    "valor": float(pag.valor),
                }
                for pag in payload.pagamentos
            ]
        if tipo in {TipoEntregaEnum.MESA, TipoEntregaEnum.BALCAO}:
            if payload.observacoes is not None:
                pedido.observacoes = payload.observacoes
            if payload.num_pessoas is not None:
                pedido.num_pessoas = payload.num_pessoas
        self.db.commit()
        pedido_atualizado = self.repo.get_pedido(pedido_id)
        return self.pedido_service.response_builder.pedido_to_response_completo(pedido_atualizado)

    def atualizar_status(self, pedido_id: int, payload: PedidoStatusPatchRequest, *, user_id: Optional[int] = None):
        pedido = self._get_pedido(pedido_id)
        tipo = self._to_tipo_entrega_enum(pedido.tipo_entrega)

        if tipo == TipoEntregaEnum.MESA:
            mesa_payload = MesaStatusRequest(status=payload.status)
            return self.mesa_service.atualizar_status(pedido_id, mesa_payload)

        if tipo == TipoEntregaEnum.BALCAO:
            balcao_payload = BalcaoStatusRequest(status=payload.status)
            return self.balcao_service.atualizar_status(pedido_id, balcao_payload)

        # Delivery / retirada
        return self.pedido_service.atualizar_status(
            pedido_id=pedido_id,
            novo_status=payload.status,
            user_id=user_id or 0,
        )

    def cancelar(self, pedido_id: int, *, user_id: Optional[int] = None):
        pedido = self._get_pedido(pedido_id)
        tipo = self._to_tipo_entrega_enum(pedido.tipo_entrega)
        if tipo == TipoEntregaEnum.MESA:
            return self.mesa_service.cancelar(pedido_id)
        if tipo == TipoEntregaEnum.BALCAO:
            return self.balcao_service.cancelar(pedido_id)
        return self.pedido_service.atualizar_status(
            pedido_id=pedido_id,
            novo_status=PedidoStatusEnum.C,
            user_id=user_id or 0,
        )

    def atualizar_observacoes(self, pedido_id: int, payload: PedidoObservacaoPatchRequest):
        pedido = self._get_pedido(pedido_id)
        tipo = self._to_tipo_entrega_enum(pedido.tipo_entrega)
        if tipo == TipoEntregaEnum.MESA:
            return self.mesa_service.atualizar_observacoes(
                pedido_id,
                MesaObservacoesRequest(observacoes=payload.observacoes),
            )
        if tipo == TipoEntregaEnum.BALCAO:
            pedido.observacoes = payload.observacoes
        else:
            pedido.observacao_geral = payload.observacoes
        self.db.commit()
        pedido_atualizado = self.repo.get_pedido(pedido_id)
        return self.pedido_service.response_builder.pedido_to_response_completo(pedido_atualizado)

    def fechar_conta(self, pedido_id: int, payload: PedidoFecharContaRequest | None):
        pedido = self._get_pedido(pedido_id)
        tipo = self._to_tipo_entrega_enum(pedido.tipo_entrega)
        if tipo == TipoEntregaEnum.MESA:
            mesa_payload = FecharContaMesaRequest(**(payload.model_dump() if payload else {})) if payload else None
            return self.mesa_service.fechar_conta(pedido_id, mesa_payload)
        if tipo == TipoEntregaEnum.BALCAO:
            balcao_payload = FecharContaBalcaoRequest(**(payload.model_dump() if payload else {})) if payload else None
            return self.balcao_service.fechar_conta(pedido_id, balcao_payload)
        # Delivery e Retirada: marca como pago sem mudar status
        if tipo in {TipoEntregaEnum.DELIVERY, TipoEntregaEnum.RETIRADA}:
            return self._fechar_conta_delivery(pedido_id, payload)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Fechamento de conta não suportado para este tipo de pedido.",
        )
    
    def _fechar_conta_delivery(self, pedido_id: int, payload: PedidoFecharContaRequest | None) -> PedidoResponseCompleto:
        """Fecha conta de pedido delivery/retirada marcando como pago e entregue."""
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        
        # Valida meio de pagamento se fornecido
        if payload and payload.meio_pagamento_id:
            from app.api.cadastros.services.service_meio_pagamento import MeioPagamentoService
            meio_pagamento = MeioPagamentoService(self.db).get(payload.meio_pagamento_id)
            if not meio_pagamento or not meio_pagamento.ativo:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Meio de pagamento inválido ou inativo")
            pedido.meio_pagamento_id = payload.meio_pagamento_id
        
        # Atualiza troco se fornecido
        if payload and payload.troco_para is not None:
            pedido.troco_para = payload.troco_para
        
        # Marca como pago
        pedido.pago = True
        
        # Prepara observações para o histórico
        meio_pagamento_nome = pedido.meio_pagamento.nome if pedido.meio_pagamento else "N/A"
        observacoes = f"Conta fechada. Meio de pagamento: {meio_pagamento_nome}"
        if payload and payload.troco_para is not None:
            observacoes += f". Troco para: R$ {payload.troco_para:.2f}"
        
        # Atualiza status para ENTREGUE e registra no histórico
        status_anterior = pedido.status
        pedido.status = PedidoStatusEnum.E.value
        
        # Registra no histórico
        self.repo.add_status_historico(
            pedido.id,
            PedidoStatusEnum.E.value,
            motivo="Conta fechada",
            observacoes=observacoes,
            criado_por_id=None,
        )
        
        self.db.commit()
        self.db.refresh(pedido)
        
        return self.pedido_service.response_builder.pedido_to_response_completo(pedido)

    def reabrir(self, pedido_id: int):
        pedido = self._get_pedido(pedido_id)
        tipo = self._to_tipo_entrega_enum(pedido.tipo_entrega)
        if tipo == TipoEntregaEnum.MESA:
            return self.mesa_service.reabrir(pedido_id)
        if tipo == TipoEntregaEnum.BALCAO:
            return self.balcao_service.reabrir(pedido_id)
        return self.pedido_service.atualizar_status(
            pedido_id=pedido_id,
            novo_status=PedidoStatusEnum.P,
            user_id=0,
        )

    # ------------------------------------------------------------------ #
    # Itens
    # ------------------------------------------------------------------ #
    def gerenciar_item(self, pedido_id: int, payload: PedidoItemMutationRequest):
        pedido = self._get_pedido(pedido_id)
        tipo = self._to_tipo_entrega_enum(pedido.tipo_entrega)

        if tipo == TipoEntregaEnum.DELIVERY:
            acao_map = {
                PedidoItemMutationAction.ADD: "adicionar",
                PedidoItemMutationAction.UPDATE: "atualizar",
                PedidoItemMutationAction.REMOVE: "remover",
            }
            item = ItemPedidoEditar(
                id=payload.item_id,
                produto_cod_barras=payload.produto_cod_barras,
                quantidade=payload.quantidade,
                observacao=payload.observacao,
                acao=acao_map[payload.acao],
            )
            return self.pedido_service.atualizar_item_pedido(pedido_id, item)

        if tipo == TipoEntregaEnum.MESA:
            if payload.acao == PedidoItemMutationAction.ADD:
                if payload.receita_id or payload.combo_id or payload.complementos:
                    from app.api.pedidos.services.service_pedidos_mesa import AdicionarProdutoGenericoRequest

                    body = AdicionarProdutoGenericoRequest(
                        produto_cod_barras=payload.produto_cod_barras,
                        receita_id=payload.receita_id,
                        combo_id=payload.combo_id,
                        quantidade=payload.quantidade or 1,
                        observacao=payload.observacao,
                        complementos=payload.complementos,
                    )
                    self.mesa_service.adicionar_produto_generico(pedido_id, body)
                from app.api.pedidos.services.service_pedidos_mesa import AdicionarItemRequest

                body = AdicionarItemRequest(
                    produto_cod_barras=payload.produto_cod_barras or "",
                    quantidade=payload.quantidade or 1,
                    observacao=payload.observacao,
                )
                self.mesa_service.adicionar_item(pedido_id, body)
            if payload.acao == PedidoItemMutationAction.REMOVE:
                if not payload.item_id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "item_id é obrigatório para remover item.")
                self.mesa_service.remover_item(pedido_id, payload.item_id)
            else:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Atualização parcial de itens não suportada para mesa.")
            pedido_atualizado = self.repo.get_pedido(pedido_id)
            return self._build_pedido_response(pedido_atualizado)

        if tipo == TipoEntregaEnum.BALCAO:
            from app.api.pedidos.services.service_pedidos_balcao import (
                AdicionarItemRequest as BalcaoAdicionarItemRequest,
                AdicionarProdutoGenericoRequest as BalcaoProdutoGenericoRequest,
            )

            if payload.acao == PedidoItemMutationAction.ADD:
                if payload.receita_id or payload.combo_id or payload.complementos:
                    body = BalcaoProdutoGenericoRequest(
                        produto_cod_barras=payload.produto_cod_barras,
                        receita_id=payload.receita_id,
                        combo_id=payload.combo_id,
                        quantidade=payload.quantidade or 1,
                        observacao=payload.observacao,
                        complementos=payload.complementos,
                    )
                    self.balcao_service.adicionar_produto_generico(pedido_id, body)
                body = BalcaoAdicionarItemRequest(
                    produto_cod_barras=payload.produto_cod_barras or "",
                    quantidade=payload.quantidade or 1,
                    observacao=payload.observacao,
                )
                self.balcao_service.adicionar_item(pedido_id, body)
            if payload.acao == PedidoItemMutationAction.REMOVE:
                if not payload.item_id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "item_id é obrigatório para remover item.")
                self.balcao_service.remover_item(pedido_id, payload.item_id)
            else:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Atualização parcial de itens não suportada para balcão.")
            pedido_atualizado = self.repo.get_pedido(pedido_id)
            return self._build_pedido_response(pedido_atualizado)

        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Tipo de pedido '{tipo}' não suportado.")

    def remover_item(self, pedido_id: int, item_id: int):
        payload = PedidoItemMutationRequest(acao=PedidoItemMutationAction.REMOVE, item_id=item_id)
        return self.gerenciar_item(pedido_id, payload)

    # ------------------------------------------------------------------ #
    # Entregador
    # ------------------------------------------------------------------ #
    def atualizar_entregador(self, pedido_id: int, payload: PedidoEntregadorRequest) -> PedidoResponse:
        pedido = self._get_pedido(pedido_id)
        tipo = self._to_tipo_entrega_enum(pedido.tipo_entrega)
        if tipo not in {TipoEntregaEnum.DELIVERY, TipoEntregaEnum.RETIRADA}:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Vinculação de entregador permitida apenas para pedidos de delivery/retirada.",
            )
        return self.pedido_service.vincular_entregador(pedido_id, payload.entregador_id)

    def remover_entregador(self, pedido_id: int) -> PedidoResponse:
        pedido = self._get_pedido(pedido_id)
        tipo = self._to_tipo_entrega_enum(pedido.tipo_entrega)
        if tipo not in {TipoEntregaEnum.DELIVERY, TipoEntregaEnum.RETIRADA}:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Desvinculação de entregador permitida apenas para pedidos de delivery/retirada.",
            )
        return self.pedido_service.desvincular_entregador(pedido_id)


