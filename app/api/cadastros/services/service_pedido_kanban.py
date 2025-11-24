from __future__ import annotations

from datetime import date, datetime as dt, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.api.cardapio.repositories.repo_pedidos import PedidoRepository
from app.api.cardapio.schemas.schema_pedido import (
    KanbanAgrupadoResponse,
    MeioPagamentoKanbanResponse,
    PedidoKanbanResponse,
)
from app.api.cadastros.schemas.schema_cliente import ClienteOut
from app.api.cadastros.schemas.schema_shared_enums import PedidoStatusEnum
from app.api.cardapio.services.pedidos.service_pedido_helpers import build_pagamento_resumo
from app.utils.logger import logger
from app.api.mesas.contracts.pedidos_mesa_contract import IMesaPedidosContract
from app.api.balcao.contracts.pedidos_balcao_contract import IBalcaoPedidosContract
from app.api.cadastros.repositories.repo_cliente import ClienteRepository


class KanbanService:
    """Serviço responsável pela lógica do Kanban de pedidos."""

    def __init__(
        self, 
        db: Session, 
        repo: PedidoRepository,
        mesa_contract: IMesaPedidosContract | None = None,
        balcao_contract: IBalcaoPedidosContract | None = None,
    ):
        self.db = db
        self.repo = repo
        self.mesa_contract = mesa_contract
        self.balcao_contract = balcao_contract
        self.repo_cliente = ClienteRepository(db)
    
    def _buscar_cliente_completo(self, cliente_id: int | None) -> ClienteOut | None:
        """Busca cliente completo do banco quando temos apenas o ID"""
        if not cliente_id:
            return None
        try:
            cliente = self.repo_cliente.get_by_id(cliente_id)
            if cliente:
                return ClienteOut.model_validate(cliente, from_attributes=True)
        except Exception:
            pass
        return None
    
    def _calcular_valor_total_delivery_com_receitas_combos(self, pedido) -> float:
        """
        Recalcula o valor total do pedido de delivery incluindo receitas, combos e adicionais.
        
        Inclui:
        - Itens normais e seus adicionais
        - Receitas do produtos_snapshot e seus adicionais
        - Combos do produtos_snapshot e seus adicionais
        - Desconto, taxas de entrega e serviço
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
        
        # Soma receitas e combos do produtos_snapshot
        produtos_snapshot = getattr(pedido, "produtos_snapshot", None)
        if produtos_snapshot and isinstance(produtos_snapshot, dict):
            # Receitas
            receitas = produtos_snapshot.get("receitas", [])
            for receita in receitas:
                if isinstance(receita, dict):
                    preco_unit = Dec(str(receita.get("preco_unitario", 0) or 0))
                    quantidade = Dec(str(receita.get("quantidade", 0) or 0))
                    subtotal += preco_unit * quantidade
                    
                    # Adiciona adicionais da receita
                    adicionais = receita.get("adicionais", [])
                    for adicional in adicionais:
                        try:
                            adicional_total = Dec(str(adicional.get("total", 0) or 0))
                            subtotal += adicional_total
                        except (ValueError, TypeError):
                            pass
            
            # Combos
            combos = produtos_snapshot.get("combos", [])
            for combo in combos:
                if isinstance(combo, dict):
                    preco_unit = Dec(str(combo.get("preco_unitario", 0) or 0))
                    quantidade = Dec(str(combo.get("quantidade", 0) or 0))
                    subtotal += preco_unit * quantidade
                    
                    # Adiciona adicionais do combo
                    adicionais = combo.get("adicionais", [])
                    for adicional in adicionais:
                        try:
                            adicional_total = Dec(str(adicional.get("total", 0) or 0))
                            subtotal += adicional_total
                        except (ValueError, TypeError):
                            pass
        
        # Calcula valor total final (subtotal - desconto + taxas)
        desconto = Dec(str(pedido.desconto or 0))
        taxa_entrega = Dec(str(pedido.taxa_entrega or 0))
        taxa_servico = Dec(str(pedido.taxa_servico or 0))
        
        valor_total = subtotal - desconto + taxa_entrega + taxa_servico
        if valor_total < 0:
            valor_total = Dec("0")
        
        return float(valor_total)
    
    def _calcular_valor_total_mesa_balcao_com_receitas_combos(self, pedido_completo) -> float:
        """
        Recalcula o valor total do pedido de mesa/balcão incluindo receitas, combos e adicionais.
        Usa a mesma lógica dos repositórios de mesa e balcão.
        """
        from decimal import Decimal as Dec
        
        # Soma itens e seus adicionais
        total = Dec("0")
        for item in pedido_completo.itens or []:
            item_total = (item.preco_unitario or Dec("0")) * (item.quantidade or 0)
            
            # Adiciona adicionais do item
            adicionais_snapshot = getattr(item, "adicionais_snapshot", None) or []
            for adicional in adicionais_snapshot:
                try:
                    if isinstance(adicional, dict):
                        adicional_total = adicional.get("total", 0) or 0
                    else:
                        adicional_total = getattr(adicional, "total", 0) or 0
                    item_total += Dec(str(adicional_total))
                except (AttributeError, ValueError, TypeError):
                    pass
            
            total += item_total
        
        # Soma receitas e combos do produtos_snapshot
        produtos_snapshot = getattr(pedido_completo, "produtos_snapshot", None)
        if produtos_snapshot and isinstance(produtos_snapshot, dict):
            # Receitas
            receitas = produtos_snapshot.get("receitas", [])
            for receita in receitas:
                preco_unit = Dec(str(receita.get("preco_unitario", 0) or 0))
                quantidade = Dec(str(receita.get("quantidade", 0) or 0))
                total += preco_unit * quantidade
                
                # Adiciona adicionais da receita
                adicionais = receita.get("adicionais", [])
                for adicional in adicionais:
                    adicional_total = Dec(str(adicional.get("total", 0) or 0))
                    total += adicional_total
            
            # Combos
            combos = produtos_snapshot.get("combos", [])
            for combo in combos:
                preco_unit = Dec(str(combo.get("preco_unitario", 0) or 0))
                quantidade = Dec(str(combo.get("quantidade", 0) or 0))
                total += preco_unit * quantidade
                
                # Adiciona adicionais do combo
                adicionais = combo.get("adicionais", [])
                for adicional in adicionais:
                    adicional_total = Dec(str(adicional.get("total", 0) or 0))
                    total += adicional_total
        
        if total < 0:
            total = Dec("0")
        
        return float(total)
    

    def list_all_kanban(
        self, date_filter: date, empresa_id: int = 1, limit: int = 500
    ) -> KanbanAgrupadoResponse:
        """
        Lista todos os pedidos para visualização no Kanban, agrupados por categoria.
        
        Retorna pedidos separados por categoria (DELIVERY, BALCÃO, MESAS) para evitar
        conflitos de IDs entre tabelas diferentes. Cada categoria mantém seus IDs originais.
        """
        # Inicializa listas separadas por categoria
        pedidos_delivery_list = []
        pedidos_balcao_list = []
        pedidos_mesas_list = []
        
        # Busca pedidos de DELIVERY
        pedidos_delivery = self.repo.list_all_kanban(
            date_filter=date_filter, empresa_id=empresa_id, limit=limit * 2
        )

        # Processa pedidos de DELIVERY
        for p in pedidos_delivery:
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
                    historicos = getattr(p, "historicos", []) or []
                    entregas = [h.criado_em for h in historicos if getattr(h, "status", None) == "E"]
                    entregue_em = min(entregas) if entregas else getattr(p, "data_atualizacao", None)
                    if entregue_em and getattr(p, "data_criacao", None):
                        delta_min = round(((entregue_em - p.data_criacao).total_seconds()) / 60.0, 2)
                        if delta_min >= 0:
                            tempo_entrega_minutos = float(delta_min)
            except Exception:
                tempo_entrega_minutos = None

            # Campos alternativos para cliente
            nome_cliente = None
            telefone_cliente = None
            if cliente:
                nome_cliente = cliente.nome
                telefone_cliente = cliente.telefone
            
            # Recalcula valor total incluindo receitas, combos e adicionais
            valor_total_calculado = self._calcular_valor_total_delivery_com_receitas_combos(p)
            
            pedidos_delivery_list.append(
                PedidoKanbanResponse(
                    id=p.id,
                    status=p.status,
                    cliente=ClienteOut.model_validate(cliente) if cliente else None,
                    valor_total=valor_total_calculado,
                    data_criacao=p.data_criacao,
                    endereco=endereco_str,
                    observacao_geral=p.observacao_geral,
                    meio_pagamento=MeioPagamentoKanbanResponse.model_validate(p.meio_pagamento) if p.meio_pagamento else None,
                    entregador={"id": p.entregador.id, "nome": p.entregador.nome} if getattr(p, "entregador", None) else None,
                    pagamento=build_pagamento_resumo(p),
                    acertado_entregador=getattr(p, "acertado_entregador", None),
                    tempo_entrega_minutos=tempo_entrega_minutos,
                    troco_para=float(p.troco_para) if getattr(p, "troco_para", None) is not None else None,
                    tipo_pedido="DELIVERY",
                    numero_pedido=getattr(p, "numero_pedido", None) or str(p.id),
                    nome_cliente=nome_cliente,
                    telefone_cliente=telefone_cliente,
                )
            )

        # Busca pedidos de MESA usando contrato DDD
        pedidos_mesa_dtos = []
        if self.mesa_contract:
            try:
                # Busca pedidos abertos
                pedidos_abertos = self.mesa_contract.listar_abertos(empresa_id=empresa_id)
                
                # Filtra pedidos abertos pela data de criação
                start_dt = dt.combine(date_filter, dt.min.time())
                end_dt = start_dt + timedelta(days=1)
                
                # Normaliza created_at para naive datetime se for timezone-aware
                def normalize_datetime(dt_obj):
                    if dt_obj is None:
                        return None
                    if dt_obj.tzinfo is not None:
                        # Remove timezone info convertendo para UTC e depois removendo
                        return dt_obj.replace(tzinfo=None)
                    return dt_obj
                
                pedidos_abertos_filtrados = [
                    p for p in pedidos_abertos
                    if normalize_datetime(p.created_at) is not None
                    and normalize_datetime(p.created_at) >= start_dt 
                    and normalize_datetime(p.created_at) < end_dt
                ]
                
                # Busca pedidos finalizados
                pedidos_finalizados = self.mesa_contract.listar_finalizados(
                    empresa_id=empresa_id, 
                    date_filter=date_filter
                )
                
                # Combina abertos filtrados e finalizados
                todos_mesa = pedidos_abertos_filtrados + pedidos_finalizados
                
                # Remove duplicados e ordena
                from app.api.mesas.contracts.pedidos_mesa_contract import MesaPedidoDTO
                vistos_mesa: dict[int, MesaPedidoDTO] = {}
                for pedido in todos_mesa:
                    vistos_mesa[pedido.id] = pedido
                pedidos_mesa_dtos = sorted(vistos_mesa.values(), key=lambda p: p.created_at, reverse=True)[:limit * 2]
            except Exception as e:
                logger.warning(f"[Kanban] Erro ao buscar pedidos de mesa via contrato: {e}. Continuando sem pedidos de mesa.")
                pedidos_mesa_dtos = []
        
        # Mapeamento de status Mesa → Delivery (suporta valores legados e novos)
        status_mapa_mesa = {
            "P": PedidoStatusEnum.P.value,
            "I": PedidoStatusEnum.I.value,
            "R": PedidoStatusEnum.R.value,
            "E": PedidoStatusEnum.E.value,
            "C": PedidoStatusEnum.C.value,
            "D": PedidoStatusEnum.D.value,
            "X": PedidoStatusEnum.X.value,
            "A": PedidoStatusEnum.A.value,
            # Legados
            "O": PedidoStatusEnum.I.value,  # Confirmado (antigo) → Impressão
            "T": PedidoStatusEnum.R.value,  # Pronto (antigo) → Em preparo (fluxo interno)
        }
        
        for p_mesa in pedidos_mesa_dtos:
            # p_mesa é um MesaPedidoDTO do contrato
            status_mesa = p_mesa.status
            status_delivery = status_mapa_mesa.get(status_mesa, PedidoStatusEnum.P.value)
            
            # Busca pedido completo do banco para obter numero_pedido, mesa_id, meio_pagamento e troco_para
            numero_pedido = None
            mesa_id = None
            observacoes_completas = p_mesa.observacoes
            meio_pagamento_out = None
            troco_para = None
            try:
                from app.api.mesas.models.model_pedido_mesa import PedidoMesaModel
                pedido_completo = (
                    self.db.query(PedidoMesaModel)
                    .options(joinedload(PedidoMesaModel.itens))
                    .filter_by(id=p_mesa.id)
                    .first()
                )
                if pedido_completo:
                    numero_pedido = pedido_completo.numero_pedido
                    mesa_id = pedido_completo.mesa_id
                    troco_para = float(pedido_completo.troco_para) if pedido_completo.troco_para is not None else None
                    # Usa observações do banco se disponível (mais completo que o DTO)
                    if pedido_completo.observacoes:
                        observacoes_completas = pedido_completo.observacoes
                    # Busca meio de pagamento do relacionamento
                    if pedido_completo.meio_pagamento:
                        meio_pagamento_out = MeioPagamentoKanbanResponse.model_validate(
                            pedido_completo.meio_pagamento, from_attributes=True
                        )
            except Exception:
                pass
            
            # Para mesa, endereço pode ser a mesa ou "Retirada"
            endereco_str = None
            referencia_mesa = None
            if p_mesa.mesa_numero:
                endereco_str = f"Mesa {p_mesa.mesa_numero}"
                referencia_mesa = f"Mesa {p_mesa.mesa_numero}"
            else:
                endereco_str = "Retirada"
            
            # Calcula tempo de entrega
            tempo_entrega_minutos = None
            try:
                if status_delivery == "E" and p_mesa.updated_at and p_mesa.created_at:
                    delta_min = round(((p_mesa.updated_at - p_mesa.created_at).total_seconds()) / 60.0, 2)
                    if delta_min >= 0:
                        tempo_entrega_minutos = float(delta_min)
            except Exception:
                tempo_entrega_minutos = None
            
            # Busca cliente completo se tivermos ID
            cliente_out = None
            nome_cliente = None
            telefone_cliente = None
            if p_mesa.cliente and p_mesa.cliente.id:
                cliente_out = self._buscar_cliente_completo(p_mesa.cliente.id)
                if p_mesa.cliente.nome:
                    nome_cliente = p_mesa.cliente.nome
                if cliente_out:
                    telefone_cliente = cliente_out.telefone
            
            # Objeto mesa
            mesa_obj = None
            if mesa_id:
                mesa_obj = {"id": mesa_id}
            
            # Recalcula valor total incluindo receitas, combos e adicionais
            valor_total_mesa = float(p_mesa.valor_total or 0)
            if pedido_completo:
                try:
                    valor_total_mesa = self._calcular_valor_total_mesa_balcao_com_receitas_combos(pedido_completo)
                except Exception:
                    # Em caso de erro, usa o valor do DTO como fallback
                    pass
            
            pedidos_mesas_list.append(
                PedidoKanbanResponse(
                    id=p_mesa.id,
                    status=PedidoStatusEnum(status_delivery),
                    cliente=cliente_out,
                    valor_total=valor_total_mesa,
                    data_criacao=p_mesa.created_at,
                    endereco=endereco_str,
                    observacao_geral=observacoes_completas or f"Pedido de mesa",
                    meio_pagamento=meio_pagamento_out,
                    entregador=None,  # Mesa não tem entregador
                    pagamento=None,  # Mesa não tem pagamento separado
                    acertado_entregador=None,
                    tempo_entrega_minutos=tempo_entrega_minutos,
                    troco_para=troco_para,
                    tipo_pedido="MESA",
                    numero_pedido=numero_pedido,
                    mesa_id=mesa_id,
                    mesa=mesa_obj,
                    mesa_numero=p_mesa.mesa_numero,
                    referencia_mesa=referencia_mesa,
                    nome_cliente=nome_cliente,
                    telefone_cliente=telefone_cliente,
                )
            )
        
        # Busca pedidos de BALCÃO usando contrato DDD
        pedidos_balcao_dtos = []
        if self.balcao_contract:
            try:
                # Busca pedidos abertos
                pedidos_abertos = self.balcao_contract.listar_abertos(empresa_id=empresa_id)
                
                # Filtra pedidos abertos pela data de criação
                start_dt = dt.combine(date_filter, dt.min.time())
                end_dt = start_dt + timedelta(days=1)
                
                # Normaliza created_at para naive datetime se for timezone-aware
                def normalize_datetime(dt_obj):
                    if dt_obj is None:
                        return None
                    if dt_obj.tzinfo is not None:
                        # Remove timezone info convertendo para UTC e depois removendo
                        return dt_obj.replace(tzinfo=None)
                    return dt_obj
                
                pedidos_abertos_filtrados = [
                    p for p in pedidos_abertos
                    if normalize_datetime(p.created_at) is not None
                    and normalize_datetime(p.created_at) >= start_dt 
                    and normalize_datetime(p.created_at) < end_dt
                ]
                
                # Busca pedidos finalizados
                pedidos_finalizados = self.balcao_contract.listar_finalizados(
                    empresa_id=empresa_id, 
                    date_filter=date_filter
                )
                
                # Combina abertos filtrados e finalizados
                todos_balcao = pedidos_abertos_filtrados + pedidos_finalizados
                
                # Remove duplicados e ordena
                from app.api.balcao.contracts.pedidos_balcao_contract import BalcaoPedidoDTO
                vistos_balcao: dict[int, BalcaoPedidoDTO] = {}
                for pedido in todos_balcao:
                    vistos_balcao[pedido.id] = pedido
                pedidos_balcao_dtos = sorted(vistos_balcao.values(), key=lambda p: p.created_at, reverse=True)[:limit * 2]
            except Exception as e:
                logger.warning(f"[Kanban] Erro ao buscar pedidos de balcão via contrato: {e}. Continuando sem pedidos de balcão.")
                pedidos_balcao_dtos = []
        
        # Mapeamento de status Balcão → Delivery (suporta valores legados e novos)
        status_mapa_balcao = {
            "P": PedidoStatusEnum.P.value,
            "I": PedidoStatusEnum.I.value,
            "R": PedidoStatusEnum.R.value,
            "E": PedidoStatusEnum.E.value,
            "C": PedidoStatusEnum.C.value,
            "D": PedidoStatusEnum.D.value,
            "X": PedidoStatusEnum.X.value,
            "A": PedidoStatusEnum.A.value,
            # Legados
            "O": PedidoStatusEnum.I.value,
            "T": PedidoStatusEnum.R.value,
        }
        
        for p_balcao in pedidos_balcao_dtos:
            # p_balcao é um BalcaoPedidoDTO do contrato
            status_balcao = p_balcao.status
            status_delivery = status_mapa_balcao.get(status_balcao, PedidoStatusEnum.P.value)
            
            # Busca pedido completo do banco para obter numero_pedido, mesa_id, meio_pagamento e troco_para
            numero_pedido = None
            mesa_id = None
            observacoes_completas = p_balcao.observacoes
            meio_pagamento_out = None
            troco_para = None
            try:
                from app.api.balcao.models.model_pedido_balcao import PedidoBalcaoModel
                pedido_completo = (
                    self.db.query(PedidoBalcaoModel)
                    .options(joinedload(PedidoBalcaoModel.itens))
                    .filter_by(id=p_balcao.id)
                    .first()
                )
                if pedido_completo:
                    numero_pedido = pedido_completo.numero_pedido
                    mesa_id = pedido_completo.mesa_id
                    troco_para = float(pedido_completo.troco_para) if pedido_completo.troco_para is not None else None
                    # Usa observações do banco se disponível (mais completo que o DTO)
                    if pedido_completo.observacoes:
                        observacoes_completas = pedido_completo.observacoes
                    # Busca meio de pagamento do relacionamento
                    if pedido_completo.meio_pagamento:
                        meio_pagamento_out = MeioPagamentoKanbanResponse.model_validate(
                            pedido_completo.meio_pagamento, from_attributes=True
                        )
            except Exception:
                pass
            
            # Para balcão, endereço pode ser a mesa associada ou "Balcão"
            endereco_str = None
            referencia_mesa = None
            if p_balcao.mesa_numero:
                endereco_str = f"Mesa {p_balcao.mesa_numero} (Balcão)"
                referencia_mesa = f"Mesa {p_balcao.mesa_numero}"
            else:
                endereco_str = "Balcão - Retirada"
            
            # Calcula tempo de entrega
            tempo_entrega_minutos = None
            try:
                if status_delivery == "E" and p_balcao.updated_at and p_balcao.created_at:
                    delta_min = round(((p_balcao.updated_at - p_balcao.created_at).total_seconds()) / 60.0, 2)
                    if delta_min >= 0:
                        tempo_entrega_minutos = float(delta_min)
            except Exception:
                tempo_entrega_minutos = None
            
            # Busca cliente completo se tivermos ID
            cliente_out = None
            nome_cliente = None
            telefone_cliente = None
            if p_balcao.cliente and p_balcao.cliente.id:
                cliente_out = self._buscar_cliente_completo(p_balcao.cliente.id)
                if p_balcao.cliente.nome:
                    nome_cliente = p_balcao.cliente.nome
                if cliente_out:
                    telefone_cliente = cliente_out.telefone
            
            # Objeto mesa
            mesa_obj = None
            if mesa_id:
                mesa_obj = {"id": mesa_id}
            
            # Recalcula valor total incluindo receitas, combos e adicionais
            valor_total_balcao = float(p_balcao.valor_total or 0)
            if pedido_completo:
                try:
                    valor_total_balcao = self._calcular_valor_total_mesa_balcao_com_receitas_combos(pedido_completo)
                except Exception:
                    # Em caso de erro, usa o valor do DTO como fallback
                    pass
            
            pedidos_balcao_list.append(
                PedidoKanbanResponse(
                    id=p_balcao.id,
                    status=PedidoStatusEnum(status_delivery),
                    cliente=cliente_out,
                    valor_total=valor_total_balcao,
                    data_criacao=p_balcao.created_at,
                    endereco=endereco_str,
                    observacao_geral=observacoes_completas or f"Pedido de balcão",
                    meio_pagamento=meio_pagamento_out,
                    entregador=None,  # Balcão não tem entregador
                    pagamento=None,  # Balcão não tem pagamento separado
                    acertado_entregador=None,
                    tempo_entrega_minutos=tempo_entrega_minutos,
                    troco_para=troco_para,
                    tipo_pedido="BALCAO",
                    numero_pedido=numero_pedido,
                    mesa_id=mesa_id,
                    mesa=mesa_obj,
                    mesa_numero=p_balcao.mesa_numero,
                    referencia_mesa=referencia_mesa,
                    nome_cliente=nome_cliente,
                    telefone_cliente=telefone_cliente,
                )
            )
        
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

