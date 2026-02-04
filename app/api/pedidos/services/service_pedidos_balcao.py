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
from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum, TipoEntregaEnum
from app.api.pedidos.models.model_pedido_unificado import StatusPedido
from app.api.pedidos.schemas.schema_pedido_status_historico import PedidoStatusHistoricoOut, HistoricoDoPedidoResponse
from app.api.pedidos.services.service_pedido_taxas import TaxaService
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
from app.utils.logger import logger


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

    def _recalcular_totais(self, pedido) -> None:
        """
        Recalcula subtotal/taxas/valor_total para pedidos de BALCAO.

        O repo._calc_total calcula apenas itens+complementos. Aqui somamos a taxa de serviço
        para refletir o valor_total final (mesma regra do checkout/preview).
        """
        subtotal = self.repo._calc_total(pedido)
        taxa_entrega, taxa_servico, distancia_km, _ = TaxaService(self.db).calcular_taxas(
            tipo_entrega=TipoEntregaEnum.BALCAO,
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
                if mesa is None:
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND,
                        f"Mesa com código {payload.mesa_id} não encontrada"
                    )
                mesa_id_real = mesa.id
            except HTTPException:
                raise
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
                
                # IMPORTANTE: preco_unitario deve ser apenas o preço BASE (sem complementos).
                # Os complementos são persistidos relacionalmente e somados no total via _calc_item_total.
                preco_unitario = product.get_preco_venda()
                descricao_produto = product.nome or product.descricao or ""
                
                # Adiciona item
                self.repo.add_item(
                    pedido.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=qtd,
                    preco_unitario=preco_unitario,
                    observacao=it.observacao,
                    produto_descricao_snapshot=descricao_produto,
                    complementos=it.complementos if it.complementos else None,
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

        # Recalcula totais incluindo taxa de serviço (evita divergência com /checkout/preview)
        pedido_atualizado = self.repo.get(pedido.id, TipoEntrega.BALCAO)
        self._recalcular_totais(pedido_atualizado)
        self.repo.commit()
        pedido = self.repo.get(pedido.id, TipoEntrega.BALCAO)

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
        self._recalcular_totais(pedido)
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)
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
        
        # IMPORTANTE: preco_unitario deve ser apenas o preço BASE do produto (sem complementos)
        # Os complementos são somados separadamente via _sum_complementos_total_relacional
        # para evitar duplicação no cálculo do total do item
        preco_unitario = product.get_preco_venda()
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
                preco_unitario=preco_unitario,
                observacao=observacao_completa,
                produto_descricao_snapshot=descricao_produto,
                complementos=body.complementos if body.complementos else None,
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
                complementos=body.complementos if body.complementos else None,
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
                complementos=body.complementos if body.complementos else None,
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
        self._recalcular_totais(pedido)
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)
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
        Atualiza um item do pedido de balcão.
        Permite atualizar quantidade, observação e complementos.
        """
        pedido = self.repo.get(pedido_id, TipoEntrega.BALCAO)
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
        pedido_atualizado = self.repo.get(pedido_id, TipoEntrega.BALCAO)
        self._recalcular_totais(pedido_atualizado)
        
        # Registra histórico
        descricao_parts = []
        if quantidade_alterada:
            descricao_parts.append(f"quantidade: {quantidade}")
        if observacao is not None:
            descricao_parts.append("observação atualizada")
        if complementos is not None:
            descricao_parts.append("complementos atualizados")
        
        descricao = f"Item {item_id} atualizado"
        if descricao_parts:
            descricao += f" ({', '.join(descricao_parts)})"
        
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedido.STATUS_ALTERADO,  # Usa STATUS_ALTERADO como fallback
            descricao=descricao,
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
        pedido_atualizado = self.repo.get(pedido.id, TipoEntrega.BALCAO)
        self._recalcular_totais(pedido_atualizado)
        self.repo.commit()
        pedido_atualizado = self.repo.get(pedido.id, TipoEntrega.BALCAO)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedido.ITEM_REMOVIDO,
            descricao=f"Item removido: ID {item_id}",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return RemoverItemResponse(
            ok=True,
            pedido_id=pedido_atualizado.id,
            valor_total=float(pedido_atualizado.valor_total or 0),
        )

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
            logger.error("Erro ao agendar notificação de cancelamento (balcão) %s: %s", pedido_id, e)

        # Notifica frontend/kanban sobre cancelamento (evento WS) (em background)
        try:
            import asyncio
            import threading
            from app.api.pedidos.utils.pedido_notification_helper import notificar_pedido_cancelado
            _pid = int(pedido_id)
            _eid = int(pedido.empresa_id) if pedido.empresa_id else None
            _cancelado_por = str(usuario_id) if usuario_id is not None else "admin"
            threading.Thread(
                target=lambda p=_pid, e=_eid, c=_cancelado_por: asyncio.run(
                    notificar_pedido_cancelado(
                        p,
                        e,
                        motivo="Pedido cancelado",
                        cancelado_por=c,
                    )
                ),
                daemon=True,
            ).start()
        except Exception as e:
            logger.error("Erro ao agendar notificação WS de cancelamento (balcão) %s: %s", pedido_id, e)

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

        pedido_atual = self.repo.get(pedido_id, TipoEntrega.BALCAO)
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

        # Notifica cliente quando o pedido (balcão) muda para "Aguardando pagamento" (status A)
        # (em background, não bloqueia a resposta do endpoint)
        try:
            if str(status_anterior) != PedidoStatusEnum.A.value and novo_status == PedidoStatusEnum.A:
                import asyncio
                import threading
                from app.api.pedidos.utils.pedido_notification_helper import (
                    notificar_cliente_pedido_pronto_aguardando_pagamento,
                )

                _pid = int(pedido_id)
                _eid = int(pedido.empresa_id) if pedido.empresa_id else None
                threading.Thread(
                    target=lambda p=_pid, e=_eid: asyncio.run(
                        notificar_cliente_pedido_pronto_aguardando_pagamento(p, e)
                    ),
                    daemon=True,
                ).start()
        except Exception as e:
            logger.error(
                "Erro ao agendar notificação de aguardando pagamento (balcão) %s: %s",
                pedido_id,
                e,
            )

        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def fechar_conta(self, pedido_id: int, payload: FecharContaBalcaoRequest | None = None, usuario_id: int | None = None) -> PedidoResponseCompleto:
        pedido_antes = self.repo.get(pedido_id, TipoEntrega.BALCAO)
        status_anterior = self._status_value(pedido_antes.status)
        mesa_id = pedido_antes.mesa_id  # Guarda mesa_id antes de fechar
        # Fechar conta: registra pagamento via transação (PAGO).
        from app.api.cardapio.repositories.repo_pagamentos import PagamentoRepository
        from app.api.cadastros.services.service_meio_pagamento import MeioPagamentoService
        from app.api.cadastros.schemas.schema_meio_pagamento import MeioPagamentoTipoEnum
        from app.api.pedidos.services.service_pedido_helpers import _dec
        from app.api.shared.schemas.schema_shared_enums import (
            PagamentoGatewayEnum,
            PagamentoMetodoEnum,
            PagamentoStatusEnum,
        )
        
        # Se receber payload, salva dados de pagamento nos campos diretos
        if payload is not None:
            if payload.troco_para is not None:
                pedido_antes.troco_para = payload.troco_para
            if payload.meio_pagamento_id is not None:
                pedido_antes.meio_pagamento_id = payload.meio_pagamento_id
            self.db.commit()
            self.db.refresh(pedido_antes)

        meio_pagamento_id = getattr(pedido_antes, "meio_pagamento_id", None)
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
        txs = pagamento_repo.list_by_pedido_id(pedido_antes.id)
        if not any(getattr(tx, "status", None) in {"PAGO", "AUTORIZADO"} for tx in txs):
            tx_nova = pagamento_repo.criar(
                pedido_id=pedido_antes.id,
                meio_pagamento_id=int(meio_pagamento_id),
                gateway=gateway.value,
                metodo=metodo.value,
                valor=_dec(getattr(pedido_antes, "valor_total", 0) or 0),
                status=PagamentoStatusEnum.PAGO.value,
                provider_transaction_id=f"manual_fechar_conta_balcao_{pedido_antes.id}_{int(meio_pagamento_id)}",
                payload_solicitacao={"origem": "fechar_conta_balcao", "usuario_id": usuario_id},
            )
            pagamento_repo.registrar_evento(tx_nova, "pago_em")

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
        # ⚠️ Não mutar `pedido.itens` aqui (delete-orphan). Filtragem deve ser feita apenas na camada de response/DTO.
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

