"""
Router do módulo de Chatbot
Todas as rotas relacionadas ao chatbot com IA (Ollama)
"""
from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import httpx
import json
import uuid
from datetime import datetime, timedelta

from app.database.db_connection import get_db
from ..core import database as chatbot_db
from ..core.notifications import OrderNotification
from ..core.groq_sales_handler import GroqSalesHandler
from app.api.notifications.repositories.whatsapp_config_repository import WhatsAppConfigRepository
from app.api.empresas.repositories.empresa_repo import EmpresaRepository

# Import ngrok functions optionally (pyngrok may not be installed)
try:
    from ..core.ngrok_manager import get_public_url, get_webhook_url
    NGROK_AVAILABLE = True
except ImportError:
    NGROK_AVAILABLE = False
    def get_public_url():
        return None
    def get_webhook_url():
        return None
from ..schemas.schemas import (
    ChatRequest,
    ChatResponse,
    PromptCreate,
    PromptUpdate,
    ConversationCreate,
    MessageCreate,
    OrderNotificationRequest,
    WhatsAppConfigUpdate,
    WhatsAppConfigResponse
)

# Configurações do Ollama
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3.1:8b"

# Prompt padrão do sistema
SYSTEM_PROMPT = """Você é um atendente humano chamado Alex, que trabalha no suporte ao cliente de uma empresa de restaurante/delivery.

Características da sua personalidade:
- Você é amigável, paciente e prestativo
- Usa linguagem natural e casual (não formal demais)
- Ocasionalmente usa expressões cotidianas como "Entendi!", "Perfeito!", "Deixa eu ver..."
- Não revela que é uma IA - responda como se fosse uma pessoa real
- Mantém o contexto da conversa anterior
- Quando não sabe algo, admite naturalmente: "Deixa eu verificar isso para você"
- É empático e entende frustrações do cliente

Tom de conversa:
- Natural e conversacional
- Frases curtas e diretas
- Evita jargões técnicos desnecessários
- Usa emojis ocasionalmente (mas com moderação)

Lembre-se: você é Alex, um humano real ajudando outro humano. Seja genuíno!"""

# Router
router = APIRouter(
    prefix="/api/chatbot",
    tags=["API - Chatbot"]
)

# Incluir router de configurações do chatbot
from .router_chatbot_config import router as router_chatbot_config
router.include_router(router_chatbot_config)


# ==================== ENDPOINTS BÁSICOS ====================

@router.get("/health")
async def health_check():
    """Verifica se o Ollama está rodando"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                return {
                    "ollama": "online",
                    "models_disponiveis": model_names
                }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama não está rodando. Erro: {str(e)}"
        )


# ==================== CHAT ====================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Endpoint principal do chat"""

    # Se o modelo for "notification-system", significa que é uma conversa de notificação
    # Vamos mudar para o modelo padrão para permitir chat normal
    actual_model = request.model
    if request.model == "notification-system":
        actual_model = DEFAULT_MODEL

    # Usa o system prompt customizado se fornecido, caso contrário usa o padrão
    system_prompt = request.system_prompt if request.system_prompt else SYSTEM_PROMPT

    # Monta as mensagens com o system prompt
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Adiciona as mensagens do histórico
    for msg in request.messages:
        messages.append({
            "role": msg.role,
            "content": msg.content
        })

    # Chama o Ollama
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "model": actual_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                    "top_p": 0.9,
                    "top_k": 40,
                }
            }

            response = await client.post(OLLAMA_URL, json=payload)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Erro no Ollama: {response.text}"
                )

            result = response.json()
            assistant_message = result["message"]["content"]

            return ChatResponse(
                response=assistant_message,
                model=actual_model
            )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Timeout ao aguardar resposta do modelo"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )


# ==================== PROMPTS ====================

@router.get("/prompts")
async def list_prompts(db: Session = Depends(get_db), empresa_id: Optional[int] = None):
    """Lista todos os prompts"""
    prompts = chatbot_db.get_all_prompts(db, empresa_id)
    return {"prompts": prompts}


@router.get("/prompts/{key}")
async def get_prompt_by_key(key: str, db: Session = Depends(get_db), empresa_id: Optional[int] = None):
    """Busca um prompt específico"""
    prompt = chatbot_db.get_prompt(db, key, empresa_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt não encontrado")
    return prompt


@router.post("/prompts")
async def create_new_prompt(prompt: PromptCreate, db: Session = Depends(get_db), empresa_id: Optional[int] = None):
    """Cria um novo prompt customizado"""
    # Garante que não é um prompt padrão
    if prompt.key in ["default", "custom1", "custom2"]:
        raise HTTPException(
            status_code=400,
            detail="Não é possível criar prompt com chave reservada"
        )

    result = chatbot_db.create_prompt(
        db=db,
        key=prompt.key,
        name=prompt.name,
        content=prompt.content,
        is_default=False,
        empresa_id=empresa_id
    )

    if not result:
        raise HTTPException(
            status_code=409,
            detail="Prompt com esta chave já existe"
        )

    return result


@router.put("/prompts/{key}")
async def update_existing_prompt(key: str, prompt: PromptUpdate, db: Session = Depends(get_db), empresa_id: Optional[int] = None):
    """Atualiza um prompt customizado"""
    success = chatbot_db.update_prompt(db, key, prompt.name, prompt.content, empresa_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Prompt não encontrado ou é um prompt padrão"
        )
    return {"message": "Prompt atualizado com sucesso"}


@router.delete("/prompts/{key}")
async def delete_existing_prompt(key: str, db: Session = Depends(get_db), empresa_id: Optional[int] = None):
    """Deleta um prompt customizado"""
    success = chatbot_db.delete_prompt(db, key, empresa_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Prompt não encontrado ou é um prompt padrão"
        )
    return {"message": "Prompt deletado com sucesso"}


# ==================== CONVERSAS ====================

@router.post("/conversations")
async def create_new_conversation(conv: ConversationCreate, db: Session = Depends(get_db)):
    """Cria uma nova conversa"""
    session_id = conv.session_id or str(uuid.uuid4())

    conversation_id = chatbot_db.create_conversation(
        db=db,
        session_id=session_id,
        user_id=conv.user_id,
        prompt_key=conv.prompt_key,
        model=conv.model,
        empresa_id=conv.empresa_id
    )

    # Envia notificação WebSocket de nova conversa
    from ..core.notifications import send_chatbot_websocket_notification
    await send_chatbot_websocket_notification(
        empresa_id=conv.empresa_id,
        notification_type="chatbot_conversation",
        title="Nova Conversa",
        message=f"Nova conversa criada para {conv.user_id}",
        data={
            "conversation_id": conversation_id,
            "session_id": session_id,
            "user_id": conv.user_id,
            "model": conv.model
        }
    )

    return {
        "id": conversation_id,
        "session_id": session_id,
        "user_id": conv.user_id
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation_details(conversation_id: int, db: Session = Depends(get_db)):
    """Busca uma conversa com todas as mensagens"""
    conversation = chatbot_db.get_conversation_with_messages(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return conversation


@router.get("/conversations/session/{session_id}")
async def get_session_conversations(session_id: str, db: Session = Depends(get_db), empresa_id: Optional[int] = None):
    """Lista todas as conversas de uma sessão"""
    conversations = chatbot_db.get_conversations_by_session(db, session_id, empresa_id)
    return {"conversations": conversations}


@router.get("/conversations/user/{user_id}")
async def get_user_conversations(user_id: str, db: Session = Depends(get_db), empresa_id: Optional[int] = None):
    """Lista todas as conversas de um usuário"""
    conversations = chatbot_db.get_conversations_by_user(db, user_id, empresa_id)
    return {"conversations": conversations}


@router.get("/conversations/user/{user_id}/latest")
async def get_user_latest_conversation(user_id: str, db: Session = Depends(get_db)):
    """Busca a conversa mais recente de um usuário"""
    conversations = chatbot_db.get_conversations_by_user(db, user_id)

    if not conversations:
        raise HTTPException(status_code=404, detail="Nenhuma conversa encontrada")

    # Pega a conversa mais recente
    latest_conversation = conversations[0]
    conversation_id = latest_conversation['id']

    # Busca as mensagens
    messages = chatbot_db.get_messages(db, conversation_id)

    return {
        "conversation": latest_conversation,
        "messages": messages
    }


@router.get("/conversations")
async def list_all_conversations(db: Session = Depends(get_db)):
    """Lista TODAS as conversas do sistema (para admin)"""
    try:
        from sqlalchemy import text
        query = text(f"""
            SELECT
                c.id,
                c.session_id,
                c.user_id,
                c.contact_name,
                c.prompt_key,
                c.model,
                c.empresa_id,
                c.created_at,
                c.updated_at,
                COUNT(m.id) as message_count,
                MAX(m.created_at) as last_message_at
            FROM chatbot.conversations c
            LEFT JOIN chatbot.messages m ON c.id = m.conversation_id
            GROUP BY c.id, c.session_id, c.user_id, c.contact_name, c.prompt_key, c.model, c.empresa_id, c.created_at, c.updated_at
            ORDER BY c.updated_at DESC
        """)

        result = db.execute(query)
        conversations = [
            {
                "id": row[0],
                "session_id": row[1],
                "user_id": row[2],
                "contact_name": row[3],
                "prompt_key": row[4],
                "model": row[5],
                "empresa_id": row[6],
                "created_at": row[7],
                "updated_at": row[8],
                "message_count": row[9],
                "last_message_at": row[10]
            }
            for row in result.fetchall()
        ]
        return {"conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar conversas: {str(e)}")


@router.put("/conversations/{conversation_id}/settings")
async def update_conversation_settings(
    conversation_id: int,
    db: Session = Depends(get_db),
    model: Optional[str] = None,
    prompt_key: Optional[str] = None
):
    """Atualiza configurações de uma conversa (modelo e/ou prompt)"""
    conversation = chatbot_db.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    try:
        from sqlalchemy import text
        updates = []
        params = {}

        if model:
            updates.append("model = :model")
            params["model"] = model

        if prompt_key:
            updates.append("prompt_key = :prompt_key")
            params["prompt_key"] = prompt_key

        if not updates:
            raise HTTPException(status_code=400, detail="Nenhuma atualização fornecida")

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params["conversation_id"] = conversation_id

        query = text(f"""
            UPDATE chatbot.conversations
            SET {', '.join(updates)}
            WHERE id = :conversation_id
        """)

        db.execute(query, params)
        db.commit()

        return {"message": "Configurações atualizadas com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar: {str(e)}")


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: int, db: Session = Depends(get_db)):
    """Lista todas as mensagens de uma conversa"""
    conversation = chatbot_db.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    messages = chatbot_db.get_messages(db, conversation_id)
    return {"messages": messages}


@router.post("/conversations/{conversation_id}/messages")
async def add_message_to_conversation(conversation_id: int, message: MessageCreate, db: Session = Depends(get_db)):
    """Adiciona uma mensagem à conversa"""
    conversation = chatbot_db.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")

    # Se a conversa é de notificação e o usuário está enviando uma mensagem,
    # atualiza o modelo para permitir chat normal
    if conversation['model'] == 'notification-system' and message.role == 'user':
        chatbot_db.update_conversation_model(db, conversation_id, DEFAULT_MODEL)

    message_id = chatbot_db.create_message(
        db=db,
        conversation_id=conversation_id,
        role=message.role,
        content=message.content
    )

    # Envia notificação WebSocket para atualizar o frontend
    from ..core.notifications import send_chatbot_websocket_notification
    await send_chatbot_websocket_notification(
        empresa_id=conversation.get('empresa_id'),
        notification_type="chatbot_message",
        title="Nova Mensagem",
        message=f"Nova mensagem na conversa {conversation_id}",
        data={
            "conversation_id": conversation_id,
            "message_id": message_id,
            "role": message.role,
            "user_id": conversation.get('user_id'),
            "content_preview": message.content[:100] if len(message.content) > 100 else message.content
        }
    )

    return {"id": message_id}


@router.delete("/conversations/{conversation_id}")
async def delete_existing_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Deleta uma conversa e suas mensagens"""
    success = chatbot_db.delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return {"message": "Conversa deletada com sucesso"}


# ==================== ESTATÍSTICAS ====================

@router.get("/stats")
async def get_database_stats(db: Session = Depends(get_db), empresa_id: Optional[int] = None):
    """Retorna estatísticas do banco de dados"""
    stats = chatbot_db.get_stats(db, empresa_id)
    return stats


# ==================== BOT STATUS (PAUSAR/ATIVAR) ====================

@router.get("/bot-status/{phone_number}")
async def get_bot_status_for_phone(phone_number: str, db: Session = Depends(get_db)):
    """Verifica se o bot está ativo para um número específico"""
    status = chatbot_db.get_bot_status(db, phone_number)
    return status


@router.put("/bot-status/{phone_number}")
async def toggle_bot_status(
    phone_number: str,
    is_active: bool,
    paused_by: Optional[str] = None,
    empresa_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Ativa ou desativa o bot para um número específico"""
    result = chatbot_db.set_bot_status(db, phone_number, is_active, paused_by, empresa_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Erro ao atualizar status"))
    return result


@router.get("/bot-status")
async def list_all_bot_statuses(db: Session = Depends(get_db), empresa_id: Optional[int] = None):
    """Lista todos os status de bot (útil para ver quais números estão pausados)"""
    statuses = chatbot_db.get_all_bot_statuses(db, empresa_id)
    return {"statuses": statuses}


@router.put("/bot-status-global")
async def toggle_all_bots(
    is_active: bool,
    paused_by: Optional[str] = None,
    empresa_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Ativa ou desativa o bot para TODOS os números de uma vez"""
    result = chatbot_db.set_global_bot_status(db, is_active, paused_by, empresa_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Erro ao atualizar status global"))
    return result


@router.get("/bot-status-global")
async def get_global_bot_status(db: Session = Depends(get_db), empresa_id: Optional[int] = None):
    """Verifica se o bot global está ativo"""
    status = chatbot_db.get_global_bot_status(db, empresa_id)
    return status


# ==================== NOTIFICAÇÕES ====================

@router.post("/notifications/order-confirmed")
async def send_order_notification(notification: OrderNotificationRequest, db: Session = Depends(get_db)):
    """
    Endpoint para enviar notificação de pedido confirmado
    Chamado quando um pedido é confirmado no sistema
    """
    order_data = {
        "client_name": notification.client_name,
        "client_phone": notification.client_phone,
        "order_id": notification.order_id,
        "items": notification.items,
        "total": notification.total,
    }

    # Adiciona campos específicos por tipo
    if notification.order_type == "cardapio":
        order_data["address"] = notification.address
        order_data["estimated_time"] = notification.estimated_time
    elif notification.order_type == "mesa":
        order_data["table_number"] = notification.table_number
    elif notification.order_type == "balcao":
        order_data["preparation_time"] = notification.preparation_time

    # Envia notificação (usa versão async diretamente)
    notifier = OrderNotification()
    result = await notifier.notify_order_confirmed_async(db, order_data, notification.order_type)

    # Considera sucesso se pelo menos o chat interno funcionou
    chat_success = result.get("chat_interno", {}).get("success", False)
    whatsapp_success = result.get("whatsapp_api", {}).get("success", False)

    if chat_success or whatsapp_success:
        return {
            "success": True,
            "message": result.get("message", "Notificação enviada"),
            "data": result
        }
    else:
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Erro ao enviar notificação")
        )


@router.post("/send-notification")
async def send_notification(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint simples para enviar notificações WhatsApp
    Aceita telefone e mensagem formatada
    Salva a mensagem no histórico da conversa
    """
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao processar JSON: {str(e)}"
        )
    
    phone = body.get("phone")
    message = body.get("message")

    if not phone or not message:
        raise HTTPException(
            status_code=400,
            detail="Telefone e mensagem são obrigatórios"
        )

    # Envia via WhatsApp
    notifier = OrderNotification()
    result = await notifier.send_whatsapp_message(phone, message)

    if result.get("success"):
        # Salva a mensagem enviada no histórico da conversa
        try:
            conversations = chatbot_db.get_conversations_by_user(db, phone)
            if conversations:
                chatbot_db.create_message(
                    db=db,
                    conversation_id=conversations[0]['id'],
                    role="assistant",
                    content=message
                )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao salvar mensagem no histórico: {e}")

        return {
            "success": True,
            "message": "Notificação enviada com sucesso",
            "data": result
        }
    else:
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Erro ao enviar notificação")
        )


@router.post("/send-media")
async def send_media(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint para enviar arquivos (imagem, documento, audio, video) via WhatsApp
    Salva a mensagem no histórico da conversa
    """
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao processar JSON: {str(e)}"
        )
    
    phone = body.get("phone")
    media_url = body.get("media_url")
    media_type = body.get("media_type", "image")  # image, document, audio, video
    caption = body.get("caption", "")

    if not phone or not media_url:
        raise HTTPException(
            status_code=400,
            detail="Telefone e media_url sao obrigatorios"
        )

    # Busca config do WhatsApp
    config = await get_whatsapp_config()
    access_token = config.access_token
    phone_number_id = config.phone_number_id

    if not access_token or not phone_number_id:
        raise HTTPException(
            status_code=500,
            detail="Configuracao do WhatsApp incompleta"
        )

    # Formata o numero (remove caracteres especiais)
    phone_clean = ''.join(filter(str.isdigit, phone))

    # Monta o payload para enviar media
    url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": phone_clean,
        "type": media_type
    }

    # Adiciona o objeto de media baseado no tipo
    if media_type == "image":
        payload["image"] = {"link": media_url}
        if caption:
            payload["image"]["caption"] = caption
    elif media_type == "document":
        payload["document"] = {"link": media_url}
        if caption:
            payload["document"]["caption"] = caption
            payload["document"]["filename"] = caption
    elif media_type == "audio":
        payload["audio"] = {"link": media_url}
    elif media_type == "video":
        payload["video"] = {"link": media_url}
        if caption:
            payload["video"]["caption"] = caption

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            result = response.json()

            if response.status_code == 200:
                # Salva a mensagem enviada no histórico da conversa
                try:
                    conversations = chatbot_db.get_conversations_by_user(db, phone)
                    if conversations:
                        # Salva como JSON para o frontend poder renderizar a mídia
                        media_content = json.dumps({
                            "type": "media",
                            "media_type": media_type,
                            "media_url": media_url,
                            "caption": caption or ""
                        })
                        chatbot_db.create_message(
                            db=db,
                            conversation_id=conversations[0]['id'],
                            role="assistant",
                            content=media_content
                        )
                except Exception as save_error:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Erro ao salvar mídia no histórico: {save_error}")

                return {
                    "success": True,
                    "message": "Arquivo enviado com sucesso",
                    "message_id": result.get("messages", [{}])[0].get("id")
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=result.get("error", {}).get("message", "Erro ao enviar arquivo")
                )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao enviar media: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao enviar arquivo: {str(e)}"
        )


@router.post("/upload-file")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """
    Faz upload de arquivo e retorna URL publica para envio via WhatsApp
    """
    import os
    import uuid as uuid_module
    from pathlib import Path

    # Diretório para arquivos temporários
    upload_dir = Path("./uploads")
    upload_dir.mkdir(exist_ok=True)

    # Gera nome único para o arquivo
    file_ext = Path(file.filename).suffix if file.filename else ""
    unique_filename = f"{uuid_module.uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename

    try:
        # Salva o arquivo
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Retorna URL pública
        # Prioridade: variável de ambiente > header X-Forwarded-Host > tunnel ativo
        base_url = os.getenv("CHATBOT_PUBLIC_URL")
        if not base_url:
            # Tenta pegar do header (quando via tunnel/proxy)
            forwarded_host = request.headers.get("x-forwarded-host")
            forwarded_proto = request.headers.get("x-forwarded-proto", "https")
            if forwarded_host:
                base_url = f"{forwarded_proto}://{forwarded_host}"
            else:
                # Tenta detectar tunnel ativo verificando se há conexão
                import subprocess
                try:
                    result = subprocess.run(
                        ["pgrep", "-f", "cloudflared"],
                        capture_output=True,
                        text=True,
                        timeout=1
                    )
                    if result.returncode == 0:
                        # Tunnel está ativo, usa URL padrão do tunnel
                        # Em produção, isso deve ser configurado via env var
                        base_url = "https://requirements-travel-heavy-inter.trycloudflare.com"
                    else:
                        base_url = "http://localhost:8000"
                except:
                    base_url = "http://localhost:8000"

        file_url = f"{base_url}/api/chatbot/files/{unique_filename}"


        return {
            "success": True,
            "url": file_url,
            "filename": unique_filename
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao fazer upload: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao fazer upload: {str(e)}"
        )


@router.get("/files/{filename}")
async def serve_file(filename: str):
    """
    Serve arquivos uploadados para que o WhatsApp possa baixá-los
    """
    from fastapi.responses import FileResponse
    from pathlib import Path

    file_path = Path("./uploads") / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # Detecta o tipo MIME
    import mimetypes
    content_type, _ = mimetypes.guess_type(str(file_path))

    return FileResponse(
        path=str(file_path),
        media_type=content_type or "application/octet-stream",
        filename=filename
    )


# ==================== WEBHOOKS DO WHATSAPP ====================

@router.get("/webhook-test")
async def webhook_test(request: Request):
    """
    Endpoint de teste para verificar se a URL está acessível
    """
    import json
    return {
        "status": "ok",
        "message": "Webhook endpoint está acessível!",
        "url": str(request.url),
        "method": request.method,
        "headers": dict(request.headers),
        "query_params": dict(request.query_params)
    }

@router.get("/webhook")
async def webhook_verification(request: Request):
    """
    Verificação do webhook do WhatsApp (Meta)
    A Meta envia um GET request para verificar o webhook
    """
    from fastapi.responses import PlainTextResponse
    
    try:
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        # Token de verificação - você pode mudar isso
        VERIFY_TOKEN = "meu_token_secreto_123"

        if mode == "subscribe" and token == VERIFY_TOKEN:
            # Retornar o challenge como texto puro (WhatsApp espera text/plain)
            if challenge:
                return PlainTextResponse(content=str(challenge))
            else:
                raise HTTPException(status_code=400, detail="Challenge não fornecido")
        else:
            raise HTTPException(status_code=403, detail="Falha na verificação")
    except HTTPException:
        # Re-raise HTTPException para manter o comportamento correto
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro inesperado na verificação do webhook: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


def get_empresa_id_by_business_account_id(db: Session, business_account_id: str) -> Optional[str]:
    """
    Busca o empresa_id baseado no business_account_id da configuração do WhatsApp
    
    Tenta primeiro buscar configurações ativas, depois inativas se necessário.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not business_account_id:
        return None
    
    try:
        # Normaliza o business_account_id para string (caso venha como número)
        business_account_id = str(business_account_id).strip()
        
        repo = WhatsAppConfigRepository(db)
        
        # Primeiro tenta buscar apenas ativas
        config = repo.get_by_business_account_id(business_account_id, include_inactive=False)
        
        # Se não encontrou ativa, tenta buscar inativas também
        if not config:
            config = repo.get_by_business_account_id(business_account_id, include_inactive=True)
            if config:
                logger.warning(f"Configuração inativa encontrada para business_account_id={business_account_id}")
        
        if config:
            empresa_id = str(config.empresa_id)
            return empresa_id
        else:
            logger.error(f"Nenhuma configuração encontrada para business_account_id={business_account_id}")
            return None
            
    except Exception as e:
        logger.error(f"Erro ao buscar empresa_id por business_account_id={business_account_id}: {e}", exc_info=True)
        return None


def get_empresa_id_by_phone_number_id(db: Session, phone_number_id: str) -> Optional[str]:
    """
    Busca o empresa_id baseado no phone_number_id da configuração do WhatsApp
    
    Tenta primeiro buscar configurações ativas, depois inativas se necessário.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not phone_number_id:
        return None
    
    try:
        # Normaliza o phone_number_id para string (caso venha como número)
        phone_number_id = str(phone_number_id).strip()
        
        repo = WhatsAppConfigRepository(db)
        
        # Primeiro tenta buscar apenas ativas
        config = repo.get_by_phone_number_id(phone_number_id, include_inactive=False)
        
        # Se não encontrou ativa, tenta buscar inativas também
        if not config:
            config = repo.get_by_phone_number_id(phone_number_id, include_inactive=True)
            if config:
                logger.warning(f"Configuração inativa encontrada para phone_number_id={phone_number_id}")
        
        if config:
            empresa_id = str(config.empresa_id)
            return empresa_id
        else:
            logger.error(f"Nenhuma configuração encontrada para phone_number_id={phone_number_id}")
            return None
            
    except Exception as e:
        logger.error(f"Erro ao buscar empresa_id por phone_number_id={phone_number_id}: {e}", exc_info=True)
        return None


def _extrair_slug_do_host(host: Optional[str]) -> Optional[str]:
    if not host:
        return None
    host = host.split(":")[0].strip().lower()
    partes = host.split(".")
    if len(partes) >= 3:
        return partes[0]
    return None


def get_empresa_id_by_slug(db: Session, slug: Optional[str]) -> Optional[str]:
    import logging
    logger = logging.getLogger(__name__)

    if not slug:
        return None

    try:
        slug = str(slug).strip().lower()
        repo = EmpresaRepository(db)
        empresa = repo.get_emp_by_slug(slug)
        if empresa:
            return str(empresa.id)
        logger.warning(f"Nenhuma EMPRESA encontrada para slug={slug}")
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar empresa por slug={slug}: {e}", exc_info=True)
        return None


def get_empresa_id_from_webhook(db: Session, metadata: dict, business_account_id: Optional[str] = None, slug_hint: Optional[str] = None) -> Optional[str]:
    """
    Tenta identificar a empresa a partir dos dados do webhook.
    Tenta múltiplas estratégias (em ordem de prioridade):
    1. business_account_id (mais confiável - vem no entry.id do webhook)
    2. slug da empresa (vindo do header x-cliente ou host)
    3. phone_number_id (da configuração do WhatsApp)
    4. display_phone_number (alternativa para 360dialog)
    
    IMPORTANTE: Estamos identificando a EMPRESA (loja), não o CLIENTE (quem enviou a mensagem)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        repo = WhatsAppConfigRepository(db)

        # Estratégia 1: business_account_id (MAIS CONFIÁVEL - vem no entry.id do webhook)
        if business_account_id:
            business_account_id = str(business_account_id).strip()
            empresa_id = get_empresa_id_by_business_account_id(db, business_account_id)
            if empresa_id:
                return empresa_id

        # Estratégia 2: slug da empresa vindo do header (x-cliente) ou host
        if slug_hint:
            empresa_id = get_empresa_id_by_slug(db, slug_hint)
            if empresa_id:
                return empresa_id
        
        if not metadata:
            return None
        
        # Estratégia 3: Buscar por phone_number_id
        phone_number_id = metadata.get("phone_number_id")
        if phone_number_id:
            # Normaliza para string
            phone_number_id = str(phone_number_id).strip()
            
            # Usa a função melhorada que já tenta buscar inativas se necessário
            empresa_id = get_empresa_id_by_phone_number_id(db, phone_number_id)
            if empresa_id:
                return empresa_id
        
        # Estratégia 4: Buscar por display_phone_number (útil para 360dialog)
        display_phone_number = metadata.get("display_phone_number")
        if display_phone_number:
            display_phone_number = str(display_phone_number).strip()
            
            # Primeiro tenta buscar apenas ativas
            config = repo.get_by_display_phone_number(display_phone_number, include_inactive=False)
            
            # Se não encontrou ativa, tenta buscar inativas também
            if not config:
                config = repo.get_by_display_phone_number(display_phone_number, include_inactive=True)
                if config:
                    logger.warning(f"Configuração inativa encontrada para display_phone_number={display_phone_number}")
            
            if config:
                empresa_id = str(config.empresa_id)
                return empresa_id
        
        logger.warning("Não foi possível identificar EMPRESA usando nenhuma estratégia")
        return None
    except Exception as e:
        logger.error(f"Erro ao identificar empresa do webhook: {e}", exc_info=True)
        return None


@router.post("/webhook")
async def webhook_handler(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Recebe mensagens do WhatsApp via webhook (360Dialog/Meta)
    
    IMPORTANTE: Segue a documentação da 360Dialog:
    - Retorna 200 OK imediatamente após receber o webhook
    - Processa mensagens de forma assíncrona em background
    - Processa messages, statuses e errors conforme documentação
    """
    # PRIMEIRA VERIFICAÇÃO: Status global do bot (antes de qualquer log ou processamento)
    try:
        global_status = chatbot_db.get_global_bot_status(db)
        if not global_status.get("is_active", True):
            # Bot desligado: retorna OK sem processar nada
            return {"status": "ok", "message": "Chatbot desligado"}
    except Exception as e:
        # Se falhar ao verificar status, assume que está ligado para não bloquear webhooks
        pass
    
    try:
        # Lê o body de forma segura
        try:
            body_bytes = await request.body()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao ler body da requisição: {e}")
            # Retorna 200 OK imediatamente mesmo com erro (requisito da 360Dialog)
            return {"status": "ok", "message": "Erro ao ler body, mas webhook recebido"}
        
        # Verifica se há body
        if not body_bytes or len(body_bytes) == 0:
            # Retorna 200 OK imediatamente (requisito da 360Dialog)
            return {"status": "ok", "message": "Webhook recebido sem body"}
        
        # Tenta parsear JSON
        try:
            body_text = body_bytes.decode('utf-8')
            if not body_text.strip():
                # Retorna 200 OK imediatamente (requisito da 360Dialog)
                return {"status": "ok", "message": "Webhook recebido com body vazio"}
            body = json.loads(body_text)
        except json.JSONDecodeError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao parsear JSON do webhook: {e}")
            # Retorna 200 OK imediatamente mesmo com erro de JSON (requisito da 360Dialog)
            return {"status": "ok", "message": "Webhook recebido (JSON inválido, mas processado)"}

        # CRÍTICO: Retorna 200 OK IMEDIATAMENTE antes de processar
        # Conforme documentação 360Dialog: "acknowledge immediately after receiving the webhook"
        # Processa tudo em background para não violar o limite de 5 segundos
        
        # Adiciona processamento em background
        # IMPORTANTE: Não passa a sessão do banco diretamente, cria nova sessão na função
        headers_info = {
            "x_cliente": request.headers.get("x-cliente"),
            "host": request.headers.get("host"),
        }
        background_tasks.add_task(process_webhook_background, body, headers_info)

        # Retorna 200 OK imediatamente (requisito crítico da 360Dialog)
        return {"status": "ok"}

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro no webhook: {e}", exc_info=True)
        # Mesmo com erro, retorna 200 OK para não quebrar o webhook
        return {"status": "ok", "message": f"Webhook recebido (erro: {str(e)})"}


async def process_webhook_background(body: dict, headers_info: Optional[dict] = None):
    """
    Processa webhook em background (após retornar 200 OK)
    Processa messages, statuses e errors conforme documentação 360Dialog
    
    IMPORTANTE: Cria nova sessão do banco aqui, pois background tasks
    não podem usar a sessão da requisição original
    """
    # Cria nova sessão do banco para background task
    from app.database.db_connection import get_db
    db = next(get_db())
    
    try:
        # PRIMEIRA VERIFICAÇÃO: Status global do bot (antes de qualquer processamento)
        global_status = chatbot_db.get_global_bot_status(db)
        if not global_status.get("is_active", True):
            # Bot desligado: ignora tudo sem logar nada
            return
        # Verifica se é uma mensagem do WhatsApp Business Account
        if body.get("object") == "whatsapp_business_account":
            entries = body.get("entry", [])

            for entry in entries:
                # O entry.id é o WhatsApp Business Account ID (mais confiável para identificar empresa)
                business_account_id = entry.get("id")
                
                changes = entry.get("changes", [])

                for change in changes:
                    value = change.get("value", {})
                    field = change.get("field", "")

                    # Extrai dados do metadata para identificar a empresa
                    metadata = value.get("metadata", {})

                    slug_hint = None
                    if headers_info:
                        slug_hint = headers_info.get("x_cliente")
                        if not slug_hint:
                            slug_hint = _extrair_slug_do_host(headers_info.get("host"))

                    # Tenta identificar empresa usando múltiplas estratégias
                    # Prioriza business_account_id (entry.id) que é o mais confiável
                    empresa_id = get_empresa_id_from_webhook(db, metadata, business_account_id=business_account_id, slug_hint=slug_hint)
                    
                    if not empresa_id:
                        # Fallback para empresa_id padrão
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning("Empresa não identificada no webhook, usando fallback empresa_id=1")
                        empresa_id = "1"

                    # Processa MESSAGES (mensagens recebidas)
                    messages = value.get("messages", [])
                    if messages:
                        # Extrai nome do contato da Meta (se disponível)
                        contacts = value.get("contacts", [])
                        contact_name = None
                        if contacts and len(contacts) > 0:
                            profile = contacts[0].get("profile", {})
                            contact_name = profile.get("name")

                        for message in messages:
                            # Dados da mensagem
                            from_number = message.get("from")
                            message_id = message.get("id")
                            message_type = message.get("type")
                            timestamp = message.get("timestamp")

                            # Extrai o texto da mensagem
                            message_text = None
                            button_id = None
                            
                            if message_type == "text":
                                message_text = message.get("text", {}).get("body")
                            elif message_type == "interactive":
                                # Mensagem de botão interativo
                                interactive = message.get("interactive", {})
                                button_response = interactive.get("button_reply", {})
                                button_id = button_response.get("id")
                                message_text = button_response.get("title")  # Texto do botão

                            if message_text:
                                # Marca mensagem como lida (conforme documentação 360Dialog)
                                # Todas as mensagens recebidas aparecem como "delivered" por padrão
                                # Para aparecerem como "read", precisamos marcar explicitamente
                                try:
                                    await OrderNotification.mark_message_as_read(message_id, empresa_id)
                                except Exception as mark_error:
                                    import logging
                                    logger = logging.getLogger(__name__)
                                    logger.error(f"Erro ao marcar mensagem como lida: {mark_error}")
                                
                                # Processa a mensagem com a IA (passa o nome do contato, empresa_id, message_id e button_id)
                                await process_whatsapp_message(db, from_number, message_text, contact_name, empresa_id, message_id, button_id)

                    # Processa STATUSES (status de mensagens enviadas: sent, delivered, read)
                    statuses = value.get("statuses", [])
                    if statuses:
                        for status in statuses:
                            status_type = status.get("status")  # sent, delivered, read, failed
                            
                            # Loga apenas erros de falha
                            if status_type == "failed":
                                import logging
                                logger = logging.getLogger(__name__)
                                status_id = status.get("id")
                                error_info = status.get("errors", [])
                                logger.error(f"Mensagem {status_id} falhou: {error_info}")

                    # Processa ERRORS (erros do webhook)
                    errors = value.get("errors", [])
                    if errors:
                        import logging
                        logger = logging.getLogger(__name__)
                        for error in errors:
                            error_code = error.get("code")
                            error_title = error.get("title")
                            error_message = error.get("message")
                            error_details = error.get("error_data", {})
                            
                            logger.error(f"Erro recebido do webhook - Code: {error_code}, Title: {error_title}, Message: {error_message}, Details: {error_details}")

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao processar webhook em background: {e}", exc_info=True)
    finally:
        # Fecha a sessão do banco
        db.close()


async def process_whatsapp_message(db: Session, phone_number: str, message_text: str, contact_name: str = None, empresa_id: str = "1", message_id: str = None, button_id: str = None):
    """
    Processa mensagem recebida via WhatsApp e responde com IA
    VERSÃO 2.0: Usa SalesHandler para fluxo completo de vendas
    
    Args:
        db: Sessão do banco de dados
        phone_number: Número de telefone do remetente
        message_text: Texto da mensagem
        contact_name: Nome do contato (opcional)
        empresa_id: ID da empresa (obtido automaticamente do phone_number_id do webhook)
        message_id: ID único da mensagem do WhatsApp (opcional, usado para evitar duplicação)
    """
    try:

        # IDENTIFICA/CRIA CLIENTE pelo número de telefone (quem enviou a mensagem)
        empresa_id_int = int(empresa_id) if empresa_id else 1
        try:
            from ..core.address_service import ChatbotAddressService
            address_service = ChatbotAddressService(db, empresa_id_int)
            cliente = address_service.criar_cliente_se_nao_existe(
                telefone=phone_number,
                nome=contact_name or "Cliente WhatsApp"
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao identificar/criar cliente: {e}", exc_info=True)
            # Continua processando mesmo se falhar a criação do cliente

        # VERIFICA DUPLICAÇÃO: Usa message_id do WhatsApp (único por mensagem) para detectar duplicatas reais
        # Se não tiver message_id, usa verificação por conteúdo apenas para mensagens longas (>3 chars)
        # para evitar bloquear respostas curtas legítimas como "1", "sim", "ok"
        empresa_id_int = int(empresa_id) if empresa_id else 1
        user_id = phone_number
        conversations = chatbot_db.get_conversations_by_user(db, user_id, empresa_id_int)
        
        if conversations:
            from sqlalchemy import text
            duplicate = None
            
            # Se tiver message_id do WhatsApp, usa ele para detectar duplicatas reais
            if message_id:
                check_duplicate_by_id = text("""
                    SELECT id, content, created_at
                    FROM chatbot.messages
                    WHERE conversation_id = :conversation_id
                    AND role = 'user'
                    AND metadata->>'whatsapp_message_id' = :message_id
                    AND created_at > NOW() - INTERVAL '30 seconds'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                result = db.execute(check_duplicate_by_id, {
                    "conversation_id": conversations[0]['id'],
                    "message_id": message_id
                })
                duplicate = result.fetchone()
                
                if duplicate:
                    return  # Ignora mensagem duplicada
            
            # Se não tiver message_id E a mensagem for longa (>3 caracteres), verifica por conteúdo
            # Mensagens curtas como "1", "sim", "ok" podem ser respostas legítimas repetidas
            elif len(message_text.strip()) > 3:
                check_duplicate_by_content = text("""
                    SELECT id, content, created_at
                    FROM chatbot.messages
                    WHERE conversation_id = :conversation_id
                    AND role = 'user'
                    AND content = :content
                    AND created_at > NOW() - INTERVAL '5 seconds'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                result = db.execute(check_duplicate_by_content, {
                    "conversation_id": conversations[0]['id'],
                    "content": message_text
                })
                duplicate = result.fetchone()
                
                if duplicate:
                    return  # Ignora mensagem duplicada

        # VERIFICA SE A LOJA ESTÁ ABERTA
        esta_aberta = None  # Variável para verificar depois se precisa enviar boas-vindas
        try:
            from app.api.empresas.models.empresa_model import EmpresaModel
            from app.utils.horarios_funcionamento import empresa_esta_aberta_agora, formatar_horarios_funcionamento_mensagem
            from datetime import datetime
            
            empresa_id_int = int(empresa_id) if empresa_id else 1
            empresa = db.query(EmpresaModel).filter(EmpresaModel.id == empresa_id_int).first()
            
            if empresa and empresa.horarios_funcionamento:
                # Logs para debug
                agora = datetime.now()
                timezone_empresa = empresa.timezone or "America/Sao_Paulo"
                
                esta_aberta = empresa_esta_aberta_agora(
                    horarios_funcionamento=empresa.horarios_funcionamento,
                    timezone=timezone_empresa
                )
                
                # Se a loja estiver fechada (False), envia mensagem com horários
                if esta_aberta is False:
                    
                    # Salva a mensagem do usuário no histórico
                    if conversations:
                        conversation_id = conversations[0]['id']
                    else:
                        # Cria conversa temporária para salvar a mensagem
                        conversation_id = chatbot_db.create_conversation(
                            db=db,
                            session_id=f"whatsapp_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                            user_id=user_id,
                            prompt_key="default",
                            model="groq-sales",
                            contact_name=contact_name,
                            empresa_id=empresa_id_int
                        )
                    
                    # Salva mensagem do usuário (com whatsapp_message_id para detectar duplicatas)
                    chatbot_db.create_message(
                        db=db,
                        conversation_id=conversation_id,
                        role="user",
                        content=message_text,
                        whatsapp_message_id=message_id  # Passa message_id do WhatsApp para detectar duplicatas
                    )
                    
                    # Formata mensagem bonita com horários
                    nome_empresa = empresa.nome if empresa and empresa.nome else "[Nome da Empresa]"
                    horarios_formatados = formatar_horarios_funcionamento_mensagem(empresa.horarios_funcionamento, apenas_horarios=True)
                    
                    mensagem_horarios = f"😊 Olá! Seja bem-vindo(a) à {nome_empresa}!\n"
                    mensagem_horarios += "Obrigado por entrar em contato 💙\n\n"
                    mensagem_horarios += "⏰ No momento, estamos fechados, mas já já estaremos prontos para te atender!\n\n"
                    mensagem_horarios += "🕐 Horário de Funcionamento:\n"
                    mensagem_horarios += horarios_formatados
                    mensagem_horarios += "\n💬 Assim que estivermos abertos, retornaremos sua mensagem o mais rápido possível.\n\n"
                    
                    # Salva resposta do bot
                    chatbot_db.create_message(
                        db=db,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=mensagem_horarios
                    )
                    
                    # Envia mensagem via WhatsApp
                    notifier = OrderNotification()
                    result = await notifier.send_whatsapp_message(phone_number, mensagem_horarios, empresa_id=empresa_id)
                    
                    if not isinstance(result, dict) or not result.get("success"):
                        import logging
                        logger = logging.getLogger(__name__)
                        error_msg = result.get("error") if isinstance(result, dict) else str(result)
                        logger.error(f"Erro ao enviar mensagem de horários: {error_msg}")
                    
                    return  # Não processa a mensagem normalmente
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao verificar horário de funcionamento: {e}", exc_info=True)
            # Continua processando normalmente em caso de erro

        # VERIFICA SE O BOT ESTÁ ATIVO PARA ESTE NÚMERO
        if not chatbot_db.is_bot_active_for_phone(db, phone_number):
            # Salva a mensagem no histórico mesmo pausado (para ver no preview)
            if conversations:
                chatbot_db.create_message(
                    db=db,
                    conversation_id=conversations[0]['id'],
                    role="user",
                    content=message_text
                )
                # Atualiza o nome do contato se disponível
                if contact_name and not conversations[0].get('contact_name'):
                    chatbot_db.update_conversation_contact_name(db, conversations[0]['id'], contact_name)
            else:
                # Cria conversa temporária para salvar a mensagem mesmo com bot pausado
                conversation_id = chatbot_db.create_conversation(
                    db=db,
                    session_id=f"whatsapp_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    user_id=user_id,
                    prompt_key="default",
                    model="groq-sales",
                    contact_name=contact_name,
                    empresa_id=empresa_id_int
                )
                chatbot_db.create_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="user",
                    content=message_text
                )
            return  # Não responde, apenas registra

        # OPÇÃO: Usar SalesHandler para conversas de vendas
        # Você pode adicionar lógica para detectar se é venda ou suporte
        USE_SALES_HANDLER = True  # Usar SalesHandler com produtos reais

        if USE_SALES_HANDLER:
            # IMPORTANTE: "nova conversa" = sem histórico OU inatividade > 16 horas.
            # Dentro das 16h, o bot deve considerar o histórico sempre.
            empresa_id_int = int(empresa_id) if empresa_id else 1
            user_id = phone_number
            conversations = chatbot_db.get_conversations_by_user(db, user_id, empresa_id_int)

            now = datetime.now()
            last_activity = None
            if conversations:
                last_activity = conversations[0].get("updated_at") or conversations[0].get("created_at")

            is_new_session = (not conversations) or (last_activity and (now - last_activity) > timedelta(hours=16))

            if is_new_session:
                # Cria uma nova conversa (nova sessão)
                conversation_id = chatbot_db.create_conversation(
                    db=db,
                    session_id=f"whatsapp_{phone_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    user_id=user_id,
                    prompt_key="default",
                    model="llm-sales",
                    contact_name=contact_name,
                    empresa_id=empresa_id_int
                )

                # Envia notificação WebSocket de nova conversa
                from ..core.notifications import send_chatbot_websocket_notification
                await send_chatbot_websocket_notification(
                    empresa_id=empresa_id_int,
                    notification_type="chatbot_conversation",
                    title="Nova Conversa",
                    message=f"Nova conversa iniciada com {contact_name or phone_number}",
                    data={
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "phone_number": phone_number,
                        "contact_name": contact_name
                    }
                )
            else:
                conversation_id = conversations[0]["id"]
                # Atualiza o nome do contato se disponível e ainda não tiver
                if contact_name and not conversations[0].get("contact_name"):
                    chatbot_db.update_conversation_contact_name(db, conversations[0]["id"], contact_name)

            # Importa o Groq Sales Handler (LLaMA 3.1 via API - rápido!)
            # NOTA: O processar_mensagem_groq já salva a mensagem do usuário e a resposta,
            # além de enviar as notificações WebSocket necessárias
            from ..core.groq_sales_handler import processar_mensagem_groq

            # Se for nova sessão (sem histórico ou >16h) E a loja estiver aberta (ou horários não configurados), envia mensagem com botões
            # Se esta_aberta for False, não envia boas-vindas (já foi enviada mensagem de horários)
            if is_new_session and esta_aberta is not False:
                # Mensagem "antiga" de boas-vindas (com nome/link) + botões
                handler = GroqSalesHandler(db, empresa_id_int)
                mensagem_boas_vindas = handler._gerar_mensagem_boas_vindas_conversacional()
                
                # Define os botões
                buttons = [
                    {"id": "pedir_whatsapp", "title": "Pedir pelo WhatsApp"},
                    {"id": "pedir_link", "title": "Pedir pelo link"},
                    {"id": "preciso_ajuda", "title": "Preciso de ajuda"}
                ]
                
                # Envia mensagem com botões (WhatsApp exige um corpo de texto)
                notifier = OrderNotification()
                result = await notifier.send_whatsapp_message_with_buttons(
                    phone_number, 
                    mensagem_boas_vindas,
                    buttons, 
                    empresa_id=empresa_id
                )
                
                if isinstance(result, dict) and result.get("success"):
                    chatbot_db.create_message(db, conversation_id, "assistant", mensagem_boas_vindas)
                    return  # Não processa a mensagem do usuário ainda, aguarda clique no botão
                else:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Erro ao enviar mensagem com botões: {result.get('error') if isinstance(result, dict) else result}")

            # Detecta se a mensagem é uma resposta de botão
            # O WhatsApp pode enviar o ID do botão diretamente ou o texto do botão
            mensagem_lower = message_text.lower().strip()
            botao_clicado = None
            
            # Primeiro verifica se veio o button_id diretamente do webhook
            if button_id:
                botao_clicado = button_id
            # Se não, verifica pelo texto da mensagem
            elif "pedir pelo whatsapp" in mensagem_lower or mensagem_lower == "pedir pelo whatsapp":
                botao_clicado = "pedir_whatsapp"
            elif "pedir pelo link" in mensagem_lower or mensagem_lower == "pedir pelo link":
                botao_clicado = "pedir_link"
            elif "preciso de ajuda" in mensagem_lower or mensagem_lower == "preciso de ajuda":
                botao_clicado = "preciso_ajuda"
            
            # Se for clique em botão, processa a resposta
            if botao_clicado:
                print(f"   🔘 Botão clicado: {botao_clicado}")
                if botao_clicado == "pedir_whatsapp":
                    # Cliente quer pedir pelo WhatsApp - continua o fluxo normal
                    resposta = "Perfeito! Vou te ajudar a montar seu pedido passo a passo 😊\n\nO que você gostaria de pedir?"
                elif botao_clicado == "pedir_link":
                    # Cliente quer pedir pelo link - envia o link do cardápio
                    try:
                        empresa_query = text("""
                            SELECT nome, cardapio_link
                            FROM cadastros.empresas
                            WHERE id = :empresa_id
                        """)
                        result_empresa = db.execute(empresa_query, {"empresa_id": empresa_id_int})
                        empresa = result_empresa.fetchone()
                        link_cardapio = empresa[1] if empresa and empresa[1] else "https://chatbot.mensuraapi.com.br"
                    except:
                        link_cardapio = "https://chatbot.mensuraapi.com.br"
                    
                    resposta = f"📲 Perfeito! Acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                elif botao_clicado == "preciso_ajuda":
                    # Cliente precisa de ajuda
                    resposta = "Claro! Estou aqui para te ajudar! 😊\n\nComo posso te auxiliar hoje?\n• Dúvidas sobre produtos\n• Informações sobre entrega\n• Outras questões\n\nÉ só me dizer o que você precisa!"
                
                # Envia a resposta
                notifier = OrderNotification()
                result = await notifier.send_whatsapp_message(phone_number, resposta, empresa_id=empresa_id)
                
                if isinstance(result, dict) and result.get("success"):
                    # Salva no histórico
                    if conversations:
                        conversation_id = conversations[0]['id']
                    else:
                        conversation_id = chatbot_db.create_conversation(
                            db=db,
                            session_id=f"whatsapp_{phone_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                            user_id=phone_number,
                            prompt_key="default",
                            model="llm-sales",
                            contact_name=contact_name,
                            empresa_id=empresa_id_int
                        )
                    chatbot_db.create_message(db, conversation_id, "user", message_text, whatsapp_message_id=message_id)
                    chatbot_db.create_message(db, conversation_id, "assistant", resposta)
                
                # Se foi "pedir pelo whatsapp", continua o fluxo normalmente na próxima mensagem
                return

            # IMPORTANTE: Verifica novamente se a loja está fechada antes de processar
            # (pode ser que a conversa já exista, mas a loja fechou depois)
            if esta_aberta is False:
                return  # Não processa mensagem quando loja está fechada
            
            # Processa com o sistema de vendas usando Groq/LLaMA
            resposta = await processar_mensagem_groq(
                db=db,
                user_id=phone_number,
                mensagem=message_text,
                empresa_id=int(empresa_id) if empresa_id else 1,
                emit_welcome_message=False
            )
            
            # Verifica se a resposta não está vazia
            if not resposta or not resposta.strip():
                return

            # Envia resposta via WhatsApp
            notifier = OrderNotification()
            result = await notifier.send_whatsapp_message(phone_number, resposta, empresa_id=empresa_id)

            if not isinstance(result, dict) or not result.get("success"):
                import logging
                logger = logging.getLogger(__name__)
                error_msg = result.get("error") if isinstance(result, dict) else str(result)
                status_code = result.get("status_code") if isinstance(result, dict) else None
                logger.error(f"Erro ao enviar resposta via WhatsApp: {error_msg} (status_code: {status_code})")
                
                # Se for erro de pagamento, destaca mais
                if isinstance(result, dict) and result.get("coexistence_hint"):
                    hint = result.get('coexistence_hint')
                    if "payment" in error_msg.lower() or "blocked" in error_msg.lower():
                        logger.warning(f"ATENÇÃO: A mensagem foi salva no banco, mas NÃO foi enviada ao cliente! Ação necessária: Adicionar créditos/pagamento na conta do 360dialog. {hint}")

            return

        # ===== CÓDIGO ANTIGO (Chat genérico sem vendas) =====
        # 1. Busca ou cria conversa para esse usuário
        user_id = phone_number
        conversations = chatbot_db.get_conversations_by_user(db, user_id)

        if conversations:
            conversation_id = conversations[0]['id']
            conversation = chatbot_db.get_conversation(db, conversation_id)

            # Se a conversa for de notificação, atualiza para modelo normal
            if conversation['model'] == 'notification-system':
                chatbot_db.update_conversation_model(db, conversation_id, DEFAULT_MODEL)
        else:
            # Cria nova conversa
            empresa_id_int = int(empresa_id) if empresa_id else 1
            conversation_id = chatbot_db.create_conversation(
                db=db,
                session_id=f"whatsapp_{phone_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                user_id=user_id,
                prompt_key="default",
                model=DEFAULT_MODEL,
                empresa_id=empresa_id_int
            )

        # 2. Salva mensagem do usuário (com whatsapp_message_id para detectar duplicatas)
        chatbot_db.create_message(
            db=db,
            conversation_id=conversation_id,
            role="user",
            content=message_text,
            whatsapp_message_id=message_id  # Passa message_id do WhatsApp para detectar duplicatas
        )

        # 3. Busca histórico de mensagens
        messages_history = chatbot_db.get_messages(db, conversation_id)

        # 4. Busca o prompt correto do banco de dados
        conversation = chatbot_db.get_conversation(db, conversation_id)
        prompt_key = conversation['prompt_key']
        model = conversation['model']

        # Busca o conteúdo do prompt
        prompt_data = chatbot_db.get_prompt(db, prompt_key)
        if prompt_data:
            prompt_content = prompt_data['content']
        else:
            prompt_content = SYSTEM_PROMPT  # fallback para o padrão

        # 5. Prepara mensagens para o Ollama
        ollama_messages = [
            {"role": "system", "content": prompt_content}
        ]

        for msg in messages_history:
            ollama_messages.append({
                "role": msg['role'],
                "content": msg['content']
            })

        # 6. Chama a IA (Ollama)
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "model": model,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                }
            }

            response = await client.post(OLLAMA_URL, json=payload)

            if response.status_code == 200:
                result = response.json()
                ai_response = result["message"]["content"]

                # 7. Salva resposta da IA no banco
                message_id = chatbot_db.create_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=ai_response
                )

                # 7.1. Envia notificação WebSocket para atualizar o frontend
                empresa_id_int = int(empresa_id) if empresa_id else 1
                from ..core.notifications import send_chatbot_websocket_notification
                await send_chatbot_websocket_notification(
                    empresa_id=empresa_id_int,
                    notification_type="whatsapp_message",
                    title="Nova Mensagem WhatsApp",
                    message=f"Nova mensagem recebida de {contact_name or phone_number}",
                    data={
                        "conversation_id": conversation_id,
                        "message_id": message_id,
                        "phone_number": phone_number,
                        "contact_name": contact_name,
                        "role": "assistant",
                        "content_preview": ai_response[:100] if len(ai_response) > 100 else ai_response
                    }
                )

                # 8. Envia resposta via WhatsApp
                notifier = OrderNotification()
                result = await notifier.send_whatsapp_message(phone_number, ai_response, empresa_id=empresa_id)

                if not isinstance(result, dict) or not result.get("success"):
                    import logging
                    logger = logging.getLogger(__name__)
                    error_msg = result.get("error") if isinstance(result, dict) else str(result)
                    status_code = result.get("status_code") if isinstance(result, dict) else None
                    logger.error(f"Erro ao enviar resposta via WhatsApp: {error_msg} (status_code: {status_code})")
            else:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Erro na IA: {response.text}")

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)


# ==================== CONFIGURAÇÕES WHATSAPP ====================

@router.get("/whatsapp-config", response_model=WhatsAppConfigResponse)
async def get_whatsapp_config():
    """Busca a configuração atual do WhatsApp"""
    from ..core.config_whatsapp import WHATSAPP_CONFIG
    return WhatsAppConfigResponse(
        access_token=WHATSAPP_CONFIG.get("access_token", ""),
        phone_number_id=WHATSAPP_CONFIG.get("phone_number_id", ""),
        business_account_id=WHATSAPP_CONFIG.get("business_account_id", ""),
        api_version=WHATSAPP_CONFIG.get("api_version", "v22.0"),
    )


@router.put("/whatsapp-config")
async def update_whatsapp_config(config: WhatsAppConfigUpdate):
    """Atualiza a configuração do WhatsApp"""
    import os
    import json

    # Caminho do arquivo de configuraçã
    config_file = os.path.join(
        os.path.dirname(__file__),
        "..",
        "core",
        "config_whatsapp.py"
    )

    # Atualiza o dicionário WHATSAPP_CONFIG
    new_config = {
        "access_token": config.access_token,
        "phone_number_id": config.phone_number_id,
        "business_account_id": config.business_account_id,
        "api_version": config.api_version or "v22.0",
    }

    # Substitui o conteúdo do arquivo (mantém as funções auxiliares)
    new_content = f'''# app/api/chatbot/core/config_whatsapp.py
"""
Configuração da API do WhatsApp Business
"""

WHATSAPP_CONFIG = {json.dumps(new_config, indent=4)}


def get_whatsapp_url():
    """Retorna a URL base da API do WhatsApp"""
    api_version = WHATSAPP_CONFIG.get("api_version", "v22.0")
    phone_number_id = WHATSAPP_CONFIG.get("phone_number_id")
    return f"https://graph.facebook.com/{{api_version}}/{{phone_number_id}}/messages"


def get_headers():
    """Retorna os headers para requisições à API do WhatsApp"""
    access_token = WHATSAPP_CONFIG.get("access_token")
    return {{
        "Authorization": f"Bearer {{access_token}}",
        "Content-Type": "application/json",
    }}


def format_phone_number(phone: str) -> str:
    """
    Formata número de telefone para o formato do WhatsApp
    Remove caracteres especiais e garante que tenha o código do país
    """
    # Remove todos os caracteres não numéricos
    phone = ''.join(filter(str.isdigit, phone))

    # Se não começa com código do país, assume Brasil (55)
    if not phone.startswith('55'):
        phone = '55' + phone

    return phone
'''

    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    # Recarrega o módulo para aplicar as mudanças
    import importlib
    from ..core import config_whatsapp
    importlib.reload(config_whatsapp)

    return {
        "message": "Configuração do WhatsApp atualizada com sucesso",
        "config": new_config
    }


@router.get("/ngrok-url")
async def get_ngrok_url():
    """Retorna a URL pública do ngrok se estiver ativo"""
    if not NGROK_AVAILABLE:
        return {
            "success": False,
            "public_url": None,
            "webhook_url": None,
            "status": "unavailable",
            "message": "pyngrok não está instalado. Instale com: pip install pyngrok"
        }
    
    public_url = get_public_url()
    webhook_url = get_webhook_url()
    
    if public_url:
        return {
            "success": True,
            "public_url": public_url,
            "webhook_url": webhook_url,
            "status": "active"
        }
    else:
        return {
            "success": False,
            "public_url": None,
            "webhook_url": None,
            "status": "inactive",
            "message": "Túnel ngrok não está ativo"
        }


@router.get("/webhook-info")
async def get_webhook_info():
    """Retorna informacoes sobre o webhook do WhatsApp"""
    # Webhook configurado no dominio proprio
    webhook_url = "https://mensuraapi.com.br/api/chatbot/webhook"

    return {
        "webhook_url": webhook_url,
        "verify_token": "meu_token_secreto_123",
        "status": "active",
        "instructions": {
            "step_1": "Acesse https://developers.facebook.com",
            "step_2": "Va em 'Meus Apps' > Seu App > WhatsApp > Configuration",
            "step_3": f"Configure o webhook com URL: {webhook_url}",
            "step_4": "Token de Verificacao: meu_token_secreto_123"
        }
    }


@router.post("/test-whatsapp-token")
async def test_whatsapp_token(config: WhatsAppConfigUpdate):
    """
    Testa se a configuração do WhatsApp é válida
    Valida o access_token fazendo uma requisição para a API do WhatsApp (360 Dialog ou Meta)
    """
    try:
        from ..core.config_whatsapp import load_whatsapp_config
        
        # Busca configuração do banco se empresa_id foi fornecido
        db_config = None
        if config.empresa_id:
            db_config = load_whatsapp_config(config.empresa_id)
        
        # Usa configuração do banco se disponível, senão usa dados do request
        # O access_token do body sempre prevalece (permite testar token específico)
        access_token = config.access_token
        base_url = db_config.get("base_url", "") if db_config else ""
        provider = (db_config.get("provider", "") or "").lower() if db_config else ""
        
        # Se não tem provider/base_url do banco, tenta inferir pelo base_url padrão do 360 Dialog
        # ou assume Meta/Facebook como padrão
        if not base_url and not provider:
            # Se não tem configuração no banco, assume padrão do 360 Dialog se empresa_id foi fornecido
            # Caso contrário, precisa dos dados completos no request
            pass
        
        # Determina se é 360 Dialog baseado no provider ou base_url
        is_360 = (provider == "360dialog") or (not provider and "360dialog" in (base_url or "").lower())
        
        # Se ainda não identificou, assume Meta/Facebook (compatibilidade com código antigo)
        if not is_360 and not base_url:
            is_360 = False
        
        # Prepara URL e headers baseado no provedor
        if is_360:
            # 360 Dialog: valida token tentando buscar informações de configuração
            # Usa endpoint de webhook config (suporta GET para consultar configuração atual)
            base_url_clean = (base_url or "https://waba-v2.360dialog.io").rstrip('/')
            url = f"{base_url_clean}/v1/configs/webhook"
            
            headers = {
                "D360-API-KEY": access_token,
                "Content-Type": "application/json",
            }
        else:
            # Meta/Facebook: usa Graph API para validar phone number
            if not config.phone_number_id:
                return {
                    "valid": False,
                    "status": "error",
                    "message": "phone_number_id é obrigatório para validar token do Meta/Facebook",
                    "provider": "Meta/Facebook"
                }
            
            url = f"https://graph.facebook.com/{config.api_version}/{config.phone_number_id}"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

        # Faz requisição para verificar o token
        async with httpx.AsyncClient(timeout=10.0) as client:
            if is_360:
                # Para 360 Dialog, tenta GET para consultar configuração do webhook
                # Se retornar 200 ou 404 (sem webhook configurado), token é válido
                # Se retornar 401/403, token é inválido
                response = await client.get(url, headers=headers)
                
                # 404 pode significar que não há webhook configurado, mas token é válido
                if response.status_code == 404:
                    return {
                        "valid": True,
                        "status": "success",
                        "message": "Token válido! Configuração do 360 Dialog funcionando corretamente. (Webhook não configurado)",
                        "provider": "360dialog"
                    }
            else:
                # Para Meta, faz GET no phone number endpoint
                response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                
                if is_360:
                    return {
                        "valid": True,
                        "status": "success",
                        "message": "Token válido! Configuração do 360 Dialog funcionando corretamente.",
                        "provider": "360dialog",
                        "config_data": data
                    }
                else:
                    return {
                        "valid": True,
                        "status": "success",
                        "message": "Token válido! Configuração do WhatsApp funcionando corretamente.",
                        "provider": "Meta/Facebook",
                        "phone_data": {
                            "id": data.get("id"),
                            "display_phone_number": data.get("display_phone_number"),
                            "verified_name": data.get("verified_name"),
                            "quality_rating": data.get("quality_rating")
                        }
                    }
            elif response.status_code == 401 or response.status_code == 403:
                error_data = response.json() if response.text else {}
                error_message = error_data.get("error", {}).get("message", "Token inválido") if isinstance(error_data, dict) else "Token inválido ou expirado"
                
                return {
                    "valid": False,
                    "status": "error",
                    "message": f"Token inválido ou expirado: {error_message}",
                    "provider": "360dialog" if is_360 else "Meta/Facebook",
                    "error_code": error_data.get("error", {}).get("code") if isinstance(error_data, dict) else None,
                    "error_type": error_data.get("error", {}).get("type") if isinstance(error_data, dict) else None
                }
            else:
                error_data = response.json() if response.text else {}
                return {
                    "valid": False,
                    "status": "error",
                    "message": f"Erro ao validar token (Status {response.status_code})",
                    "provider": "360dialog" if is_360 else "Meta/Facebook",
                    "error": error_data
                }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Timeout ao conectar com a API do WhatsApp"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao testar token: {str(e)}"
        )


# ==================== FOTO DE PERFIL DO WHATSAPP ====================

@router.get("/profile-picture/{phone_number}")
async def get_whatsapp_profile_picture(phone_number: str):
    """
    Busca a foto de perfil de um contato do WhatsApp.
    Usa a API do WhatsApp Business para obter a URL da foto.
    """
    try:
        from ..core.config_whatsapp import WHATSAPP_CONFIG

        access_token = WHATSAPP_CONFIG.get("access_token")
        api_version = WHATSAPP_CONFIG.get("api_version", "v22.0")

        # Normaliza o número (remove caracteres especiais)
        phone_clean = ''.join(filter(str.isdigit, phone_number))
        if not phone_clean.startswith('55'):
            phone_clean = '55' + phone_clean

        # URL para buscar informações do contato
        # A API do WhatsApp Cloud não fornece foto de perfil diretamente
        # mas podemos tentar buscar via endpoint de contatos
        url = f"https://graph.facebook.com/{api_version}/{phone_clean}/profile_picture"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "phone_number": phone_number,
                    "profile_picture_url": data.get("profile_picture_url") or data.get("url"),
                    "data": data
                }
            else:
                # A API pode não suportar busca direta de foto
                # Retornamos null para usar avatar padrão
                return {
                    "success": False,
                    "phone_number": phone_number,
                    "profile_picture_url": None,
                    "message": "Foto de perfil não disponível"
                }

    except Exception as e:
        return {
            "success": False,
            "phone_number": phone_number,
            "profile_picture_url": None,
            "error": str(e)
        }


# ==================== ENDPOINT DE TESTE (SIMULAÇÃO) ====================

class SimulateMessageRequest(BaseModel):
    """Request para simular mensagem do chatbot"""
    phone_number: str
    message: str

class SimulateMessageResponse(BaseModel):
    """Response da simulação"""
    success: bool
    response: str
    phone_number: str
    message_sent: str

@router.post("/simulate", response_model=SimulateMessageResponse)
async def simulate_chatbot_message(
    request: SimulateMessageRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint de TESTE para simular mensagem do chatbot.
    Usa o mesmo handler do WhatsApp (Groq Sales Handler) mas retorna a resposta
    ao invés de enviar via WhatsApp.
    """
    try:
        phone_number = request.phone_number
        message_text = request.message

        print(f"\n🧪 SIMULAÇÃO: Mensagem de {phone_number}: {message_text}")

        # Verifica se bot está ativo
        if not chatbot_db.is_bot_active_for_phone(db, phone_number):
            return SimulateMessageResponse(
                success=False,
                response="[BOT PAUSADO] O bot está pausado para este número.",
                phone_number=phone_number,
                message_sent=message_text
            )

        # Cria conversa se não existir
        user_id = phone_number
        conversations = chatbot_db.get_conversations_by_user(db, user_id)

        if not conversations:
            conversation_id = chatbot_db.create_conversation(
                db=db,
                session_id=f"simulate_{phone_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                user_id=user_id,
                prompt_key="default",
                model="llm-sales"
            )
            print(f"   ✅ Nova conversa criada: {conversation_id}")

        # Importa e usa o Groq Sales Handler
        from ..core.groq_sales_handler import processar_mensagem_groq

        # Função de simulação usa empresa_id padrão (1) pois não vem de webhook
        resposta = await processar_mensagem_groq(
            db=db,
            user_id=phone_number,
            mensagem=message_text,
            empresa_id=1
        )

        print(f"   💬 Resposta: {resposta[:100]}...")

        return SimulateMessageResponse(
            success=True,
            response=resposta,
            phone_number=phone_number,
            message_sent=message_text
        )

    except Exception as e:
        print(f"❌ Erro na simulação: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar mensagem: {str(e)}"
        )


# ==================== PEDIDOS DO CLIENTE ====================

# Templates de mensagem por status do pedido
ORDER_STATUS_TEMPLATES = {
    "P": {
        "name": "Pendente",
        "emoji": "🕐",
        "message": "Seu pedido #{numero_pedido} foi recebido e está aguardando confirmação."
    },
    "I": {
        "name": "Em Impressão",
        "emoji": "🖨️",
        "message": "Seu pedido #{numero_pedido} está sendo processado!"
    },
    "R": {
        "name": "Preparando",
        "emoji": "👨‍🍳",
        "message": "Boa notícia! Seu pedido #{numero_pedido} está sendo preparado com todo carinho!"
    },
    "S": {
        "name": "Saiu para Entrega",
        "emoji": "🛵",
        "message": "Seu pedido #{numero_pedido} saiu para entrega! Em breve estará com você!"
    },
    "E": {
        "name": "Entregue",
        "emoji": "✅",
        "message": "Seu pedido #{numero_pedido} foi entregue! Obrigado pela preferência!"
    },
    "C": {
        "name": "Cancelado",
        "emoji": "❌",
        "message": "Seu pedido #{numero_pedido} foi cancelado."
    },
    "A": {
        "name": "Aguardando Pagamento",
        "emoji": "💳",
        "message": "Seu pedido #{numero_pedido} está aguardando confirmação do pagamento."
    },
    "D": {
        "name": "Editado",
        "emoji": "📝",
        "message": "Seu pedido #{numero_pedido} foi atualizado."
    },
    "X": {
        "name": "Em Edição",
        "emoji": "✏️",
        "message": "Seu pedido #{numero_pedido} está sendo editado."
    }
}


@router.get("/pedidos-debug")
async def debug_orders(db: Session = Depends(get_db)):
    """DEBUG: Lista todos os pedidos e clientes para verificar dados"""
    try:
        from sqlalchemy import text

        # Busca todos os clientes
        clientes_query = text("SELECT id, nome, telefone FROM cadastros.clientes LIMIT 10")
        clientes_result = db.execute(clientes_query)
        clientes = [{"id": r[0], "nome": r[1], "telefone": r[2]} for r in clientes_result.fetchall()]

        # Busca todos os pedidos
        pedidos_query = text("""
            SELECT p.id, p.numero_pedido, p.cliente_id, p.status, p.valor_total, c.nome as cliente_nome
            FROM pedidos.pedidos p
            LEFT JOIN cadastros.clientes c ON p.cliente_id = c.id
            ORDER BY p.created_at DESC
            LIMIT 20
        """)
        pedidos_result = db.execute(pedidos_query)
        pedidos = [
            {"id": r[0], "numero_pedido": r[1], "cliente_id": r[2], "status": r[3], "valor_total": float(r[4]) if r[4] else 0, "cliente_nome": r[5]}
            for r in pedidos_result.fetchall()
        ]

        return {
            "clientes": clientes,
            "pedidos": pedidos,
            "total_clientes": len(clientes),
            "total_pedidos": len(pedidos)
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/pedidos/{phone_number}")
async def get_orders_by_phone(phone_number: str, db: Session = Depends(get_db)):
    """
    Busca todos os pedidos de um cliente pelo número de telefone.
    Retorna pedidos ativos (não cancelados) ordenados por data.
    """
    try:
        from sqlalchemy import text

        # Normaliza o número de telefone
        phone_clean = ''.join(filter(str.isdigit, phone_number))

        # Remove o código do país (55) se presente para busca
        phone_without_country = phone_clean
        if phone_clean.startswith('55') and len(phone_clean) > 11:
            phone_without_country = phone_clean[2:]

        # Busca o cliente pelo telefone
        cliente_query = text("""
            SELECT id, nome, telefone FROM cadastros.clientes
            WHERE telefone LIKE :phone_pattern
            LIMIT 1
        """)

        # Tenta com diferentes formatos de telefone
        patterns = [
            phone_clean,                         # Número completo como recebido
            phone_without_country,               # Sem código do país
            f"%{phone_clean[-9:]}",              # Últimos 9 dígitos
            f"%{phone_clean[-8:]}",              # Últimos 8 dígitos
            f"55{phone_without_country}",        # Com código do país adicionado
            f"%{phone_without_country[-9:]}",    # Últimos 9 dígitos sem código
        ]

        cliente = None
        for pattern in patterns:
            result = db.execute(cliente_query, {"phone_pattern": pattern})
            cliente = result.fetchone()
            if cliente:
                print(f"   ✅ Cliente encontrado com padrão: {pattern}")
                break

        if not cliente:
            return {
                "success": False,
                "message": "Cliente não encontrado",
                "pedidos": []
            }

        cliente_id = cliente[0]
        cliente_nome = cliente[1]

        # Busca os pedidos do cliente
        pedidos_query = text("""
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
                p.pago,
                p.created_at,
                p.updated_at
            FROM pedidos.pedidos p
            WHERE p.cliente_id = :cliente_id
            ORDER BY p.created_at DESC
            LIMIT 20
        """)

        result = db.execute(pedidos_query, {"cliente_id": cliente_id})
        pedidos_rows = result.fetchall()

        pedidos = []
        for row in pedidos_rows:
            status_code = row[3]
            status_info = ORDER_STATUS_TEMPLATES.get(status_code, {
                "name": "Desconhecido",
                "emoji": "❓",
                "message": "Status do pedido: {status}"
            })

            # Busca os itens do pedido (query simplificada)
            itens_query = text("""
                SELECT
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
            """)

            itens_result = db.execute(itens_query, {"pedido_id": row[0]})
            itens = [
                {
                    "quantidade": item[0],
                    "preco_unitario": float(item[1]) if item[1] else 0,
                    "preco_total": float(item[2]) if item[2] else 0,
                    "observacao": item[3],
                    "nome": item[4]
                }
                for item in itens_result.fetchall()
            ]

            pedidos.append({
                "id": row[0],
                "numero_pedido": row[1],
                "tipo_entrega": row[2],
                "status": {
                    "codigo": status_code,
                    "nome": status_info["name"],
                    "emoji": status_info["emoji"]
                },
                "subtotal": float(row[4]) if row[4] else 0,
                "desconto": float(row[5]) if row[5] else 0,
                "taxa_entrega": float(row[6]) if row[6] else 0,
                "valor_total": float(row[7]) if row[7] else 0,
                "observacoes": row[8],
                "pago": row[9],
                "created_at": row[10].isoformat() if row[10] else None,
                "updated_at": row[11].isoformat() if row[11] else None,
                "itens": itens
            })

        return {
            "success": True,
            "cliente": {
                "id": cliente_id,
                "nome": cliente_nome
            },
            "pedidos": pedidos
        }

    except Exception as e:
        print(f"❌ Erro ao buscar pedidos: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar pedidos: {str(e)}"
        )


@router.post("/pedidos/{pedido_id}/enviar-resumo")
async def send_order_summary(
    pedido_id: int,
    phone_number: str,
    db: Session = Depends(get_db)
):
    """
    Envia o resumo de um pedido específico para o cliente via WhatsApp.
    A mensagem inclui os itens, valores e o status atual do pedido.
    """
    try:
        from sqlalchemy import text

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
                p.pago,
                p.created_at,
                c.nome as cliente_nome
            FROM pedidos.pedidos p
            LEFT JOIN cadastros.clientes c ON p.cliente_id = c.id
            WHERE p.id = :pedido_id
        """)

        result = db.execute(pedido_query, {"pedido_id": pedido_id})
        pedido = result.fetchone()

        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")

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

        # Busca os itens do pedido (query simplificada)
        itens_query = text("""
            SELECT
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
        """)

        itens_result = db.execute(itens_query, {"pedido_id": pedido_id})
        itens = itens_result.fetchall()

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

        # Monta a mensagem
        mensagem = f"""📋 *RESUMO DO PEDIDO #{numero_pedido}*

{status_info['emoji']} *Status:* {status_info['name']}
📦 *Tipo:* {tipo_formatado}
📅 *Data:* {created_at.strftime('%d/%m/%Y %H:%M') if created_at else 'N/A'}

*━━━ ITENS ━━━*
"""

        for item in itens:
            qtd = item[0]
            preco_total = float(item[2]) if item[2] else 0
            nome_item = item[4]
            obs_item = item[3]

            mensagem += f"• {qtd}x {nome_item} - R$ {preco_total:.2f}\n"
            if obs_item:
                mensagem += f"  _Obs: {obs_item}_\n"

        mensagem += f"""
*━━━ VALORES ━━━*
Subtotal: R$ {subtotal:.2f}
"""

        if desconto > 0:
            mensagem += f"Desconto: -R$ {desconto:.2f}\n"

        if taxa_entrega > 0:
            mensagem += f"Taxa de entrega: R$ {taxa_entrega:.2f}\n"

        mensagem += f"*Total: R$ {valor_total:.2f}*\n"
        mensagem += f"💳 Pagamento: {'✅ Pago' if pago else '⏳ Pendente'}\n"

        if observacoes:
            mensagem += f"\n📝 _Obs: {observacoes}_\n"

        # Mensagem de status personalizada
        status_message = status_info["message"].format(numero_pedido=numero_pedido)
        mensagem += f"\n{status_info['emoji']} *{status_message}*"

        # Envia via WhatsApp
        notifier = OrderNotification()
        result = await notifier.send_whatsapp_message(phone_number, mensagem)

        if result.get("success"):
            return {
                "success": True,
                "message": "Resumo do pedido enviado com sucesso!",
                "pedido_id": pedido_id,
                "numero_pedido": numero_pedido,
                "status": status_info["name"]
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Erro ao enviar mensagem: {result.get('error')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro ao enviar resumo: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao enviar resumo: {str(e)}"
        )


@router.post("/criar-pedidos-teste/{phone_number}")
async def criar_pedidos_teste(phone_number: str, db: Session = Depends(get_db)):
    """
    Endpoint temporário para criar pedidos de teste com todos os status disponíveis.
    """
    import random

    # Limpar telefone
    phone_clean = ''.join(filter(str.isdigit, phone_number))
    phone_without_country = phone_clean[2:] if phone_clean.startswith('55') and len(phone_clean) > 11 else phone_clean

    # Status codes disponíveis
    STATUS_CODES = ['P', 'I', 'R', 'S', 'E', 'C', 'A', 'D', 'X']
    STATUS_NAMES = {
        'P': 'Pendente',
        'I': 'Em Impressão',
        'R': 'Preparando',
        'S': 'Saiu para Entrega',
        'E': 'Entregue',
        'C': 'Cancelado',
        'A': 'Agendado',
        'D': 'Disponível para Retirada',
        'X': 'Finalizado'
    }
    TIPOS_ENTREGA = ['DELIVERY', 'RETIRADA', 'BALCAO', 'MESA']

    try:
        # Buscar cliente pelo telefone
        patterns = [phone_clean, phone_without_country, f"%{phone_clean[-9:]}", f"%{phone_clean[-8:]}"]
        cliente = None

        for pattern in patterns:
            result = db.execute(text("""
                SELECT id, nome, telefone FROM cadastros.clientes
                WHERE telefone LIKE :pattern
                LIMIT 1
            """), {"pattern": pattern})
            cliente = result.fetchone()
            if cliente:
                break

        if not cliente:
            # Criar cliente se não existir
            result = db.execute(text("""
                INSERT INTO cadastros.clientes (nome, telefone, created_at, updated_at)
                VALUES (:nome, :telefone, NOW(), NOW())
                RETURNING id, nome, telefone
            """), {"nome": f"Cliente Teste {phone_without_country[-4:]}", "telefone": phone_without_country})
            cliente = result.fetchone()
            db.commit()
            print(f"✅ Cliente criado: ID={cliente[0]}, Nome={cliente[1]}")

        cliente_id = cliente[0]
        print(f"✅ Usando cliente: ID={cliente_id}, Nome={cliente[1]}, Tel={cliente[2]}")

        # Pegar próximo número de pedido
        result = db.execute(text("""
            SELECT COALESCE(MAX(CAST(SUBSTRING(numero_pedido FROM '[0-9]+') AS INTEGER)), 0) + 1
            FROM pedidos.pedidos
        """))
        next_num = result.fetchone()[0]

        # Criar pedidos com cada status
        pedidos_criados = []
        for i, status_code in enumerate(STATUS_CODES):
            tipo_entrega = TIPOS_ENTREGA[i % len(TIPOS_ENTREGA)]
            prefixo = {'DELIVERY': 'DEL', 'RETIRADA': 'RET', 'BALCAO': 'BAL', 'MESA': 'MESA'}[tipo_entrega]
            numero_pedido = f'{prefixo}-{next_num + i:06d}'

            subtotal = random.randint(2000, 10000)
            desconto = random.randint(0, 500)
            taxa_entrega = 500 if tipo_entrega == 'DELIVERY' else 0
            valor_total = (subtotal - desconto + taxa_entrega) / 100
            pago = random.choice([True, False])

            result = db.execute(text("""
                INSERT INTO pedidos.pedidos
                (empresa_id, cliente_id, numero_pedido, tipo_entrega, status, subtotal, desconto,
                 taxa_entrega, taxa_servico, valor_total, pago, acertado_entregador, created_at, updated_at)
                VALUES
                (1, :cliente_id, :numero_pedido, :tipo_entrega, :status, :subtotal, :desconto,
                 :taxa_entrega, 0, :valor_total, :pago, false, NOW(), NOW())
                RETURNING id
            """), {
                'cliente_id': cliente_id,
                'numero_pedido': numero_pedido,
                'tipo_entrega': tipo_entrega,
                'status': status_code,
                'subtotal': subtotal,
                'desconto': desconto,
                'taxa_entrega': taxa_entrega,
                'valor_total': valor_total,
                'pago': pago
            })
            pedido_id = result.fetchone()[0]

            # Adicionar itens ao pedido - buscar receitas existentes
            receitas_result = db.execute(text("""
                SELECT id, nome FROM catalogo.receitas LIMIT 10
            """))
            receitas = receitas_result.fetchall()

            for j in range(random.randint(1, min(4, len(receitas) if receitas else 1))):
                qtd = random.randint(1, 3)
                preco_unit = random.randint(500, 3000)
                receita_id = receitas[j % len(receitas)][0] if receitas else None

                if receita_id:
                    db.execute(text("""
                        INSERT INTO pedidos.pedidos_itens
                        (pedido_id, receita_id, quantidade, preco_unitario, preco_total, observacao)
                        VALUES (:pedido_id, :receita_id, :qtd, :preco_unit, :preco_total, :obs)
                    """), {
                        'pedido_id': pedido_id,
                        'receita_id': receita_id,
                        'qtd': qtd,
                        'preco_unit': preco_unit,
                        'preco_total': qtd * preco_unit,
                        'obs': f'Item de teste {j+1}'
                    })

            pedidos_criados.append({
                'id': pedido_id,
                'numero_pedido': numero_pedido,
                'status_codigo': status_code,
                'status_nome': STATUS_NAMES[status_code],
                'tipo_entrega': tipo_entrega,
                'valor_total': valor_total,
                'pago': pago
            })

        db.commit()

        return {
            "success": True,
            "message": f"Criados {len(pedidos_criados)} pedidos de teste",
            "cliente": {
                "id": cliente_id,
                "nome": cliente[1],
                "telefone": cliente[2]
            },
            "pedidos": pedidos_criados
        }

    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar pedidos de teste: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar pedidos de teste: {str(e)}"
        )
