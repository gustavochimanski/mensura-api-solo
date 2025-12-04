"""
Router do módulo de Chatbot
Todas as rotas relacionadas ao chatbot com IA (Ollama)
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
import json
import uuid
from datetime import datetime

from app.database.db_connection import get_db
from ..core import database as chatbot_db
from ..core.notifications import OrderNotification
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
                c.prompt_key,
                c.model,
                c.empresa_id,
                c.created_at,
                c.updated_at,
                COUNT(m.id) as message_count,
                MAX(m.created_at) as last_message_at
            FROM chatbot.conversations c
            LEFT JOIN chatbot.messages m ON c.id = m.conversation_id
            GROUP BY c.id, c.session_id, c.user_id, c.prompt_key, c.model, c.empresa_id, c.created_at, c.updated_at
            ORDER BY c.updated_at DESC
        """)

        result = db.execute(query)
        conversations = [
            {
                "id": row[0],
                "session_id": row[1],
                "user_id": row[2],
                "prompt_key": row[3],
                "model": row[4],
                "empresa_id": row[5],
                "created_at": row[6],
                "updated_at": row[7],
                "message_count": row[8],
                "last_message_at": row[9]
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
async def send_notification(request: dict):
    """
    Endpoint simples para enviar notificações WhatsApp
    Aceita telefone e mensagem formatada
    """
    phone = request.get("phone")
    message = request.get("message")

    if not phone or not message:
        raise HTTPException(
            status_code=400,
            detail="Telefone e mensagem são obrigatórios"
        )

    # Envia via WhatsApp
    notifier = OrderNotification()
    result = await notifier.send_whatsapp_message(phone, message)

    if result.get("success"):
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


# ==================== WEBHOOKS DO WHATSAPP ====================

@router.get("/webhook")
async def webhook_verification(request: Request):
    """
    Verificação do webhook do WhatsApp (Meta)
    A Meta envia um GET request para verificar o webhook
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    # Token de verificação - você pode mudar isso
    VERIFY_TOKEN = "meu_token_secreto_123"

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook verificado com sucesso!")
        # Retornar o challenge exatamente como recebido (Facebook espera int ou string)
        try:
            return int(challenge)
        except (ValueError, TypeError):
            return challenge
    else:
        print("❌ Falha na verificação do webhook")
        raise HTTPException(status_code=403, detail="Falha na verificação")


@router.post("/webhook")
async def webhook_handler(request: Request, db: Session = Depends(get_db)):
    """
    Recebe mensagens do WhatsApp via webhook
    Processa e responde automaticamente com a IA
    """
    try:
        body = await request.json()

        # Log do webhook recebido
        print(f"\n📥 Webhook recebido: {json.dumps(body, indent=2)}")

        # Verifica se é uma mensagem
        if body.get("object") == "whatsapp_business_account":
            entries = body.get("entry", [])

            for entry in entries:
                changes = entry.get("changes", [])

                for change in changes:
                    value = change.get("value", {})

                    # Verifica se há mensagens
                    messages = value.get("messages", [])

                    for message in messages:
                        # Dados da mensagem
                        from_number = message.get("from")
                        message_id = message.get("id")
                        message_type = message.get("type")
                        timestamp = message.get("timestamp")

                        # Extrai o texto da mensagem
                        message_text = None
                        if message_type == "text":
                            message_text = message.get("text", {}).get("body")

                        print(f"\n📨 Mensagem recebida:")
                        print(f"   De: {from_number}")
                        print(f"   Tipo: {message_type}")
                        print(f"   Texto: {message_text}")

                        if message_text:
                            # Processa a mensagem com a IA
                            await process_whatsapp_message(db, from_number, message_text)

        return {"status": "ok"}

    except Exception as e:
        print(f"❌ Erro no webhook: {e}")
        return {"status": "error", "message": str(e)}


async def process_whatsapp_message(db: Session, phone_number: str, message_text: str):
    """
    Processa mensagem recebida via WhatsApp e responde com IA
    VERSÃO 2.0: Usa SalesHandler para fluxo completo de vendas
    """
    try:
        print(f"\n🤖 Processando mensagem de {phone_number}: {message_text}")

        # OPÇÃO: Usar SalesHandler para conversas de vendas
        # Você pode adicionar lógica para detectar se é venda ou suporte
        USE_SALES_HANDLER = True  # Usar SalesHandler com produtos reais

        if USE_SALES_HANDLER:
            # IMPORTANTE: Criar conversa primeiro para que o estado possa ser salvo
            user_id = phone_number
            conversations = chatbot_db.get_conversations_by_user(db, user_id)

            if not conversations:
                # Cria nova conversa
                conversation_id = chatbot_db.create_conversation(
                    db=db,
                    session_id=f"whatsapp_{phone_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    user_id=user_id,
                    prompt_key="default",
                    model="llm-sales"
                )
                print(f"   ✅ Nova conversa criada: {conversation_id}")

            # Importa o Groq Sales Handler (LLaMA 3.1 via API - rápido!)
            from ..core.groq_sales_handler import processar_mensagem_groq

            # Processa com o sistema de vendas usando Groq/LLaMA
            print(f"   🤖 Usando Groq Sales Handler (LLaMA 3.1 + dados do banco)")
            resposta = await processar_mensagem_groq(
                db=db,
                user_id=phone_number,
                mensagem=message_text,
                empresa_id=1  # TODO: Pegar empresa_id correto
            )

            print(f"   💬 Resposta do SalesHandler: {resposta[:100]}...")

            # Envia resposta via WhatsApp
            notifier = OrderNotification()
            result = await notifier.send_whatsapp_message(phone_number, resposta)

            if result.get("success"):
                print(f"   ✅ Resposta enviada via WhatsApp!")
            else:
                print(f"   ❌ Erro ao enviar resposta: {result.get('error')}")

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
                print(f"   ↪️ Conversa {conversation_id} atualizada para chat normal")
        else:
            # Cria nova conversa
            conversation_id = chatbot_db.create_conversation(
                db=db,
                session_id=f"whatsapp_{phone_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                user_id=user_id,
                prompt_key="default",
                model=DEFAULT_MODEL
            )
            print(f"   ✅ Nova conversa criada: {conversation_id}")

        # 2. Salva mensagem do usuário
        chatbot_db.create_message(
            db=db,
            conversation_id=conversation_id,
            role="user",
            content=message_text
        )
        print(f"   💾 Mensagem do usuário salva")

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

        print(f"   📝 Usando prompt: {prompt_key}")
        print(f"   🤖 Usando modelo: {model}")

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
        print(f"   🧠 Consultando IA...")
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

                print(f"   💬 Resposta da IA: {ai_response[:100]}...")

                # 7. Salva resposta da IA no banco
                chatbot_db.create_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=ai_response
                )

                # 8. Envia resposta via WhatsApp
                notifier = OrderNotification()
                result = await notifier.send_whatsapp_message(phone_number, ai_response)

                if result.get("success"):
                    print(f"   ✅ Resposta enviada via WhatsApp!")
                else:
                    print(f"   ❌ Erro ao enviar resposta: {result.get('error')}")
            else:
                print(f"   ❌ Erro na IA: {response.text}")

    except Exception as e:
        print(f"❌ Erro ao processar mensagem: {e}")
        import traceback
        traceback.print_exc()


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

    # Caminho do arquivo de configuração
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
        "send_mode": "api",
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
    Valida o access_token fazendo uma requisição para a API do WhatsApp
    """
    try:
        # URL da API do WhatsApp
        url = f"https://graph.facebook.com/{config.api_version}/{config.phone_number_id}"

        # Headers com o token
        headers = {
            "Authorization": f"Bearer {config.access_token}",
            "Content-Type": "application/json",
        }

        # Faz requisição GET para verificar o phone number
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return {
                    "valid": True,
                    "status": "success",
                    "message": "Token válido! Configuração do WhatsApp funcionando corretamente.",
                    "phone_data": {
                        "id": data.get("id"),
                        "display_phone_number": data.get("display_phone_number"),
                        "verified_name": data.get("verified_name"),
                        "quality_rating": data.get("quality_rating")
                    }
                }
            elif response.status_code == 401 or response.status_code == 403:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "Token inválido")
                return {
                    "valid": False,
                    "status": "error",
                    "message": f"Token inválido ou expirado: {error_message}",
                    "error_code": error_data.get("error", {}).get("code"),
                    "error_type": error_data.get("error", {}).get("type")
                }
            else:
                error_data = response.json() if response.text else {}
                return {
                    "valid": False,
                    "status": "error",
                    "message": f"Erro ao validar token (Status {response.status_code})",
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
