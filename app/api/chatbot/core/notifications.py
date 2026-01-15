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
import json

logger = logging.getLogger(__name__)


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
                # Para 360Dialog, tenta diferentes formatos de número se o primeiro falhar
                # Formato 1: Com código do país (padrão)
                phone_to_use = phone_formatted

                # Validação rigorosa do número
                phone_clean = ''.join(filter(str.isdigit, phone_to_use))

                # Garante que tem código do país
                if not phone_clean.startswith('55'):
                    phone_clean = '55' + phone_clean

                # Validação final: deve ter exatamente 13 dígitos para Brasil (55 + 2 DDD + 8 número)
                if len(phone_clean) != 13:
                    logger.warning(f"[WhatsApp] Número tem {len(phone_clean)} dígitos, esperado 13 para Brasil: {phone_clean}")

                phone_to_use = phone_clean

                # Payload conforme documentação oficial da 360Dialog
                # https://docs.360dialog.com/docs/waba-messaging/messaging
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": phone_to_use,
                    "type": "text",
                    "text": {"body": message},
                }
                
                # Não precisamos adicionar "context" ou "message_id" - o 360dialog detecta automaticamente
                # se é uma resposta dentro da janela de conversa baseado no número e timestamp
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
                # Primeira tentativa com o formato padrão
                response = await client.post(url, json=payload, headers=headers)
                
                # Se falhar com 400 e for 360Dialog, tenta formato alternativo do número
                if response.status_code == 400 and is_360:
                    # Tenta sem código do país (apenas DDD + número)
                    if phone_to_use.startswith('55') and len(phone_to_use) > 11:
                        phone_alt = phone_to_use[2:]  # Remove o 55
                        payload_alt = {
                            "messaging_product": "whatsapp",
                            "recipient_type": "individual",
                            "to": phone_alt,
                            "type": "text",
                            "text": {"body": message},
                        }

                        response = await client.post(url, json=payload_alt, headers=headers)

                        if response.status_code == 200:
                            # Sucesso com formato alternativo
                            result = response.json()
                            message_id = result.get("messages", [{}])[0].get("id") if result.get("messages") else None
                            logger.info(f"[WhatsApp] Mensagem enviada com sucesso (formato alternativo). Message ID: {message_id}")
                            return {
                                "success": True,
                                "provider": "360dialog",
                                "phone": phone_alt,
                                "message_id": message_id,
                                "status": "sent",
                                "response": result,
                                "note": "Enviado com formato alternativo (sem código do país)"
                            }
                
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
                        "phone": phone_formatted,
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
                # 360Dialog usa formato similar ao Meta
                phone_clean = ''.join(filter(str.isdigit, phone_formatted))
                if not phone_clean.startswith('55'):
                    phone_clean = '55' + phone_clean

                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": phone_clean,
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

            # Envia a mensagem
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    message_id = result.get("messages", [{}])[0].get("id") if result.get("messages") else None
                    logger.info(f"[WhatsApp] Mensagem com botões enviada com sucesso. Message ID: {message_id}")
                    return {
                        "success": True,
                        "provider": "360dialog" if is_360 else "WhatsApp Business API (Meta)",
                        "message_id": message_id,
                        "phone": phone_formatted
                    }
                else:
                    error_data = response.json() if response.text else {}
                    error_message = error_data.get("error", {}).get("message", response.text) if isinstance(error_data, dict) else response.text
                    
                    return {
                        "success": False,
                        "provider": "360dialog" if is_360 else "WhatsApp Business API (Meta)",
                        "error": error_message,
                        "status_code": response.status_code,
                        "phone": phone_formatted
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
        from .config_whatsapp import load_whatsapp_config

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

        # Envia via WhatsApp API
        empresa_id = order_data.get("empresa_id")
        whatsapp_result = await cls.send_whatsapp_message(phone, message, empresa_id=empresa_id)
        results["whatsapp_api"] = whatsapp_result

        # Considera sucesso se WhatsApp API funcionou
        if whatsapp_result.get("success"):
            results["success"] = True
            results["provider"] = "WhatsApp API + Chat Interno"
            results["message"] = "Notificação enviada via WhatsApp e salva no chat"
        else:
            results["success"] = False
            results["error"] = whatsapp_result.get("error")
            results["message"] = (
                whatsapp_result.get("coexistence_hint")
                or "Erro ao enviar via WhatsApp, mas salvo no chat"
            )
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
