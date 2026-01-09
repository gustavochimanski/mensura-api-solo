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
                    logger.debug(f"[WhatsApp] Mensagem {message_id} marcada como lida")
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
                        print(f"   ❌ ERRO COMPLETO ao marcar como lida:")
                        print(f"   📊 Status: {response.status_code}")
                        print(f"   📄 Resposta: {error_message}")
                        print(f"   🔗 URL: {url}")
                        print(f"   📦 Payload enviado: {json.dumps(payload, indent=2, ensure_ascii=False)}")
                    except:
                        error_message = error_text
                        logger.error(f"[WhatsApp] Erro ao marcar mensagem como lida (Status {response.status_code}): {error_message}")
                        print(f"   ❌ ERRO ao marcar como lida: {error_message}")
                    
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

            # Log de debug (também usa print para garantir visibilidade)
            log_msg = f"[WhatsApp] Enviando mensagem - empresa_id={empresa_id}, provider={provider}, base_url={base_url}, is_360={is_360}, token_length={len(access_token) if access_token else 0}"
            logger.debug(log_msg)
            print(f"   🔍 {log_msg}")

            # Valida se o token existe e não está vazio
            if not access_token or access_token.strip() == "":
                error_msg = f"Configuração do WhatsApp ausente ou incompleta: access_token não configurado (empresa_id={empresa_id})"
                logger.error(f"[WhatsApp] {error_msg}")
                print(f"   ❌ {error_msg}")
                print(f"   🔍 Config completa: {config}")
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
                logger.debug(f"[WhatsApp] Headers preparados: {list(headers.keys())}")
                print(f"   🔍 Headers preparados: {list(headers.keys())}")
                # Não mostra o token completo por segurança, apenas indica se existe
                for key in headers.keys():
                    if "key" in key.lower() or "token" in key.lower() or "authorization" in key.lower():
                        header_value = headers[key]
                        if header_value:
                            # Mostra últimos 10 caracteres para debug
                            masked = "***" + str(header_value)[-10:] if len(str(header_value)) > 10 else "***"
                            print(f"   🔍 Header {key}: {masked} (length: {len(str(header_value))})")
                        else:
                            print(f"   ⚠️ Header {key}: VAZIO!")
                
                # Validação extra para 360dialog
                if is_360:
                    api_key = headers.get("D360-API-KEY", "")
                    if not api_key or len(api_key.strip()) == 0:
                        error_msg = "API Key do 360dialog está vazia!"
                        print(f"   ❌ {error_msg}")
                        return {
                            "success": False,
                            "provider": "360dialog",
                            "error": error_msg,
                            "phone": phone,
                        }
                    print(f"   ✅ API Key do 360dialog presente (length: {len(api_key)})")
            except ValueError as e:
                error_msg = f"Erro na configuração do WhatsApp: {str(e)}"
                logger.error(f"[WhatsApp] {error_msg}")
                print(f"   ❌ {error_msg}")
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

                # Validação: remove espaços e caracteres especiais do número
                phone_to_use = ''.join(filter(str.isdigit, phone_to_use))

                # Garante que tem código do país
                if not phone_to_use.startswith('55'):
                    phone_to_use = '55' + phone_to_use

                # Payload conforme documentação oficial da 360Dialog
                # https://docs.360dialog.com/docs/waba-messaging/messaging
                payload = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": phone_to_use,
                    "type": "text",
                    "text": {"body": message},
                }
                
                # Log do número que será usado
                print(f"   📱 Número formatado para envio: {phone_to_use} (original: {phone})")
                
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
            logger.debug(f"[WhatsApp] Enviando para URL: {url}")
            print(f"   🔍 URL: {url}")
            print(f"   🔍 Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
            
            # Para 360Dialog, tenta diferentes formatos se o primeiro falhar
            last_error = None
            last_response = None
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Primeira tentativa com o formato padrão
                response = await client.post(url, json=payload, headers=headers)
                logger.debug(f"[WhatsApp] Resposta recebida - status_code={response.status_code}")
                print(f"   📡 Resposta HTTP: status_code={response.status_code}")
                
                # Se falhar com 400 e for 360Dialog, tenta formato alternativo do número
                if response.status_code == 400 and is_360:
                    # Log detalhado do primeiro erro
                    try:
                        error_json = response.json()
                        print(f"   🔄 PRIMEIRO ERRO DETALHADO (Status 400):")
                        if isinstance(error_json, dict) and "error" in error_json:
                            error_detail = error_json["error"]
                            if isinstance(error_detail, dict):
                                error_code = error_detail.get("code")
                                error_type = error_detail.get("type")
                                error_message = error_detail.get("message")
                                if error_code: print(f"      📋 Code: {error_code}")
                                if error_type: print(f"      🏷️  Type: {error_type}")
                                if error_message: print(f"      💬 Message: {error_message}")
                    except:
                        print(f"   🔄 Primeiro erro: {response.text}")

                    last_error = response.text or ""
                    last_response = response

                    # Tenta sem código do país (apenas DDD + número)
                    if phone_to_use.startswith('55') and len(phone_to_use) > 11:
                        phone_alt = phone_to_use[2:]  # Remove o 55
                        print(f"   🔄 Tentando formato alternativo (sem código do país): {phone_alt}")
                        payload_alt = {
                            "messaging_product": "whatsapp",
                            "recipient_type": "individual",
                            "to": phone_alt,
                            "type": "text",
                            "text": {"body": message},
                        }

                        response = await client.post(url, json=payload_alt, headers=headers)
                        print(f"   📡 Resposta HTTP (tentativa alternativa): status_code={response.status_code}")

                        if response.status_code == 200:
                            # Sucesso com formato alternativo
                            result = response.json()
                            message_id = result.get("messages", [{}])[0].get("id") if result.get("messages") else None
                            print(f"   ✅ Mensagem enviada com sucesso (formato alternativo)! Message ID: {message_id}")
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

                        # Extração detalhada dos erros da 360Dialog/Meta
                        print(f"   ❌ ERRO DETALHADO da API:")
                        print(f"   📊 Status HTTP: {response.status_code}")
                        print(f"   🔗 URL: {url}")
                        print(f"   📦 Payload enviado: {json.dumps(payload, indent=2, ensure_ascii=False)}")
                        print(f"   🔑 Headers: {json.dumps({k: v if 'key' not in k.lower() and 'token' not in k.lower() else '***' + str(v)[-10:] for k, v in headers.items()}, indent=2)}")
                        print(f"   📄 Resposta completa: {error_message}")

                        # Extração específica dos campos de erro
                        if isinstance(error_json, dict):
                            # Para 360Dialog - estrutura comum
                            if "error" in error_json:
                                error_detail = error_json["error"]
                                if isinstance(error_detail, dict):
                                    print(f"   🔍 CAMPOS DO ERRO EXTRAÍDOS:")
                                    error_code = error_detail.get("code")
                                    error_type = error_detail.get("type")
                                    error_subcode = error_detail.get("error_subcode")
                                    error_message = error_detail.get("message")
                                    error_fbtrace_id = error_detail.get("fbtrace_id")

                                    if error_code: print(f"      📋 Code: {error_code}")
                                    if error_type: print(f"      🏷️  Type: {error_type}")
                                    if error_subcode: print(f"      🔢 Subcode: {error_subcode}")
                                    if error_message: print(f"      💬 Message: {error_message}")
                                    if error_fbtrace_id: print(f"      🔍 FBTrace ID: {error_fbtrace_id}")

                                    # Interpretação dos códigos de erro comuns
                                    if error_code == 100:
                                        print(f"      💡 INTERPRETAÇÃO: Número de telefone inválido ou não registrado")
                                    elif error_code == 613:
                                        print(f"      💡 INTERPRETAÇÃO: Número não está na lista de destinatários permitidos")
                                    elif error_code == 615:
                                        print(f"      💡 INTERPRETAÇÃO: Limite de mensagens excedido")
                                    elif error_code == 1003:
                                        print(f"      💡 INTERPRETAÇÃO: Payload inválido ou formato incorreto")
                                    elif error_code == 200:
                                        print(f"      💡 INTERPRETAÇÃO: Permissões insuficientes da API key")
                                    else:
                                        print(f"      💡 INTERPRETAÇÃO: Erro genérico - verificar documentação da 360Dialog")

                                elif isinstance(error_detail, str):
                                    print(f"   🔍 Erro (string): {error_detail}")
                            else:
                                # Outras estruturas de erro possíveis
                                for key, value in error_json.items():
                                    print(f"   🔍 {key}: {value}")

                    except Exception as parse_error:
                        error_message = error_text
                        logger.error(f"[WhatsApp] Erro ao enviar mensagem (Status {response.status_code}): {error_message}")
                        print(f"   ❌ ERRO ao enviar mensagem: {error_message}")
                        print(f"   📄 Resposta completa (texto): {error_text[:1000]}")
                        print(f"   ⚠️ Erro ao parsear JSON: {parse_error}")

                if response.status_code == 200:
                    result = response.json()
                    message_id = result.get("messages", [{}])[0].get("id") if result.get("messages") else None
                    print(f"   ✅ Mensagem enviada com sucesso! Message ID: {message_id}")
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
                
                print(f"   ❌ Erro na API: status_code={response.status_code}, error={error_message}")

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
