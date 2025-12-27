from __future__ import annotations

from decimal import Decimal
from typing import Optional
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.cadastros.models.model_mesa import StatusMesa
from app.api.cadastros.repositories.repo_mesas import MesaRepository
from app.api.pedidos.models.model_pedido_unificado import TipoEntrega
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.catalogo.contracts.adicional_contract import IAdicionalContract
from app.api.catalogo.contracts.complemento_contract import IComplementoContract
from app.api.catalogo.contracts.combo_contract import IComboContract
from app.api.pedidos.models.model_pedido_historico_unificado import TipoOperacaoPedido
from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
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
from app.api.pedidos.schemas.schema_pedido_status_historico import PedidoStatusHistoricoOut, HistoricoDoPedidoResponse
from pydantic import BaseModel
from typing import Optional, List


# Schemas de request para pedidos de balcão
class PedidoBalcaoCreate(BaseModel):
    empresa_id: int
    mesa_id: Optional[int] = None  # Código da mesa (opcional)
    cliente_id: Optional[int] = None
    observacoes: Optional[str] = None
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


class FecharContaBalcaoRequest(BaseModel):
    meio_pagamento_id: Optional[int] = None
    troco_para: Optional[float] = None


class AtualizarStatusPedidoRequest(BaseModel):
    status: PedidoStatusEnum

from app.api.catalogo.models.model_receita import ReceitaModel
from app.api.catalogo.models.model_combo import ComboModel
from app.api.pedidos.utils.complementos import resolve_produto_complementos, resolve_complementos_diretos
from app.api.pedidos.services.service_pedido_helpers import _dec
from app.api.catalogo.core import ProductCore
from app.api.catalogo.adapters.produto_adapter import ProdutoAdapter
from app.api.catalogo.adapters.combo_adapter import ComboAdapter
from app.api.catalogo.adapters.complemento_adapter import ComplementoAdapter


class PedidoBalcaoService:
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

    @staticmethod
    def _status_value(status_obj):
        """Normaliza valor de status para string."""
        if hasattr(status_obj, "value"):
            return status_obj.value
        return status_obj
    

    # -------- Pedido --------
    def criar_pedido(self, payload: PedidoBalcaoCreate) -> PedidoResponseCompleto:
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

        pedido = self.repo.criar_pedido_balcao(
            empresa_id=payload.empresa_id,
            mesa_id=mesa_id_real,
            cliente_id=payload.cliente_id,
            observacoes=payload.observacoes,
        )

        # Registra histórico de criação
        self.repo.add_historico(
            pedido_id=pedido.id,
            tipo_operacao=TipoOperacaoPedido.PEDIDO_CRIADO,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} criado",
            cliente_id=payload.cliente_id,
        )
        if mesa_id_real:
            self.repo.add_historico(
                pedido_id=pedido.id,
                tipo_operacao=TipoOperacaoPedido.MESA_ASSOCIADA,
                descricao=f"Mesa associada ao pedido",
            )
        self.repo.commit()

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
                
                # Calcula preço com complementos
                preco_total, adicionais_snapshot = self.product_core.calcular_preco_com_complementos(
                    product=product,
                    quantidade=qtd,
                    complementos_request=it.complementos,
                )
                
                preco_unitario = preco_total / qtd
                descricao_produto = product.nome or product.descricao or ""
                
                # Adiciona item
                self.repo.add_item(
                    pedido.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=qtd,
                    observacao=it.observacao,
                    adicionais_snapshot=adicionais_snapshot if adicionais_snapshot else None,
                )
                # Registra histórico de item adicionado
                self.repo.add_historico(
                    pedido_id=pedido.id,
                    tipo_operacao=TipoOperacaoPedido.ITEM_ADICIONADO,
                    descricao=f"Item adicionado: {it.produto_cod_barras} (qtd: {qtd})",
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
                
                # Calcula preço com complementos
                preco_total, adicionais_snapshot = self.product_core.calcular_preco_com_complementos(
                    product=product,
                    quantidade=qtd,
                    complementos_request=receita_req.complementos,
                )
                
                preco_unitario = preco_total / qtd
                descricao_produto = product.nome or product.descricao or ""
                
                # Adiciona item
                self.repo.add_item(
                    pedido.id,
                    receita_id=receita_req.receita_id,
                    quantidade=qtd,
                    preco_unitario=preco_unitario,
                    observacao=receita_req.observacao,
                    produto_descricao_snapshot=descricao_produto,
                    adicionais_snapshot=adicionais_snapshot if adicionais_snapshot else None,
                )
                # Registra histórico
                self.repo.add_historico(
                    pedido_id=pedido.id,
                    tipo_operacao=TipoOperacaoPedido.ITEM_ADICIONADO,
                    descricao=f"Receita adicionada: {descricao_produto} (ID: {receita_req.receita_id}, qtd: {qtd})",
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
                
                # Calcula preço com complementos
                preco_total, adicionais_snapshot = self.product_core.calcular_preco_com_complementos(
                    product=product,
                    quantidade=qtd,
                    complementos_request=combo_req.complementos,
                )
                
                preco_unitario = preco_total / qtd
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
                    adicionais_snapshot=adicionais_snapshot if adicionais_snapshot else None,
                )
                # Registra histórico
                self.repo.add_historico(
                    pedido_id=pedido.id,
                    tipo_operacao=TipoOperacaoPedido.ITEM_ADICIONADO,
                    descricao=f"Combo adicionado: {descricao_produto} (ID: {combo_req.combo_id}, qtd: {qtd})",
                )
            self.repo.commit()
        
        # Recarrega pedido com todos os itens
        pedido = self.repo.get(pedido.id, TipoEntrega.BALCAO)

        # Notifica novo pedido em background
        try:
            import asyncio
            from app.api.pedidos.utils.pedido_notification_helper import notificar_novo_pedido
            # Recarrega pedido com todos os relacionamentos para a notificação
            pedido_completo = self.repo.get(pedido.id, TipoEntrega.BALCAO)
            if pedido_completo:
                asyncio.create_task(notificar_novo_pedido(pedido_completo))
        except Exception as e:
            # Loga erro mas não quebra o fluxo
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao agendar notificação de novo pedido {pedido.id}: {e}")

        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def adicionar_item(self, pedido_id: int, body: AdicionarItemRequest, usuario_id: int | None = None) -> PedidoResponseCompleto:
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)
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
            tipo_operacao=TipoOperacaoPedido.ITEM_ADICIONADO,
            descricao=f"Item adicionado: {body.produto_cod_barras} (qtd: {body.quantidade})",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)  # Recarrega com itens atualizados
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def adicionar_produto_generico(
        self, 
        pedido_id: int, 
        body: AdicionarProdutoGenericoRequest, 
        usuario_id: int | None = None
    ) -> PedidoResponseCompleto:
        """
        Adiciona um produto genérico ao pedido (produto normal, receita ou combo).
        Identifica automaticamente o tipo baseado nos campos preenchidos.
        
        Usa ProductCore para unificar o tratamento de diferentes tipos de produtos.
        """
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)
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
        
        # Calcula preço com complementos usando ProductCore
        preco_total, adicionais_snapshot = self.product_core.calcular_preco_com_complementos(
            product=product,
            quantidade=qtd,
            complementos_request=body.complementos,
        )
        
        # Prepara dados para adicionar item
        preco_unitario = preco_total / qtd
        descricao_produto = product.nome or product.descricao or ""
        
        # Monta observação completa para combos
        observacao_completa = body.observacao
        if product.product_type.value == "combo":
            observacao_completa = f"Combo #{product.identifier} - {descricao_produto}"
            if body.observacao:
                observacao_completa += f" | {body.observacao}"
        
        # Adiciona item ao pedido baseado no tipo
        if product.product_type.value == "produto":
            pedido = self.repo.add_item(
                pedido_id,
                produto_cod_barras=str(product.identifier),
                quantidade=qtd,
                observacao=observacao_completa,
                adicionais_snapshot=adicionais_snapshot if adicionais_snapshot else None,
            )
            descricao_historico = f"Produto adicionado: {product.identifier} (qtd: {qtd})"
            
        elif product.product_type.value == "receita":
            pedido = self.repo.add_item(
                pedido_id,
                receita_id=int(product.identifier),
                quantidade=qtd,
                preco_unitario=preco_unitario,
                observacao=observacao_completa,
                produto_descricao_snapshot=descricao_produto,
                adicionais_snapshot=adicionais_snapshot if adicionais_snapshot else None,
            )
            descricao_historico = f"Receita adicionada: {descricao_produto} (ID: {product.identifier}, qtd: {qtd})"
            
        elif product.product_type.value == "combo":
            pedido = self.repo.add_item(
                pedido_id,
                combo_id=int(product.identifier),
                quantidade=qtd,
                preco_unitario=preco_unitario,
                observacao=observacao_completa,
                produto_descricao_snapshot=descricao_produto,
                adicionais_snapshot=adicionais_snapshot if adicionais_snapshot else None,
            )
            descricao_historico = f"Combo adicionado: {descricao_produto} (ID: {product.identifier}, qtd: {qtd})"
        
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Tipo de produto não suportado"
            )
        
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedido.ITEM_ADICIONADO,
            descricao=descricao_historico,
            usuario_id=usuario_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)  # Recarrega com itens atualizados
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def remover_item(self, pedido_id: int, item_id: int, usuario_id: int | None = None) -> RemoverItemResponse:
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        pedido = self.repo.remove_item(pedido_id, item_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedido.ITEM_REMOVIDO,
            descricao=f"Item removido: ID {item_id}",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return RemoverItemResponse(ok=True, pedido_id=pedido.id, valor_total=float(pedido.valor_total or 0))

    def cancelar(self, pedido_id: int, usuario_id: int | None = None) -> PedidoResponseCompleto:
        pedido_antes = self.repo.get(pedido_id, TipoEntrega.BALCAO)
        status_anterior = self._status_value(pedido_antes.status)
        pedido = self.repo.cancelar(pedido_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedido.PEDIDO_CANCELADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} cancelado",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def confirmar(self, pedido_id: int, usuario_id: int | None = None) -> PedidoResponseCompleto:
        pedido_antes = self.repo.get(pedido_id, TipoEntrega.BALCAO)
        status_anterior = self._status_value(pedido_antes.status)
        pedido = self.repo.confirmar(pedido_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedido.PEDIDO_CONFIRMADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} confirmado",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def atualizar_status(
        self,
        pedido_id: int,
        payload: AtualizarStatusPedidoRequest,
        usuario_id: int | None = None
    ) -> PedidoResponseCompleto:
        novo_status = payload.status
        if novo_status == PedidoStatusEnum.C:
            return self.cancelar(pedido_id, usuario_id=usuario_id)
        if novo_status == PedidoStatusEnum.E:
            return self.fechar_conta(pedido_id, payload=None, usuario_id=usuario_id)
        if novo_status == PedidoStatusEnum.I:
            return self.confirmar(pedido_id, usuario_id=usuario_id)

        pedido_atual = self.repo.get(pedido_id)
        status_anterior = self._status_value(pedido_atual.status)
        pedido = self.repo.atualizar_status(pedido_id, novo_status)
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedido.STATUS_ALTERADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Status atualizado para {self._status_value(pedido.status)}",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def fechar_conta(self, pedido_id: int, payload: FecharContaBalcaoRequest | None = None, usuario_id: int | None = None) -> PedidoResponseCompleto:
        pedido_antes = self.repo.get(pedido_id, TipoEntrega.BALCAO)
        status_anterior = self._status_value(pedido_antes.status)
        mesa_id = pedido_antes.mesa_id  # Guarda mesa_id antes de fechar
        
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
        
        # Se o pedido tinha mesa associada, verifica se há outros pedidos abertos antes de liberar
        if mesa_id is not None:
            # Verifica pedidos abertos de balcão na mesa
            pedidos_balcao_abertos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.BALCAO, empresa_id=pedido.empresa_id)
            # Verifica pedidos abertos de mesa na mesa
            from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
            repo_mesa_pedidos = PedidoRepository(self.db, produto_contract=self.produto_contract)
            pedidos_mesa_abertos = repo_mesa_pedidos.list_abertos_by_mesa(mesa_id, TipoEntrega.MESA, empresa_id=pedido.empresa_id)
            
            # Só libera a mesa se não houver mais nenhum pedido aberto (nem de balcão nem de mesa)
            if len(pedidos_balcao_abertos) == 0 and len(pedidos_mesa_abertos) == 0:
                mesa = self.repo_mesa.get_by_id(mesa_id)
                if mesa.empresa_id != pedido.empresa_id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mesa não pertence à empresa")
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
            tipo_operacao=TipoOperacaoPedido.PEDIDO_FECHADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} fechado",
            observacoes=observacoes_historico,
            usuario_id=usuario_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def reabrir(self, pedido_id: int, usuario_id: int | None = None) -> PedidoResponseCompleto:
        pedido_antes = self.repo.get(pedido_id, TipoEntrega.BALCAO)
        status_anterior = self._status_value(pedido_antes.status)
        pedido = self.repo.reabrir(pedido_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedido.PEDIDO_REABERTO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} reaberto",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    # -------- Consultas --------
    def get_pedido(self, pedido_id: int) -> PedidoResponseCompleto:
        """
        Busca um pedido de balcão e retorna no formato padronizado.
        
        Segue o padrão definido em PADRAO_RETORNO_PEDIDOS.md:
        - Constrói o campo 'produtos' com itens, receitas e combos
        - Recalcula 'valor_total' incluindo receitas, combos e adicionais
        - Itens ficam apenas dentro de produtos.itens (não na raiz)
        """
        # Busca pedido (o repositório já carrega os itens via joinedload)
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def list_pedidos_abertos(self, *, empresa_id: Optional[int] = None) -> list[PedidoResponseCompleto]:
        pedidos = self.repo.list_abertos_all(TipoEntrega.BALCAO, empresa_id=empresa_id)
        return [PedidoResponseBuilder.pedido_to_response_completo(p) for p in pedidos]

    def list_pedidos_finalizados(self, data_filtro: Optional[date] = None, *, empresa_id: Optional[int] = None) -> list[PedidoResponseCompleto]:
        """Retorna todos os pedidos finalizados (ENTREGUE), opcionalmente filtrando por data"""
        pedidos = self.repo.list_finalizados(TipoEntrega.BALCAO, data_filtro, empresa_id=empresa_id)
        return [PedidoResponseBuilder.pedido_to_response_completo(p) for p in pedidos]

    def list_pedidos_by_cliente(self, cliente_id: int, *, empresa_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> list[PedidoResponseCompleto]:
        """Lista todos os pedidos de balcão de um cliente específico"""
        pedidos = self.repo.list_by_cliente_id(cliente_id, TipoEntrega.BALCAO, empresa_id=empresa_id, skip=skip, limit=limit)
        return [PedidoResponseBuilder.pedido_to_response_completo(p) for p in pedidos]

    # -------- Histórico --------
    def get_historico(self, pedido_id: int, limit: int = 100) -> HistoricoDoPedidoResponse:
        """Busca histórico completo de um pedido de balcão"""
        # Verifica se o pedido existe
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)
        
        # Busca histórico
        historicos = self.repo.get_historico(pedido_id, limit)
        
        # Converte para schema unificado
        historicos_out = []
        for h in historicos:
            historico_out = PedidoResponseBuilder.build_historico_response(h)
            historicos_out.append(historico_out)
        
        return HistoricoDoPedidoResponse(
            pedido_id=pedido_id,
            historicos=historicos_out
        )

