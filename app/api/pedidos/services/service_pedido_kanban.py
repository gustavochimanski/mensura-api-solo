from __future__ import annotations

from datetime import date, datetime as dt, timedelta
from decimal import Decimal
from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel, TipoEntrega, StatusPedido
from app.api.pedidos.schemas.schema_pedido import (
    KanbanAgrupadoResponse,
    MeioPagamentoKanbanResponse,
    PedidoKanbanResponse,
    ClienteKanbanSimplificado,
    PedidoPagamentoResumoKanban,
)
from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum
from app.api.pedidos.services.service_pedido_helpers import build_pagamento_resumo
from app.utils.logger import logger
from app.api.cadastros.repositories.repo_cliente import ClienteRepository


class KanbanService:
    """Serviço responsável pela lógica do Kanban de pedidos usando modelos unificados."""

    def __init__(self, db: Session, repo: PedidoRepository):
        self.db = db
        self.repo = repo
        self.repo_cliente = ClienteRepository(db)
    
    def _buscar_cliente_simplificado(self, cliente_id: int | None) -> ClienteKanbanSimplificado | None:
        """Busca apenas campos do cliente necessários para o kanban"""
        if not cliente_id:
            return None
        try:
            cliente = self.repo_cliente.get_by_id(cliente_id)
            if cliente:
                return ClienteKanbanSimplificado(
                    id=cliente.id,
                    nome=cliente.nome,
                    telefone=cliente.telefone
                )
        except Exception:
            pass
        return None
    
    def _calcular_valor_total_com_receitas_combos(self, pedido: PedidoUnificadoModel) -> float:
        """
        Recalcula o valor total do pedido incluindo receitas, combos e adicionais.
        
        Funciona para todos os tipos de pedidos (DELIVERY, MESA, BALCAO).
        """
        from decimal import Decimal as Dec
        
        subtotal = Dec("0")
        
        # Soma itens normais e seus adicionais
        for item in pedido.itens or []:
            item_total = (item.preco_unitario or Dec("0")) * (item.quantidade or 0)
            
            # Adiciona adicionais do item
            adicionais_snapshot = getattr(item, "adicionais_snapshot", None) or []
            if adicionais_snapshot:
                for adicional in adicionais_snapshot:
                    try:
                        if isinstance(adicional, dict):
                            adicional_total = adicional.get("total", 0) or 0
                        else:
                            adicional_total = getattr(adicional, "total", 0) or 0
                        item_total += Dec(str(adicional_total))
                    except (AttributeError, ValueError, TypeError):
                        pass
            
            subtotal += item_total
        
        # Para delivery, adiciona taxas; para mesa/balcão, apenas desconto
        if pedido.is_delivery():
            desconto = Dec(str(pedido.desconto or 0))
            taxa_entrega = Dec(str(pedido.taxa_entrega or 0))
            taxa_servico = Dec(str(pedido.taxa_servico or 0))
            valor_total = subtotal - desconto + taxa_entrega + taxa_servico
        else:
            # Mesa e balcão não têm taxas de entrega
            desconto = Dec(str(pedido.desconto or 0))
            taxa_servico = Dec(str(pedido.taxa_servico or 0))
            valor_total = subtotal - desconto + taxa_servico
        
        if valor_total < 0:
            valor_total = Dec("0")
        
        return float(valor_total)
    
    def _buscar_pedidos_por_tipo(
        self, 
        tipo_pedido: str, 
        date_filter: date, 
        empresa_id: int, 
        limit: int
    ) -> list[PedidoUnificadoModel]:
        """Busca pedidos de um tipo específico para a data filtrada."""
        start_dt = dt.combine(date_filter, dt.min.time())
        end_dt = start_dt + timedelta(days=1)
        
        query = (
            self.db.query(PedidoUnificadoModel)
            .options(
                joinedload(PedidoUnificadoModel.itens),
                joinedload(PedidoUnificadoModel.cliente),
                joinedload(PedidoUnificadoModel.mesa),
                joinedload(PedidoUnificadoModel.empresa),
                joinedload(PedidoUnificadoModel.meio_pagamento),
                joinedload(PedidoUnificadoModel.entregador),
            )
            .filter(
                and_(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_entrega == tipo_pedido,
                    PedidoUnificadoModel.created_at >= start_dt,
                    PedidoUnificadoModel.created_at < end_dt,
                )
            )
            .order_by(PedidoUnificadoModel.created_at.desc())
            .limit(limit * 2)
        )
        
        return query.all()
    
    def _processar_pedido_delivery(self, p: PedidoUnificadoModel) -> PedidoKanbanResponse:
        """Processa um pedido de delivery para o kanban."""
        cliente = p.cliente

        endereco_str = None
        if p.endereco_snapshot:
            snapshot = p.endereco_snapshot
            endereco_str = ", ".join(
                filter(None, [
                    snapshot.get("logradouro"),
                    snapshot.get("numero"),
                    snapshot.get("bairro"),
                    snapshot.get("cidade"),
                    snapshot.get("cep"),
                    snapshot.get("complemento"),
                ])
            )
        elif p.endereco:
            endereco_model = p.endereco
            endereco_str = ", ".join(
                filter(None, [
                    endereco_model.logradouro,
                    endereco_model.numero,
                    endereco_model.bairro,
                    endereco_model.cidade,
                    endereco_model.cep,
                    endereco_model.complemento,
                ])
            )
        elif cliente and cliente.enderecos:
            endereco_model = cliente.enderecos[0]
            endereco_str = ", ".join(
                filter(None, [
                    endereco_model.logradouro,
                    endereco_model.numero,
                    endereco_model.bairro,
                    endereco_model.cidade,
                    endereco_model.cep,
                    endereco_model.complemento,
                ])
            )

        # Calcula tempo de entrega em minutos apenas quando status = 'E'
        tempo_entrega_minutos = None
        try:
            status_str = p.status if isinstance(p.status, str) else getattr(p.status, "value", str(p.status))
            if status_str == "E":
                historicos = getattr(p, "historico", []) or []
                entregas = [h.criado_em for h in historicos if getattr(h, "status", None) == "E"]
                entregue_em = min(entregas) if entregas else getattr(p, "updated_at", None)
                if entregue_em and getattr(p, "created_at", None):
                    delta_min = round(((entregue_em - p.created_at).total_seconds()) / 60.0, 2)
                    if delta_min >= 0:
                        tempo_entrega_minutos = float(delta_min)
        except Exception:
            tempo_entrega_minutos = None

        # Campos alternativos para cliente
        nome_cliente = None
        telefone_cliente = None
        cliente_simplificado = None
        if cliente:
            nome_cliente = cliente.nome
            telefone_cliente = cliente.telefone
            cliente_simplificado = ClienteKanbanSimplificado(
                id=cliente.id,
                nome=cliente.nome,
                telefone=cliente.telefone
            )
        
        # Recalcula valor total incluindo receitas, combos e adicionais
        valor_total_calculado = self._calcular_valor_total_com_receitas_combos(p)
        
        # Meio de pagamento simplificado (apenas nome)
        meio_pagamento_simplificado = None
        if p.meio_pagamento:
            meio_pagamento_simplificado = MeioPagamentoKanbanResponse(
                nome=p.meio_pagamento.nome
            )
        
        # Pagamento simplificado (apenas campos usados pelo front)
        pagamento_simplificado = None
        pagamento_resumo = build_pagamento_resumo(p)
        if pagamento_resumo:
            pagamento_simplificado = PedidoPagamentoResumoKanban(
                meio_pagamento_nome=pagamento_resumo.meio_pagamento_nome,
                esta_pago=pagamento_resumo.esta_pago
            )
        
        return PedidoKanbanResponse(
            id=p.id,
            status=p.status,
            cliente=cliente_simplificado,
            valor_total=valor_total_calculado,
            data_criacao=p.created_at,
            endereco=endereco_str,
            observacao_geral=p.observacao_geral,
            meio_pagamento=meio_pagamento_simplificado,
            entregador={"id": p.entregador.id, "nome": p.entregador.nome} if getattr(p, "entregador", None) else None,
            pagamento=pagamento_simplificado,
            acertado_entregador=getattr(p, "acertado_entregador", None),
            tempo_entrega_minutos=tempo_entrega_minutos,
            troco_para=float(p.troco_para) if getattr(p, "troco_para", None) is not None else None,
            tipo_pedido="DELIVERY",
            numero_pedido=getattr(p, "numero_pedido", None) or str(p.id),
            nome_cliente=nome_cliente,
            telefone_cliente=telefone_cliente,
        )
    
    def _processar_pedido_mesa(self, p: PedidoUnificadoModel) -> PedidoKanbanResponse:
        """Processa um pedido de mesa para o kanban."""
        # Para mesa, endereço pode ser a mesa ou "Retirada"
        endereco_str = None
        referencia_mesa = None
        mesa_numero = None
        if p.mesa:
            mesa_numero = getattr(p.mesa, "numero", None)
            if mesa_numero:
                endereco_str = f"Mesa {mesa_numero}"
                referencia_mesa = f"Mesa {mesa_numero}"
            else:
                endereco_str = "Retirada"
        else:
            endereco_str = "Retirada"
        
        # Calcula tempo de entrega
        tempo_entrega_minutos = None
        try:
            status_str = p.status if isinstance(p.status, str) else getattr(p.status, "value", str(p.status))
            if status_str == "E" and p.updated_at and p.created_at:
                delta_min = round(((p.updated_at - p.created_at).total_seconds()) / 60.0, 2)
                if delta_min >= 0:
                    tempo_entrega_minutos = float(delta_min)
        except Exception:
            tempo_entrega_minutos = None
        
        # Busca cliente simplificado se tivermos ID
        cliente_simplificado = None
        nome_cliente = None
        telefone_cliente = None
        if p.cliente_id:
            cliente_simplificado = self._buscar_cliente_simplificado(p.cliente_id)
            if p.cliente:
                nome_cliente = p.cliente.nome
            if cliente_simplificado:
                telefone_cliente = cliente_simplificado.telefone
        
        # Objeto mesa
        mesa_obj = None
        if p.mesa_id:
            mesa_obj = {"id": p.mesa_id}
        
        # Recalcula valor total incluindo receitas, combos e adicionais
        valor_total_mesa = self._calcular_valor_total_com_receitas_combos(p)
        
        # Meio de pagamento simplificado (apenas nome)
        meio_pagamento_simplificado = None
        if p.meio_pagamento:
            meio_pagamento_simplificado = MeioPagamentoKanbanResponse(
                nome=p.meio_pagamento.nome
            )
        
        return PedidoKanbanResponse(
            id=p.id,
            status=p.status,
            cliente=cliente_simplificado,
            valor_total=valor_total_mesa,
            data_criacao=p.created_at,
            endereco=endereco_str,
            observacao_geral=p.observacoes or p.observacao_geral or "Pedido de mesa",
            meio_pagamento=meio_pagamento_simplificado,
            entregador=None,  # Mesa não tem entregador
            pagamento=None,  # Mesa não tem pagamento separado
            acertado_entregador=None,
            tempo_entrega_minutos=tempo_entrega_minutos,
            troco_para=float(p.troco_para) if getattr(p, "troco_para", None) is not None else None,
            tipo_pedido="MESA",
            numero_pedido=getattr(p, "numero_pedido", None) or str(p.id),
            mesa_id=p.mesa_id,
            mesa=mesa_obj,
            mesa_numero=mesa_numero,
            referencia_mesa=referencia_mesa,
            nome_cliente=nome_cliente,
            telefone_cliente=telefone_cliente,
        )
    
    def _processar_pedido_balcao(self, p: PedidoUnificadoModel) -> PedidoKanbanResponse:
        """Processa um pedido de balcão para o kanban."""
        # Para balcão, endereço pode ser a mesa associada ou "Balcão"
        endereco_str = None
        referencia_mesa = None
        mesa_numero = None
        if p.mesa:
            mesa_numero = getattr(p.mesa, "numero", None)
            if mesa_numero:
                endereco_str = f"Mesa {mesa_numero} (Balcão)"
                referencia_mesa = f"Mesa {mesa_numero}"
            else:
                endereco_str = "Balcão - Retirada"
        else:
            endereco_str = "Balcão - Retirada"
        
        # Calcula tempo de entrega
        tempo_entrega_minutos = None
        try:
            status_str = p.status if isinstance(p.status, str) else getattr(p.status, "value", str(p.status))
            if status_str == "E" and p.updated_at and p.created_at:
                delta_min = round(((p.updated_at - p.created_at).total_seconds()) / 60.0, 2)
                if delta_min >= 0:
                    tempo_entrega_minutos = float(delta_min)
        except Exception:
            tempo_entrega_minutos = None
        
        # Busca cliente simplificado se tivermos ID
        cliente_simplificado = None
        nome_cliente = None
        telefone_cliente = None
        if p.cliente_id:
            cliente_simplificado = self._buscar_cliente_simplificado(p.cliente_id)
            if p.cliente:
                nome_cliente = p.cliente.nome
            if cliente_simplificado:
                telefone_cliente = cliente_simplificado.telefone
        
        # Objeto mesa
        mesa_obj = None
        if p.mesa_id:
            mesa_obj = {"id": p.mesa_id}
        
        # Recalcula valor total incluindo receitas, combos e adicionais
        valor_total_balcao = self._calcular_valor_total_com_receitas_combos(p)
        
        # Meio de pagamento simplificado (apenas nome)
        meio_pagamento_simplificado = None
        if p.meio_pagamento:
            meio_pagamento_simplificado = MeioPagamentoKanbanResponse(
                nome=p.meio_pagamento.nome
            )
        
        return PedidoKanbanResponse(
            id=p.id,
            status=p.status,
            cliente=cliente_simplificado,
            valor_total=valor_total_balcao,
            data_criacao=p.created_at,
            endereco=endereco_str,
            observacao_geral=p.observacoes or p.observacao_geral or "Pedido de balcão",
            meio_pagamento=meio_pagamento_simplificado,
            entregador=None,  # Balcão não tem entregador
            pagamento=None,  # Balcão não tem pagamento separado
            acertado_entregador=None,
            tempo_entrega_minutos=tempo_entrega_minutos,
            troco_para=float(p.troco_para) if getattr(p, "troco_para", None) is not None else None,
            tipo_pedido="BALCAO",
            numero_pedido=getattr(p, "numero_pedido", None) or str(p.id),
            mesa_id=p.mesa_id,
            mesa=mesa_obj,
            mesa_numero=mesa_numero,
            referencia_mesa=referencia_mesa,
            nome_cliente=nome_cliente,
            telefone_cliente=telefone_cliente,
        )

    def list_all_kanban(
        self, date_filter: date, empresa_id: int = 1, limit: int = 500
    ) -> KanbanAgrupadoResponse:
        """
        Lista todos os pedidos para visualização no Kanban, agrupados por categoria.
        
        Usa o modelo unificado PedidoUnificadoModel para buscar todos os tipos de pedidos.
        """
        # Busca pedidos de DELIVERY
        pedidos_delivery = self.repo.list_all_kanban(
            date_filter=date_filter, empresa_id=empresa_id, limit=limit * 2
        )
        pedidos_delivery_list = [self._processar_pedido_delivery(p) for p in pedidos_delivery]

        # Busca pedidos de MESA
        try:
            pedidos_mesa = self._buscar_pedidos_por_tipo(
                tipo_pedido=TipoEntrega.MESA.value,
                date_filter=date_filter,
                empresa_id=empresa_id,
                limit=limit
            )
            pedidos_mesas_list = [self._processar_pedido_mesa(p) for p in pedidos_mesa]
        except Exception as e:
            logger.warning(f"[Kanban] Erro ao buscar pedidos de mesa: {e}. Continuando sem pedidos de mesa.")
            pedidos_mesas_list = []
        
        # Busca pedidos de BALCÃO
        try:
            pedidos_balcao = self._buscar_pedidos_por_tipo(
                tipo_pedido=TipoEntrega.BALCAO.value,
                date_filter=date_filter,
                empresa_id=empresa_id,
                limit=limit
            )
            pedidos_balcao_list = [self._processar_pedido_balcao(p) for p in pedidos_balcao]
        except Exception as e:
            logger.warning(f"[Kanban] Erro ao buscar pedidos de balcão: {e}. Continuando sem pedidos de balcão.")
            pedidos_balcao_list = []
        
        # Ordena cada categoria por data de criação (mais recentes primeiro)
        pedidos_delivery_list.sort(key=lambda p: p.data_criacao, reverse=True)
        pedidos_balcao_list.sort(key=lambda p: p.data_criacao, reverse=True)
        pedidos_mesas_list.sort(key=lambda p: p.data_criacao, reverse=True)
        
        # Aplica limite por categoria
        pedidos_delivery_list = pedidos_delivery_list[:limit]
        pedidos_balcao_list = pedidos_balcao_list[:limit]
        pedidos_mesas_list = pedidos_mesas_list[:limit]
        
        # Retorna estrutura agrupada
        return KanbanAgrupadoResponse(
            delivery=pedidos_delivery_list,
            balcao=pedidos_balcao_list,
            mesas=pedidos_mesas_list,
        )
