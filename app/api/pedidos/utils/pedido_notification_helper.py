"""
Helper para notificações de novos pedidos.
Extrai dados do pedido e envia notificação via WebSocket para o frontend.
"""
from typing import Dict, Any, Optional
import logging
from decimal import Decimal

from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel

logger = logging.getLogger(__name__)

def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _extrair_adicionais_do_item(item: Any) -> list[Dict[str, Any]]:
    """
    Extrai adicionais (com quantidade/preço) a partir do modelo relacional:
    item.complementos -> complemento.adicionais -> adicional.nome.
    """
    adicionais_out: list[Dict[str, Any]] = []

    complementos_rel = getattr(item, "complementos", None) or []
    for comp in complementos_rel:
        comp_nome = None
        comp_catalogo = getattr(comp, "complemento", None)
        if comp_catalogo is not None:
            comp_nome = getattr(comp_catalogo, "nome", None)

        adicionais_rel = getattr(comp, "adicionais", None) or []
        for ad_rel in adicionais_rel:
            catalogo_ad = getattr(ad_rel, "adicional", None)
            nome = getattr(catalogo_ad, "nome", None) if catalogo_ad is not None else None
            adicionais_out.append(
                {
                    "nome": nome or "Adicional",
                    "quantidade": int(getattr(ad_rel, "quantidade", 1) or 1),
                    "preco_unitario": _to_float(getattr(ad_rel, "preco_unitario", 0)),
                    "total": _to_float(getattr(ad_rel, "total", 0)),
                    "complemento_nome": comp_nome,
                }
            )

    return adicionais_out


def _montar_sufixo_adicionais(adicionais: list[Dict[str, Any]]) -> str:
    """
    Monta texto no formato: "+ AdicionalX + 2x AdicionalY".
    """
    if not adicionais:
        return ""

    # Agrupa por nome (e complemento, se quiser distinguir) para evitar repetição na renderização
    agrupado: dict[tuple[str, str | None], Dict[str, Any]] = {}
    for ad in adicionais:
        nome = str(ad.get("nome") or "Adicional")
        comp_nome = ad.get("complemento_nome")
        key = (nome, comp_nome)
        if key not in agrupado:
            agrupado[key] = {**ad}
            agrupado[key]["quantidade"] = int(ad.get("quantidade") or 1)
        else:
            agrupado[key]["quantidade"] = int(agrupado[key].get("quantidade") or 1) + int(ad.get("quantidade") or 1)

    partes: list[str] = []
    for (nome, _comp_nome), ad in agrupado.items():
        qtd = int(ad.get("quantidade") or 1)
        if qtd > 1:
            partes.append(f"+ {qtd}x {nome}")
        else:
            partes.append(f"+ {nome}")

    return " " + " ".join(partes) if partes else ""


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
                descricao_base = getattr(item, "produto_descricao_snapshot", None) or "Produto"
                adicionais = _extrair_adicionais_do_item(item)
                descricao_render = descricao_base + _montar_sufixo_adicionais(adicionais)
                item_data = {
                    "id": item.id,
                    # Mantém o base e também entrega uma versão "render" com adicionais no formato "+ adicionalX"
                    "produto_descricao_base": descricao_base,
                    "produto_descricao": descricao_render,
                    "quantidade": getattr(item, "quantidade", 1),
                    "preco_unitario": float(getattr(item, "preco_unitario", 0) or 0),
                    "preco_total": float(getattr(item, "preco_unitario", 0) or 0) * getattr(item, "quantidade", 1),
                    "adicionais": adicionais,
                    # compat: mesmo campo, nome explícito para o frontend usar se preferir
                    "adicionais_render": _montar_sufixo_adicionais(adicionais).strip(),
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


async def agendar_notificar_novo_pedido(*, pedido_id: int, delay_seconds: int = 0) -> None:
    """
    Notifica "novo pedido" de forma segura para o ciclo de request.

    - Cria uma sessão própria (evita DetachedInstanceError quando o request fecha a sessão do FastAPI).
    - Opcionalmente aguarda um delay (em segundos).
    """
    import asyncio
    from app.database.db_connection import SessionLocal
    from sqlalchemy.orm import joinedload

    if delay_seconds and delay_seconds > 0:
        await asyncio.sleep(int(delay_seconds))

    db_session = SessionLocal()
    try:
        # Recarrega o pedido com relacionamentos básicos necessários para montar payload do evento.
        pedido = (
            db_session.query(PedidoUnificadoModel)
            .options(
                joinedload(PedidoUnificadoModel.cliente),
                joinedload(PedidoUnificadoModel.itens),
                joinedload(PedidoUnificadoModel.mesa),
                joinedload(PedidoUnificadoModel.empresa),
            )
            .filter(PedidoUnificadoModel.id == int(pedido_id))
            .first()
        )
        if not pedido:
            logger.warning("[novo_pedido] Pedido %s não encontrado para notificação", pedido_id)
            return

        await notificar_novo_pedido(pedido)
    except Exception as e:
        logger.error("[novo_pedido] Falha ao notificar pedido %s: %s", pedido_id, e, exc_info=True)
    finally:
        db_session.close()


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
                descricao_base = getattr(item, "produto_descricao_snapshot", None) or "Produto"
                adicionais = _extrair_adicionais_do_item(item)
                descricao_render = descricao_base + _montar_sufixo_adicionais(adicionais)
                item_data = {
                    "id": item.id,
                    "produto_descricao_base": descricao_base,
                    "produto_descricao": descricao_render,
                    "quantidade": getattr(item, "quantidade", 1),
                    "preco_unitario": float(getattr(item, "preco_unitario", 0) or 0),
                    "preco_total": float(getattr(item, "preco_unitario", 0) or 0) * getattr(item, "quantidade", 1),
                    "adicionais": adicionais,
                    "adicionais_render": _montar_sufixo_adicionais(adicionais).strip(),
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


async def notificar_pedido_cancelado(
    pedido_id: int,
    empresa_id: Optional[int] = None,
    *,
    motivo: str = "Pedido cancelado",
    cancelado_por: str = "sistema",
) -> None:
    """
    Notifica o frontend sobre um pedido cancelado (evento + notificação em tempo real).

    Observação: esta notificação é independente da mensagem WhatsApp ao cliente.
    """
    from app.database.db_connection import SessionLocal
    from sqlalchemy.orm import joinedload

    db_session = SessionLocal()
    try:
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
            logger.warning(f"Pedido {pedido_id} não encontrado para notificação de cancelado")
            return

        empresa_id_final = empresa_id or pedido.empresa_id
        if not empresa_id_final:
            logger.warning(f"Pedido {pedido_id} não tem empresa_id")
            return

        from app.api.notifications.services.pedido_notification_service import PedidoNotificationService

        # Cliente
        cliente_data: Dict[str, Any] = {}
        if pedido.cliente:
            cliente_data = {
                "id": pedido.cliente.id,
                "nome": getattr(pedido.cliente, "nome", None)
                or getattr(pedido.cliente, "nome_completo", None)
                or "Cliente",
                "telefone": getattr(pedido.cliente, "telefone", None),
                "email": getattr(pedido.cliente, "email", None),
            }
        else:
            cliente_data = {"nome": "Cliente não identificado"}

        # Itens
        itens = []
        if hasattr(pedido, "itens") and pedido.itens:
            for item in pedido.itens:
                descricao_base = getattr(item, "produto_descricao_snapshot", None) or "Produto"
                adicionais = _extrair_adicionais_do_item(item)
                descricao_render = descricao_base + _montar_sufixo_adicionais(adicionais)
                itens.append(
                    {
                        "id": item.id,
                        "produto_descricao_base": descricao_base,
                        "produto_descricao": descricao_render,
                        "quantidade": getattr(item, "quantidade", 1),
                        "preco_unitario": float(getattr(item, "preco_unitario", 0) or 0),
                        "preco_total": float(getattr(item, "preco_unitario", 0) or 0) * getattr(item, "quantidade", 1),
                        "adicionais": adicionais,
                        "adicionais_render": _montar_sufixo_adicionais(adicionais).strip(),
                    }
                )

        valor_total = float(pedido.valor_total or 0)

        tipo_entrega = pedido.tipo_entrega.value if hasattr(pedido.tipo_entrega, "value") else str(pedido.tipo_entrega)
        numero_pedido = pedido.numero_pedido or str(pedido_id)

        channel_metadata = {
            "tipo_entrega": tipo_entrega,
            "numero_pedido": numero_pedido,
            "status": pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status),
            "mesa_id": pedido.mesa_id,
            "mesa_codigo": pedido.mesa.codigo if pedido.mesa and hasattr(pedido.mesa, "codigo") else None,
        }

        notification_service = PedidoNotificationService()
        await notification_service.notify_pedido_cancelado(
            empresa_id=str(empresa_id_final),
            pedido_id=str(pedido_id),
            motivo=motivo,
            cancelado_por=cancelado_por,
            channel_metadata=channel_metadata,
        )

        logger.debug(
            f"Processo de notificação de cancelado concluído: pedido_id={pedido_id}, empresa_id={empresa_id_final}"
        )
    except Exception as e:
        logger.error(f"Erro ao notificar pedido cancelado {pedido_id}: {e}", exc_info=True)
    finally:
        db_session.close()


async def notificar_cliente_pedido_cancelado(
    pedido_id: int,
    empresa_id: Optional[int] = None,
) -> None:
    """
    Notifica o cliente via WhatsApp quando o pedido é cancelado (status C).
    Envia mensagem formatada com link do site e botão "Chamar atendente".

    Executada em background (ex.: thread com asyncio.run). Cria própria sessão de DB.
    """
    from app.database.db_connection import SessionLocal
    from sqlalchemy.orm import joinedload
    from app.api.chatbot.core.config_whatsapp import format_phone_number
    from app.api.chatbot.core.notifications import OrderNotification
    from app.api.chatbot.core.utils.config_loader import ConfigLoader

    db_session = SessionLocal()
    try:
        pedido = (
            db_session.query(PedidoUnificadoModel)
            .options(
                joinedload(PedidoUnificadoModel.cliente),
                joinedload(PedidoUnificadoModel.empresa),
            )
            .filter(PedidoUnificadoModel.id == pedido_id)
            .first()
        )
        if not pedido:
            logger.warning("[Cancelado] Pedido %s não encontrado para notificação", pedido_id)
            return

        empresa_id_val = empresa_id or (pedido.empresa_id if pedido.empresa_id else None)
        if not empresa_id_val:
            logger.warning("[Cancelado] Pedido %s sem empresa_id", pedido_id)
            return

        if not pedido.cliente:
            logger.debug("[Cancelado] Pedido %s sem cliente; notificação omitida", pedido_id)
            return

        telefone_raw = getattr(pedido.cliente, "telefone", None)
        if not telefone_raw or not str(telefone_raw).strip():
            logger.warning("[Cancelado] Cliente do pedido %s sem telefone; notificação omitida", pedido_id)
            return

        telefone = format_phone_number(str(telefone_raw).strip())
        numero_pedido = pedido.numero_pedido or str(pedido_id)
        cliente_nome = getattr(pedido.cliente, "nome", None) or "Cliente"

        # Compliance WhatsApp: só enviamos mensagem "livre" se o cliente falou nas últimas 24h.
        # Caso contrário, seria necessário usar template aprovado — por enquanto, omitimos o envio.
        try:
            from app.api.chatbot.core import database as chatbot_db

            conversou_24h = chatbot_db.cliente_conversou_nas_ultimas_horas(
                db_session,
                telefone,
                empresa_id=int(empresa_id_val) if empresa_id_val is not None else None,
                horas=24,
            )
            if not conversou_24h:
                logger.info(
                    "[Cancelado] Cliente fora da janela de 24h; WhatsApp não enviado (pedido #%s, telefone=%s)",
                    numero_pedido,
                    telefone,
                )
                return
        except Exception as e:
            # Se der erro ao checar a janela, falha de forma conservadora (não envia).
            logger.warning(
                "[Cancelado] Falha ao checar janela 24h; WhatsApp não enviado (pedido #%s): %s",
                numero_pedido,
                e,
            )
            return

        try:
            loader = ConfigLoader(db_session, int(empresa_id_val))
            link_cardapio = loader.obter_link_cardapio()
        except Exception as e:
            logger.warning("[Cancelado] Erro ao obter link do cardápio (empresa %s): %s", empresa_id_val, e)
            link_cardapio = "https://chatbot.mensuraapi.com.br"

        mensagem = (
            "❌ *Pedido #%s cancelado*\n\n"
            "Olá, *%s*! 👋\n"
            "Infelizmente seu pedido foi cancelado.\n\n"
            "📱 *Quer fazer outro pedido?*\n"
            "É só acessar nosso site e pedir por lá:\n\n"
            "👉 %s\n\n"
            "💬 Precisa de ajuda? Toque no botão abaixo para *chamar um atendente*."
        ) % (numero_pedido, cliente_nome, link_cardapio)

        botoes = [{"id": "chamar_atendente", "title": "Chamar atendente"}]
        result = await OrderNotification.send_whatsapp_message_with_buttons(
            telefone,
            mensagem,
            botoes,
            empresa_id=str(empresa_id_val),
        )

        # Salva no chat interno para manter histórico (apenas quando houve envio com sucesso)
        try:
            if isinstance(result, dict) and result.get("success"):
                whatsapp_message_id = result.get("message_id")
                await OrderNotification.send_notification_async(
                    db=db_session,
                    phone=telefone,
                    message=mensagem,
                    order_type="cancelado",
                    empresa_id=int(empresa_id_val) if empresa_id_val is not None else None,
                    whatsapp_message_id=whatsapp_message_id,
                )
        except Exception as e:
            logger.warning(
                "[Cancelado] WhatsApp enviado, mas falhou ao salvar mensagem no chat (pedido %s): %s",
                pedido_id,
                e,
            )

        if result.get("success"):
            logger.info(
                "[Cancelado] Notificação de cancelamento enviada ao cliente (pedido #%s)",
                numero_pedido,
            )
        else:
            logger.warning(
                "[Cancelado] Erro ao enviar WhatsApp de cancelamento (pedido #%s): %s",
                numero_pedido,
                result.get("error", "erro desconhecido"),
            )
    except Exception as e:
        logger.error(
            "[Cancelado] Falha ao notificar cliente sobre cancelamento (pedido %s): %s",
            pedido_id,
            e,
            exc_info=True,
        )
    finally:
        db_session.close()


async def notificar_cliente_pedido_pronto_aguardando_pagamento(
    pedido_id: int,
    empresa_id: Optional[int] = None,
) -> None:
    """
    Notifica o cliente via WhatsApp quando um pedido de balcão muda para
    status "Aguardando pagamento" (status A).

    Executada em background (ex.: thread com asyncio.run). Cria própria sessão de DB.
    """
    from app.database.db_connection import SessionLocal
    from sqlalchemy.orm import joinedload
    from app.api.chatbot.core.config_whatsapp import format_phone_number
    from app.api.chatbot.core.notifications import OrderNotification

    db_session = SessionLocal()
    try:
        pedido = (
            db_session.query(PedidoUnificadoModel)
            .options(
                joinedload(PedidoUnificadoModel.cliente),
                joinedload(PedidoUnificadoModel.empresa),
            )
            .filter(PedidoUnificadoModel.id == pedido_id)
            .first()
        )
        if not pedido:
            logger.warning("[AguardandoPgto] Pedido %s não encontrado para notificação", pedido_id)
            return

        empresa_id_val = empresa_id or (pedido.empresa_id if pedido.empresa_id else None)
        if not empresa_id_val:
            logger.warning("[AguardandoPgto] Pedido %s sem empresa_id", pedido_id)
            return

        # Só envia se houver cliente e telefone
        if not pedido.cliente:
            logger.debug("[AguardandoPgto] Pedido %s sem cliente; notificação omitida", pedido_id)
            return

        telefone_raw = getattr(pedido.cliente, "telefone", None)
        if not telefone_raw or not str(telefone_raw).strip():
            logger.warning(
                "[AguardandoPgto] Cliente do pedido %s sem telefone; notificação omitida",
                pedido_id,
            )
            return

        # Garante que o pedido realmente está no status esperado (evita mensagens duplicadas/fora de hora)
        status_val = pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)
        if status_val != "A":
            logger.debug(
                "[AguardandoPgto] Pedido %s com status %s; notificação omitida",
                pedido_id,
                status_val,
            )
            return

        telefone = format_phone_number(str(telefone_raw).strip())
        numero_pedido = pedido.numero_pedido or str(pedido_id)
        cliente_nome = getattr(pedido.cliente, "nome", None) or "Cliente"

        mensagem = (
            "✅ *Pedido #%s pronto!*\n\n"
            "Olá, *%s*! 👋\n"
            "Seu pedido está pronto e *aguardando pagamento* no balcão.\n\n"
            "💬 Se precisar de ajuda, toque no botão abaixo para *chamar um atendente*."
        ) % (numero_pedido, cliente_nome)

        botoes = [{"id": "chamar_atendente", "title": "Chamar atendente"}]
        result = await OrderNotification.send_whatsapp_message_with_buttons(
            telefone,
            mensagem,
            botoes,
            empresa_id=str(empresa_id_val),
        )

        if result.get("success"):
            # Salva a mensagem no banco (chatbot.messages) para histórico no atendimento
            try:
                await OrderNotification.send_notification_async(
                    db=db_session,
                    phone=telefone,
                    message=mensagem,
                    order_type="balcao",
                    empresa_id=int(empresa_id_val),
                    whatsapp_message_id=result.get("message_id"),
                )
            except Exception as e:
                logger.warning(
                    "[AguardandoPgto] WhatsApp enviado, mas falhou ao salvar mensagem no chat (pedido %s): %s",
                    pedido_id,
                    e,
                )

            logger.info(
                "[AguardandoPgto] Notificação enviada ao cliente (pedido #%s)",
                numero_pedido,
            )
        else:
            logger.warning(
                "[AguardandoPgto] Erro ao enviar WhatsApp (pedido #%s): %s",
                numero_pedido,
                result.get("error", "erro desconhecido"),
            )
    except Exception as e:
        logger.error(
            "[AguardandoPgto] Falha ao notificar cliente (pedido %s): %s",
            pedido_id,
            e,
            exc_info=True,
        )
    finally:
        db_session.close()

