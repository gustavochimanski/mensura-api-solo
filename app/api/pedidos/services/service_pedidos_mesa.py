from __future__ import annotations

from decimal import Decimal
from typing import Optional
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.cadastros.models.model_mesa import StatusMesa
from app.api.cadastros.repositories.repo_mesas import MesaRepository
from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.pedidos.models.model_pedido_unificado import TipoEntrega
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.catalogo.contracts.adicional_contract import IAdicionalContract
from app.api.catalogo.contracts.complemento_contract import IComplementoContract
from app.api.catalogo.contracts.combo_contract import IComboContract
from app.api.pedidos.schemas.schema_pedido import (
    ItemPedidoRequest,
    ReceitaPedidoRequest,
    ComboPedidoRequest,
    PedidoResponseCompleto,
    ItemComplementoRequest,
)
from app.api.pedidos.services.service_pedido_responses import PedidoResponseBuilder
from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum
from app.api.pedidos.models.model_pedido_unificado import StatusPedido
from app.api.pedidos.models.model_pedido_historico_unificado import TipoOperacaoPedido
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal as PyDecimal


# Schemas de request para pedidos de mesa
class PedidoMesaCreate(BaseModel):
    empresa_id: int
    mesa_id: int  # Código da mesa
    cliente_id: Optional[int] = None
    observacoes: Optional[str] = None
    num_pessoas: Optional[int] = None
    itens: Optional[List[ItemPedidoRequest]] = None
    receitas: Optional[List[ReceitaPedidoRequest]] = None
    combos: Optional[List[ComboPedidoRequest]] = None


class AdicionarItemRequest(BaseModel):
    produto_cod_barras: str
    quantidade: int
    observacao: Optional[str] = None


class AdicionarProdutoGenericoRequest(BaseModel):
    produto_cod_barras: Optional[str] = None
    receita_id: Optional[int] = None
    combo_id: Optional[int] = None
    quantidade: int = 1
    observacao: Optional[str] = None
    complementos: Optional[List[ItemComplementoRequest]] = None


class RemoverItemResponse(BaseModel):
    ok: bool
    pedido_id: int
    valor_total: float


class FecharContaMesaRequest(BaseModel):
    meio_pagamento_id: Optional[int] = None
    troco_para: Optional[float] = None


class AtualizarObservacoesRequest(BaseModel):
    observacoes: str


class AtualizarStatusPedidoRequest(BaseModel):
    status: PedidoStatusEnum
from app.api.catalogo.models.model_receita import ReceitaModel
from app.api.catalogo.models.model_combo import ComboModel
from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
from app.api.pedidos.utils.complementos import resolve_produto_complementos, resolve_complementos_diretos
from app.api.pedidos.services.service_pedido_helpers import _dec
from app.utils.logger import logger
from app.api.catalogo.core import ProductCore
from app.api.catalogo.adapters.produto_adapter import ProdutoAdapter
from app.api.catalogo.adapters.combo_adapter import ComboAdapter
from app.api.catalogo.adapters.complemento_adapter import ComplementoAdapter


class PedidoMesaService:
    def __init__(
        self,
        db: Session,
        produto_contract: IProdutoContract | None = None,
        adicional_contract: IAdicionalContract | None = None,
        complemento_contract: IComplementoContract | None = None,
        combo_contract: IComboContract | None = None,
    ):
        self.db = db
        self.repo_mesa = MesaRepository(db)
        self.repo = PedidoRepository(db, produto_contract=produto_contract)
        self.produto_contract = produto_contract
        self.adicional_contract = adicional_contract
        self.complemento_contract = complemento_contract
        self.combo_contract = combo_contract
        
        # Inicializa ProductCore com os adapters
        # Se os contracts não foram fornecidos, cria os adapters
        produto_adapter = produto_contract if produto_contract else ProdutoAdapter(db)
        combo_adapter = combo_contract if combo_contract else ComboAdapter(db)
        complemento_adapter = complemento_contract if complemento_contract else ComplementoAdapter(db)
        
        self.product_core = ProductCore(
            produto_contract=produto_adapter,
            combo_contract=combo_adapter,
            complemento_contract=complemento_adapter,
        )

    # -------- Pedido --------
    def criar_pedido(self, payload: PedidoMesaCreate) -> PedidoResponseCompleto:
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
        
        # Valida se a mesa foi encontrada
        if mesa is None:
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

        pedido = self.repo.criar_pedido_mesa(
            mesa_id=mesa_id_real,
            empresa_id=payload.empresa_id,
            cliente_id=payload.cliente_id,
            observacoes=payload.observacoes,
            num_pessoas=payload.num_pessoas,
        )

        # itens iniciais (produtos normais)
        if payload.itens:
            for it in payload.itens:
                empresa_id = payload.empresa_id
                qtd = max(int(it.quantidade or 1), 1)
                
                # Busca produto usando ProductCore
                product = self.product_core.buscar_qualquer(
                    empresa_id=empresa_id,
                    cod_barras=it.produto_cod_barras,
                    combo_id=None,
                    receita_id=None,
                    receita_model=None,
                )
                
                if not product:
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND,
                        f"Produto não encontrado: {it.produto_cod_barras}"
                    )
                
                # Valida disponibilidade
                if not self.product_core.validar_disponivel(product, qtd):
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        "Produto não disponível"
                    )
                
                # Adiciona item
                self.repo.add_item(
                    pedido.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=qtd,
                    # IMPORTANTE: preco_unitario deve ser apenas o preço BASE (sem complementos).
                    # Os complementos são persistidos relacionalmente e somados no total via _calc_item_total.
                    preco_unitario=product.get_preco_venda(),
                    observacao=it.observacao,
                    complementos=it.complementos if it.complementos else None,
                )
            self.repo.commit()
        
        # receitas iniciais
        if payload.receitas:
            for receita_req in payload.receitas:
                empresa_id = payload.empresa_id
                qtd = max(int(receita_req.quantidade or 1), 1)
                
                # Busca receita do banco
                receita_model = self.db.query(ReceitaModel).filter(ReceitaModel.id == receita_req.receita_id).first()
                if not receita_model:
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND,
                        f"Receita não encontrada: {receita_req.receita_id}"
                    )
                
                # Busca receita usando ProductCore
                product = self.product_core.buscar_qualquer(
                    empresa_id=empresa_id,
                    cod_barras=None,
                    combo_id=None,
                    receita_id=receita_req.receita_id,
                    receita_model=receita_model,
                )
                
                if not product:
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND,
                        f"Receita não encontrada: {receita_req.receita_id}"
                    )
                
                # Valida disponibilidade
                if not self.product_core.validar_disponivel(product, qtd):
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        "Receita não disponível"
                    )
                
                # IMPORTANTE: preco_unitario deve ser apenas o preço BASE (sem complementos).
                # Os complementos são persistidos relacionalmente e somados no total via _calc_item_total.
                preco_unitario = product.get_preco_venda()
                descricao_produto = product.nome or product.descricao or ""
                
                # Adiciona item
                self.repo.add_item(
                    pedido.id,
                    receita_id=receita_req.receita_id,
                    quantidade=qtd,
                    preco_unitario=preco_unitario,
                    observacao=receita_req.observacao,
                    produto_descricao_snapshot=descricao_produto,
                    complementos=receita_req.complementos if receita_req.complementos else None,
                )
            self.repo.commit()
        
        # combos iniciais
        if payload.combos:
            for combo_req in payload.combos:
                empresa_id = payload.empresa_id
                qtd = max(int(combo_req.quantidade or 1), 1)
                
                # Busca combo usando ProductCore
                product = self.product_core.buscar_qualquer(
                    empresa_id=empresa_id,
                    cod_barras=None,
                    combo_id=combo_req.combo_id,
                    receita_id=None,
                    receita_model=None,
                )
                
                if not product:
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND,
                        f"Combo não encontrado: {combo_req.combo_id}"
                    )
                
                # Valida disponibilidade
                if not self.product_core.validar_disponivel(product, qtd):
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        "Combo não disponível"
                    )
                
                # IMPORTANTE: preco_unitario deve ser apenas o preço BASE (sem complementos).
                # Os complementos são persistidos relacionalmente e somados no total via _calc_item_total.
                preco_unitario = product.get_preco_venda()
                descricao_produto = product.nome or product.descricao or ""
                
                # Monta observação completa para combos
                observacao_completa = f"Combo #{product.identifier} - {descricao_produto}"
                
                # Adiciona item
                self.repo.add_item(
                    pedido.id,
                    combo_id=combo_req.combo_id,
                    quantidade=qtd,
                    preco_unitario=preco_unitario,
                    observacao=observacao_completa,
                    produto_descricao_snapshot=descricao_produto,
                    complementos=combo_req.complementos if combo_req.complementos else None,
                )
            self.repo.commit()
        
        # Recarrega pedido com todos os itens
        pedido = self.repo.get(pedido.id, TipoEntrega.MESA)

        # Registra histórico (mesa) - pedido criado
        status_novo = pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)
        self.repo.add_historico(
            pedido_id=pedido.id,
            tipo_operacao=TipoOperacaoPedido.PEDIDO_CRIADO,
            status_anterior=None,
            status_novo=status_novo,
            descricao=f"Pedido {pedido.numero_pedido} criado",
            cliente_id=payload.cliente_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido.id, TipoEntrega.MESA)

        # Notifica novo pedido em background
        try:
            import asyncio
            from app.api.pedidos.utils.pedido_notification_helper import notificar_novo_pedido
            # Recarrega pedido com todos os relacionamentos para a notificação
            pedido_completo = self.repo.get(pedido.id, TipoEntrega.MESA)
            if pedido_completo:
                asyncio.create_task(notificar_novo_pedido(pedido_completo))
        except Exception as e:
            # Loga erro mas não quebra o fluxo
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao agendar notificação de novo pedido {pedido.id}: {e}")

        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def adicionar_item(self, pedido_id: int, body: AdicionarItemRequest) -> PedidoResponseCompleto:
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        pedido = self.repo.add_item(
            pedido_id,
            produto_cod_barras=body.produto_cod_barras,
            quantidade=body.quantidade,
            observacao=body.observacao,
        )
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def adicionar_produto_generico(
        self, 
        pedido_id: int, 
        body: AdicionarProdutoGenericoRequest
    ) -> PedidoResponseCompleto:
        """
        Adiciona um produto genérico ao pedido (produto normal, receita ou combo).
        Identifica automaticamente o tipo baseado nos campos preenchidos.
        
        Usa ProductCore para unificar o tratamento de diferentes tipos de produtos.
        """
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        
        empresa_id = pedido.empresa_id
        qtd = max(int(body.quantidade or 1), 1)
        
        # Busca receita do banco se necessário (para passar ao ProductCore)
        receita_model = None
        if body.receita_id:
            receita_model = self.db.query(ReceitaModel).filter(ReceitaModel.id == body.receita_id).first()
        
        # Usa ProductCore para buscar e validar qualquer tipo de produto
        product = self.product_core.buscar_qualquer(
            empresa_id=empresa_id,
            cod_barras=body.produto_cod_barras,
            combo_id=body.combo_id,
            receita_id=body.receita_id,
            receita_model=receita_model,
        )
        
        if not product:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "Produto não encontrado"
            )
        
        # Valida disponibilidade usando ProductCore
        if not self.product_core.validar_disponivel(product, qtd):
            tipo_nome = product.product_type.value
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"{tipo_nome.capitalize()} não disponível"
            )
        
        # Valida empresa usando ProductCore
        if not self.product_core.validar_empresa(product, empresa_id):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Produto não pertence à empresa {empresa_id}"
            )
        
        # IMPORTANTE: preco_unitario deve ser apenas o preço BASE do produto (sem complementos)
        # Os complementos são somados separadamente via _sum_complementos_total_relacional
        # para evitar duplicação no cálculo do total do item
        preco_unitario = product.get_preco_venda()
        descricao_produto = product.nome or product.descricao or ""
        
        # Monta observação completa
        observacao_completa = body.observacao
        if product.product_type.value == "combo":
            observacao_completa = f"Combo #{product.identifier} - {descricao_produto}"
            if body.observacao:
                observacao_completa += f" | {body.observacao}"
        elif product.product_type.value == "receita":
            observacao_completa = f"Receita #{product.identifier} - {descricao_produto}"
            if body.observacao:
                observacao_completa += f" | {body.observacao}"
        
        # Adiciona item ao pedido baseado no tipo
        if product.product_type.value == "produto":
            pedido = self.repo.add_item(
                pedido_id,
                produto_cod_barras=str(product.identifier),
                quantidade=qtd,
                observacao=observacao_completa,
                complementos=body.complementos if body.complementos else None,
            )
            
        elif product.product_type.value == "receita":
            pedido = self.repo.add_item(
                pedido_id,
                receita_id=int(product.identifier),
                quantidade=qtd,
                preco_unitario=preco_unitario,
                observacao=observacao_completa,
                produto_descricao_snapshot=descricao_produto,
                complementos=body.complementos if body.complementos else None,
            )
            
        elif product.product_type.value == "combo":
            pedido = self.repo.add_item(
                pedido_id,
                combo_id=int(product.identifier),
                quantidade=qtd,
                preco_unitario=preco_unitario,
                observacao=observacao_completa,
                produto_descricao_snapshot=descricao_produto,
                complementos=body.complementos if body.complementos else None,
            )
        
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Tipo de produto não suportado"
            )
        
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def atualizar_item(
        self,
        pedido_id: int,
        item_id: int,
        quantidade: Optional[int] = None,
        observacao: Optional[str] = None,
        complementos: Optional[List[ItemComplementoRequest]] = None,
        usuario_id: int | None = None
    ) -> PedidoResponseCompleto:
        """
        Atualiza um item do pedido de mesa.
        Permite atualizar quantidade, observação e complementos.
        """
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        
        # Busca o item
        item_db = self.repo.get_item_by_id(item_id)
        if not item_db:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Item {item_id} não encontrado")
        
        if item_db.pedido_id != pedido_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Item {item_id} não pertence ao pedido {pedido_id}")
        
        quantidade_alterada = False
        
        # Atualiza quantidade se fornecida
        if quantidade is not None and quantidade != item_db.quantidade:
            if quantidade <= 0:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Quantidade deve ser maior que zero")
            item_db.quantidade = quantidade
            quantidade_alterada = True
        
        # Atualiza observação se fornecida
        if observacao is not None:
            item_db.observacao = observacao
        
        # Processa complementos se fornecidos
        if complementos is not None:
            # Remove complementos antigos do item
            from app.api.pedidos.models.model_pedido_item_complemento import PedidoItemComplementoModel
            complementos_antigos = self.db.query(PedidoItemComplementoModel).filter(
                PedidoItemComplementoModel.pedido_item_id == item_db.id
            ).all()
            for comp_antigo in complementos_antigos:
                self.db.delete(comp_antigo)
            self.db.flush()
            
            # Busca o produto/receita/combo para calcular preço com complementos
            product = None
            if item_db.produto_cod_barras:
                product = self.product_core.buscar_produto(
                    empresa_id=pedido.empresa_id,
                    cod_barras=str(item_db.produto_cod_barras)
                )
            elif item_db.receita_id:
                receita_model = self.db.query(ReceitaModel).filter(ReceitaModel.id == item_db.receita_id).first()
                product = self.product_core.buscar_receita(receita_id=item_db.receita_id, receita_model=receita_model)
            elif item_db.combo_id:
                product = self.product_core.buscar_combo(combo_id=item_db.combo_id)
            
            if product:
                # IMPORTANTE: preco_unitario deve ser apenas o preço BASE do produto (sem complementos)
                # Os complementos são somados separadamente via _sum_complementos_total_relacional
                # para evitar duplicação no cálculo do total do item
                quantidade_item = quantidade if quantidade is not None else item_db.quantidade
                preco_base_produto = product.get_preco_venda()
                item_db.preco_unitario = preco_base_produto
                # preco_total é apenas produto base * quantidade (sem complementos)
                item_db.preco_total = preco_base_produto * Decimal(str(quantidade_item))
            
            # Persiste novos complementos
            self.repo._persistir_complementos_do_request(
                item=item_db,
                pedido_id=pedido_id,
                complementos_request=complementos,
            )
        elif quantidade_alterada:
            # Se quantidade mudou mas não há complementos, recalcula apenas o preço total
            item_db.preco_total = item_db.preco_unitario * Decimal(str(item_db.quantidade))
        
        # Recalcula valor total do pedido incluindo complementos relacionais
        pedido_atualizado = self.repo.get(pedido_id, TipoEntrega.MESA)
        pedido_atualizado.valor_total = self.repo._calc_total(pedido_atualizado)
        self.db.flush()
        
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)  # Recarrega com itens atualizados
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def remover_item(self, pedido_id: int, item_id: int) -> RemoverItemResponse:
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        pedido = self.repo.remove_item(pedido_id, item_id)
        return RemoverItemResponse(ok=True, pedido_id=pedido.id, valor_total=float(pedido.valor_total or 0))

    def cancelar(self, pedido_id: int) -> PedidoResponseCompleto:
        # Obtém o pedido antes de cancelar para pegar o mesa_id
        pedido_antes = self.repo.get(pedido_id, TipoEntrega.MESA)
        mesa_id = pedido_antes.mesa_id
        status_anterior = (
            pedido_antes.status.value if hasattr(pedido_antes.status, "value") else str(pedido_antes.status)
        )
        
        # Cancela o pedido (muda status para CANCELADO)
        pedido = self.repo.cancelar(pedido_id)
        status_novo = pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)

        # Registra histórico (mesa)
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedido.PEDIDO_CANCELADO,
            status_anterior=status_anterior,
            status_novo=status_novo,
            descricao=f"Pedido {pedido.numero_pedido} cancelado",
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        
        
        # IMPORTANTE: Força refresh da sessão para garantir que a query veja o status atualizado
        self.db.expire_all()
        
        # IMPORTANTE: Não muda o status da mesa imediatamente ao cancelar o pedido
        # Verifica se ainda há outros pedidos abertos nesta mesa (tanto de mesa quanto de balcão)
        # O pedido que acabou de ser cancelado já não será contado (status CANCELADO)
        pedidos_mesa_abertos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.MESA, empresa_id=pedido_antes.empresa_id)
        pedidos_balcao_abertos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.BALCAO, empresa_id=pedido_antes.empresa_id)
        
        logger.info(
            f"[Pedidos Mesa] Cancelar - pedido_id={pedido_id}, mesa_id={mesa_id}, "
            f"pedidos_mesa_abertos={len(pedidos_mesa_abertos)}, pedidos_balcao_abertos={len(pedidos_balcao_abertos)}"
        )
        
        # Só libera a mesa se realmente não houver mais nenhum pedido em aberto (nem de mesa nem de balcão)
        if len(pedidos_mesa_abertos) == 0 and len(pedidos_balcao_abertos) == 0:
            # Verifica se a mesa está ocupada antes de liberar
            mesa = self.repo_mesa.get_by_id(mesa_id)
            if mesa.empresa_id != pedido_antes.empresa_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mesa não pertence à empresa")
            if mesa.status == StatusMesa.OCUPADA:
                logger.info(f"[Pedidos Mesa] Liberando mesa automaticamente (cancelar) - mesa_id={mesa_id} (sem pedidos abertos)")
                self.repo_mesa.liberar_mesa(mesa_id, empresa_id=pedido_antes.empresa_id)
        else:
            logger.info(
                f"[Pedidos Mesa] Mesa NÃO liberada (cancelar) - mesa_id={mesa_id} "
                f"(ainda há {len(pedidos_mesa_abertos)} pedidos de mesa e {len(pedidos_balcao_abertos)} de balcão abertos)"
            )

        # Notifica cliente sobre cancelamento (em background)
        try:
            import asyncio
            import threading
            from app.api.pedidos.utils.pedido_notification_helper import notificar_cliente_pedido_cancelado
            _pid = int(pedido_id)
            _eid = int(pedido.empresa_id) if pedido.empresa_id else None
            threading.Thread(
                target=lambda p=_pid, e=_eid: asyncio.run(notificar_cliente_pedido_cancelado(p, e)),
                daemon=True,
            ).start()
        except Exception as e:
            logger.error("Erro ao agendar notificação de cancelamento (mesa) %s: %s", pedido_id, e)

        # Notifica frontend/kanban sobre cancelamento (evento WS) (em background)
        try:
            import asyncio
            import threading
            from app.api.pedidos.utils.pedido_notification_helper import notificar_pedido_cancelado
            _pid = int(pedido_id)
            _eid = int(pedido.empresa_id) if pedido.empresa_id else None
            threading.Thread(
                target=lambda p=_pid, e=_eid: asyncio.run(
                    notificar_pedido_cancelado(
                        p,
                        e,
                        motivo="Pedido cancelado",
                        cancelado_por="admin",
                    )
                ),
                daemon=True,
            ).start()
        except Exception as e:
            logger.error("Erro ao agendar notificação WS de cancelamento (mesa) %s: %s", pedido_id, e)
        
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def confirmar(self, pedido_id: int) -> PedidoResponseCompleto:
        pedido_antes = self.repo.get(pedido_id, TipoEntrega.MESA)
        status_anterior = (
            pedido_antes.status.value if hasattr(pedido_antes.status, "value") else str(pedido_antes.status)
        )

        pedido = self.repo.confirmar(pedido_id)
        status_novo = pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)

        # Registra histórico (mesa)
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedido.PEDIDO_CONFIRMADO,
            status_anterior=status_anterior,
            status_novo=status_novo,
            descricao=f"Pedido {pedido.numero_pedido} confirmado",
        )
        self.repo.commit()

        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def atualizar_status(self, pedido_id: int, payload: AtualizarStatusPedidoRequest) -> PedidoResponseCompleto:
        novo_status = payload.status
        if novo_status == PedidoStatusEnum.C:
            return self.cancelar(pedido_id)
        if novo_status == PedidoStatusEnum.E:
            return self.fechar_conta(pedido_id, None)
        if novo_status == PedidoStatusEnum.I:
            return self.confirmar(pedido_id)

        pedido_antes = self.repo.get(pedido_id, TipoEntrega.MESA)
        status_anterior = (
            pedido_antes.status.value if hasattr(pedido_antes.status, "value") else str(pedido_antes.status)
        )

        pedido = self.repo.atualizar_status(pedido_id, novo_status)
        status_novo = pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)

        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedido.STATUS_ALTERADO,
            status_anterior=status_anterior,
            status_novo=status_novo,
            descricao=f"Status atualizado para {status_novo}",
        )
        self.repo.commit()

        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def fechar_conta(self, pedido_id: int, payload: FecharContaMesaRequest | None = None) -> PedidoResponseCompleto:
        # Obtém o pedido antes de fechar para pegar o mesa_id
        pedido_antes = self.repo.get(pedido_id, TipoEntrega.MESA)
        mesa_id = pedido_antes.mesa_id
        status_anterior = (
            pedido_antes.status.value if hasattr(pedido_antes.status, "value") else str(pedido_antes.status)
        )
        # Fechar conta implica marcar como pago (regra: só aqui e no marcar-pago).
        pedido_antes.pago = True
        
        # Se receber payload, salva dados de pagamento nos campos diretos
        if payload is not None:
            if payload.troco_para is not None:
                pedido_antes.troco_para = payload.troco_para
            if payload.meio_pagamento_id is not None:
                pedido_antes.meio_pagamento_id = payload.meio_pagamento_id
            self.db.commit()
            self.db.refresh(pedido_antes)

        # Fecha o pedido (muda status para ENTREGUE)
        pedido = self.repo.fechar_conta(pedido_id)
        status_novo = pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)
        
        # IMPORTANTE: Força refresh da sessão para garantir que a query veja o status atualizado
        self.db.expire_all()
        
        # IMPORTANTE: Não muda o status da mesa imediatamente ao fechar a conta
        # Verifica se ainda há outros pedidos abertos nesta mesa (tanto de mesa quanto de balcão)
        # O pedido que acabou de ser fechado já não será contado (status ENTREGUE)
        pedidos_mesa_abertos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.MESA, empresa_id=pedido_antes.empresa_id)
        pedidos_balcao_abertos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.BALCAO, empresa_id=pedido_antes.empresa_id)
        
        logger.info(
            f"[Pedidos Mesa] Fechar conta - pedido_id={pedido_id}, mesa_id={mesa_id}, "
            f"pedidos_mesa_abertos={len(pedidos_mesa_abertos)}, pedidos_balcao_abertos={len(pedidos_balcao_abertos)}"
        )
        
        # Só libera a mesa se realmente não houver mais nenhum pedido em aberto (nem de mesa nem de balcão)
        if len(pedidos_mesa_abertos) == 0 and len(pedidos_balcao_abertos) == 0:
            # Verifica se a mesa está ocupada antes de liberar
            mesa = self.repo_mesa.get_by_id(mesa_id)
            if mesa.empresa_id != pedido_antes.empresa_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mesa não pertence à empresa")
            if mesa.status == StatusMesa.OCUPADA:
                logger.info(f"[Pedidos Mesa] Liberando mesa automaticamente - mesa_id={mesa_id} (sem pedidos abertos)")
                self.repo_mesa.liberar_mesa(mesa_id, empresa_id=pedido_antes.empresa_id)
        else:
            logger.info(
                f"[Pedidos Mesa] Mesa NÃO liberada - mesa_id={mesa_id} "
                f"(ainda há {len(pedidos_mesa_abertos)} pedidos de mesa e {len(pedidos_balcao_abertos)} de balcão abertos)"
            )

        # Registra histórico (mesa) - pedido fechado
        observacoes_historico = None
        if payload:
            if payload.meio_pagamento_id:
                observacoes_historico = f"Meio pagamento: {payload.meio_pagamento_id}"
            if payload.troco_para:
                observacoes_historico = (observacoes_historico or "") + f" | Troco para: {payload.troco_para}"
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedido.PEDIDO_FECHADO,
            status_anterior=status_anterior,
            status_novo=status_novo,
            descricao=f"Pedido {pedido.numero_pedido} fechado",
            observacoes=observacoes_historico,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def reabrir(self, pedido_id: int) -> PedidoResponseCompleto:
        pedido_antes = self.repo.get(pedido_id, TipoEntrega.MESA)
        status_anterior = (
            pedido_antes.status.value if hasattr(pedido_antes.status, "value") else str(pedido_antes.status)
        )
        pedido = self.repo.reabrir(pedido_id)
        status_novo = pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)
        logger.info(f"[Pedidos Mesa] Reabrindo pedido - pedido_id={pedido_id}, novo_status=PENDENTE, mesa_id={pedido.mesa_id}")
        # Ao reabrir o pedido, garantir que a mesa vinculada esteja marcada como OCUPADA
        self.repo_mesa.ocupar_mesa(pedido.mesa_id, empresa_id=pedido.empresa_id)

        # Registra histórico (mesa) - pedido reaberto
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedido.PEDIDO_REABERTO,
            status_anterior=status_anterior,
            status_novo=status_novo,
            descricao=f"Pedido {pedido.numero_pedido} reaberto",
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    # Fluxo cliente
    def fechar_conta_cliente(self, pedido_id: int, cliente_id: int, payload: FecharContaMesaRequest) -> PedidoResponseCompleto:
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        if pedido.cliente_id and pedido.cliente_id != cliente_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Pedido não pertence ao cliente")
        status_anterior = pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)
        # Fechar conta (cliente) implica marcar como pago (regra: só aqui e no marcar-pago).
        pedido.pago = True

        # Salva dados de pagamento nos campos diretos
        if payload.troco_para is not None:
            pedido.troco_para = payload.troco_para
        if payload.meio_pagamento_id is not None:
            pedido.meio_pagamento_id = payload.meio_pagamento_id

        self.db.commit()
        self.db.refresh(pedido)

        # Obtém o mesa_id antes de fechar
        mesa_id = pedido.mesa_id

        # Fecha pedido (muda status para ENTREGUE)
        pedido = self.repo.fechar_conta(pedido_id)
        status_novo = pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)
        
        # IMPORTANTE: Força refresh da sessão para garantir que a query veja o status atualizado
        self.db.expire_all()
        
        # IMPORTANTE: Não muda o status da mesa imediatamente ao fechar a conta
        # Verifica se ainda há outros pedidos abertos nesta mesa (tanto de mesa quanto de balcão)
        pedidos_mesa_abertos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.MESA, empresa_id=pedido.empresa_id)
        pedidos_balcao_abertos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.BALCAO, empresa_id=pedido.empresa_id)
        
        logger.info(
            f"[Pedidos Mesa] Fechar conta cliente - pedido_id={pedido_id}, mesa_id={mesa_id}, "
            f"pedidos_mesa_abertos={len(pedidos_mesa_abertos)}, pedidos_balcao_abertos={len(pedidos_balcao_abertos)}"
        )
        
        # Só libera a mesa se realmente não houver mais nenhum pedido em aberto (nem de mesa nem de balcão)
        if len(pedidos_mesa_abertos) == 0 and len(pedidos_balcao_abertos) == 0:
            # Verifica se a mesa está ocupada antes de liberar
            mesa = self.repo_mesa.get_by_id(mesa_id)
            if mesa.empresa_id != pedido.empresa_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mesa não pertence à empresa")
            if mesa.status == StatusMesa.OCUPADA:
                logger.info(f"[Pedidos Mesa] Liberando mesa automaticamente (cliente) - mesa_id={mesa_id} (sem pedidos abertos)")
                self.repo_mesa.liberar_mesa(mesa_id, empresa_id=pedido.empresa_id)
        else:
            logger.info(
                f"[Pedidos Mesa] Mesa NÃO liberada (cliente) - mesa_id={mesa_id} "
                f"(ainda há {len(pedidos_mesa_abertos)} pedidos de mesa e {len(pedidos_balcao_abertos)} de balcão abertos)"
            )

        # Registra histórico (mesa) - pedido fechado pelo cliente
        observacoes_historico = None
        if payload:
            if payload.meio_pagamento_id:
                observacoes_historico = f"Meio pagamento: {payload.meio_pagamento_id}"
            if payload.troco_para:
                observacoes_historico = (observacoes_historico or "") + f" | Troco para: {payload.troco_para}"
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedido.PEDIDO_FECHADO,
            status_anterior=status_anterior,
            status_novo=status_novo,
            descricao=f"Pedido {pedido.numero_pedido} fechado (cliente)",
            observacoes=observacoes_historico,
            cliente_id=cliente_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    # -------- Consultas --------
    def get_pedido(self, pedido_id: int) -> PedidoResponseCompleto:
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def list_pedidos_abertos(self, empresa_id: int, mesa_id: Optional[int] = None) -> list[PedidoResponseCompleto]:
        if mesa_id is not None:
            pedidos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.MESA, empresa_id=empresa_id)
        else:
            pedidos = self.repo.list_abertos_all(TipoEntrega.MESA, empresa_id=empresa_id)
        return [PedidoResponseBuilder.pedido_to_response_completo(p) for p in pedidos]

    def list_pedidos_finalizados(self, mesa_id: int, data_filtro: Optional[date] = None, *, empresa_id: int) -> list[PedidoResponseCompleto]:
        """Retorna todos os pedidos finalizados (ENTREGUE) de uma mesa, opcionalmente filtrando por data"""
        # Valida se a mesa existe
        mesa = self.repo_mesa.get_by_id(mesa_id)
        if mesa.empresa_id != empresa_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mesa não pertence à empresa")
        pedidos = self.repo.list_finalizados(TipoEntrega.MESA, data_filtro, empresa_id=empresa_id, mesa_id=mesa_id)
        return [PedidoResponseBuilder.pedido_to_response_completo(p) for p in pedidos]

    def list_pedidos_by_cliente(self, cliente_id: int, *, empresa_id: int, skip: int = 0, limit: int = 50) -> list[PedidoResponseCompleto]:
        """Lista todos os pedidos de mesa/balcão de um cliente específico"""
        pedidos = self.repo.list_by_cliente_id(cliente_id, TipoEntrega.MESA, skip=skip, limit=limit, empresa_id=empresa_id)
        # ⚠️ Não mutar `pedido.itens` aqui (delete-orphan). Filtragem deve ser feita apenas na camada de response/DTO.
        return [PedidoResponseBuilder.pedido_to_response_completo(p) for p in pedidos]

    def atualizar_observacoes(self, pedido_id: int, payload: AtualizarObservacoesRequest) -> PedidoResponseCompleto:
        """Atualiza as observações de um pedido"""
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        pedido.observacoes = payload.observacoes
        self.db.commit()
        self.db.refresh(pedido)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)


