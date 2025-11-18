from __future__ import annotations

from decimal import Decimal
from typing import Optional
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.mesas.repositories.repo_mesas import MesaRepository
from app.api.mesas.repositories.repo_pedidos_mesa import PedidoMesaRepository
from app.api.mesas.models.model_mesa import StatusMesa
from app.api.balcao.repositories.repo_pedidos_balcao import PedidoBalcaoRepository
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.balcao.models.model_pedido_balcao_historico import TipoOperacaoPedidoBalcao
from app.api.balcao.schemas.schema_pedido_balcao import (
    PedidoBalcaoCreate,
    PedidoBalcaoOut,
    AdicionarItemRequest,
    RemoverItemResponse,
    StatusPedidoBalcaoEnum,
    FecharContaBalcaoRequest,
    AtualizarStatusPedidoRequest,
)
from app.api.balcao.schemas.schema_pedido_balcao_historico import (
    PedidoBalcaoHistoricoOut,
    HistoricoPedidoBalcaoResponse,
)


class PedidoBalcaoService:
    def __init__(self, db: Session, produto_contract: IProdutoContract | None = None):
        self.db = db
        self.repo_mesa = MesaRepository(db)
        self.repo_mesa_pedidos = PedidoMesaRepository(db, produto_contract=produto_contract)
        self.repo = PedidoBalcaoRepository(db, produto_contract=produto_contract)

    @staticmethod
    def _status_value(status_obj):
        """Normaliza valor de status para string."""
        if hasattr(status_obj, "value"):
            return status_obj.value
        return status_obj

    # -------- Pedido --------
    def criar_pedido(self, payload: PedidoBalcaoCreate) -> PedidoBalcaoOut:
        # Se mesa_id informado, busca a mesa pelo código
        mesa_id_real = None
        if payload.mesa_id is not None:
            from decimal import Decimal
            try:
                codigo = Decimal(str(payload.mesa_id))
                mesa = self.repo_mesa.get_by_codigo(codigo)
                mesa_id_real = mesa.id
            except Exception as e:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    f"Mesa com código {payload.mesa_id} não encontrada"
                )

        pedido = self.repo.create(
            empresa_id=payload.empresa_id,
            mesa_id=mesa_id_real,
            cliente_id=payload.cliente_id,
            observacoes=payload.observacoes,
        )

        # Registra histórico de criação
        self.repo.add_historico(
            pedido_id=pedido.id,
            tipo_operacao=TipoOperacaoPedidoBalcao.PEDIDO_CRIADO,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} criado",
            cliente_id=payload.cliente_id,
        )
        if mesa_id_real:
            self.repo.add_historico(
                pedido_id=pedido.id,
                tipo_operacao=TipoOperacaoPedidoBalcao.MESA_ASSOCIADA,
                descricao=f"Mesa associada ao pedido",
            )
        self.repo.commit()

        # itens iniciais
        if payload.itens:
            for it in payload.itens:
                self.repo.add_item(
                    pedido.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    observacao=it.observacao,
                )
                # Registra histórico de item adicionado
                self.repo.add_historico(
                    pedido_id=pedido.id,
                    tipo_operacao=TipoOperacaoPedidoBalcao.ITEM_ADICIONADO,
                    descricao=f"Item adicionado: {it.produto_cod_barras} (qtd: {it.quantidade})",
                )
            self.repo.commit()
            pedido = self.repo.get(pedido.id)

        return PedidoBalcaoOut.model_validate(pedido)

    def adicionar_item(self, pedido_id: int, body: AdicionarItemRequest, usuario_id: int | None = None) -> PedidoBalcaoOut:
        pedido = self.repo.get(pedido_id)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        pedido = self.repo.add_item(
            pedido_id,
            produto_cod_barras=body.produto_cod_barras,
            quantidade=body.quantidade,
            observacao=body.observacao,
        )
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedidoBalcao.ITEM_ADICIONADO,
            descricao=f"Item adicionado: {body.produto_cod_barras} (qtd: {body.quantidade})",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return PedidoBalcaoOut.model_validate(pedido)

    def remover_item(self, pedido_id: int, item_id: int, usuario_id: int | None = None) -> RemoverItemResponse:
        pedido = self.repo.get(pedido_id)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        pedido = self.repo.remove_item(pedido_id, item_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedidoBalcao.ITEM_REMOVIDO,
            descricao=f"Item removido: ID {item_id}",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return RemoverItemResponse(ok=True, pedido_id=pedido.id, valor_total=float(pedido.valor_total or 0))

    def cancelar(self, pedido_id: int, usuario_id: int | None = None) -> PedidoBalcaoOut:
        pedido_antes = self.repo.get(pedido_id)
        status_anterior = self._status_value(pedido_antes.status)
        pedido = self.repo.cancelar(pedido_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedidoBalcao.PEDIDO_CANCELADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} cancelado",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return PedidoBalcaoOut.model_validate(pedido)

    def confirmar(self, pedido_id: int, usuario_id: int | None = None) -> PedidoBalcaoOut:
        pedido_antes = self.repo.get(pedido_id)
        status_anterior = self._status_value(pedido_antes.status)
        pedido = self.repo.confirmar(pedido_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedidoBalcao.PEDIDO_CONFIRMADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} confirmado",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return PedidoBalcaoOut.model_validate(pedido)

    def atualizar_status(
        self,
        pedido_id: int,
        payload: AtualizarStatusPedidoRequest,
        usuario_id: int | None = None
    ) -> PedidoBalcaoOut:
        novo_status = payload.status
        if novo_status == StatusPedidoBalcaoEnum.CANCELADO:
            return self.cancelar(pedido_id, usuario_id=usuario_id)
        if novo_status == StatusPedidoBalcaoEnum.ENTREGUE:
            return self.fechar_conta(pedido_id, payload=None, usuario_id=usuario_id)
        if novo_status == StatusPedidoBalcaoEnum.IMPRESSAO:
            return self.confirmar(pedido_id, usuario_id=usuario_id)

        pedido_atual = self.repo.get(pedido_id)
        status_anterior = self._status_value(pedido_atual.status)
        pedido = self.repo.atualizar_status(pedido_id, novo_status)
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedidoBalcao.STATUS_ALTERADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Status atualizado para {self._status_value(pedido.status)}",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return PedidoBalcaoOut.model_validate(pedido)

    def fechar_conta(self, pedido_id: int, payload: FecharContaBalcaoRequest | None = None, usuario_id: int | None = None) -> PedidoBalcaoOut:
        pedido_antes = self.repo.get(pedido_id)
        status_anterior = self._status_value(pedido_antes.status)
        mesa_id = pedido_antes.mesa_id  # Guarda mesa_id antes de fechar
        
        # Se receber payload, anexa dados de pagamento em observacoes
        if payload is not None:
            if payload.troco_para is not None:
                obs = (pedido_antes.observacoes or "").strip()
                complemento = f"Troco para: {payload.troco_para}"
                pedido_antes.observacoes = f"{obs} | {complemento}" if obs else complemento
            if payload.meio_pagamento_id is not None:
                obs = (pedido_antes.observacoes or "").strip()
                complemento = f"Meio pagamento ID: {payload.meio_pagamento_id}"
                pedido_antes.observacoes = f"{obs} | {complemento}" if obs else complemento
            self.db.commit()
            self.db.refresh(pedido_antes)

        # Fecha o pedido (muda status para ENTREGUE)
        pedido = self.repo.fechar_conta(pedido_id)
        
        # Se o pedido tinha mesa associada, verifica se há outros pedidos abertos antes de liberar
        if mesa_id is not None:
            # Verifica pedidos abertos de balcão na mesa
            pedidos_balcao_abertos = self.repo.list_abertos_by_mesa(mesa_id, empresa_id=pedido.empresa_id)
            # Verifica pedidos abertos de mesa na mesa
            pedidos_mesa_abertos = self.repo_mesa_pedidos.list_abertos_by_mesa(mesa_id, empresa_id=pedido.empresa_id)
            
            # Só libera a mesa se não houver mais nenhum pedido aberto (nem de balcão nem de mesa)
            if len(pedidos_balcao_abertos) == 0 and len(pedidos_mesa_abertos) == 0:
                mesa = self.repo_mesa.get_by_id(mesa_id, empresa_id=pedido.empresa_id)
                if mesa.status == StatusMesa.OCUPADA:
                    self.repo_mesa.liberar_mesa(mesa_id, empresa_id=pedido.empresa_id)
        
        # Registra histórico
        observacoes_historico = None
        if payload:
            if payload.meio_pagamento_id:
                observacoes_historico = f"Meio pagamento: {payload.meio_pagamento_id}"
            if payload.troco_para:
                observacoes_historico = (observacoes_historico or "") + f" | Troco para: {payload.troco_para}"
        
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedidoBalcao.PEDIDO_FECHADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} fechado",
            observacoes=observacoes_historico,
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return PedidoBalcaoOut.model_validate(pedido)

    def reabrir(self, pedido_id: int, usuario_id: int | None = None) -> PedidoBalcaoOut:
        pedido_antes = self.repo.get(pedido_id)
        status_anterior = self._status_value(pedido_antes.status)
        pedido = self.repo.reabrir(pedido_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedidoBalcao.PEDIDO_REABERTO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} reaberto",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return PedidoBalcaoOut.model_validate(pedido)

    # Fluxo cliente
    def fechar_conta_cliente(self, pedido_id: int, cliente_id: int, payload: FecharContaBalcaoRequest) -> PedidoBalcaoOut:
        pedido = self.repo.get(pedido_id)
        if pedido.cliente_id and pedido.cliente_id != cliente_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Pedido não pertence ao cliente")

        status_anterior = self._status_value(pedido.status)
        mesa_id = pedido.mesa_id  # Guarda mesa_id antes de fechar

        # Aplica informações de pagamento no pedido
        if payload.troco_para is not None:
            obs = (pedido.observacoes or "").strip()
            complemento = f"Troco para: {payload.troco_para}"
            pedido.observacoes = f"{obs} | {complemento}" if obs else complemento

        if payload.meio_pagamento_id is not None:
            obs = (pedido.observacoes or "").strip()
            complemento = f"Meio pagamento ID: {payload.meio_pagamento_id}"
            pedido.observacoes = f"{obs} | {complemento}" if obs else complemento

        self.db.commit()
        self.db.refresh(pedido)

        # Fecha o pedido (muda status para ENTREGUE)
        pedido = self.repo.fechar_conta(pedido_id)
        
        # Se o pedido tinha mesa associada, verifica se há outros pedidos abertos antes de liberar
        if mesa_id is not None:
            # Verifica pedidos abertos de balcão na mesa
            pedidos_balcao_abertos = self.repo.list_abertos_by_mesa(mesa_id, empresa_id=pedido.empresa_id)
            # Verifica pedidos abertos de mesa na mesa
            pedidos_mesa_abertos = self.repo_mesa_pedidos.list_abertos_by_mesa(mesa_id, empresa_id=pedido.empresa_id)
            
            # Só libera a mesa se não houver mais nenhum pedido aberto (nem de balcão nem de mesa)
            if len(pedidos_balcao_abertos) == 0 and len(pedidos_mesa_abertos) == 0:
                mesa = self.repo_mesa.get_by_id(mesa_id, empresa_id=pedido.empresa_id)
                if mesa.status == StatusMesa.OCUPADA:
                    self.repo_mesa.liberar_mesa(mesa_id, empresa_id=pedido.empresa_id)
        
        # Registra histórico (cliente fechou conta)
        observacoes_historico = None
        if payload.meio_pagamento_id:
            observacoes_historico = f"Meio pagamento: {payload.meio_pagamento_id}"
        if payload.troco_para:
            observacoes_historico = (observacoes_historico or "") + f" | Troco para: {payload.troco_para}"
        
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedidoBalcao.PEDIDO_FECHADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} fechado pelo cliente",
            observacoes=observacoes_historico,
            cliente_id=cliente_id,
        )
        self.repo.commit()
        return PedidoBalcaoOut.model_validate(pedido)

    # -------- Consultas --------
    def get_pedido(self, pedido_id: int) -> PedidoBalcaoOut:
        pedido = self.repo.get(pedido_id)
        return PedidoBalcaoOut.model_validate(pedido)

    def list_pedidos_abertos(self, *, empresa_id: Optional[int] = None) -> list[PedidoBalcaoOut]:
        pedidos = self.repo.list_abertos_all(empresa_id=empresa_id)
        return [PedidoBalcaoOut.model_validate(p) for p in pedidos]

    def list_pedidos_finalizados(self, data_filtro: Optional[date] = None, *, empresa_id: Optional[int] = None) -> list[PedidoBalcaoOut]:
        """Retorna todos os pedidos finalizados (ENTREGUE), opcionalmente filtrando por data"""
        pedidos = self.repo.list_finalizados(data_filtro, empresa_id=empresa_id)
        return [PedidoBalcaoOut.model_validate(p) for p in pedidos]

    def list_pedidos_by_cliente(self, cliente_id: int, *, empresa_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> list[PedidoBalcaoOut]:
        """Lista todos os pedidos de balcão de um cliente específico"""
        pedidos = self.repo.list_by_cliente_id(cliente_id, empresa_id=empresa_id, skip=skip, limit=limit)
        return [PedidoBalcaoOut.model_validate(p) for p in pedidos]

    # -------- Histórico --------
    def get_historico(self, pedido_id: int, limit: int = 100) -> HistoricoPedidoBalcaoResponse:
        """Busca histórico completo de um pedido de balcão"""
        # Verifica se o pedido existe
        pedido = self.repo.get(pedido_id)
        
        # Busca histórico
        historicos = self.repo.get_historico(pedido_id, limit)
        
        # Converte para schema incluindo nome do usuário
        historicos_out = []
        for h in historicos:
            hist_dict = PedidoBalcaoHistoricoOut.model_validate(h).model_dump()
            # Adiciona nome do usuário se disponível
            if h.usuario:
                hist_dict["usuario"] = h.usuario.nome
            historicos_out.append(PedidoBalcaoHistoricoOut(**hist_dict))
        
        return HistoricoPedidoBalcaoResponse(
            pedido_id=pedido_id,
            historicos=historicos_out
        )

