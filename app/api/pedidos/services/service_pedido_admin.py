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
                itens=[
                    ItemPedidoRequest(
                        produto_cod_barras=item.produto_cod_barras,
                        quantidade=item.quantidade,
                        observacao=item.observacao,
                    )
                    for item in itens_payload
                ],
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
        
        # Valida e atualiza meio de pagamento se fornecido
        if payload and payload.meio_pagamento_id is not None:
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
        
        # IMPORTANTE: Faz commit e refresh ANTES de acessar o relacionamento meio_pagamento
        # Isso garante que o meio_pagamento_id seja persistido e o relacionamento seja atualizado
        if payload and (payload.meio_pagamento_id is not None or payload.troco_para is not None):
            self.db.commit()
            self.db.refresh(pedido)
        
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
        
        # Reseta o campo pago para False ao reabrir
        pedido.pago = False
        
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


