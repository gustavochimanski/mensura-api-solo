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
    MeioPagamentoParcialRequest,
)
from app.api.pedidos.services.service_pedido_responses import PedidoResponseBuilder
from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum, TipoEntregaEnum
from app.api.pedidos.models.model_pedido_unificado import StatusPedido
from app.api.pedidos.models.model_pedido_historico_unificado import TipoOperacaoPedido
from app.api.pedidos.services.service_pedido_taxas import TaxaService
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
    meio_pagamento_id: Optional[int] = None
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
    pagamentos: Optional[List[MeioPagamentoParcialRequest]] = None
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

    def _recalcular_totais(self, pedido) -> None:
        """
        Recalcula subtotal/taxas/valor_total para pedidos de MESA.

        IMPORTANTE: o repo._calc_total calcula apenas itens+complementos. Aqui somamos taxa de serviço
        (e taxa_entrega apenas para DELIVERY, que não é o caso).
        """
        subtotal = self.repo._calc_total(pedido)
        taxa_entrega, taxa_servico, distancia_km, _ = TaxaService(self.db).calcular_taxas(
            tipo_entrega=TipoEntregaEnum.MESA,
            subtotal=subtotal,
            endereco=None,
            empresa_id=pedido.empresa_id,
        )
        self.repo.atualizar_totais(
            pedido,
            subtotal=subtotal,
            desconto=Decimal("0"),
            taxa_entrega=taxa_entrega,
            taxa_servico=taxa_servico,
            distancia_km=distancia_km,
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
            meio_pagamento_id=payload.meio_pagamento_id,
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
                
                # Adiciona item (inclui secoes selecionadas se presentes)
                complementos_payload = {
                    "complementos": combo_req.complementos if getattr(combo_req, "complementos", None) else [],
                    "secoes": combo_req.secoes if getattr(combo_req, "secoes", None) else [],
                }
                self.repo.add_item(
                    pedido.id,
                    combo_id=combo_req.combo_id,
                    quantidade=qtd,
                    preco_unitario=preco_unitario,
                    observacao=observacao_completa,
                    produto_descricao_snapshot=descricao_produto,
                    complementos=complementos_payload,
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

        # Recalcula totais incluindo taxa de serviço (evita divergência com /checkout/preview)
        pedido_atualizado = self.repo.get(pedido.id, TipoEntrega.MESA)
        self._recalcular_totais(pedido_atualizado)
        self.repo.commit()
        pedido = self.repo.get(pedido.id, TipoEntrega.MESA)

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
        pedido_atualizado = self.repo.get(pedido_id, TipoEntrega.MESA)
        self._recalcular_totais(pedido_atualizado)
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
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

        pedido_atualizado = self.repo.get(pedido_id, TipoEntrega.MESA)
        self._recalcular_totais(pedido_atualizado)
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
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
        self._recalcular_totais(pedido_atualizado)
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)  # Recarrega com itens atualizados
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def remover_item(self, pedido_id: int, item_id: int) -> RemoverItemResponse:
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        pedido = self.repo.remove_item(pedido_id, item_id)
        pedido_atualizado = self.repo.get(pedido.id, TipoEntrega.MESA)
        self._recalcular_totais(pedido_atualizado)
        self.repo.commit()
        pedido_atualizado = self.repo.get(pedido.id, TipoEntrega.MESA)
        return RemoverItemResponse(
            ok=True,
            pedido_id=pedido_atualizado.id,
            valor_total=float(pedido_atualizado.valor_total or 0),
        )

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
        # Fechar conta: registra pagamento via transação (PAGO).
        from app.api.cardapio.repositories.repo_pagamentos import PagamentoRepository
        from app.api.cadastros.services.service_meio_pagamento import MeioPagamentoService
        from app.api.cadastros.schemas.schema_meio_pagamento import MeioPagamentoTipoEnum
        from app.api.pedidos.services.service_pedido_helpers import _dec, ajustar_pagamento_dinheiro_com_troco
        from app.api.shared.schemas.schema_shared_enums import (
            PagamentoGatewayEnum,
            PagamentoMetodoEnum,
            PagamentoStatusEnum,
        )
        
        # Se receber payload, salva dados de pagamento nos campos diretos
        pagamentos_payload: list[dict] = []
        if payload is not None:
            if payload.troco_para is not None:
                pedido_antes.troco_para = payload.troco_para
            # Novo formato: múltiplos meios (pagamentos: [{id|meio_pagamento_id, valor}])
            if getattr(payload, "pagamentos", None):
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
                # Mantém compatibilidade: primeiro meio vira "principal" no pedido
                if pagamentos_payload:
                    pedido_antes.meio_pagamento_id = pagamentos_payload[0]["meio_pagamento_id"]
                    if hasattr(pedido_antes, "pagamentos_snapshot"):
                        pedido_antes.pagamentos_snapshot = [
                            {"id": p["meio_pagamento_id"], "valor": float(p["valor"])}
                            for p in pagamentos_payload
                        ]
            elif payload.meio_pagamento_id is not None:
                pedido_antes.meio_pagamento_id = payload.meio_pagamento_id
            self.db.commit()
            self.db.refresh(pedido_antes)

        valor_total = _dec(getattr(pedido_antes, "valor_total", 0) or 0)

        # Se o pedido já estiver totalmente pago (via transações PAGO/AUTORIZADO),
        # não criamos/atualizamos novas transações ao fechar a conta.
        from app.api.pedidos.services.service_pedido_helpers import build_pagamento_resumo

        pagamento_resumo = build_pagamento_resumo(pedido_antes)
        if pagamento_resumo and getattr(pagamento_resumo, "esta_pago", False):
            # Fecha o pedido (muda status para ENTREGUE)
            pedido = self.repo.fechar_conta(pedido_id)
            status_novo = pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)

            # IMPORTANTE: Força refresh da sessão para garantir que a query veja o status atualizado
            self.db.expire_all()

            # IMPORTANTE: Não muda o status da mesa imediatamente ao fechar a conta
            pedidos_mesa_abertos = self.repo.list_abertos_by_mesa(
                mesa_id, TipoEntrega.MESA, empresa_id=pedido_antes.empresa_id
            )
            pedidos_balcao_abertos = self.repo.list_abertos_by_mesa(
                mesa_id, TipoEntrega.BALCAO, empresa_id=pedido_antes.empresa_id
            )

            logger.info(
                f"[Pedidos Mesa] Fechar conta (já pago) - pedido_id={pedido_id}, mesa_id={mesa_id}, "
                f"pedidos_mesa_abertos={len(pedidos_mesa_abertos)}, pedidos_balcao_abertos={len(pedidos_balcao_abertos)}"
            )

            if len(pedidos_mesa_abertos) == 0 and len(pedidos_balcao_abertos) == 0:
                mesa = self.repo_mesa.get_by_id(mesa_id)
                if mesa.empresa_id != pedido_antes.empresa_id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mesa não pertence à empresa")
                if mesa.status == StatusMesa.OCUPADA:
                    logger.info(f"[Pedidos Mesa] Liberando mesa automaticamente (já pago) - mesa_id={mesa_id} (sem pedidos abertos)")
                    self.repo_mesa.liberar_mesa(mesa_id, empresa_id=pedido_antes.empresa_id)

            # Registra histórico (mesa) - pedido fechado
            observacoes_historico = "Pagamento já registrado (fechando conta sem recriar transações)"
            if payload and getattr(payload, "meio_pagamento_id", None):
                observacoes_historico += f" | Meio pagamento: {payload.meio_pagamento_id}"
            if getattr(pedido, "troco_para", None) is not None:
                observacoes_historico += f" | Troco para: {float(pedido.troco_para):.2f}"

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

        meio_pagamento_id = getattr(pedido_antes, "meio_pagamento_id", None)
        if meio_pagamento_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Meio de pagamento é obrigatório para fechar conta.")

        # Se o frontend mandou "valor recebido" em DINHEIRO (valor > total) dentro de `pagamentos`,
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

            if troco_para_derivado is not None and (payload is None or getattr(payload, "troco_para", None) is None):
                pedido_antes.troco_para = float(troco_para_derivado)

            if hasattr(pedido_antes, "pagamentos_snapshot") and pagamentos_payload:
                pedido_antes.pagamentos_snapshot = [
                    {"id": p["meio_pagamento_id"], "valor": float(p["valor"])} for p in pagamentos_payload
                ]

        pagamentos_para_fechar = pagamentos_payload or [
            {"meio_pagamento_id": int(meio_pagamento_id), "valor": valor_total}
        ]
        # Se veio lista de pagamentos, valida soma = total (evita fechar conta com valor divergente)
        if pagamentos_payload:
            soma_pagamentos = sum((p["valor"] for p in pagamentos_payload), _dec(0))
            if soma_pagamentos != valor_total:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "PAGAMENTOS_INVALIDOS",
                        "message": "Soma dos pagamentos deve ser igual ao valor total do pedido para fechar conta.",
                        "valor_total": float(valor_total),
                        "soma_pagamentos": float(soma_pagamentos),
                    },
                )

        # Inicializa repositório de pagamentos e transações existentes para reutilização/idempotência
        pagamento_repo = PagamentoRepository(self.db)
        txs = pagamento_repo.list_by_pedido_id(pedido_antes.id)

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
            provider_id = f"manual_fechar_conta_mesa_{pedido_antes.id}_{mp_id}_{centavos}"

            # Tenta reutilizar transação pendente existente (evita duplicar)
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
                    payload_solicitacao={"origem": "fechar_conta_mesa"},
                )
                pagamento_repo.registrar_evento(tx_existente, "pago_em")
                continue

            # Idempotência: se já existe algo com esse provider_id, não recria
            if pagamento_repo.get_by_provider_transaction_id(provider_transaction_id=provider_id) is not None:
                continue

            tx_nova = pagamento_repo.criar(
                pedido_id=pedido_antes.id,
                meio_pagamento_id=mp_id,
                gateway=gateway.value,
                metodo=metodo.value,
                valor=valor_parcial,
                status=PagamentoStatusEnum.PAGO.value,
                provider_transaction_id=provider_id,
                payload_solicitacao={"origem": "fechar_conta_mesa"},
            )
            pagamento_repo.registrar_evento(tx_nova, "pago_em")

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
        if getattr(pedido, "troco_para", None) is not None:
            observacoes_historico = (observacoes_historico or "") + f" | Troco para: {float(pedido.troco_para):.2f}"
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
        # Fechar conta (cliente): registra pagamento via transação (PAGO).
        from app.api.cardapio.repositories.repo_pagamentos import PagamentoRepository
        from app.api.cadastros.services.service_meio_pagamento import MeioPagamentoService
        from app.api.cadastros.schemas.schema_meio_pagamento import MeioPagamentoTipoEnum
        from app.api.pedidos.services.service_pedido_helpers import _dec
        from app.api.shared.schemas.schema_shared_enums import (
            PagamentoGatewayEnum,
            PagamentoMetodoEnum,
            PagamentoStatusEnum,
        )

        # Salva dados de pagamento nos campos diretos
        if payload.troco_para is not None:
            pedido.troco_para = payload.troco_para
        if payload.meio_pagamento_id is not None:
            pedido.meio_pagamento_id = payload.meio_pagamento_id

        meio_pagamento_id = getattr(pedido, "meio_pagamento_id", None)
        if meio_pagamento_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Meio de pagamento é obrigatório para fechar conta.")

        mp = MeioPagamentoService(self.db).get(int(meio_pagamento_id))
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

        pagamento_repo = PagamentoRepository(self.db)
        txs = pagamento_repo.list_by_pedido_id(pedido.id)
        if not any(getattr(tx, "status", None) in {"PAGO", "AUTORIZADO"} for tx in txs):
            tx_nova = pagamento_repo.criar(
                pedido_id=pedido.id,
                meio_pagamento_id=int(meio_pagamento_id),
                gateway=gateway.value,
                metodo=metodo.value,
                valor=_dec(getattr(pedido, "valor_total", 0) or 0),
                status=PagamentoStatusEnum.PAGO.value,
                provider_transaction_id=f"manual_fechar_conta_mesa_cliente_{pedido.id}_{int(meio_pagamento_id)}",
                payload_solicitacao={"origem": "fechar_conta_mesa_cliente", "cliente_id": cliente_id},
            )
            pagamento_repo.registrar_evento(tx_nova, "pago_em")

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
        if getattr(pedido, "troco_para", None) is not None:
            observacoes_historico = (observacoes_historico or "") + f" | Troco para: {float(pedido.troco_para):.2f}"
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


