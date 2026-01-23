"""
Helper para notificações de novos pedidos.
Extrai dados do pedido e envia notificação via WebSocket para o frontend.
"""
from typing import Dict, Any, Optional
import logging
from decimal import Decimal

from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel

logger = logging.getLogger(__name__)


async def notificar_novo_pedido(pedido: PedidoUnificadoModel) -> None:
    """
    Notifica o frontend sobre um novo pedido criado.
    
    Esta função é chamada de forma assíncrona após a criação do pedido,
    sem bloquear o fluxo principal.
    
    Args:
        pedido: Instância do PedidoUnificadoModel com todos os relacionamentos carregados
    """
    # Extrai o ID do pedido logo no início para evitar DetachedInstanceError
    # caso o objeto seja desconectado da sessão durante operações assíncronas
    try:
        pedido_id = str(pedido.id)
        empresa_id = str(pedido.empresa_id)
    except Exception as e:
        logger.error(f"Erro ao extrair IDs do pedido: {e}", exc_info=True)
        return
    
    try:
        from app.api.notifications.services.pedido_notification_service import PedidoNotificationService
        
        # Extrai dados do cliente
        cliente_data: Dict[str, Any] = {}
        if pedido.cliente:
            cliente_data = {
                "id": pedido.cliente.id,
                "nome": getattr(pedido.cliente, "nome", None) or getattr(pedido.cliente, "nome_completo", None) or "Cliente",
                "telefone": getattr(pedido.cliente, "telefone", None),
                "email": getattr(pedido.cliente, "email", None),
            }
        else:
            cliente_data = {
                "nome": "Cliente não identificado",
            }
        
        # Extrai itens do pedido
        itens = []
        if hasattr(pedido, "itens") and pedido.itens:
            for item in pedido.itens:
                item_data = {
                    "id": item.id,
                    "produto_descricao": getattr(item, "produto_descricao_snapshot", None) or "Produto",
                    "quantidade": getattr(item, "quantidade", 1),
                    "preco_unitario": float(getattr(item, "preco_unitario", 0) or 0),
                    "preco_total": float(getattr(item, "preco_unitario", 0) or 0) * getattr(item, "quantidade", 1),
                }
                itens.append(item_data)
        
        # Valor total do pedido
        valor_total = float(pedido.valor_total or 0)
        
        # Informações adicionais sobre o pedido
        tipo_entrega = pedido.tipo_entrega.value if hasattr(pedido.tipo_entrega, "value") else str(pedido.tipo_entrega)
        numero_pedido = pedido.numero_pedido or pedido_id
        
        # Metadados adicionais
        channel_metadata = {
            "tipo_entrega": tipo_entrega,
            "numero_pedido": numero_pedido,
            "status": pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status),
            "mesa_id": pedido.mesa_id,
            "mesa_codigo": pedido.mesa.codigo if pedido.mesa and hasattr(pedido.mesa, "codigo") else None,
        }
        
        # Chama o serviço de notificação
        notification_service = PedidoNotificationService()
        event_id = await notification_service.notify_novo_pedido(
            empresa_id=empresa_id,
            pedido_id=pedido_id,
            cliente_data=cliente_data,
            itens=itens,
            valor_total=valor_total,
            channel_metadata=channel_metadata
        )
        
        # O log de sucesso/aviso já é feito dentro do notify_novo_pedido
        logger.debug(f"Processo de notificação concluído: pedido_id={pedido_id}, empresa_id={empresa_id}, event_id={event_id}")
        
    except Exception as e:
        # Loga o erro mas não propaga para não quebrar o fluxo de criação do pedido
        # Usa pedido_id extraído no início para evitar DetachedInstanceError
        logger.error(f"Erro ao notificar novo pedido {pedido_id}: {e}", exc_info=True)


async def notificar_pedido_impresso(pedido_id: int, empresa_id: Optional[int] = None) -> None:
    """
    Notifica o frontend sobre um pedido marcado como impresso (notificação kanban).
    
    Esta função é chamada de forma assíncrona após o pedido ser marcado como impresso,
    sem bloquear o fluxo principal.
    
    Args:
        pedido_id: ID do pedido que foi marcado como impresso
        empresa_id: ID da empresa (opcional, será buscado do pedido se não fornecido)
    """
    # Cria uma nova sessão do banco para a thread assíncrona
    from app.database.db_connection import SessionLocal
    from sqlalchemy.orm import joinedload
    db_session = SessionLocal()
    
    try:
        # Recarrega o pedido com os relacionamentos necessários
        pedido = (
            db_session.query(PedidoUnificadoModel)
            .options(
                joinedload(PedidoUnificadoModel.cliente),
                joinedload(PedidoUnificadoModel.itens),
                joinedload(PedidoUnificadoModel.mesa),
                joinedload(PedidoUnificadoModel.empresa),
            )
            .filter(PedidoUnificadoModel.id == pedido_id)
            .first()
        )
        
        if not pedido:
            logger.warning(f"Pedido {pedido_id} não encontrado para notificação de impresso")
            return
        
        # Usa empresa_id do pedido se não foi fornecido
        empresa_id_final = empresa_id or pedido.empresa_id
        if not empresa_id_final:
            logger.warning(f"Pedido {pedido_id} não tem empresa_id")
            return
        
        from app.api.notifications.services.pedido_notification_service import PedidoNotificationService
        
        # Extrai dados do cliente
        cliente_data: Dict[str, Any] = {}
        if pedido.cliente:
            cliente_data = {
                "id": pedido.cliente.id,
                "nome": getattr(pedido.cliente, "nome", None) or getattr(pedido.cliente, "nome_completo", None) or "Cliente",
                "telefone": getattr(pedido.cliente, "telefone", None),
                "email": getattr(pedido.cliente, "email", None),
            }
        else:
            cliente_data = {
                "nome": "Cliente não identificado",
            }
        
        # Extrai itens do pedido
        itens = []
        if hasattr(pedido, "itens") and pedido.itens:
            for item in pedido.itens:
                item_data = {
                    "id": item.id,
                    "produto_descricao": getattr(item, "produto_descricao_snapshot", None) or "Produto",
                    "quantidade": getattr(item, "quantidade", 1),
                    "preco_unitario": float(getattr(item, "preco_unitario", 0) or 0),
                    "preco_total": float(getattr(item, "preco_unitario", 0) or 0) * getattr(item, "quantidade", 1),
                }
                itens.append(item_data)
        
        # Valor total do pedido
        valor_total = float(pedido.valor_total or 0)
        
        # Informações adicionais sobre o pedido
        tipo_entrega = pedido.tipo_entrega.value if hasattr(pedido.tipo_entrega, "value") else str(pedido.tipo_entrega)
        numero_pedido = pedido.numero_pedido or str(pedido_id)
        pedido_id_str = str(pedido_id)
        empresa_id_str = str(empresa_id_final)
        
        # Metadados adicionais
        channel_metadata = {
            "tipo_entrega": tipo_entrega,
            "numero_pedido": numero_pedido,
            "status": pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status),
            "mesa_id": pedido.mesa_id,
            "mesa_codigo": pedido.mesa.codigo if pedido.mesa and hasattr(pedido.mesa, "codigo") else None,
        }
        
        # Chama o serviço de notificação
        notification_service = PedidoNotificationService()
        sent_count = await notification_service.notify_pedido_impresso(
            empresa_id=empresa_id_str,
            pedido_id=pedido_id_str,
            cliente_data=cliente_data,
            itens=itens,
            valor_total=valor_total,
            channel_metadata=channel_metadata
        )
        
        logger.debug(f"Processo de notificação kanban concluído: pedido_id={pedido_id_str}, empresa_id={empresa_id_str}, sent_count={sent_count}")
        
    except Exception as e:
        # Loga o erro mas não propaga para não quebrar o fluxo de marcação como impresso
        logger.error(f"Erro ao notificar pedido impresso {pedido_id}: {e}", exc_info=True)
    finally:
        # Fecha a sessão do banco
        db_session.close()


