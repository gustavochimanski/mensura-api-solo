from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
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
    FinalizarPedidoRequest,
    PreviewCheckoutResponse,
    PedidoCreateRequest,
    PedidoEntregadorRequest,
    PedidoFecharContaRequest,
    PedidoMarcarPedidoPagoRequest,
    PedidoItemMutationAction,
    PedidoItemMutationRequest,
    PedidoObservacaoPatchRequest,
    PedidoResponse,
    PedidoResponseCompleto,
    PedidoResponseCompletoTotal,
    PedidoStatusPatchRequest,
    PedidoTrocarTipoRequest,
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
        return self.pedido_service.response_builder.pedido_to_response(pedido)

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
        tipo: Optional[TipoEntregaEnum] = None,
    ) -> KanbanAgrupadoResponse:
        return self.pedido_service.list_all_kanban(
            date_filter=date_filter,
            empresa_id=empresa_id,
            limit=limit,
            tipo=tipo,
        )

    # ------------------------------------------------------------------ #
    # Checkout (preview)
    # ------------------------------------------------------------------ #
    def calcular_preview_checkout(
        self,
        payload: FinalizarPedidoRequest,
        *,
        cliente_id: Optional[int] = None,
    ) -> PreviewCheckoutResponse:
        """
        Calcula os valores do checkout sem criar pedido no banco.

        Observação:
        - Se `cliente_id` for informado, o serviço valida se `endereco_id` pertence ao cliente.
        """
        return self.pedido_service.calcular_preview_checkout(payload, cliente_id=cliente_id)

    def obter_pedido(self, pedido_id: int, empresa_id: Optional[int] = None) -> PedidoResponseCompletoTotal:
        # Busca o modelo primeiro para validar empresa_id se necessário
        pedido_model = self.repo.get_pedido(pedido_id)
        if not pedido_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido com ID {pedido_id} não encontrado",
            )
        # Valida empresa_id se fornecido
        if empresa_id is not None and pedido_model.empresa_id != empresa_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido com ID {pedido_id} não encontrado para a empresa {empresa_id}",
            )
        # Converte para response completo
        return self.pedido_service.get_pedido_by_id_completo_total(pedido_id)

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
        import asyncio
        from app.api.pedidos.utils.pedido_notification_helper import notificar_novo_pedido
        
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
            
            # Notifica novo pedido em background
            if pedido_atualizado:
                asyncio.create_task(notificar_novo_pedido(pedido_atualizado))
            
            return self.pedido_service.response_builder.pedido_to_response_completo(pedido_atualizado)

        # Extrai itens/receitas/combos do payload (novo formato `produtos.*` ou legado na raiz)
        produtos_payload = payload.produtos if getattr(payload, "produtos", None) is not None else None
        itens_payload = (
            (produtos_payload.itens if produtos_payload and produtos_payload.itens is not None else payload.itens)
            or []
        )
        receitas_payload = (
            (produtos_payload.receitas if produtos_payload and produtos_payload.receitas is not None else payload.receitas)
            or []
        )
        combos_payload = (
            (produtos_payload.combos if produtos_payload and produtos_payload.combos is not None else payload.combos)
            or []
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
                meio_pagamento_id=(
                    (getattr(payload.meios_pagamento[0], "id", None) or getattr(payload.meios_pagamento[0], "meio_pagamento_id", None))
                    if getattr(payload, "meios_pagamento", None)
                    else None
                ),
                itens=(
                    [
                        ItemPedidoRequest(
                            produto_cod_barras=item.produto_cod_barras,
                            quantidade=item.quantidade,
                            observacao=item.observacao,
                            complementos=getattr(item, "complementos", None),
                        )
                        for item in itens_payload
                    ]
                    if itens_payload
                    else None
                ),
                receitas=receitas_payload if receitas_payload else None,
                combos=combos_payload if combos_payload else None,
            )
            resultado = self.mesa_service.criar_pedido(mesa_payload)
            
            # Notifica novo pedido em background
            pedido_model = self.repo.get_pedido(resultado.id)
            if pedido_model:
                asyncio.create_task(notificar_novo_pedido(pedido_model))
            
            return resultado

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
                meio_pagamento_id=(
                    (getattr(payload.meios_pagamento[0], "id", None) or getattr(payload.meios_pagamento[0], "meio_pagamento_id", None))
                    if getattr(payload, "meios_pagamento", None)
                    else None
                ),
                itens=(
                    [
                        ItemPedidoRequest(
                            produto_cod_barras=item.produto_cod_barras,
                            quantidade=item.quantidade,
                            observacao=item.observacao,
                            complementos=getattr(item, "complementos", None),
                        )
                        for item in itens_payload
                    ]
                    if itens_payload
                    else None
                ),
                receitas=receitas_payload if receitas_payload else None,
                combos=combos_payload if combos_payload else None,
            )
            resultado = self.balcao_service.criar_pedido(balcao_payload)
            
            # Notifica novo pedido em background
            pedido_model = self.repo.get_pedido(resultado.id)
            if pedido_model:
                asyncio.create_task(notificar_novo_pedido(pedido_model))
            
            return resultado

        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Tipo de pedido '{tipo}' não suportado para criação via admin.",
        )

    def atualizar_pedido(self, pedido_id: int, payload: PedidoUpdateRequest) -> PedidoResponseCompleto:
        pedido = self._get_pedido(pedido_id)
        # Garanta que os totais estejam atualizados antes de validar pagamentos
        try:
            # Recalcula e persiste subtotal/valores/taxas a partir do estado atual do pedido
            self.pedido_service._recalcular_pedido(pedido)
            self.repo.commit()
            pedido = self._get_pedido(pedido_id)
        except Exception:
            # Best-effort: se falhar a recomputação, segue com o pedido carregado (evita quebrar fluxo)
            pass
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
        # Delivery e Retirada: fecha a conta (registra transação PAGO e muda status para ENTREGUE).
        if tipo in {TipoEntregaEnum.DELIVERY, TipoEntregaEnum.RETIRADA}:
            return self._fechar_conta_delivery(pedido_id, payload)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Fechamento de conta não suportado para este tipo de pedido.",
        )

    def marcar_pedido_pago(
        self,
        pedido_id: int,
        payload: PedidoMarcarPedidoPagoRequest | None,
        *,
        user_id: Optional[int] = None,
    ) -> PedidoResponseCompleto:
        """
        Registra pagamento do pedido via transação (sem alterar o status).

        Regra:
        - `meio_pagamento_id` é obrigatório.
        - O pagamento passa a ser controlado por transações (status PAGO/AUTORIZADO).
        """
        from app.api.pedidos.models.model_pedido_historico_unificado import TipoOperacaoPedido
        from app.api.cardapio.repositories.repo_pagamentos import PagamentoRepository
        from app.api.shared.schemas.schema_shared_enums import (
            PagamentoGatewayEnum,
            PagamentoMetodoEnum,
            PagamentoStatusEnum,
        )
        from app.api.cadastros.schemas.schema_meio_pagamento import MeioPagamentoTipoEnum
        from app.api.pedidos.services.service_pedido_helpers import _dec, ajustar_pagamento_dinheiro_com_troco
        from decimal import Decimal

        pedido = self._get_pedido(pedido_id)
        # Garantia explícita: este endpoint NÃO altera status do pedido.
        status_original = (
            pedido.status.value
            if hasattr(pedido.status, "value")
            else str(pedido.status)
        )

        from app.api.cadastros.services.service_meio_pagamento import MeioPagamentoService

        pagamento_repo = PagamentoRepository(self.db)
        txs = pagamento_repo.list_by_pedido_id(pedido.id)

        pagamentos_payload: list[dict] = []
        if payload is not None and getattr(payload, "pagamentos", None):
            for pag in payload.pagamentos or []:
                mp_id = getattr(pag, "id", None) or getattr(pag, "meio_pagamento_id", None)
                if mp_id is None:
                    continue
                pagamentos_payload.append(
                    {
                        "meio_pagamento_id": int(mp_id),
                        "valor": _dec(pag.valor),
                    }
                )
            if pagamentos_payload:
                pedido.meio_pagamento_id = pagamentos_payload[0]["meio_pagamento_id"]
                if hasattr(pedido, "pagamentos_snapshot"):
                    pedido.pagamentos_snapshot = [
                        {"id": p["meio_pagamento_id"], "valor": float(p["valor"])}
                        for p in pagamentos_payload
                    ]

        meio_pagamento_id: Optional[int] = None
        if not pagamentos_payload:
            if payload is not None and getattr(payload, "meio_pagamento_id", None) is not None:
                meio_pagamento_id = int(payload.meio_pagamento_id)
            else:
                # Body vazio/omitido: usa o meio já salvo no pedido, se existir.
                meio_pagamento_id = (
                    int(pedido.meio_pagamento_id) if getattr(pedido, "meio_pagamento_id", None) else None
                )

            if meio_pagamento_id is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "meio_pagamento_id é obrigatório para marcar pedido como pago (envie no payload ou defina no pedido).",
                )
            # Compat: persistimos no pedido para referência do checkout/UI.
            pedido.meio_pagamento_id = meio_pagamento_id

        valor_total = _dec(getattr(pedido, "valor_total", 0) or 0)

        # Se o frontend mandou "valor recebido" em dinheiro (valor > total) em `pagamentos`,
        # normalizamos: transação registra apenas o total e persistimos `troco_para` como valor recebido.
        if pagamentos_payload:
            def _is_dinheiro(mp_id: int) -> bool:
                mp = MeioPagamentoService(self.db).get(int(mp_id))
                if not mp or not getattr(mp, "ativo", False):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Meio de pagamento inválido ou inativo")
                return mp.tipo == MeioPagamentoTipoEnum.DINHEIRO or str(mp.tipo) == "DINHEIRO"

            try:
                pagamentos_payload, troco_para_derivado = ajustar_pagamento_dinheiro_com_troco(
                    pagamentos=pagamentos_payload,
                    valor_total=valor_total,
                    is_dinheiro=_is_dinheiro,
                )
            except ValueError as e:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail={"code": "TROCO_INVALIDO", "message": str(e)},
                )

            if troco_para_derivado is not None and getattr(pedido, "troco_para", None) is None:
                pedido.troco_para = float(troco_para_derivado)

            # Atualiza snapshot com valores normalizados (aplicados no pedido)
            if hasattr(pedido, "pagamentos_snapshot") and pagamentos_payload:
                pedido.pagamentos_snapshot = [
                    {"id": p["meio_pagamento_id"], "valor": float(p["valor"])} for p in pagamentos_payload
                ]
        pagamentos_para_marcar = pagamentos_payload or [
            {"meio_pagamento_id": int(pedido.meio_pagamento_id), "valor": valor_total}
        ]
        if pagamentos_payload:
            soma_pagamentos = sum((p["valor"] for p in pagamentos_payload), _dec(0))
            # Considera pagamentos já marcados via transações (PAGO/AUTORIZADO)
            valor_pago_existente = _dec(0)
            for tx in txs:
                if str(getattr(tx, "status", "")).upper() in {"PAGO", "AUTORIZADO"}:
                    valor_pago_existente += _dec(getattr(tx, "valor", 0) or 0)

            total_pos_aplicacao = valor_pago_existente + soma_pagamentos
            if total_pos_aplicacao != valor_total:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "PAGAMENTOS_INVALIDOS",
                        "message": "Soma dos pagamentos (incluindo transações já pagas) deve igualar o valor total do pedido para marcar como pago.",
                        "valor_total": float(valor_total),
                        "soma_pagamentos_enviados": float(soma_pagamentos),
                        "valor_pago_existente": float(valor_pago_existente),
                        "soma_total": float(total_pos_aplicacao),
                    },
                )
        else:
            # No formato legado, mantém idempotência simples: se já existe pago, não duplica.
            if any(getattr(tx, "status", None) in {"PAGO", "AUTORIZADO"} for tx in txs):
                pedido.status = status_original
                self.db.commit()
                pedido_atualizado = self.repo.get_pedido(pedido_id)
                return self.pedido_service.response_builder.pedido_to_response_completo(pedido_atualizado)

        meios_pagamento_nomes: list[str] = []
        for p in pagamentos_para_marcar:
            mp_id = int(p["meio_pagamento_id"])
            valor_parcial = _dec(p["valor"])

            meio_pagamento = MeioPagamentoService(self.db).get(mp_id)
            if not meio_pagamento or not getattr(meio_pagamento, "ativo", False):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Meio de pagamento inválido ou inativo")

            # Mapeia meio de pagamento -> (método, gateway)
            if meio_pagamento.tipo == MeioPagamentoTipoEnum.PIX_ONLINE or str(meio_pagamento.tipo) == "PIX_ONLINE":
                metodo = PagamentoMetodoEnum.PIX_ONLINE
                gateway = PagamentoGatewayEnum.MERCADOPAGO
            elif meio_pagamento.tipo == MeioPagamentoTipoEnum.PIX_ENTREGA or str(meio_pagamento.tipo) == "PIX_ENTREGA":
                metodo = PagamentoMetodoEnum.PIX
                gateway = PagamentoGatewayEnum.PIX_INTERNO
            elif meio_pagamento.tipo == MeioPagamentoTipoEnum.CARTAO_ENTREGA or str(meio_pagamento.tipo) == "CARTAO_ENTREGA":
                metodo = PagamentoMetodoEnum.CREDITO
                gateway = PagamentoGatewayEnum.PIX_INTERNO
            elif meio_pagamento.tipo == MeioPagamentoTipoEnum.DINHEIRO or str(meio_pagamento.tipo) == "DINHEIRO":
                metodo = PagamentoMetodoEnum.DINHEIRO
                gateway = PagamentoGatewayEnum.PIX_INTERNO
            else:
                metodo = PagamentoMetodoEnum.OUTRO
                gateway = PagamentoGatewayEnum.PIX_INTERNO

            meio_pagamento_nome = meio_pagamento.nome if getattr(meio_pagamento, "nome", None) else str(mp_id)
            meios_pagamento_nomes.append(meio_pagamento_nome)

            centavos = int((valor_parcial * Decimal("100")).quantize(Decimal("1")))
            provider_id = f"manual_marcar_pago_{pedido.id}_{mp_id}_{centavos}"

            # Tenta reutilizar transação pendente existente (mesmo meio+valor)
            tx_match = next(
                (
                    tx
                    for tx in txs
                    if int(getattr(tx, "meio_pagamento_id", 0) or 0) == mp_id
                    and _dec(getattr(tx, "valor", 0) or 0) == valor_parcial
                    and str(getattr(tx, "status", "")).upper() not in {"PAGO", "AUTORIZADO"}
                ),
                None,
            )

            if tx_match is not None:
                pagamento_repo.atualizar(
                    tx_match,
                    status=PagamentoStatusEnum.PAGO.value,
                    provider_transaction_id=(getattr(tx_match, "provider_transaction_id", None) or provider_id),
                    payload_solicitacao={"origem": "marcar_pedido_pago", "usuario_id": user_id},
                )
                pagamento_repo.registrar_evento(tx_match, "pago_em")
                continue

            # Idempotência: se já existe transação com esse provider_id, não recria
            if pagamento_repo.get_by_provider_transaction_id(provider_transaction_id=provider_id) is not None:
                continue

            tx_nova = pagamento_repo.criar(
                pedido_id=pedido.id,
                meio_pagamento_id=mp_id,
                gateway=gateway.value,
                metodo=metodo.value,
                valor=valor_parcial,
                status=PagamentoStatusEnum.PAGO.value,
                provider_transaction_id=provider_id,
                payload_solicitacao={"origem": "marcar_pedido_pago", "usuario_id": user_id},
            )
            pagamento_repo.registrar_evento(tx_nova, "pago_em")

        # Histórico detalhado (sem mudança de status)
        if meios_pagamento_nomes:
            observacoes = f"Meios de pagamento: {', '.join(meios_pagamento_nomes)}"
        else:
            observacoes = "Pagamento registrado"
        self.repo.add_historico(
            pedido_id=pedido.id,
            tipo_operacao=TipoOperacaoPedido.PAGAMENTO_REALIZADO,
            descricao="Pagamento registrado (transação PAGO)",
            observacoes=observacoes,
            usuario_id=user_id,
        )

        # Reforço: não permitir alteração de status neste fluxo.
        pedido.status = status_original
        self.db.commit()
        pedido_atualizado = self.repo.get_pedido(pedido_id)
        # Caso algum gatilho/fluxo externo tenha alterado status, desfazemos aqui (best-effort).
        status_atual = (
            pedido_atualizado.status.value
            if hasattr(pedido_atualizado.status, "value")
            else str(pedido_atualizado.status)
        )
        if status_atual != status_original:
            logger.warning(
                "[marcar_pedido_pago] status alterado indevidamente; revertendo | pedido_id=%s de=%s para=%s",
                pedido_id,
                status_atual,
                status_original,
            )
            pedido_atualizado.status = status_original
            self.db.commit()
            pedido_atualizado = self.repo.get_pedido(pedido_id)
        return self.pedido_service.response_builder.pedido_to_response_completo(pedido_atualizado)
    
    def _fechar_conta_delivery(self, pedido_id: int, payload: PedidoFecharContaRequest | None) -> PedidoResponseCompleto:
        """Fecha conta de pedido delivery/retirada registrando transação PAGO e marcando como entregue."""
        pedido = self.repo.get_pedido(pedido_id)
        # Recalcula totais antes de fechar conta para evitar divergência (item adicionado fora deste request)
        try:
            self.pedido_service._recalcular_pedido(pedido)
            self.repo.commit()
            pedido = self.repo.get_pedido(pedido_id)
        except Exception:
            pass
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        
        from app.api.pedidos.services.service_pedido_helpers import _dec, ajustar_pagamento_dinheiro_com_troco

        pagamentos_payload: list[dict] = []
        if payload and getattr(payload, "pagamentos", None):
            for pag in payload.pagamentos or []:
                mp_id = getattr(pag, "id", None) or getattr(pag, "meio_pagamento_id", None)
                if mp_id is None:
                    continue
                pagamentos_payload.append(
                    {
                        "meio_pagamento_id": int(mp_id),
                        "valor": _dec(pag.valor),
                    }
                )
            if pagamentos_payload:
                pedido.meio_pagamento_id = pagamentos_payload[0]["meio_pagamento_id"]
                if hasattr(pedido, "pagamentos_snapshot"):
                    pedido.pagamentos_snapshot = [
                        {"id": p["meio_pagamento_id"], "valor": float(p["valor"])}
                        for p in pagamentos_payload
                    ]
        # Valida e atualiza meio de pagamento legado (1 meio) se fornecido
        elif payload and payload.meio_pagamento_id is not None:
            from app.api.cadastros.services.service_meio_pagamento import MeioPagamentoService
            meio_pagamento = MeioPagamentoService(self.db).get(payload.meio_pagamento_id)
            if not meio_pagamento or not meio_pagamento.ativo:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Meio de pagamento inválido ou inativo")
            pedido.meio_pagamento_id = payload.meio_pagamento_id
        
        # Atualiza troco se fornecido
        if payload and payload.troco_para is not None:
            pedido.troco_para = payload.troco_para

        # Se o pedido já estiver totalmente pago (via transações PAGO/AUTORIZADO),
        # podemos marcar como ENTREGUE sem recriar transações e sem exigir meio_pagamento_id no payload.
        try:
            from app.api.pedidos.services.service_pedido_helpers import build_pagamento_resumo

            pagamento_resumo = build_pagamento_resumo(pedido)
            if pagamento_resumo and getattr(pagamento_resumo, "esta_pago", False):
                # Persiste eventuais ajustes do payload (troco/snapshot/meio_pagamento_id) antes de finalizar
                self.db.commit()
                self.db.refresh(pedido)

                meio_pagamento_nome = pedido.meio_pagamento.nome if getattr(pedido, "meio_pagamento", None) else "N/A"
                observacoes = f"Conta fechada (já pago). Meio de pagamento: {meio_pagamento_nome}"
                if getattr(pedido, "troco_para", None) is not None:
                    observacoes += f". Troco para: R$ {float(pedido.troco_para):.2f}"

                status_anterior = pedido.status
                pedido.status = PedidoStatusEnum.E.value
                self.repo.add_status_historico(
                    pedido.id,
                    PedidoStatusEnum.E.value,
                    motivo="Conta fechada (já pago)",
                    observacoes=observacoes,
                    criado_por_id=None,
                )
                self.db.flush()
                self.db.commit()
                self.db.refresh(pedido)
                return self.pedido_service.response_builder.pedido_to_response_completo(pedido)
        except Exception:
            # Best-effort: se falhar a checagem, segue o fluxo padrão (registrar transação)
            pass

        # Precisa ter meio de pagamento para registrar transação
        meio_pagamento_id = getattr(pedido, "meio_pagamento_id", None)
        if meio_pagamento_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Meio de pagamento não informado para fechamento de conta.")

        # Registra pagamento via transação (idempotente)
        from app.api.cadastros.services.service_meio_pagamento import MeioPagamentoService
        from app.api.cadastros.schemas.schema_meio_pagamento import MeioPagamentoTipoEnum
        from app.api.cardapio.repositories.repo_pagamentos import PagamentoRepository
        from app.api.shared.schemas.schema_shared_enums import (
            PagamentoGatewayEnum,
            PagamentoMetodoEnum,
            PagamentoStatusEnum,
        )
        from decimal import Decimal

        # Se o frontend mandou "valor recebido" em DINHEIRO (valor > total) dentro de `pagamentos`,
        # normalizamos: transação registra apenas o total e persistimos `troco_para` como valor recebido.
        troco_para_derivado = None
        # Valor total do pedido em Decimal (compatível com helpers)
        valor_total = _dec(getattr(pedido, "valor_total", 0) or 0)
        if pagamentos_payload:
            def _is_dinheiro(mp_id: int) -> bool:
                mp = MeioPagamentoService(self.db).get(int(mp_id))
                if not mp or not getattr(mp, "ativo", False):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Meio de pagamento inválido ou inativo")
                return mp.tipo == MeioPagamentoTipoEnum.DINHEIRO or str(mp.tipo) == "DINHEIRO"

            try:
                pagamentos_payload, troco_para_derivado = ajustar_pagamento_dinheiro_com_troco(
                    pagamentos=pagamentos_payload,
                    valor_total=valor_total,
                    is_dinheiro=_is_dinheiro,
                )
            except ValueError as e:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail={"code": "TROCO_INVALIDO", "message": str(e)},
                )

            if troco_para_derivado is not None and (payload is None or getattr(payload, "troco_para", None) is None):
                pedido.troco_para = float(troco_para_derivado)

            # Atualiza snapshot com valores normalizados (aplicados no pedido)
            if hasattr(pedido, "pagamentos_snapshot") and pagamentos_payload:
                pedido.pagamentos_snapshot = [
                    {"id": p["meio_pagamento_id"], "valor": float(p["valor"])} for p in pagamentos_payload
                ]

        pagamentos_para_fechar = pagamentos_payload or [
            {"meio_pagamento_id": int(meio_pagamento_id), "valor": valor_total}
        ]
        if pagamentos_payload:
            soma_pagamentos = sum((p["valor"] for p in pagamentos_payload), _dec(0))
            # Considera pagamentos já marcados via transações (PAGO/AUTORIZADO)
            pagamento_repo_tmp = PagamentoRepository(self.db)
            txs_existentes = pagamento_repo_tmp.list_by_pedido_id(pedido.id)
            valor_pago_existente = _dec(0)
            for tx in txs_existentes:
                if str(getattr(tx, "status", "")).upper() in {"PAGO", "AUTORIZADO"}:
                    valor_pago_existente += _dec(getattr(tx, "valor", 0) or 0)

            total_pos_aplicacao = valor_pago_existente + soma_pagamentos
            if total_pos_aplicacao != valor_total:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "PAGAMENTOS_INVALIDOS",
                        "message": "Soma dos pagamentos (incluindo transações já pagas) deve igualar o valor total do pedido para fechar conta.",
                        "valor_total": float(valor_total),
                        "soma_pagamentos_enviados": float(soma_pagamentos),
                        "valor_pago_existente": float(valor_pago_existente),
                        "soma_total": float(total_pos_aplicacao),
                    },
                )

        pagamento_repo = PagamentoRepository(self.db)
        txs = pagamento_repo.list_by_pedido_id(pedido.id)
        for p in pagamentos_para_fechar:
            mp_id = int(p["meio_pagamento_id"])
            valor_parcial = _dec(p["valor"])

            mp = MeioPagamentoService(self.db).get(mp_id)
            if not mp or not getattr(mp, "ativo", False):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Meio de pagamento inválido ou inativo")

            if mp.tipo == MeioPagamentoTipoEnum.PIX_ONLINE or str(mp.tipo) == "PIX_ONLINE":
                metodo = PagamentoMetodoEnum.PIX_ONLINE
                gateway = PagamentoGatewayEnum.MERCADOPAGO
            elif mp.tipo == MeioPagamentoTipoEnum.PIX_ENTREGA or str(mp.tipo) == "PIX_ENTREGA":
                metodo = PagamentoMetodoEnum.PIX
                gateway = PagamentoGatewayEnum.PIX_INTERNO
            elif mp.tipo == MeioPagamentoTipoEnum.CARTAO_ENTREGA or str(mp.tipo) == "CARTAO_ENTREGA":
                metodo = PagamentoMetodoEnum.CREDITO
                gateway = PagamentoGatewayEnum.PIX_INTERNO
            elif mp.tipo == MeioPagamentoTipoEnum.DINHEIRO or str(mp.tipo) == "DINHEIRO":
                metodo = PagamentoMetodoEnum.DINHEIRO
                gateway = PagamentoGatewayEnum.PIX_INTERNO
            else:
                metodo = PagamentoMetodoEnum.OUTRO
                gateway = PagamentoGatewayEnum.PIX_INTERNO

            centavos = int((valor_parcial * Decimal("100")).quantize(Decimal("1")))
            provider_id = f"manual_fechar_conta_delivery_{pedido.id}_{mp_id}_{centavos}"

            tx_existente = next(
                (
                    tx
                    for tx in txs
                    if int(getattr(tx, "meio_pagamento_id", 0) or 0) == mp_id
                    and _dec(getattr(tx, "valor", 0) or 0) == valor_parcial
                    and str(getattr(tx, "status", "")).upper() not in {"PAGO", "AUTORIZADO"}
                ),
                None,
            )
            if tx_existente is not None:
                pagamento_repo.atualizar(
                    tx_existente,
                    status=PagamentoStatusEnum.PAGO.value,
                    provider_transaction_id=provider_id,
                    payload_solicitacao={"origem": "fechar_conta_delivery"},
                )
                pagamento_repo.registrar_evento(tx_existente, "pago_em")
                continue

            if pagamento_repo.get_by_provider_transaction_id(provider_transaction_id=provider_id) is not None:
                continue

            tx_nova = pagamento_repo.criar(
                pedido_id=pedido.id,
                meio_pagamento_id=mp_id,
                gateway=gateway.value,
                metodo=metodo.value,
                valor=valor_parcial,
                status=PagamentoStatusEnum.PAGO.value,
                provider_transaction_id=provider_id,
                payload_solicitacao={"origem": "fechar_conta_delivery"},
            )
            pagamento_repo.registrar_evento(tx_nova, "pago_em")

        # IMPORTANTE: Faz commit e refresh ANTES de acessar o relacionamento meio_pagamento
        # Isso garante que o meio_pagamento_id seja persistido e o relacionamento seja atualizado
        if payload and (
            payload.meio_pagamento_id is not None
            or payload.troco_para is not None
            or getattr(payload, "pagamentos", None)
            or troco_para_derivado is not None
        ):
            self.db.commit()
            self.db.refresh(pedido)
        
        # Prepara observações para o histórico
        meio_pagamento_nome = pedido.meio_pagamento.nome if pedido.meio_pagamento else "N/A"
        observacoes = f"Conta fechada. Meio de pagamento: {meio_pagamento_nome}"
        if getattr(pedido, "troco_para", None) is not None:
            observacoes += f". Troco para: R$ {float(pedido.troco_para):.2f}"
        
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
        
        # Força flush para garantir que as alterações sejam enviadas ao banco
        self.db.flush()
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
        # Delivery e Retirada: reabre com método específico
        if tipo in {TipoEntregaEnum.DELIVERY, TipoEntregaEnum.RETIRADA}:
            return self._reabrir_delivery(pedido_id)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Reabertura de pedido não suportada para este tipo de pedido.",
        )
    
    def _reabrir_delivery(self, pedido_id: int) -> PedidoResponseCompleto:
        """Reabre um pedido delivery/retirada que foi entregue ou cancelado."""
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        
        # Valida que o pedido pode ser reaberto (deve estar ENTREGUE ou CANCELADO)
        status_atual = pedido.status
        if status_atual not in {PedidoStatusEnum.E.value, PedidoStatusEnum.C.value}:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Não é possível reabrir um pedido com status '{status_atual}'. Apenas pedidos ENTREGUE ou CANCELADO podem ser reabertos."
            )
        
        # Atualiza status para PENDENTE (P)
        status_anterior = pedido.status
        pedido.status = PedidoStatusEnum.P.value
        
        # Prepara observações para o histórico
        observacoes = f"Pedido reaberto. Status anterior: {status_anterior}"
        
        # Registra no histórico
        self.repo.add_status_historico(
            pedido.id,
            PedidoStatusEnum.P.value,
            motivo="Pedido reaberto",
            observacoes=observacoes,
            criado_por_id=None,
        )
        
        # Força flush para garantir que as alterações sejam enviadas ao banco
        self.db.flush()
        self.db.commit()
        self.db.refresh(pedido)
        
        return self.pedido_service.response_builder.pedido_to_response_completo(pedido)

    # ------------------------------------------------------------------ #
    # Itens
    # ------------------------------------------------------------------ #
    def gerenciar_item(self, pedido_id: int, payload: PedidoItemMutationRequest):
        pedido = self._get_pedido(pedido_id)
        tipo = self._to_tipo_entrega_enum(pedido.tipo_entrega)

        # Validação: se tipo foi informado no payload, deve corresponder ao tipo do pedido
        if payload.tipo and payload.tipo != tipo:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Tipo informado no payload ({payload.tipo}) não corresponde ao tipo do pedido ({tipo})"
            )

        if tipo == TipoEntregaEnum.DELIVERY:
            if payload.acao == PedidoItemMutationAction.ADD:
                # Unificado: usa adicionar_produto_generico para todos os tipos (produto, receita, combo)
                # Agora com suporte a complementos também para delivery
                from app.api.pedidos.services.service_pedidos_balcao import (
                    AdicionarProdutoGenericoRequest as ProdutoGenericoRequest,
                )
                
                # Valida que pelo menos um identificador foi enviado
                if not payload.produto_cod_barras and not payload.receita_id and not payload.combo_id:
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        "É necessário informar produto_cod_barras, receita_id ou combo_id"
                    )
                
                # Cria serviço de balcão temporário para usar o método unificado
                # (mesmo método funciona para delivery, apenas muda o tipo de entrega)
                from app.api.catalogo.adapters.produto_adapter import ProdutoAdapter
                from app.api.catalogo.adapters.combo_adapter import ComboAdapter
                from app.api.catalogo.adapters.complemento_adapter import ComplementoAdapter
                from app.api.catalogo.contracts.produto_contract import IProdutoContract
                from app.api.catalogo.contracts.combo_contract import IComboContract
                from app.api.catalogo.contracts.complemento_contract import IComplementoContract
                
                produto_adapter = ProdutoAdapter(self.db)
                combo_adapter = ComboAdapter(self.db)
                complemento_adapter = ComplementoAdapter(self.db)
                
                # Usa o serviço de balcão que já tem a lógica unificada
                balcao_service = PedidoBalcaoService(
                    self.db,
                    produto_contract=produto_adapter,
                    combo_contract=combo_adapter,
                    complemento_contract=complemento_adapter,
                )
                
                body = ProdutoGenericoRequest(
                    produto_cod_barras=payload.produto_cod_barras,
                    receita_id=payload.receita_id,
                    combo_id=payload.combo_id,
                    quantidade=payload.quantidade or 1,
                    observacao=payload.observacao,
                    complementos=payload.complementos,  # Agora suporta complementos em delivery
                )
                
                # Usa o método unificado, mas precisa ajustar para delivery
                # Como o método adicionar_produto_generico usa TipoEntrega.BALCAO,
                # vamos usar uma abordagem diferente: usar ProductCore diretamente
                from app.api.catalogo.core import ProductCore
                from app.api.catalogo.models.model_receita import ReceitaModel
                from app.api.pedidos.models.model_pedido_unificado import TipoEntrega
                from app.api.pedidos.models.model_pedido_historico_unificado import TipoOperacaoPedido
                from app.api.pedidos.services.service_pedido_responses import PedidoResponseBuilder
                
                product_core = ProductCore(
                    produto_contract=produto_adapter,
                    combo_contract=combo_adapter,
                    complemento_contract=complemento_adapter,
                )
                
                empresa_id = pedido.empresa_id
                qtd = max(int(body.quantidade or 1), 1)
                
                # Busca receita do banco se necessário
                receita_model = None
                if body.receita_id:
                    receita_model = self.db.query(ReceitaModel).filter(ReceitaModel.id == body.receita_id).first()
                
                # Busca produto usando ProductCore
                product = product_core.buscar_qualquer(
                    empresa_id=empresa_id,
                    cod_barras=body.produto_cod_barras,
                    combo_id=body.combo_id,
                    receita_id=body.receita_id,
                    receita_model=receita_model,
                )
                
                if not product:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")
                
                if not product_core.validar_disponivel(product, qtd):
                    tipo_nome = product.product_type.value
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{tipo_nome.capitalize()} não disponível")
                
                if not product_core.validar_empresa(product, empresa_id):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Produto não pertence à empresa {empresa_id}")
                
                # IMPORTANTE: preco_unitario deve ser apenas o preço BASE do produto (sem complementos)
                # Os complementos são somados separadamente via _sum_complementos_total_relacional
                # para evitar duplicação no cálculo do total do item
                preco_unitario = product.get_preco_venda()
                
                # Adiciona item usando repositório
                descricao_produto = product.nome or product.descricao or ""
                
                if product.product_type.value == "produto":
                    # Se complementos NÃO foram fornecidos no payload, tente mesclar com item existente
                    merged = False
                    if not getattr(body, "complementos", None):
                        try:
                            # procura item existente no pedido com mesmo cod_barras (produto simples)
                            existing = next(
                                (
                                    i
                                    for i in pedido.itens
                                    if getattr(i, "produto_cod_barras", None) is not None
                                    and str(getattr(i, "produto_cod_barras")) == str(product.identifier)
                                    and (getattr(i, "receita_id", None) is None)
                                    and (getattr(i, "combo_id", None) is None)
                                ),
                                None,
                            )
                            if existing:
                                # incrementa quantidade existente (mantendo complementos já selecionados nele)
                                new_qtd = int(getattr(existing, "quantidade", 1) or 1) + int(qtd)
                                self.repo.atualizar_item(existing.id, quantidade=new_qtd)
                                merged = True
                        except Exception:
                            merged = False

                    if not merged:
                        self.repo.adicionar_item(
                            pedido_id=pedido_id,
                            cod_barras=str(product.identifier),
                            quantidade=qtd,
                            preco_unitario=preco_unitario,
                            observacao=body.observacao,
                            produto_descricao_snapshot=descricao_produto,
                            complementos=body.complementos if body.complementos else None,
                        )
                    descricao_historico = f"Produto adicionado: {product.identifier} (qtd: {qtd})"
                elif product.product_type.value == "receita":
                    self.repo.adicionar_item(
                        pedido_id=pedido_id,
                        receita_id=int(product.identifier),
                        quantidade=qtd,
                        preco_unitario=preco_unitario,
                        observacao=body.observacao,
                        produto_descricao_snapshot=descricao_produto,
                        complementos=body.complementos if body.complementos else None,
                    )
                    descricao_historico = f"Receita adicionada: {descricao_produto} (ID: {product.identifier}, qtd: {qtd})"
                elif product.product_type.value == "combo":
                    self.repo.adicionar_item(
                        pedido_id=pedido_id,
                        combo_id=int(product.identifier),
                        quantidade=qtd,
                        preco_unitario=preco_unitario,
                        observacao=body.observacao,
                        produto_descricao_snapshot=descricao_produto,
                        complementos=body.complementos if body.complementos else None,
                    )
                    descricao_historico = f"Combo adicionado: {descricao_produto} (ID: {product.identifier}, qtd: {qtd})"
                else:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tipo de produto não suportado")
                
                # Registra histórico
                self.repo.add_historico(
                    pedido_id=pedido_id,
                    tipo_operacao=TipoOperacaoPedido.ITEM_ADICIONADO,
                    descricao=descricao_historico,
                    usuario_id=None,
                )
                
                # Atualiza totais do pedido
                pedido_atualizado = self.repo.get_pedido(pedido_id)
                self.pedido_service._recalcular_pedido(pedido_atualizado)
                self.repo.commit()
                pedido_atualizado = self.repo.get_pedido(pedido_id)
                return self._build_pedido_response(pedido_atualizado)
            elif payload.acao == PedidoItemMutationAction.UPDATE:
                # Para UPDATE em delivery, usa o método existente
                if not payload.item_id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "item_id é obrigatório para atualizar item.")
                
                # Se receita_id ou combo_id vierem no payload, atualiza o item no banco antes de processar
                # Isso garante que os complementos sejam calculados com base no receita_id/combo_id correto
                if payload.receita_id is not None or payload.combo_id is not None:
                    item_db = self.repo.get_item_by_id(payload.item_id)
                    if not item_db:
                        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Item {payload.item_id} não encontrado")
                    if payload.receita_id is not None:
                        item_db.receita_id = payload.receita_id
                        item_db.produto_cod_barras = None
                        item_db.combo_id = None
                    if payload.combo_id is not None:
                        item_db.combo_id = payload.combo_id
                        item_db.produto_cod_barras = None
                        item_db.receita_id = None
                    # Não faz commit aqui - será feito no final do atualizar_item_pedido
                    self.db.flush()
                
                acao_map = {
                    PedidoItemMutationAction.UPDATE: "atualizar",
                }
                item = ItemPedidoEditar(
                    id=payload.item_id,
                    produto_cod_barras=payload.produto_cod_barras,
                    quantidade=payload.quantidade,
                    observacao=payload.observacao,
                    complementos=payload.complementos,
                    acao=acao_map[payload.acao],
                )
                return self.pedido_service.atualizar_item_pedido(pedido_id, item)
            elif payload.acao == PedidoItemMutationAction.REMOVE:
                if not payload.item_id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "item_id é obrigatório para remover item.")
                
                acao_map = {
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
                # Usa adicionar_produto_generico para aceitar qualquer tipo (produto, receita ou combo)
                from app.api.pedidos.services.service_pedidos_mesa import AdicionarProdutoGenericoRequest

                # Valida que pelo menos um identificador foi enviado
                if not payload.produto_cod_barras and not payload.receita_id and not payload.combo_id:
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        "É necessário informar produto_cod_barras, receita_id ou combo_id"
                    )

                body = AdicionarProdutoGenericoRequest(
                    produto_cod_barras=payload.produto_cod_barras,
                    receita_id=payload.receita_id,
                    combo_id=payload.combo_id,
                    quantidade=payload.quantidade or 1,
                    observacao=payload.observacao,
                    complementos=payload.complementos,
                )
                self.mesa_service.adicionar_produto_generico(pedido_id, body)
                pedido_atualizado = self.repo.get_pedido(pedido_id)
                return self._build_pedido_response(pedido_atualizado)
            elif payload.acao == PedidoItemMutationAction.UPDATE:
                # Agora suporta atualização de itens em pedidos de mesa
                if not payload.item_id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "item_id é obrigatório para atualizar item.")
                return self.mesa_service.atualizar_item(
                    pedido_id=pedido_id,
                    item_id=payload.item_id,
                    quantidade=payload.quantidade,
                    observacao=payload.observacao,
                    complementos=payload.complementos,
                )
            elif payload.acao == PedidoItemMutationAction.REMOVE:
                if not payload.item_id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "item_id é obrigatório para remover item.")
                self.mesa_service.remover_item(pedido_id, payload.item_id)
                pedido_atualizado = self.repo.get_pedido(pedido_id)
                return self._build_pedido_response(pedido_atualizado)
            else:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Ação '{payload.acao}' não suportada para mesa.")

        if tipo == TipoEntregaEnum.BALCAO:
            if payload.acao == PedidoItemMutationAction.ADD:
                # Usa adicionar_produto_generico para aceitar qualquer tipo (produto, receita ou combo)
                from app.api.pedidos.services.service_pedidos_balcao import (
                    AdicionarProdutoGenericoRequest as BalcaoProdutoGenericoRequest,
                )

                # Valida que pelo menos um identificador foi enviado
                if not payload.produto_cod_barras and not payload.receita_id and not payload.combo_id:
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        "É necessário informar produto_cod_barras, receita_id ou combo_id"
                    )

                body = BalcaoProdutoGenericoRequest(
                    produto_cod_barras=payload.produto_cod_barras,
                    receita_id=payload.receita_id,
                    combo_id=payload.combo_id,
                    quantidade=payload.quantidade or 1,
                    observacao=payload.observacao,
                    complementos=payload.complementos,
                )
                self.balcao_service.adicionar_produto_generico(pedido_id, body)
                pedido_atualizado = self.repo.get_pedido(pedido_id)
                return self._build_pedido_response(pedido_atualizado)
            elif payload.acao == PedidoItemMutationAction.UPDATE:
                # Agora suporta atualização de itens em pedidos de balcão
                if not payload.item_id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "item_id é obrigatório para atualizar item.")
                return self.balcao_service.atualizar_item(
                    pedido_id=pedido_id,
                    item_id=payload.item_id,
                    quantidade=payload.quantidade,
                    observacao=payload.observacao,
                    complementos=payload.complementos,
                )
            elif payload.acao == PedidoItemMutationAction.REMOVE:
                if not payload.item_id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "item_id é obrigatório para remover item.")
                self.balcao_service.remover_item(pedido_id, payload.item_id)
                pedido_atualizado = self.repo.get_pedido(pedido_id)
                return self._build_pedido_response(pedido_atualizado)
            else:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Ação '{payload.acao}' não suportada para balcão.")

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

    # ------------------------------------------------------------------ #
    # Troca de tipo (mesa/balcão/delivery)
    # ------------------------------------------------------------------ #
    def trocar_tipo_pedido(
        self,
        *,
        pedido_id: int,
        payload: PedidoTrocarTipoRequest,
        user_id: Optional[int] = None,
    ) -> PedidoResponseCompleto:
        """
        Troca a modalidade do pedido entre DELIVERY, MESA e BALCAO.

        Regras principais:
        - Só permite troca para pedidos em aberto (não CANCELADO/ENTREGUE).
        - Ao trocar para DELIVERY: exige endereco_id e garante cliente_id.
        - Ao trocar para MESA: exige mesa_codigo.
        - Ao trocar para BALCAO: mesa_codigo é opcional.
        - Atualiza mesa (ocupa/libera) conforme necessidade.
        - Recalcula totais/taxas após a troca.
        """
        import asyncio
        import threading
        from decimal import Decimal

        from app.api.cadastros.models.model_mesa import StatusMesa
        from app.api.cadastros.repositories.repo_mesas import MesaRepository
        from app.api.notifications.core.ws_events import WSEvents
        from app.api.notifications.core.websocket_manager import websocket_manager
        from app.api.pedidos.models.model_pedido_historico_unificado import TipoOperacaoPedido
        from app.api.pedidos.models.model_pedido_unificado import TipoEntrega as TipoEntregaModel

        pedido = self._get_pedido(pedido_id)

        status_atual = pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)
        if status_atual in {PedidoStatusEnum.C.value, PedidoStatusEnum.E.value}:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Não é possível trocar o tipo de um pedido cancelado ou entregue.",
            )

        tipo_atual = self._to_tipo_entrega_enum(pedido.tipo_entrega)
        if payload.tipo_pedido == TipoPedidoCheckoutEnum.DELIVERY:
            tipo_novo = TipoEntregaEnum.DELIVERY
        elif payload.tipo_pedido == TipoPedidoCheckoutEnum.MESA:
            tipo_novo = TipoEntregaEnum.MESA
        elif payload.tipo_pedido == TipoPedidoCheckoutEnum.BALCAO:
            tipo_novo = TipoEntregaEnum.BALCAO
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tipo de pedido inválido para troca.")

        # Normaliza dados atuais para comparar
        mesa_repo = MesaRepository(self.db)
        old_mesa_id = getattr(pedido, "mesa_id", None)

        # Resolver mesa_id (quando aplicável)
        new_mesa_id = None
        if tipo_novo == TipoEntregaEnum.MESA:
            try:
                codigo = Decimal(str(payload.mesa_codigo))
            except Exception:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "mesa_codigo inválido.")
            mesa = mesa_repo.get_by_codigo(codigo, empresa_id=int(pedido.empresa_id))
            if mesa is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa não encontrada para a empresa informada.")
            new_mesa_id = int(mesa.id)
        elif tipo_novo == TipoEntregaEnum.BALCAO:
            if payload.mesa_codigo:
                try:
                    codigo = Decimal(str(payload.mesa_codigo))
                except Exception:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "mesa_codigo inválido.")
                mesa = mesa_repo.get_by_codigo(codigo, empresa_id=int(pedido.empresa_id))
                if mesa is None:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa não encontrada para a empresa informada.")
                new_mesa_id = int(mesa.id)

        # Resolver cliente/endereço para delivery
        endereco = None
        if tipo_novo == TipoEntregaEnum.DELIVERY:
            cliente_id_target = int(getattr(pedido, "cliente_id", 0) or 0) or (int(payload.cliente_id) if payload.cliente_id else 0)
            if not cliente_id_target:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "cliente_id é obrigatório para trocar para DELIVERY quando o pedido não possui cliente_id.",
                )
            if payload.endereco_id is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "endereco_id é obrigatório para DELIVERY.")
            endereco = self.repo.get_endereco(int(payload.endereco_id))
            if not endereco:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Endereço não encontrado.")
            if getattr(endereco, "cliente_id", None) is not None and int(endereco.cliente_id) != int(cliente_id_target):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço não pertence ao cliente informado.")

            # Garante cliente_id no pedido
            pedido.cliente_id = int(cliente_id_target)

        # Se não mudou de tipo e também não mudou a mesa/endereço relevante, é idempotente.
        if tipo_atual == tipo_novo:
            if tipo_novo in {TipoEntregaEnum.MESA, TipoEntregaEnum.BALCAO}:
                if int(old_mesa_id or 0) == int(new_mesa_id or 0):
                    pedido_atualizado = self.repo.get_pedido(pedido_id)
                    return self.pedido_service.response_builder.pedido_to_response_completo(pedido_atualizado)
            if tipo_novo == TipoEntregaEnum.DELIVERY:
                if int(getattr(pedido, "endereco_id", 0) or 0) == int(payload.endereco_id or 0):
                    pedido_atualizado = self.repo.get_pedido(pedido_id)
                    return self.pedido_service.response_builder.pedido_to_response_completo(pedido_atualizado)

        # Aplica troca e ajusta campos dependentes
        if tipo_novo == TipoEntregaEnum.DELIVERY:
            pedido.tipo_entrega = TipoEntregaModel.DELIVERY.value
            pedido.mesa_id = None
            # Campos de delivery
            pedido.endereco_id = int(payload.endereco_id)
            pedido.endereco = endereco
            # Limpa campos específicos de mesa/balcão
            pedido.num_pessoas = None
            # Mantém observacoes/observacao_geral como estão (não migrar texto automaticamente)
        else:
            # MESA ou BALCAO
            pedido.tipo_entrega = (
                TipoEntregaModel.MESA.value if tipo_novo == TipoEntregaEnum.MESA else TipoEntregaModel.BALCAO.value
            )
            pedido.mesa_id = new_mesa_id
            # Limpa campos de delivery
            pedido.endereco_id = None
            pedido.endereco = None
            pedido.endereco_snapshot = None
            pedido.endereco_geo = None
            pedido.previsao_entrega = None
            pedido.distancia_km = None
            pedido.entregador_id = None
            # Num pessoas (apenas mesa)
            if tipo_novo == TipoEntregaEnum.MESA and payload.num_pessoas is not None:
                pedido.num_pessoas = int(payload.num_pessoas)
            if tipo_novo == TipoEntregaEnum.BALCAO:
                pedido.num_pessoas = None

        # Se troca envolve mudança de mesa, ocupa/libera conforme necessário
        try:
            if tipo_novo in {TipoEntregaEnum.MESA, TipoEntregaEnum.BALCAO} and new_mesa_id is not None:
                mesa_repo.ocupar_mesa(int(new_mesa_id), empresa_id=int(pedido.empresa_id))
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

        # Recalcula totals (inclui snapshot/geo quando delivery via editar_pedido_parcial-like)
        if tipo_novo == TipoEntregaEnum.DELIVERY:
            # Monta snapshot/geo do endereço (mesma lógica do editar_pedido_parcial)
            try:
                endereco_latitude = float(endereco.latitude) if getattr(endereco, "latitude", None) else None
                endereco_longitude = float(endereco.longitude) if getattr(endereco, "longitude", None) else None
                if endereco_latitude and endereco_longitude:
                    from geoalchemy2 import WKTElement
                    pedido.endereco_geo = WKTElement(
                        f"POINT({endereco_longitude} {endereco_latitude})",
                        srid=4326,
                    )
                else:
                    pedido.endereco_geo = None
                from app.utils.database_utils import now_trimmed
                pedido.endereco_snapshot = {
                    "id": endereco.id,
                    "logradouro": endereco.logradouro,
                    "numero": endereco.numero,
                    "complemento": endereco.complemento,
                    "bairro": endereco.bairro,
                    "cidade": endereco.cidade,
                    "estado": endereco.estado,
                    "cep": endereco.cep,
                    "latitude": endereco_latitude,
                    "longitude": endereco_longitude,
                    "is_principal": endereco.is_principal,
                    "cliente_id": endereco.cliente_id,
                    "snapshot_em": str(now_trimmed()),
                }
            except Exception:
                # Best-effort: não falhar a troca por inconsistência em lat/long
                pedido.endereco_geo = None
                pedido.endereco_snapshot = pedido.endereco_snapshot if isinstance(pedido.endereco_snapshot, dict) else None

        self.db.flush()
        self.pedido_service._recalcular_pedido(pedido)

        # Histórico (sem enum específico para "troca tipo")
        try:
            descricao = f"Tipo do pedido alterado de {tipo_atual.value} para {tipo_novo.value}"
            obs_parts: list[str] = []
            if tipo_novo == TipoEntregaEnum.DELIVERY:
                obs_parts.append(f"endereco_id={int(payload.endereco_id)}")
                obs_parts.append(f"cliente_id={int(pedido.cliente_id)}")
            else:
                if new_mesa_id is not None:
                    obs_parts.append(f"mesa_id={int(new_mesa_id)}")
            self.repo.add_historico(
                pedido_id=pedido.id,
                tipo_operacao=TipoOperacaoPedido.STATUS_ALTERADO,
                descricao=descricao,
                observacoes=" | ".join(obs_parts) if obs_parts else None,
                usuario_id=user_id,
            )
            self.repo.commit()
        except Exception:
            # Não quebra se falhar histórico
            self.repo.commit()

        # Liberação de mesa anterior (se saiu de uma mesa e não há mais pedidos abertos nela)
        def _maybe_liberar_mesa(mesa_id: int | None) -> None:
            if mesa_id is None:
                return
            try:
                pedidos_mesa_abertos = self.repo.list_abertos_by_mesa(
                    int(mesa_id),
                    TipoEntregaModel.MESA,
                    empresa_id=int(pedido.empresa_id),
                )
                pedidos_balcao_abertos = self.repo.list_abertos_by_mesa(
                    int(mesa_id),
                    TipoEntregaModel.BALCAO,
                    empresa_id=int(pedido.empresa_id),
                )
                if len(pedidos_mesa_abertos) == 0 and len(pedidos_balcao_abertos) == 0:
                    mesa_db = mesa_repo.get_by_id(int(mesa_id))
                    if mesa_db and int(getattr(mesa_db, "empresa_id", 0) or 0) == int(pedido.empresa_id):
                        if getattr(mesa_db, "status", None) == StatusMesa.OCUPADA:
                            mesa_repo.liberar_mesa(int(mesa_id), empresa_id=int(pedido.empresa_id))
            except Exception:
                return

        if old_mesa_id is not None:
            # Se o novo tipo não usa a mesa antiga, tenta liberar.
            if tipo_novo == TipoEntregaEnum.DELIVERY or (new_mesa_id is not None and int(new_mesa_id) != int(old_mesa_id)) or (new_mesa_id is None):
                _maybe_liberar_mesa(int(old_mesa_id))

        pedido_atualizado = self.repo.get_pedido(pedido.id)

        # WS: notifica frontend para refetch/atualizar kanban/listas
        try:
            empresa_id_str = str(pedido_atualizado.empresa_id) if pedido_atualizado.empresa_id is not None else ""
            if empresa_id_str:
                tipo_entrega_val = (
                    pedido_atualizado.tipo_entrega.value
                    if hasattr(pedido_atualizado.tipo_entrega, "value")
                    else str(pedido_atualizado.tipo_entrega)
                )
                status_val = (
                    pedido_atualizado.status.value
                    if hasattr(pedido_atualizado.status, "value")
                    else str(pedido_atualizado.status)
                )
                numero_pedido_val = getattr(pedido_atualizado, "numero_pedido", None)
                ws_payload = {
                    "pedido_id": str(pedido_atualizado.id),
                    "tipo_entrega": tipo_entrega_val,
                    "status": status_val,
                }
                if numero_pedido_val:
                    ws_payload["numero_pedido"] = str(numero_pedido_val)

                def _emit_ws() -> None:
                    try:
                        asyncio.run(
                            websocket_manager.emit_event(
                                event=WSEvents.PEDIDO_ATUALIZADO,
                                scope="empresa",
                                empresa_id=empresa_id_str,
                                payload=ws_payload,
                                required_route="/pedidos",
                            )
                        )
                    except Exception:
                        return

                threading.Thread(target=_emit_ws, daemon=True).start()
        except Exception:
            pass

        return self.pedido_service.response_builder.pedido_to_response_completo(pedido_atualizado)


