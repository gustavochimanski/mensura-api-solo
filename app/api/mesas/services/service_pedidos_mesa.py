from __future__ import annotations

from decimal import Decimal
from typing import Optional
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.mesas.models.model_mesa import StatusMesa
from app.api.mesas.repositories.repo_mesas import MesaRepository
from app.api.mesas.repositories.repo_pedidos_mesa import PedidoMesaRepository
from app.api.balcao.repositories.repo_pedidos_balcao import PedidoBalcaoRepository
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.catalogo.contracts.adicional_contract import IAdicionalContract
from app.api.mesas.schemas.schema_pedido_mesa import (
    PedidoMesaCreate,
    PedidoMesaOut,
    PedidoMesaItemIn,
    AdicionarItemRequest,
    RemoverItemResponse,
    StatusPedidoMesaEnum,
    FecharContaMesaRequest,
    AtualizarObservacoesRequest,
    AtualizarStatusPedidoRequest,
)
from app.utils.logger import logger


class PedidoMesaService:
    def __init__(
        self,
        db: Session,
        produto_contract: IProdutoContract | None = None,
        adicional_contract: IAdicionalContract | None = None,
    ):
        self.db = db
        self.repo_mesa = MesaRepository(db)
        self.repo = PedidoMesaRepository(db, produto_contract=produto_contract)
        self.repo_balcao = PedidoBalcaoRepository(db, produto_contract=produto_contract)

    # -------- Pedido --------
    def criar_pedido(self, payload: PedidoMesaCreate) -> PedidoMesaOut:
        # Busca mesa pelo código ao invés do ID
        # payload.mesa_id agora representa o código da mesa
        from decimal import Decimal
        try:
            codigo = Decimal(str(payload.mesa_id))
            mesa = self.repo_mesa.get_by_codigo(codigo, empresa_id=payload.empresa_id)
        except Exception as e:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Mesa com código {payload.mesa_id} não encontrada"
            )
        
        # Usa o ID real da mesa encontrada
        mesa_id_real = mesa.id
        if mesa.empresa_id != payload.empresa_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Mesa não pertence à empresa informada."
            )
        # Valida num_pessoas contra capacidade da mesa, quando informado
        if payload.num_pessoas is not None and payload.num_pessoas > (mesa.capacidade or 0):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Número de pessoas excede a capacidade da mesa"
            )
        # Se a mesa não estiver ocupada, ocupa automaticamente ao abrir o pedido
        if mesa.status != StatusMesa.OCUPADA:
            self.repo_mesa.ocupar_mesa(mesa_id_real, empresa_id=payload.empresa_id)

        pedido = self.repo.create(
            mesa_id=mesa_id_real,
            empresa_id=payload.empresa_id,
            cliente_id=payload.cliente_id,
            observacoes=payload.observacoes,
            num_pessoas=payload.num_pessoas,
        )

        # itens iniciais
        if payload.itens:
            for it in payload.itens:
                self.repo.add_item(
                    pedido.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    observacao=it.observacao,
                )
            pedido = self.repo.get(pedido.id)

        return PedidoMesaOut.model_validate(pedido)

    def adicionar_item(self, pedido_id: int, body: AdicionarItemRequest) -> PedidoMesaOut:
        pedido = self.repo.get(pedido_id)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        pedido = self.repo.add_item(
            pedido_id,
            produto_cod_barras=body.produto_cod_barras,
            quantidade=body.quantidade,
            observacao=body.observacao,
        )
        return PedidoMesaOut.model_validate(pedido)

    def remover_item(self, pedido_id: int, item_id: int) -> RemoverItemResponse:
        pedido = self.repo.get(pedido_id)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        pedido = self.repo.remove_item(pedido_id, item_id)
        return RemoverItemResponse(ok=True, pedido_id=pedido.id, valor_total=float(pedido.valor_total or 0))

    def cancelar(self, pedido_id: int) -> PedidoMesaOut:
        # Obtém o pedido antes de cancelar para pegar o mesa_id
        pedido_antes = self.repo.get(pedido_id)
        mesa_id = pedido_antes.mesa_id
        
        # Cancela o pedido (muda status para CANCELADO)
        pedido = self.repo.cancelar(pedido_id)

        
        # IMPORTANTE: Força refresh da sessão para garantir que a query veja o status atualizado
        self.db.expire_all()
        
        # IMPORTANTE: Não muda o status da mesa imediatamente ao cancelar o pedido
        # Verifica se ainda há outros pedidos abertos nesta mesa (tanto de mesa quanto de balcão)
        # O pedido que acabou de ser cancelado já não será contado (status CANCELADO)
        pedidos_mesa_abertos = self.repo.list_abertos_by_mesa(mesa_id, empresa_id=pedido_antes.empresa_id)
        pedidos_balcao_abertos = self.repo_balcao.list_abertos_by_mesa(mesa_id, empresa_id=pedido_antes.empresa_id)
        
        logger.info(
            f"[Pedidos Mesa] Cancelar - pedido_id={pedido_id}, mesa_id={mesa_id}, "
            f"pedidos_mesa_abertos={len(pedidos_mesa_abertos)}, pedidos_balcao_abertos={len(pedidos_balcao_abertos)}"
        )
        
        # Só libera a mesa se realmente não houver mais nenhum pedido em aberto (nem de mesa nem de balcão)
        if len(pedidos_mesa_abertos) == 0 and len(pedidos_balcao_abertos) == 0:
            # Verifica se a mesa está ocupada antes de liberar
            mesa = self.repo_mesa.get_by_id(mesa_id, empresa_id=pedido_antes.empresa_id)
            if mesa.status == StatusMesa.OCUPADA:
                logger.info(f"[Pedidos Mesa] Liberando mesa automaticamente (cancelar) - mesa_id={mesa_id} (sem pedidos abertos)")
                self.repo_mesa.liberar_mesa(mesa_id, empresa_id=pedido_antes.empresa_id)
        else:
            logger.info(
                f"[Pedidos Mesa] Mesa NÃO liberada (cancelar) - mesa_id={mesa_id} "
                f"(ainda há {len(pedidos_mesa_abertos)} pedidos de mesa e {len(pedidos_balcao_abertos)} de balcão abertos)"
            )
        
        return PedidoMesaOut.model_validate(pedido)

    def confirmar(self, pedido_id: int) -> PedidoMesaOut:
        pedido = self.repo.confirmar(pedido_id)
        return PedidoMesaOut.model_validate(pedido)

    def atualizar_status(self, pedido_id: int, payload: AtualizarStatusPedidoRequest) -> PedidoMesaOut:
        novo_status = payload.status
        if novo_status == StatusPedidoMesaEnum.CANCELADO:
            return self.cancelar(pedido_id)
        if novo_status == StatusPedidoMesaEnum.ENTREGUE:
            return self.fechar_conta(pedido_id, None)
        if novo_status == StatusPedidoMesaEnum.IMPRESSAO:
            return self.confirmar(pedido_id)
        pedido = self.repo.atualizar_status(pedido_id, novo_status)
        return PedidoMesaOut.model_validate(pedido)

    def fechar_conta(self, pedido_id: int, payload: FecharContaMesaRequest | None = None) -> PedidoMesaOut:
        # Obtém o pedido antes de fechar para pegar o mesa_id
        pedido_antes = self.repo.get(pedido_id)
        mesa_id = pedido_antes.mesa_id
        
        # Se receber payload, anexa dados de pagamento em observacoes (modelo não tem colunas próprias)
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
        
        # IMPORTANTE: Força refresh da sessão para garantir que a query veja o status atualizado
        self.db.expire_all()
        
        # IMPORTANTE: Não muda o status da mesa imediatamente ao fechar a conta
        # Verifica se ainda há outros pedidos abertos nesta mesa (tanto de mesa quanto de balcão)
        # O pedido que acabou de ser fechado já não será contado (status ENTREGUE)
        pedidos_mesa_abertos = self.repo.list_abertos_by_mesa(mesa_id, empresa_id=pedido_antes.empresa_id)
        pedidos_balcao_abertos = self.repo_balcao.list_abertos_by_mesa(mesa_id, empresa_id=pedido_antes.empresa_id)
        
        logger.info(
            f"[Pedidos Mesa] Fechar conta - pedido_id={pedido_id}, mesa_id={mesa_id}, "
            f"pedidos_mesa_abertos={len(pedidos_mesa_abertos)}, pedidos_balcao_abertos={len(pedidos_balcao_abertos)}"
        )
        
        # Só libera a mesa se realmente não houver mais nenhum pedido em aberto (nem de mesa nem de balcão)
        if len(pedidos_mesa_abertos) == 0 and len(pedidos_balcao_abertos) == 0:
            # Verifica se a mesa está ocupada antes de liberar
            mesa = self.repo_mesa.get_by_id(mesa_id, empresa_id=pedido_antes.empresa_id)
            if mesa.status == StatusMesa.OCUPADA:
                logger.info(f"[Pedidos Mesa] Liberando mesa automaticamente - mesa_id={mesa_id} (sem pedidos abertos)")
                self.repo_mesa.liberar_mesa(mesa_id, empresa_id=pedido_antes.empresa_id)
        else:
            logger.info(
                f"[Pedidos Mesa] Mesa NÃO liberada - mesa_id={mesa_id} "
                f"(ainda há {len(pedidos_mesa_abertos)} pedidos de mesa e {len(pedidos_balcao_abertos)} de balcão abertos)"
            )
        
        return PedidoMesaOut.model_validate(pedido)

    def reabrir(self, pedido_id: int) -> PedidoMesaOut:
        pedido = self.repo.reabrir(pedido_id)
        logger.info(f"[Pedidos Mesa] Reabrindo pedido - pedido_id={pedido_id}, novo_status=PENDENTE, mesa_id={pedido.mesa_id}")
        # Ao reabrir o pedido, garantir que a mesa vinculada esteja marcada como OCUPADA
        self.repo_mesa.ocupar_mesa(pedido.mesa_id, empresa_id=pedido.empresa_id)
        return PedidoMesaOut.model_validate(pedido)

    # Fluxo cliente
    def fechar_conta_cliente(self, pedido_id: int, cliente_id: int, payload: FecharContaMesaRequest) -> PedidoMesaOut:
        pedido = self.repo.get(pedido_id)
        if pedido.cliente_id and pedido.cliente_id != cliente_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Pedido não pertence ao cliente")

        # Aplica informações simples de pagamento no pedido (campos disponíveis no modelo atual)
        if payload.troco_para is not None:
            # Append/define observação com troco
            obs = (pedido.observacoes or "").strip()
            complemento = f"Troco para: {payload.troco_para}"
            pedido.observacoes = f"{obs} | {complemento}" if obs else complemento

        # Observação com meio_pagamento_id (sem coluna específica no modelo de mesas)
        if payload.meio_pagamento_id is not None:
            obs = (pedido.observacoes or "").strip()
            complemento = f"Meio pagamento ID: {payload.meio_pagamento_id}"
            pedido.observacoes = f"{obs} | {complemento}" if obs else complemento

        self.db.commit()
        self.db.refresh(pedido)

        # Obtém o mesa_id antes de fechar
        mesa_id = pedido.mesa_id

        # Fecha pedido (muda status para ENTREGUE)
        pedido = self.repo.fechar_conta(pedido_id)
        
        # IMPORTANTE: Força refresh da sessão para garantir que a query veja o status atualizado
        self.db.expire_all()
        
        # IMPORTANTE: Não muda o status da mesa imediatamente ao fechar a conta
        # Verifica se ainda há outros pedidos abertos nesta mesa (tanto de mesa quanto de balcão)
        pedidos_mesa_abertos = self.repo.list_abertos_by_mesa(mesa_id, empresa_id=pedido.empresa_id)
        pedidos_balcao_abertos = self.repo_balcao.list_abertos_by_mesa(mesa_id, empresa_id=pedido.empresa_id)
        
        logger.info(
            f"[Pedidos Mesa] Fechar conta cliente - pedido_id={pedido_id}, mesa_id={mesa_id}, "
            f"pedidos_mesa_abertos={len(pedidos_mesa_abertos)}, pedidos_balcao_abertos={len(pedidos_balcao_abertos)}"
        )
        
        # Só libera a mesa se realmente não houver mais nenhum pedido em aberto (nem de mesa nem de balcão)
        if len(pedidos_mesa_abertos) == 0 and len(pedidos_balcao_abertos) == 0:
            # Verifica se a mesa está ocupada antes de liberar
            mesa = self.repo_mesa.get_by_id(mesa_id, empresa_id=pedido.empresa_id)
            if mesa.status == StatusMesa.OCUPADA:
                logger.info(f"[Pedidos Mesa] Liberando mesa automaticamente (cliente) - mesa_id={mesa_id} (sem pedidos abertos)")
                self.repo_mesa.liberar_mesa(mesa_id, empresa_id=pedido.empresa_id)
        else:
            logger.info(
                f"[Pedidos Mesa] Mesa NÃO liberada (cliente) - mesa_id={mesa_id} "
                f"(ainda há {len(pedidos_mesa_abertos)} pedidos de mesa e {len(pedidos_balcao_abertos)} de balcão abertos)"
            )
        
        return PedidoMesaOut.model_validate(pedido)

    # -------- Consultas --------
    def get_pedido(self, pedido_id: int) -> PedidoMesaOut:
        pedido = self.repo.get(pedido_id)
        return PedidoMesaOut.model_validate(pedido)

    def list_pedidos_abertos(self, empresa_id: int, mesa_id: Optional[int] = None) -> list[PedidoMesaOut]:
        if mesa_id is not None:
            pedidos = self.repo.list_abertos_by_mesa(mesa_id, empresa_id=empresa_id)
        else:
            pedidos = self.repo.list_abertos_all(empresa_id=empresa_id)
        return [PedidoMesaOut.model_validate(p) for p in pedidos]

    def list_pedidos_finalizados(self, mesa_id: int, data_filtro: Optional[date] = None, *, empresa_id: int) -> list[PedidoMesaOut]:
        """Retorna todos os pedidos finalizados (ENTREGUE) de uma mesa, opcionalmente filtrando por data"""
        # Valida se a mesa existe
        self.repo_mesa.get_by_id(mesa_id, empresa_id=empresa_id)
        pedidos = self.repo.list_finalizados_by_mesa(mesa_id, data_filtro, empresa_id=empresa_id)
        return [PedidoMesaOut.model_validate(p) for p in pedidos]

    def list_pedidos_by_cliente(self, cliente_id: int, *, empresa_id: int, skip: int = 0, limit: int = 50) -> list[PedidoMesaOut]:
        """Lista todos os pedidos de mesa/balcão de um cliente específico"""
        pedidos = self.repo.list_by_cliente_id(cliente_id, skip=skip, limit=limit, empresa_id=empresa_id)
        return [PedidoMesaOut.model_validate(p) for p in pedidos]

    def atualizar_observacoes(self, pedido_id: int, payload: AtualizarObservacoesRequest) -> PedidoMesaOut:
        """Atualiza as observações de um pedido"""
        pedido = self.repo.get(pedido_id)
        pedido.observacoes = payload.observacoes
        self.db.commit()
        self.db.refresh(pedido)
        return PedidoMesaOut.model_validate(pedido)


