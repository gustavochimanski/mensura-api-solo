"""
Módulo de notificações de pedidos
Integra com cardápio, mesas e balcão para enviar notificações aos clientes
Suporta envio via WhatsApp Business API (Meta) e chat interno
"""
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)


class OrderNotification:
    """Gerenciador de notificações de pedidos"""

    @staticmethod
    async def send_whatsapp_message(phone: str, message: str) -> Dict:
        """
        Envia mensagem via WhatsApp Business API (Meta)

        Args:
            phone: Número de telefone (formato: 5511999999999)
            message: Texto da mensagem

        Returns:
            Dict com resultado do envio
        """
        try:
            from .config_whatsapp import WHATSAPP_CONFIG, get_whatsapp_url, get_headers, format_phone_number

            # Formata o número para o padrão WhatsApp
            phone_formatted = format_phone_number(phone)

            # URL da API
            url = get_whatsapp_url()

            # Headers com token de autorização
            headers = get_headers()

            # Payload da mensagem
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_formatted,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": message
                }
            }

            # Envia a mensagem (Cloud API) - compatível com modo de coexistência
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "provider": "WhatsApp Business API (Meta)",
                        "phone": phone_formatted,
                        "message_id": result.get("messages", [{}])[0].get("id"),
                        "status": "sent",
                        "response": result
                    }

                error_data = response.json() if response.text else {}
                error_detail = error_data.get("error", {}) if isinstance(error_data, dict) else {}

                coexistence_hint = None
                # Dica adicional quando houver conflito de registro do número
                if response.status_code in (400, 403, 409):
                    coexistence_hint = (
                        "Verifique se o número foi conectado no modo 'App e API' na Meta "
                        "(coexistência) e se o app WhatsApp Business está atualizado."
                    )

                return {
                    "success": False,
                    "provider": "WhatsApp Business API (Meta)",
                    "error": error_detail.get("message", response.text),
                    "status_code": response.status_code,
                    "phone": phone_formatted,
                    "coexistence_hint": coexistence_hint
                }

        except Exception as e:
            return {
                "success": False,
                "provider": "WhatsApp Business API (Meta)",
                "error": str(e),
                "phone": phone
            }

    @staticmethod
    def format_cardapio_notification(order_data: Dict) -> str:
        """Formata notificação de pedido delivery/cardápio"""
        message = f"""🍕 *Pedido Confirmado - Delivery*

Olá *{order_data['client_name']}*! 👋

Seu pedido #{order_data['order_id']} foi confirmado com sucesso!

📦 *Itens do Pedido:*
{order_data['items']}

💰 *Total:* {order_data['total']}

📍 *Endereço de Entrega:*
{order_data['address']}

⏱️ *Tempo Estimado:* {order_data['estimated_time']}

Aguarde, em breve seu pedido estará a caminho! 🚚

_Qualquer dúvida, entre em contato conosco._"""

        return message

    @staticmethod
    def format_mesa_notification(order_data: Dict) -> str:
        """Formata notificação de pedido de mesa"""
        message = f"""🍽️ *Pedido Confirmado - Mesa {order_data['table_number']}*

Olá *{order_data['client_name']}*! 👋

Seu pedido #{order_data['order_id']} foi confirmado!

📦 *Itens do Pedido:*
{order_data['items']}

💰 *Total:* {order_data['total']}

🪑 *Mesa:* {order_data['table_number']}

Seu pedido já está sendo preparado! Em breve será servido. 👨‍🍳

_Bom apetite!_"""

        return message

    @staticmethod
    def format_balcao_notification(order_data: Dict) -> str:
        """Formata notificação de pedido de balcão"""
        message = f"""🏪 *Pedido Confirmado - Balcão*

Olá *{order_data['client_name']}*! 👋

Seu pedido #{order_data['order_id']} foi confirmado!

📦 *Itens do Pedido:*
{order_data['items']}

💰 *Total:* {order_data['total']}

⏱️ *Tempo de Preparo:* {order_data['preparation_time']}

Aguarde na fila do balcão. Avisaremos quando estiver pronto! 🔔

_Obrigado pela preferência!_"""

        return message

    @staticmethod
    async def send_notification_async(db: Session, phone: str, message: str, order_type: str) -> Dict:
        """
        Envia notificação como mensagem no chat (versão async)

        O número de telefone do cliente vira o user_id no chat
        A IA envia automaticamente a mensagem de confirmação
        """
        from . import database as chatbot_db

        try:
            # Use o telefone como user_id
            user_id = phone
            session_id = f"order_{order_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Garante que o prompt padrão existe para não violar a FK da tabela
            prompt_key = "default"
            if not chatbot_db.get_prompt(db, prompt_key):
                chatbot_db.create_prompt(
                    db=db,
                    key=prompt_key,
                    name="Padrão (Notificações)",
                    content="Atendente virtual para notificações automáticas.",
                    is_default=True
                )

            # Cria ou busca conversa existente para esse usuário
            conversations = chatbot_db.get_conversations_by_user(db, user_id)

            if conversations:
                # Usa a conversa mais recente
                conversation_id = conversations[0]['id']
                # Busca empresa_id da conversa
                conversation = chatbot_db.get_conversation(db, conversation_id)
                empresa_id = conversation.get('empresa_id') if conversation else None
            else:
                # Cria nova conversa
                conversation_id = chatbot_db.create_conversation(
                    db=db,
                    session_id=session_id,
                    user_id=user_id,
                    prompt_key=prompt_key,
                    model="notification-system"
                )
                empresa_id = None

            # Adiciona a mensagem de notificação como resposta da IA
            message_id = chatbot_db.create_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=message
            )

            # Envia notificação WebSocket para atualizar o frontend
            try:
                await send_chatbot_websocket_notification(
                    empresa_id=empresa_id,
                    notification_type="chatbot_message",
                    title="Nova Notificação",
                    message=f"Notificação de {order_type} enviada",
                    data={
                        "conversation_id": conversation_id,
                        "message_id": message_id,
                        "user_id": user_id,
                        "phone": phone,
                        "order_type": order_type,
                        "role": "assistant"
                    }
                )
            except Exception as e:
                # Não falha a operação se WebSocket falhar
                logger.warning(f"Erro ao enviar notificação WebSocket: {e}")

            notification_log = {
                "success": True,
                "phone": phone,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message": message,
                "order_type": order_type,
                "sent_at": datetime.now().isoformat(),
                "provider": "Chat Interno",
                "status": "delivered"
            }

            return notification_log

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "phone": phone
            }

    @staticmethod
    def send_notification(db: Session, phone: str, message: str, order_type: str) -> Dict:
        """
        Envia notificação como mensagem no chat (versão síncrona - mantida para compatibilidade)
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            OrderNotification.send_notification_async(db, phone, message, order_type)
        )

    @classmethod
    async def notify_order_confirmed_async(cls, db: Session, order_data: Dict, order_type: str) -> Dict:
        """
        Processa e envia notificação de pedido confirmado (versão async)

        Args:
            db: Sessão do banco de dados
            order_data: Dados do pedido
            order_type: Tipo do pedido (cardapio, mesa, balcao)

        Returns:
            Dict com resultado do envio
        """
        from .config_whatsapp import WHATSAPP_CONFIG

        # Formata mensagem baseada no tipo de pedido
        if order_type == "cardapio":
            message = cls.format_cardapio_notification(order_data)
        elif order_type == "mesa":
            message = cls.format_mesa_notification(order_data)
        elif order_type == "balcao":
            message = cls.format_balcao_notification(order_data)
        else:
            return {
                "success": False,
                "error": "Tipo de pedido inválido"
            }

        # Valida telefone
        phone = order_data.get('client_phone')
        if not phone:
            return {
                "success": False,
                "error": "Telefone do cliente não fornecido"
            }

        results = {
            "whatsapp_api": None,
            "chat_interno": None,
            "success": False
        }

        # Sempre salva no chat interno (para histórico) - usa versão async
        chat_result = await cls.send_notification_async(db, phone, message, order_type)
        results["chat_interno"] = chat_result

        # Se modo API/coexistência estiver ativado, envia via WhatsApp também
        send_mode = WHATSAPP_CONFIG.get("send_mode")
        if send_mode in {"api", "coexistence"}:
            whatsapp_result = await cls.send_whatsapp_message(phone, message)
            results["whatsapp_api"] = whatsapp_result

            # Considera sucesso se WhatsApp API funcionou
            if whatsapp_result.get("success"):
                results["success"] = True
                provider_label = (
                    "WhatsApp API (Coexistência) + Chat Interno"
                    if send_mode == "coexistence"
                    else "WhatsApp API + Chat Interno"
                )
                results["provider"] = provider_label
                results["message"] = "Notificação enviada via WhatsApp e salva no chat"
            else:
                results["success"] = False
                results["error"] = whatsapp_result.get("error")
                results["message"] = (
                    whatsapp_result.get("coexistence_hint")
                    or "Erro ao enviar via WhatsApp, mas salvo no chat"
                )
        else:
            # Modo chat interno apenas
            results["success"] = chat_result.get("success", False)
            results["provider"] = "Chat Interno"
            results["message"] = "Notificação salva no chat interno"

        return results

    @classmethod
    def notify_order_confirmed(cls, db: Session, order_data: Dict, order_type: str) -> Dict:
        """
        Processa e envia notificação de pedido confirmado (versão síncrona)

        Args:
            db: Sessão do banco de dados
            order_data: Dados do pedido
            order_type: Tipo do pedido (cardapio, mesa, balcao)

        Returns:
            Dict com resultado do envio
        """
        # Executa a versão async de forma síncrona
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(cls.notify_order_confirmed_async(db, order_data, order_type))


# ==================== NOTIFICAÇÕES WEBSOCKET PARA CHATBOT ====================

async def send_chatbot_websocket_notification(
    empresa_id: Optional[int],
    notification_type: str,
    title: str,
    message: str,
    data: Optional[Dict] = None
) -> int:
    """
    Envia notificação WebSocket para atualizar o frontend quando há mudanças no chatbot
    
    Args:
        empresa_id: ID da empresa (None = envia para todas)
        notification_type: Tipo da notificação (chatbot_message, nova_mensagem, conversation_updated, etc)
        title: Título da notificação
        message: Mensagem da notificação
        data: Dados adicionais (conversation_id, message_id, etc)
    
    Returns:
        Número de conexões que receberam a notificação (0 se nenhuma)
    """
    try:
        from app.api.notifications.core.websocket_manager import websocket_manager
        
        # Normaliza empresa_id para string
        empresa_id_str = str(empresa_id) if empresa_id else None
        
        notification_data = {
            "type": "notification",
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Se empresa_id foi fornecido, adiciona ao payload
        if empresa_id_str:
            notification_data["empresa_id"] = empresa_id_str
        
        # Envia notificação via WebSocket
        if empresa_id_str:
            sent_count = await websocket_manager.send_to_empresa(empresa_id_str, notification_data)
        else:
            # Se não tem empresa_id, faz broadcast para todos
            sent_count = await websocket_manager.broadcast(notification_data)
        
        logger.info(
            f"[CHATBOT_WS] Notificação enviada - tipo={notification_type}, "
            f"empresa_id={empresa_id_str}, conexões={sent_count}"
        )
        
        return sent_count
        
    except ImportError:
        # Se o websocket_manager não estiver disponível, apenas loga e continua
        logger.warning(
            "[CHATBOT_WS] websocket_manager não disponível. "
            "Notificações WebSocket não serão enviadas."
        )
        return 0
    except Exception as e:
        logger.error(
            f"[CHATBOT_WS] Erro ao enviar notificação WebSocket: {e}",
            exc_info=True
        )
        return 0
