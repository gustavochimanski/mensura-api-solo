"""
Módulo de notificações de pedidos
Integra com cardápio, mesas e balcão para enviar notificações aos clientes
Suporta envio via WhatsApp Business API (Meta) e chat interno
"""
from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
import httpx
import asyncio
import logging
import json

logger = logging.getLogger(__name__)

# Mapeamento de status de pedido para templates/emoji usados nas mensagens.
ORDER_STATUS_TEMPLATES = {
    "PENDENTE": {"name": "Pendente", "emoji": "⏳", "message": "Pedido aguardando confirmação"},
    "CONFIRMADO": {"name": "Confirmado", "emoji": "✅", "message": "Pedido confirmado"},
    "PREPARANDO": {"name": "Em preparação", "emoji": "👩‍🍳", "message": "Pedido em preparação"},
    "SAINDO_PARA_ENTREGA": {"name": "Saiu para entrega", "emoji": "🛵", "message": "Pedido saiu para entrega"},
    "ENTREGUE": {"name": "Entregue", "emoji": "📦", "message": "Pedido entregue"},
    "CANCELADO": {"name": "Cancelado", "emoji": "❌", "message": "Pedido cancelado"},
}


class OrderNotification:
    """Gerenciador de notificações de pedidos"""

    @staticmethod
    async def mark_message_as_read(message_id: str, empresa_id: Optional[str] = None) -> Dict:
        """
        Marca uma mensagem como lida no WhatsApp
        Conforme documentação 360Dialog: https://docs.360dialog.com/docs/waba-messaging/messaging
        
        Args:
            message_id: ID da mensagem a ser marcada como lida
            empresa_id: ID da empresa (opcional)
        
        Returns:
            Dict com resultado da operação
        """
        try:
            from .config_whatsapp import (
                load_whatsapp_config,
                get_whatsapp_url,
                get_headers,
            )

            config = load_whatsapp_config(empresa_id)
            provider = (config.get("provider") or "").lower()
            base_url = str(config.get("base_url", "") or "").lower()
            is_360 = (provider == "360dialog") or (not provider and "360dialog" in base_url)
            access_token = config.get("access_token") or ""

            if not access_token or access_token.strip() == "":
                return {
                    "success": False,
                    "error": "Configuração do WhatsApp ausente ou incompleta",
                }

            # URL para marcar como lida
            if is_360:
                # 360Dialog: Para marcar como lida, usa o mesmo endpoint de mensagens
                # mas com payload diferente - na verdade, 360Dialog marca automaticamente como lida
                # quando você responde dentro da janela de 24h. Vamos tentar o endpoint de status.
                # NOTA: 360Dialog pode não suportar marcar como lida explicitamente da mesma forma que Meta
                # Vamos pular essa funcionalidade para 360Dialog por enquanto
                logger.info(f"[WhatsApp] 360Dialog: Mensagens são marcadas como lidas automaticamente ao responder")
                return {
                    "success": True,
                    "message_id": message_id,
                    "status": "read",
                    "note": "360Dialog marca automaticamente como lida ao responder"
                }
            else:
                # Meta Cloud API
                phone_number_id = config.get("phone_number_id")
                if not phone_number_id:
                    return {
                        "success": False,
                        "error": "phone_number_id não configurado",
                    }
                api_version = config.get("api_version", "v22.0")
                url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"

            headers = get_headers(empresa_id, config)

            # Payload para marcar como lida (formato Meta Cloud API)
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    logger.info(f"[WhatsApp] Mensagem {message_id} marcada como lida")
                    return {
                        "success": True,
                        "message_id": message_id,
                        "status": "read"
                    }
                else:
                    # Log completo do erro
                    error_text = response.text or "Erro desconhecido"
                    try:
                        error_json = response.json()
                        error_message = json.dumps(error_json, indent=2, ensure_ascii=False)
                        logger.error(f"[WhatsApp] Erro ao marcar mensagem como lida (Status {response.status_code}):\n{error_message}")
                    except:
                        error_message = error_text
                        logger.error(f"[WhatsApp] Erro ao marcar mensagem como lida (Status {response.status_code}): {error_message}")
                    
                    return {
                        "success": False,
                        "error": error_message,
                        "status_code": response.status_code,
                        "response_text": error_text
                    }

        except Exception as e:
            logger.error(f"[WhatsApp] Exceção ao marcar mensagem como lida: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def send_whatsapp_message(phone: str, message: str, empresa_id: Optional[str] = None) -> Dict:
        """
        Envia mensagem via WhatsApp Business API (Meta)

        Args:
            phone: Número de telefone (formato: 5511999999999)
            message: Texto da mensagem

        Returns:
            Dict com resultado do envio
        """
        try:
            from .config_whatsapp import (
                load_whatsapp_config,
                get_whatsapp_url,
                get_headers,
                format_phone_number,
            )
            from app.utils.telefone import variantes_telefone_para_envio_whatsapp

            config = load_whatsapp_config(empresa_id)
            provider = (config.get("provider") or "").lower()
            base_url = str(config.get("base_url", "") or "").lower()
            # `provider` tem precedência. Se estiver vazio, inferimos pelo base_url (compatibilidade).
            is_360 = (provider == "360dialog") or (not provider and "360dialog" in base_url)
            access_token = config.get("access_token") or ""

            # Valida se o token existe e não está vazio
            if not access_token or access_token.strip() == "":
                error_msg = f"Configuração do WhatsApp ausente ou incompleta: access_token não configurado (empresa_id={empresa_id})"
                logger.error(f"[WhatsApp] {error_msg}")
                return {
                    "success": False,
                    "provider": "360dialog" if is_360 else "WhatsApp Business API (Meta)",
                    "error": error_msg,
                    "phone": phone,
                }

            # Para Meta Cloud API, também precisa do phone_number_id
            if not is_360 and not config.get("phone_number_id"):
                return {
                    "success": False,
                    "provider": "WhatsApp Business API (Meta)",
                    "error": "Configuração do WhatsApp ausente ou incompleta: phone_number_id não configurado",
                    "phone": phone,
                }

            # Formata o número para o padrão WhatsApp
            phone_formatted = format_phone_number(phone)

            # URL da API
            url = get_whatsapp_url(empresa_id, config)

            # Headers com token de autorização (pode lançar ValueError se token inválido)
            try:
                headers = get_headers(empresa_id, config)
                
                # Validação extra para 360dialog
                if is_360:
                    api_key = headers.get("D360-API-KEY", "")
                    if not api_key or len(api_key.strip()) == 0:
                        error_msg = "API Key do 360dialog está vazia!"
                        logger.error(f"[WhatsApp] {error_msg}")
                        return {
                            "success": False,
                            "provider": "360dialog",
                            "error": error_msg,
                            "phone": phone,
                        }
            except ValueError as e:
                error_msg = f"Erro na configuração do WhatsApp: {str(e)}"
                logger.error(f"[WhatsApp] {error_msg}")
                return {
                    "success": False,
                    "provider": "360dialog" if is_360 else "WhatsApp Business API (Meta)",
                    "error": error_msg,
                    "phone": phone,
                }

            # Payload da mensagem conforme documentação 360Dialog
            # https://docs.360dialog.com/docs/waba-messaging/messaging
            if is_360:
                # 360dialog: tentamos variantes de telefone para maximizar entregabilidade
                # (com/sem 55 e com/sem 9 quando aplicável).
                candidates = variantes_telefone_para_envio_whatsapp(phone_formatted or phone)
                if not candidates:
                    candidates = [''.join(filter(str.isdigit, phone_formatted or phone))]

                # Payload base
                payload_base = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "type": "text",
                    "text": {"body": message},
                }
            else:
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
                phone_used = phone_formatted
                if is_360:
                    last_response = None
                    for cand in candidates:
                        phone_used = cand
                        payload = dict(payload_base)
                        payload["to"] = cand
                        last_response = await client.post(url, json=payload, headers=headers)
                        # Sucesso
                        if last_response.status_code == 200:
                            result = last_response.json()
                            message_id = result.get("messages", [{}])[0].get("id") if result.get("messages") else None
                            logger.info(f"[WhatsApp] Mensagem enviada com sucesso. Message ID: {message_id}")
                            return {
                                "success": True,
                                "provider": "360dialog",
                                "phone": phone_used,
                                "message_id": message_id,
                                "status": "sent",
                                "response": result,
                                "note": "Enviado com fallback de variantes (telefone normalizado)",
                            }
                        # Para 360dialog, só faz sentido tentar outras variantes quando o provedor rejeita o 'to'
                        if last_response.status_code != 400:
                            break

                    response = last_response
                else:
                    response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    # Log completo do erro
                    error_text = response.text or "Erro desconhecido"
                    try:
                        error_json = response.json()
                        error_message = json.dumps(error_json, indent=2, ensure_ascii=False)
                        logger.error(f"[WhatsApp] Erro ao enviar mensagem (Status {response.status_code}):\n{error_message}")
                    except Exception as parse_error:
                        error_message = error_text
                        logger.error(f"[WhatsApp] Erro ao enviar mensagem (Status {response.status_code}): {error_message}")

                if response.status_code == 200:
                    result = response.json()
                    message_id = result.get("messages", [{}])[0].get("id") if result.get("messages") else None
                    logger.info(f"[WhatsApp] Mensagem enviada com sucesso. Message ID: {message_id}")
                    return {
                        "success": True,
                        "provider": "360dialog" if is_360 else "WhatsApp Business API (Meta)",
                        "phone": phone_used if is_360 else phone_formatted,
                        "message_id": message_id,
                        "status": "sent",
                        "response": result
                    }

                # Trata erro na resposta
                error_message = response.text or "Erro desconhecido"
                error_detail = {}
                
                # Tenta parsear JSON da resposta de erro
                try:
                    if response.text:
                        error_data = response.json()
                        if isinstance(error_data, dict):
                            error_detail = error_data.get("error", {})
                            if isinstance(error_detail, dict):
                                error_message = error_detail.get("message", error_data.get("message", response.text))
                            else:
                                error_message = str(error_detail) if error_detail else response.text
                        else:
                            error_message = str(error_data) if error_data else response.text
                except (ValueError, json.JSONDecodeError):
                    # Se não conseguir parsear, usa o texto da resposta
                    error_message = response.text or f"Erro HTTP {response.status_code}"

                coexistence_hint = None
                # Dica adicional quando houver conflito de registro do número
                if response.status_code in (400, 403, 409):
                    if is_360:
                        # Verifica se é erro de pagamento
                        if "payment" in error_message.lower() or "blocked" in error_message.lower():
                            coexistence_hint = (
                                "⚠️ CONTA BLOQUEADA POR FALTA DE PAGAMENTO: "
                                "A conta do 360dialog está bloqueada por falta de créditos/pagamento. "
                                "IMPORTANTE: Mesmo respostas dentro da janela de conversa (24h) são bloqueadas quando há pendências. "
                                "É necessário regularizar o pagamento na conta do 360dialog para desbloquear TODAS as mensagens, "
                                "incluindo respostas gratuitas dentro da janela de conversa."
                            )
                        else:
                            coexistence_hint = (
                                "Verifique se a API Key do 360dialog está correta e ativa. "
                                "Status 403 geralmente indica API Key inválida ou expirada."
                            )
                    else:
                        coexistence_hint = (
                            "Verifique se o número foi conectado no modo 'App e API' na Meta "
                            "(coexistência) e se o app WhatsApp Business está atualizado."
                        )

                return {
                    "success": False,
                    "provider": "360dialog" if is_360 else "WhatsApp Business API (Meta)",
                    "error": error_message,
                    "status_code": response.status_code,
                    "phone": phone_formatted,
                    "coexistence_hint": coexistence_hint,
                    "response_text": response.text[:500] if response.text else None
                }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[WhatsApp] Exceção ao enviar mensagem: {error_msg}", exc_info=True)
            return {
                "success": False,
                "provider": "360dialog" if 'is_360' in locals() and is_360 else "WhatsApp Business API (Meta)",
                "error": error_msg,
                "phone": phone
            }

    @staticmethod
    async def send_whatsapp_message_with_buttons(
        phone: str, 
        message: str, 
        buttons: List[Dict[str, str]], 
        empresa_id: Optional[str] = None
    ) -> Dict:
        """
        Envia mensagem via WhatsApp Business API com botões interativos
        
        Args:
            phone: Número de telefone (formato: 5511999999999)
            message: Texto da mensagem
            buttons: Lista de botões. Cada botão deve ter 'id' e 'title'
                    Ex: [{"id": "pedir_whatsapp", "title": "Pedir pelo WhatsApp"}, ...]
            empresa_id: ID da empresa (opcional)
        
        Returns:
            Dict com resultado do envio
        """
        try:
            from .config_whatsapp import (
                load_whatsapp_config,
                get_whatsapp_url,
                get_headers,
                format_phone_number,
            )
            from app.utils.telefone import variantes_telefone_para_envio_whatsapp

            config = load_whatsapp_config(empresa_id)
            provider = (config.get("provider") or "").lower()
            base_url = str(config.get("base_url", "") or "").lower()
            is_360 = (provider == "360dialog") or (not provider and "360dialog" in base_url)
            access_token = config.get("access_token") or ""

            if not access_token or access_token.strip() == "":
                error_msg = f"Configuração do WhatsApp ausente ou incompleta: access_token não configurado (empresa_id={empresa_id})"
                logger.error(f"[WhatsApp] {error_msg}")
                return {
                    "success": False,
                    "provider": "360dialog" if is_360 else "WhatsApp Business API (Meta)",
                    "error": error_msg,
                    "phone": phone,
                }

            if not is_360 and not config.get("phone_number_id"):
                return {
                    "success": False,
                    "provider": "WhatsApp Business API (Meta)",
                    "error": "Configuração do WhatsApp ausente ou incompleta: phone_number_id não configurado",
                    "phone": phone,
                }

            phone_formatted = format_phone_number(phone)
            url = get_whatsapp_url(empresa_id, config)
            headers = get_headers(empresa_id, config)

            # Limita a 3 botões (limite do WhatsApp)
            buttons_to_send = buttons[:3]
            
            # Monta os botões no formato do WhatsApp
            button_list = []
            for btn in buttons_to_send:
                button_list.append({
                    "type": "reply",
                    "reply": {
                        "id": btn.get("id", ""),
                        "title": btn.get("title", "")
                    }
                })

            # Payload para mensagem interativa com botões
            if is_360:
                # 360Dialog usa formato similar ao Meta. Vamos tentar com variantes do telefone.
                candidates = variantes_telefone_para_envio_whatsapp(phone_formatted or phone)
                if not candidates:
                    candidates = [''.join(filter(str.isdigit, phone_formatted or phone))]

                payload_base = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": message},
                        "action": {"buttons": button_list},
                    },
                }
            else:
                # Meta Cloud API
                payload = {
                    "messaging_product": "whatsapp",
                    "to": phone_formatted,
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": message
                        },
                        "action": {
                            "buttons": button_list
                        }
                    }
                }

            # Envia a mensagem (com fallback para 360dialog quando rejeitar o 'to')
            async with httpx.AsyncClient(timeout=30.0) as client:
                phone_used = phone_formatted
                if is_360:
                    last_response = None
                    for cand in candidates:
                        phone_used = cand
                        payload_try = dict(payload_base)
                        payload_try["to"] = cand
                        last_response = await client.post(url, json=payload_try, headers=headers)
                        if last_response.status_code == 200:
                            result = last_response.json()
                            message_id = result.get("messages", [{}])[0].get("id") if result.get("messages") else None
                            logger.info(f"[WhatsApp] Mensagem com botões enviada com sucesso. Message ID: {message_id}")
                            return {
                                "success": True,
                                "provider": "360dialog",
                                "message_id": message_id,
                                "phone": phone_used,
                                "note": "Enviado com fallback de variantes (telefone normalizado)",
                            }
                        if last_response.status_code != 400:
                            break
                    response = last_response
                else:
                    response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    message_id = result.get("messages", [{}])[0].get("id") if result.get("messages") else None
                    logger.info(f"[WhatsApp] Mensagem com botões enviada com sucesso. Message ID: {message_id}")
                    return {
                        "success": True,
                        "provider": "360dialog" if is_360 else "WhatsApp Business API (Meta)",
                        "message_id": message_id,
                        "phone": phone_used if is_360 else phone_formatted
                    }
                else:
                    error_data = response.json() if response.text else {}
                    error_message = error_data.get("error", {}).get("message", response.text) if isinstance(error_data, dict) else response.text
                    
                    return {
                        "success": False,
                        "provider": "360dialog" if is_360 else "WhatsApp Business API (Meta)",
                        "error": error_message,
                        "status_code": response.status_code,
                        "phone": phone_used if is_360 else phone_formatted
                    }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[WhatsApp] Exceção ao enviar mensagem com botões: {error_msg}", exc_info=True)
            return {
                "success": False,
                "provider": "360dialog" if 'is_360' in locals() and is_360 else "WhatsApp Business API (Meta)",
                "error": error_msg,
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
    async def send_notification_async(
        db: Session,
        phone: str,
        message: str,
        order_type: str,
        empresa_id: Optional[int] = None,
        whatsapp_message_id: Optional[str] = None,
    ) -> Dict:
        """
        Envia notificação como mensagem no chat (versão async)

        O número de telefone do cliente vira o user_id no chat
        A IA envia automaticamente a mensagem de confirmação
        
        Args:
            db: Sessão do banco de dados
            phone: Número de telefone do cliente
            message: Mensagem a ser enviada
            order_type: Tipo do pedido (cardapio, mesa, balcao, delivery)
            empresa_id: ID da empresa (opcional, mas recomendado para garantir histórico correto)
            whatsapp_message_id: ID da mensagem no WhatsApp (opcional; salvo em metadata)
        """
        from . import database as chatbot_db
        from .config_whatsapp import format_phone_number

        try:
            # Normaliza o telefone para garantir consistência com as conversas existentes
            # Remove caracteres não numéricos e garante código do país
            phone_normalized = format_phone_number(phone)
            # Use o telefone normalizado como user_id
            user_id = phone_normalized
            session_id = f"order_{order_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Garante que o prompt padrão existe para não violar a FK da tabela
            prompt_key = "default"
            if not chatbot_db.get_prompt(db, prompt_key, empresa_id=empresa_id):
                chatbot_db.create_prompt(
                    db=db,
                    key=prompt_key,
                    name="Padrão (Notificações)",
                    content="Atendente virtual para notificações automáticas.",
                    is_default=True,
                    empresa_id=empresa_id
                )

            # Cria ou busca conversa existente para esse usuário
            # Se empresa_id foi fornecido, tenta escopar por empresa primeiro.
            # IMPORTANTE: conversas legadas podem ter empresa_id NULL; se não achar no escopo,
            # fazemos fallback global e, se necessário, atualizamos a conversa com empresa_id.
            if empresa_id is not None:
                conversations = chatbot_db.get_conversations_by_user(db, user_id, empresa_id=empresa_id)
                if not conversations:
                    conversations = chatbot_db.get_conversations_by_user(db, user_id)
            else:
                conversations = chatbot_db.get_conversations_by_user(db, user_id)

            # Se não encontrou conversa e o telefone foi normalizado, tenta buscar com o telefone original também
            if not conversations and phone != phone_normalized:
                if empresa_id is not None:
                    conversations = chatbot_db.get_conversations_by_user(db, phone, empresa_id=empresa_id)
                    if not conversations:
                        conversations = chatbot_db.get_conversations_by_user(db, phone)
                else:
                    conversations = chatbot_db.get_conversations_by_user(db, phone)

            if conversations:
                # Usa a conversa mais recente
                conversation_id = conversations[0]['id']
                # Busca empresa_id da conversa (pode ser None se não tinha antes)
                conversation = chatbot_db.get_conversation(db, conversation_id)
                empresa_id_final = conversation.get('empresa_id') if conversation else empresa_id
                
                # Se a conversa não tinha empresa_id mas agora temos, atualiza
                if empresa_id and not empresa_id_final:
                    # Atualiza a conversa com o empresa_id
                    try:
                        from sqlalchemy import text
                        query = text(f"""
                            UPDATE chatbot.conversations
                            SET empresa_id = :empresa_id
                            WHERE id = :conversation_id
                        """)
                        db.execute(query, {"empresa_id": empresa_id, "conversation_id": conversation_id})
                        db.commit()
                        empresa_id_final = empresa_id
                    except Exception as e:
                        logger.warning(f"Erro ao atualizar empresa_id da conversa {conversation_id}: {e}")
                        empresa_id_final = empresa_id
            else:
                # Cria nova conversa com empresa_id se fornecido
                # Usa o telefone normalizado para garantir consistência
                conversation_id = chatbot_db.create_conversation(
                    db=db,
                    session_id=session_id,
                    user_id=user_id,  # telefone normalizado
                    prompt_key=prompt_key,
                    model="notification-system",
                    empresa_id=empresa_id
                )
                empresa_id_final = empresa_id

            # Adiciona a mensagem de notificação como resposta da IA
            message_id = chatbot_db.create_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=message,
                whatsapp_message_id=whatsapp_message_id,
            )

            # Envia notificação WebSocket para atualizar o frontend
            try:
                await send_chatbot_websocket_notification(
                    empresa_id=empresa_id_final,
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
        
        # Envia notificação via WebSocket SOMENTE se houver cliente na rota /chatbot
        # (o frontend deve mandar { "type": "set_route", "route": "/chatbot" } ao entrar na tela)
        required_route = "/chatbot"
        if empresa_id_str:
            sent_count = await websocket_manager.send_to_empresa_on_route(
                empresa_id_str,
                notification_data,
                required_route=required_route,
            )
        else:
            # Se não tem empresa_id, faz broadcast filtrado por rota
            sent_count = await websocket_manager.broadcast_on_route(notification_data, required_route=required_route)
        
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



def _formatar_tempo_minutos(tempo_min: int) -> str:
    """Formata minutos em string amigável (ex.: 45 min, 1h 20min)."""
    try:
        tempo_int = int(tempo_min)
    except Exception:
        return str(tempo_min)

    if tempo_int < 0:
        tempo_int = 0
    if tempo_int < 60:
        return f"{tempo_int} min"
    horas = tempo_int // 60
    minutos = tempo_int % 60
    if minutos == 0:
        return f"{horas}h"
    return f"{horas}h {minutos}min"


def _obter_tempo_estimado_min_por_regiao_distancia(
    db: Session, *, empresa_id: int, distancia_km
) -> Optional[int]:
    """
    Retorna tempo_estimado_min conforme regiões de entrega (por distância).
    Usa o mesmo critério do contrato/adaptador de região.
    """
    if not empresa_id or distancia_km is None:
        return None
    try:
        from decimal import Decimal as _Dec
        from app.api.cadastros.adapters.regiao_entrega_adapter import RegiaoEntregaAdapter

        regiao = RegiaoEntregaAdapter(db).obter_regiao_por_distancia(
            int(empresa_id), _Dec(str(distancia_km))
        )
        if not regiao:
            return None
        tempo = getattr(regiao, "tempo_estimado_min", None)
        return int(tempo) if tempo is not None else None
    except Exception:
        # Mantém silencioso (não deve falhar o envio por erro de ETA)
        return None


def _obter_tempo_estimado_min_da_menor_taxa(
    db: Session, *, empresa_id: int
) -> Optional[int]:
    """
    Para balcão/mesa: retorna o tempo_estimado_min da região com MENOR taxa_entrega cadastrada.
    """
    if not empresa_id:
        return None
    try:
        from sqlalchemy import text

        row = db.execute(
            text(
                """
                SELECT re.tempo_estimado_min
                FROM cadastros.regioes_entrega re
                WHERE re.empresa_id = :empresa_id
                  AND re.ativo = true
                  AND re.tempo_estimado_min IS NOT NULL
                ORDER BY re.taxa_entrega ASC NULLS LAST, re.id ASC
                LIMIT 1
                """
            ),
            {"empresa_id": int(empresa_id)},
        ).fetchone()
        if not row:
            return None
        tempo = row[0]
        return int(tempo) if tempo is not None else None
    except Exception:
        return None


async def enviar_resumo_pedido_whatsapp(
    db: Session,
    pedido_id: int,
    phone_number: Optional[str] = None,
    empresa_id: Optional[str] = None
) -> Dict:
    """
    Envia o resumo de um pedido específico para o cliente via WhatsApp.
    A mensagem inclui os itens, valores e o status atual do pedido.
    
    Args:
        db: Sessão do banco de dados
        pedido_id: ID do pedido
        phone_number: Número de telefone do cliente (opcional, será buscado se não fornecido)
        empresa_id: ID da empresa (opcional, para configuração do WhatsApp)
    
    Returns:
        Dict com resultado do envio
    """
    try:
        from sqlalchemy import text
        from app.api.chatbot.core.config_whatsapp import format_phone_number
        # Best-effort: garante que `valor_total` e taxas estejam atualizados após edições
        # (o resumo lê do banco via SQL). Não falha o envio se o recálculo não for possível.
        try:
            from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
            from app.api.pedidos.services.service_pedido import PedidoService

            pedido_model = PedidoRepository(db).get_pedido(int(pedido_id))
            if pedido_model is not None:
                PedidoService(db)._recalcular_pedido(pedido_model)
        except Exception as e:
            logger.warning(
                f"[enviar_resumo_pedido] Não foi possível recalcular totais antes do envio do resumo "
                f"(pedido_id={pedido_id}): {e}"
            )

        def _digits_only(v: str) -> str:
            return "".join(ch for ch in str(v or "") if ch.isdigit())

        def _normalize_phone(v: Optional[str]) -> Optional[str]:
            if not v or not str(v).strip():
                return None
            try:
                return format_phone_number(str(v).strip())
            except Exception:
                d = _digits_only(str(v).strip())
                return d or None

        def _buscar_whatsapp_phone_por_pedido_id(
            db: Session, *, pedido_id_int: int, empresa_id_int: Optional[int]
        ) -> Optional[str]:
            """
            Tenta descobrir o telefone real do WhatsApp (chatbot.conversations.user_id)
            associado ao pedido, usando:
            1) metadata->>'pedido_id' em chatbot.messages (novo)
            2) fallback por conteúdo (mensagem de confirmação do pedido)
            """
            if not pedido_id_int or not empresa_id_int:
                return None
            try:
                q = text(
                    """
                    SELECT c.user_id
                    FROM chatbot.messages m
                    JOIN chatbot.conversations c ON c.id = m.conversation_id
                    WHERE c.empresa_id = :empresa_id
                      AND m.metadata ? 'pedido_id'
                      AND (m.metadata->>'pedido_id') = :pedido_id
                    ORDER BY m.created_at DESC
                    LIMIT 1
                    """
                )
                row = db.execute(
                    q,
                    {"empresa_id": int(empresa_id_int), "pedido_id": str(int(pedido_id_int))},
                ).fetchone()
                if row and row[0]:
                    return str(row[0])
            except Exception:
                pass

            # Fallback legado: procura a mensagem de confirmação do checkout pelo texto
            try:
                q2 = text(
                    """
                    SELECT c.user_id
                    FROM chatbot.messages m
                    JOIN chatbot.conversations c ON c.id = m.conversation_id
                    WHERE c.empresa_id = :empresa_id
                      AND m.role = 'assistant'
                      AND m.content ILIKE :pattern
                    ORDER BY m.created_at DESC
                    LIMIT 1
                    """
                )
                pattern = f"%Número do pedido:%#{int(pedido_id_int)}%"
                row2 = db.execute(
                    q2,
                    {"empresa_id": int(empresa_id_int), "pattern": pattern},
                ).fetchone()
                if row2 and row2[0]:
                    return str(row2[0])
            except Exception:
                pass

            return None

        # Busca o pedido
        pedido_query = text("""
            SELECT
                p.id,
                p.numero_pedido,
                p.tipo_entrega,
                p.status,
                p.subtotal,
                p.desconto,
                p.taxa_entrega,
                p.valor_total,
                p.observacoes,
                EXISTS (
                    SELECT 1
                    FROM cardapio.transacoes_pagamento_dv tx
                    WHERE tx.pedido_id = p.id
                      AND tx.status IN ('PAGO', 'AUTORIZADO')
                ) AS pago,
                p.created_at,
                c.nome as cliente_nome,
                c.telefone as cliente_telefone,
                p.empresa_id,
                p.endereco_id,
                p.distancia_km,
                p.previsao_entrega
            FROM pedidos.pedidos p
            LEFT JOIN cadastros.clientes c ON p.cliente_id = c.id
            WHERE p.id = :pedido_id
        """)

        result = db.execute(pedido_query, {"pedido_id": pedido_id})
        pedido = result.fetchone()

        if not pedido:
            logger.error(f"[enviar_resumo_pedido] Pedido {pedido_id} não encontrado")
            return {
                "success": False,
                "error": "Pedido não encontrado"
            }

        # Extrai dados do pedido
        numero_pedido = pedido[1]
        tipo_entrega = pedido[2]
        status_code = pedido[3]
        subtotal = float(pedido[4]) if pedido[4] else 0
        desconto = float(pedido[5]) if pedido[5] else 0
        taxa_entrega = float(pedido[6]) if pedido[6] else 0
        valor_total = float(pedido[7]) if pedido[7] else 0
        observacoes = pedido[8]
        pago = pedido[9]
        created_at = pedido[10]
        cliente_nome = pedido[11]
        cliente_telefone_db = pedido[12]
        empresa_id_pedido = str(pedido[13]) if pedido[13] else empresa_id
        endereco_id = pedido[14]
        distancia_km = float(pedido[15]) if pedido[15] is not None else None
        previsao_entrega = pedido[16]

        # Usa empresa_id do pedido se não foi fornecido
        empresa_id_final = empresa_id_pedido or empresa_id
        empresa_id_int: Optional[int] = None
        if empresa_id_final:
            try:
                empresa_id_int = int(str(empresa_id_final))
            except (ValueError, TypeError):
                empresa_id_int = None

        # Usa o telefone fornecido ou busca do banco
        telefone_cadastro = phone_number or cliente_telefone_db

        # Tenta descobrir o telefone real do WhatsApp associado ao pedido (se o cadastro estiver errado)
        telefone_whatsapp = _buscar_whatsapp_phone_por_pedido_id(
            db,
            pedido_id_int=int(pedido_id),
            empresa_id_int=empresa_id_int,
        )

        telefone_final = telefone_cadastro
        telefone_cadastro_norm = _normalize_phone(telefone_cadastro)
        telefone_whatsapp_norm = _normalize_phone(telefone_whatsapp)
        if telefone_whatsapp_norm and telefone_whatsapp_norm != telefone_cadastro_norm:
            telefone_final = telefone_whatsapp_norm
        
        if not telefone_final:
            logger.warning(f"[enviar_resumo_pedido] Pedido {pedido_id} não tem telefone do cliente")
            return {
                "success": False,
                "error": "Telefone do cliente não encontrado"
            }

        # Busca os itens do pedido com seus IDs
        itens_query = text("""
            SELECT
                pi.id,
                pi.quantidade,
                pi.preco_unitario,
                pi.preco_total,
                pi.observacao,
                COALESCE(
                    (SELECT p.descricao FROM catalogo.produtos p WHERE p.cod_barras = pi.produto_cod_barras),
                    (SELECT r.nome FROM catalogo.receitas r WHERE r.id = pi.receita_id),
                    (SELECT c.descricao FROM catalogo.combos c WHERE c.id = pi.combo_id),
                    'Item'
                ) as nome_item
            FROM pedidos.pedidos_itens pi
            WHERE pi.pedido_id = :pedido_id
            ORDER BY pi.id
        """)

        itens_result = db.execute(itens_query, {"pedido_id": pedido_id})
        itens = itens_result.fetchall()

        # Busca complementos e adicionais para cada item
        complementos_query = text("""
            SELECT
                pic.pedido_item_id,
                cp.nome as complemento_nome,
                pic.total as complemento_total,
                pica.quantidade as adicional_quantidade,
                pica.preco_unitario as adicional_preco_unitario,
                pica.total as adicional_total,
                COALESCE(
                    (SELECT p.descricao FROM catalogo.produtos p WHERE p.cod_barras = cvi.produto_cod_barras),
                    (SELECT r.nome FROM catalogo.receitas r WHERE r.id = cvi.receita_id),
                    (SELECT c.descricao FROM catalogo.combos c WHERE c.id = cvi.combo_id),
                    'Adicional'
                ) as adicional_nome
            FROM pedidos.pedidos_itens_complementos pic
            INNER JOIN catalogo.complemento_produto cp ON pic.complemento_id = cp.id
            LEFT JOIN pedidos.pedidos_itens_complementos_adicionais pica ON pic.id = pica.item_complemento_id
            LEFT JOIN catalogo.complemento_vinculo_item cvi ON pica.adicional_id = cvi.id
            LEFT JOIN catalogo.produtos p ON cvi.produto_cod_barras = p.cod_barras
            LEFT JOIN catalogo.receitas r ON cvi.receita_id = r.id
            LEFT JOIN catalogo.combos c ON cvi.combo_id = c.id
            WHERE pic.pedido_item_id IN (
                SELECT id FROM pedidos.pedidos_itens WHERE pedido_id = :pedido_id
            )
            ORDER BY pic.pedido_item_id, pic.id, pica.id
        """)

        complementos_result = db.execute(complementos_query, {"pedido_id": pedido_id})
        complementos_data = complementos_result.fetchall()

        # Organiza complementos por item
        complementos_por_item = {}
        for comp_row in complementos_data:
            item_id = comp_row[0]
            if item_id not in complementos_por_item:
                complementos_por_item[item_id] = []
            complementos_por_item[item_id].append({
                'complemento_nome': comp_row[1],
                'complemento_total': float(comp_row[2]) if comp_row[2] else 0,
                'adicional_quantidade': comp_row[3],
                'adicional_preco_unitario': float(comp_row[4]) if comp_row[4] else 0,
                'adicional_total': float(comp_row[5]) if comp_row[5] else 0,
                'adicional_nome': comp_row[6]
            })

        # Monta a mensagem
        status_info = ORDER_STATUS_TEMPLATES.get(status_code, {
            "name": "Desconhecido",
            "emoji": "❓",
            "message": "Status atualizado."
        })

        # Tipo de entrega formatado
        tipo_formatado = {
            "DELIVERY": "🛵 Delivery",
            "RETIRADA": "🏪 Retirada",
            "BALCAO": "🍽️ Balcão",
            "MESA": "🪑 Mesa"
        }.get(tipo_entrega, tipo_entrega)

        # Monta uma mensagem bem fácil de entender (escaneável)
        data_formatada = created_at.strftime('%d/%m/%Y %H:%M') if created_at else 'N/A'
        pagamento_str = "✅ Pago" if pago else "⏳ Pendente"

        mensagem = (
            f"📋 *Pedido #{numero_pedido}*\n"
            f"{status_info['emoji']} *Status:* {status_info['name']}\n"
            f"{tipo_formatado} | 📅 {data_formatada}\n\n"
            f"*Itens:*\n"
        )

        for idx, item in enumerate(itens, start=1):
            item_id = item[0]
            qtd = item[1]
            preco_total = float(item[3]) if item[3] else 0
            nome_item = item[5]
            obs_item = item[4]

            mensagem += f"{idx}) {qtd}x {nome_item} — R$ {preco_total:.2f}\n"
            if obs_item:
                mensagem += f"   Obs: {obs_item}\n"

            # Adiciona complementos e adicionais do item
            if item_id in complementos_por_item:
                # Agrupa apenas os ADICIONAIS (sem nome do complemento/grupo)
                adicionais_agrupados = {}
                for comp in complementos_por_item[item_id]:
                    nome_add = comp.get('adicional_nome')
                    if not nome_add:
                        continue

                    qtd_add = comp.get('adicional_quantidade') or 1
                    preco_add = float(comp.get('adicional_total') or 0)

                    if nome_add not in adicionais_agrupados:
                        adicionais_agrupados[nome_add] = {"quantidade": 0, "preco": 0.0}
                    adicionais_agrupados[nome_add]["quantidade"] += int(qtd_add or 1)
                    adicionais_agrupados[nome_add]["preco"] += float(preco_add or 0)

                # Lista somente adicionais (sem cabeçalho do complemento)
                if adicionais_agrupados:
                    for nome_add in sorted(adicionais_agrupados.keys()):
                        add = adicionais_agrupados[nome_add]
                        qtd_add = add["quantidade"] or 1
                        preco_add = add["preco"] or 0.0
                        if qtd_add > 1:
                            mensagem += f"   ➕ {qtd_add}x {nome_add} (+R$ {preco_add:.2f})\n"
                        else:
                            mensagem += f"   ➕ {nome_add} (+R$ {preco_add:.2f})\n"

            # Linha em branco entre itens para leitura rápida
            mensagem += "\n"

        # Enviar apenas total e status de pagamento (sem subtotal/desconto/taxa)
        mensagem += f"*Total:* R$ {valor_total:.2f}\n*Pagamento:* {pagamento_str}"

        if observacoes:
            mensagem += f"\n\n📝 *Obs do pedido:* {observacoes}"

        # Mensagem de status personalizada
        status_message = status_info["message"].format(numero_pedido=numero_pedido)
        mensagem += f"\n\n{status_info['emoji']} {status_message}"

        # Quando o status for "Em preparo" (R), inclui tempo estimado baseado nas regiões de entrega.
        # - Delivery: tempo da região correspondente à distância (se disponível)
        # - Balcão/Mesa: tempo da região com menor taxa cadastrada
        if str(status_code) == "R":
            tempo_estimado_min: Optional[int] = None
            if str(tipo_entrega) == "DELIVERY":
                if empresa_id_int is not None and distancia_km is not None:
                    tempo_estimado_min = _obter_tempo_estimado_min_por_regiao_distancia(
                        db, empresa_id=empresa_id_int, distancia_km=distancia_km
                    )

                # Fallback: se houver previsao_entrega, calcula minutos restantes (não depende de região)
                if tempo_estimado_min is None and previsao_entrega is not None:
                    try:
                        from datetime import datetime, timezone

                        now = datetime.now(tz=timezone.utc)
                        prev = previsao_entrega
                        if getattr(prev, "tzinfo", None) is None:
                            # prev pode vir "naive" dependendo do driver; assume UTC
                            prev = prev.replace(tzinfo=timezone.utc)
                        delta_min = int((prev - now).total_seconds() // 60)
                        tempo_estimado_min = max(delta_min, 0)
                    except Exception:
                        tempo_estimado_min = None

                if tempo_estimado_min is not None:
                    mensagem += f"\n⏱️ *Previsão de entrega:* ~{_formatar_tempo_minutos(tempo_estimado_min)}"

            elif str(tipo_entrega) in ("BALCAO", "MESA"):
                if empresa_id_int is not None:
                    tempo_estimado_min = _obter_tempo_estimado_min_da_menor_taxa(
                        db, empresa_id=empresa_id_int
                    )
                if tempo_estimado_min is not None:
                    mensagem += f"\n⏱️ *Tempo estimado:* ~{_formatar_tempo_minutos(tempo_estimado_min)}"

        # Se for delivery, tenta anexar o endereço de entrega ao resumo (quando disponível)
        try:
            if str(tipo_entrega) == "DELIVERY" and endereco_id:
                try:
                    # Usa o serviço de endereços do chatbot para obter texto formatado do endereço
                    from app.api.chatbot.core.address_service import ChatbotAddressService

                    addr_service = ChatbotAddressService(db, empresa_id=empresa_id_int or 1)
                    endereco_obj = addr_service.get_endereco_by_id(telefone_final, int(endereco_id))
                    endereco_formatado = None
                    if endereco_obj and isinstance(endereco_obj, dict):
                        endereco_formatado = endereco_obj.get("endereco_completo")
                    if endereco_formatado:
                        mensagem += f"\n\n📍 *Endereço de Entrega:*\n{endereco_formatado}"
                except Exception:
                    # Não falha o envio do resumo se houver erro ao buscar o endereço
                    pass
        except Exception:
            # Segurança adicional: qualquer erro aqui não deve impedir o envio do resumo
            pass

        # Envia via WhatsApp (se conseguir). Mesmo que falhe, NÃO deixamos de salvar no chat interno.
        result: Dict = {}
        try:
            import os
            from app.api.notifications.channels.whatsapp_channel import WhatsAppChannel
            from app.api.chatbot.core.config_whatsapp import load_whatsapp_config

            # Template de fallback (fora da janela 24h). Dentro da janela, o contract converte automaticamente para texto.
            tpl_name = (os.getenv("WHATSAPP_TEMPLATE_PEDIDO_RESUMO") or "").strip()
            tpl_lang = (os.getenv("WHATSAPP_TEMPLATE_PEDIDO_RESUMO_LANGUAGE") or "pt_BR").strip() or "pt_BR"

            if tpl_name:
                cfg = load_whatsapp_config(empresa_id_final)
                channel = WhatsAppChannel(cfg)

                title = f"Resumo do pedido #{numero_pedido}"
                channel_metadata = {
                    "_empresa_id": str(empresa_id_final) if empresa_id_final is not None else None,
                    "whatsapp": {
                        "mode": "template",
                        "template": {
                            "name": tpl_name,
                            "language": tpl_lang,
                            # Tentativa 1: template com 1 variável (body). Se o template não tiver variáveis,
                            # fazemos retry abaixo sem parâmetros.
                            "body_parameters": [f"*{title}*\n\n{mensagem}"],
                        },
                    },
                }

                wa_result = await channel.send(
                    telefone_final,
                    title=title,
                    message=mensagem,
                    channel_metadata=channel_metadata,
                )

                if not wa_result.success:
                    # Retry: template sem parâmetros (para templates "secos"/sem variáveis)
                    channel_metadata2 = {
                        "_empresa_id": str(empresa_id_final) if empresa_id_final is not None else None,
                        "whatsapp": {
                            "mode": "template",
                            "template": {
                                "name": tpl_name,
                                "language": tpl_lang,
                                "components": None,
                                "body_parameters": None,
                            },
                        },
                    }
                    wa_result2 = await channel.send(
                        telefone_final,
                        title=title,
                        message=mensagem,
                        channel_metadata=channel_metadata2,
                    )
                    wa_result = wa_result2 if wa_result2.success else wa_result

                if wa_result.success:
                    result = {
                        "success": True,
                        "provider": "notifications.contract",
                        "phone": telefone_final,
                        "message_id": wa_result.external_id,
                        "status": "sent",
                    }
                else:
                    result = {
                        "success": False,
                        "provider": "notifications.contract",
                        "phone": telefone_final,
                        "error": wa_result.message or "Erro ao enviar WhatsApp",
                        "details": wa_result.error_details,
                    }
            else:
                # Sem template configurado: fallback para envio de texto legado (pode falhar fora da janela 24h).
                notifier = OrderNotification()
                result = await notifier.send_whatsapp_message(telefone_final, mensagem, empresa_id=empresa_id_final)
        except Exception as e:
            # Último fallback: tenta envio de texto legado
            logger.warning(
                f"[enviar_resumo_pedido] Falha no envio via contract; tentando legado. Erro: {e}"
            )
            notifier = OrderNotification()
            result = await notifier.send_whatsapp_message(telefone_final, mensagem, empresa_id=empresa_id_final)

        if result.get("success"):
            logger.info(
                f"[enviar_resumo_pedido] Resumo do pedido {pedido_id} enviado com sucesso para {telefone_final}"
            )
        else:
            error_msg = result.get("error", "Erro desconhecido")
            logger.warning(
                f"[enviar_resumo_pedido] Falha ao enviar WhatsApp do resumo (pedido {pedido_id}): {error_msg}. "
                f"Resumo será salvo no chat interno."
            )

        # Salva no chat interno (chatbot.messages) para manter histórico SEMPRE
        saved_in_chat = False
        conversation_id = None
        chatbot_message_id = None
        try:
            from . import database as chatbot_db
            from sqlalchemy import text as sql_text
            from datetime import datetime as _dt

            telefone_normalizado = _normalize_phone(telefone_final) or str(telefone_final)
            user_id = telefone_normalizado

            # Converte empresa_id para int quando possível (API do DB usa int)
            empresa_id_int2 = None
            if empresa_id_final:
                try:
                    empresa_id_int2 = int(str(empresa_id_final))
                except (ValueError, TypeError):
                    empresa_id_int2 = None

            # Garante prompt default (para não violar FK)
            prompt_key = "default"
            if not chatbot_db.get_prompt(db, prompt_key, empresa_id=empresa_id_int2):
                chatbot_db.create_prompt(
                    db=db,
                    key=prompt_key,
                    name="Padrão (Resumo de Pedido)",
                    content="Atendente virtual para envio de resumo de pedidos.",
                    is_default=True,
                    empresa_id=empresa_id_int2,
                )

            # Busca conversa existente do usuário (escopada por empresa quando disponível)
            conversations = chatbot_db.get_conversations_by_user(db, user_id, empresa_id=empresa_id_int2)
            if conversations:
                conversation_id = conversations[0]["id"]

                # Se a conversa não tinha empresa_id e agora temos, atualiza
                if empresa_id_int2:
                    try:
                        db.execute(
                            sql_text(
                                """
                                UPDATE chatbot.conversations
                                SET empresa_id = :empresa_id
                                WHERE id = :conversation_id AND empresa_id IS NULL
                                """
                            ),
                            {"empresa_id": empresa_id_int2, "conversation_id": conversation_id},
                        )
                        db.commit()
                    except Exception as e:
                        logger.warning(
                            f"[enviar_resumo_pedido] Não foi possível atualizar empresa_id da conversa {conversation_id}: {e}"
                        )
            else:
                session_id = f"order_summary_{pedido_id}_{_dt.now().strftime('%Y%m%d%H%M%S')}"
                conversation_id = chatbot_db.create_conversation(
                    db=db,
                    session_id=session_id,
                    user_id=user_id,
                    prompt_key=prompt_key,
                    model="notification-system",
                    empresa_id=empresa_id_int2,
                )

            whatsapp_message_id = result.get("message_id") if isinstance(result, dict) else None
            chatbot_message_id = chatbot_db.create_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=mensagem,
                whatsapp_message_id=whatsapp_message_id,
                extra_metadata={
                    "pedido_id": int(pedido_id),
                    "numero_pedido": str(numero_pedido),
                    "status": str(status_code),
                    "tipo_entrega": str(tipo_entrega),
                },
            )
            saved_in_chat = True

            # Notifica frontend via WebSocket (não falha se der erro)
            try:
                await send_chatbot_websocket_notification(
                    empresa_id=empresa_id_int2,
                    notification_type="chatbot_message",
                    title="Resumo de pedido (impresso)",
                    message=f"Resumo do pedido #{numero_pedido} gerado",
                    data={
                        "conversation_id": conversation_id,
                        "message_id": chatbot_message_id,
                        "user_id": user_id,
                        "pedido_id": pedido_id,
                        "numero_pedido": numero_pedido,
                        "role": "assistant",
                        "whatsapp_message_id": whatsapp_message_id,
                        "whatsapp_success": bool(result.get("success")) if isinstance(result, dict) else False,
                    },
                )
            except Exception as e:
                logger.warning(f"[enviar_resumo_pedido] Erro ao enviar notificação WebSocket: {e}")
        except Exception as e:
            logger.error(
                f"[enviar_resumo_pedido] Falhou ao salvar resumo no chat interno (pedido {pedido_id}): {e}",
                exc_info=True,
            )

        return {
            "success": bool(result.get("success")) if isinstance(result, dict) else False,
            "message": "Resumo do pedido processado.",
            "pedido_id": pedido_id,
            "numero_pedido": numero_pedido,
            "status": status_info["name"],
            "used_whatsapp_phone": telefone_final,
            "used_chatbot_phone": user_id if saved_in_chat else None,
            "chat_saved": saved_in_chat,
            "conversation_id": conversation_id,
            "chat_message_id": chatbot_message_id,
            "whatsapp_message_id": result.get("message_id") if isinstance(result, dict) else None,
            "whatsapp_error": None if (isinstance(result, dict) and result.get("success")) else (result.get("error") if isinstance(result, dict) else "erro desconhecido"),
        }

    except Exception as e:
        logger.error(f"[enviar_resumo_pedido] Erro ao enviar resumo do pedido {pedido_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
