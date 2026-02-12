"""
Router do módulo de Chatbot
Todas as rotas relacionadas ao chatbot com IA (Groq)
"""
from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File, BackgroundTasks, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict
import logging
import httpx
import json
import uuid
from datetime import datetime, timedelta, date
import re

from app.database.db_connection import get_db
from ..core import database as chatbot_db
from ..core.notifications import OrderNotification, ORDER_STATUS_TEMPLATES
from ..core.groq_sales_handler import GroqSalesHandler, GROQ_API_URL, GROQ_API_KEY, MODEL_NAME
from ..core.llm_policy import build_system_prompt, clamp_temperature
from app.api.notifications.repositories.whatsapp_config_repository import WhatsAppConfigRepository
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.chatbot.repositories.repo_chatbot_config import ChatbotConfigRepository

# Logger único do módulo (evita "import logging" repetido)
logger = logging.getLogger(__name__)

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

# Configurações do Groq
DEFAULT_MODEL = MODEL_NAME

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

# Chaves de prompts para separar agentes
PROMPT_ATENDIMENTO = "atendimento"
PROMPT_ATENDIMENTO_PEDIDO_WHATSAPP = "atendimento-pedido-whatsapp"

# Termos simples para detectar tentativa de pedido
PEDIDO_INTENT_TERMS = [
    "quero",
    "pedir",
    "pedido",
    "fazer pedido",
    "adicionar",
    "me ve",
    "me vê",
    "me da",
    "me dá",
    "manda",
    "vou querer",
    "vou pedir",
    "finalizar",
    "fechar",
    "só isso",
    "pode fechar",
    "coloca",
    "colocar",
    "incluir",
    "põe",
    "põe na conta",
    "pode anotar",
    "anota",
    "anotar",
    "vou levar",
    "levar",
    "pegar",
    "vou pegar",
]


def _is_pedido_intent(message_text: Optional[str]) -> bool:
    """
    Detecta se a mensagem contém intenção de fazer um pedido.
    Retorna True se detectar termos relacionados a pedidos ou padrões numéricos de pedido.
    IMPORTANTE: NÃO detecta perguntas sobre preços/informações (ex: "quanto fica", "qual o preço").
    """
    if not message_text:
        return False
    msg = message_text.lower().strip()
    if not msg:
        return False
    
    # Palavras que indicam PERGUNTA (não pedido)
    palavras_pergunta = ['quanto', 'qual', 'quais', 'tem', 'tem?', 'custa', 'fica', 'preço', 'preco', 'valor', 'informação', 'informacao', 'saber', 'dizer']
    
    # Se começa com pergunta, não é pedido
    if any(msg.startswith(p) for p in palavras_pergunta):
        return False
    
    # Se contém padrão de pergunta no início (ex: "quanto fica 2 xbacon")
    if re.match(r'^(quanto|qual|quais|tem|preço|preco|valor).*', msg):
        return False
    
    # Verifica se contém termos de intenção de pedido (mas não se for pergunta)
    if any(term in msg for term in PEDIDO_INTENT_TERMS):
        # Se contém termos de pedido MAS também palavras de pergunta, é pergunta, não pedido
        if not any(p in msg for p in palavras_pergunta):
            return True
    
    # Padrões como "1 x-bacon", "2 pizzas", "3 coca", "2x hambúrguer"
    # Mas só se NÃO for pergunta (ex: "quanto fica 2 xbacon" não é pedido)
    if re.search(r'\d+\s*(x\s*)?\w+', msg):
        # Se contém palavras de pergunta, não é pedido
        if not any(p in msg for p in palavras_pergunta):
            return True
    
    return False


def _is_chamar_atendente_intent(message_text: Optional[str], button_id: Optional[str] = None) -> bool:
    """
    Detecta intenção explícita de falar com um atendente humano.

    IMPORTANTE:
    - Deve vir ANTES de `_is_pedido_intent`, pois frases como "quero falar com um atendente"
      contém "quero" e acabam sendo classificadas como tentativa de pedido.
    """
    try:
        if button_id and str(button_id).strip().lower() == "chamar_atendente":
            return True
        if not message_text:
            return False
        msg = str(message_text).lower().strip()
        if not msg:
            return False

        # Normaliza variações comuns do WhatsApp (id do botão pode chegar como texto)
        if msg == "chamar_atendente" or "chamar_atendente" in msg:
            return True

        # Regex mais permissivo (compatível com o GroqSalesHandler)
        return bool(
            re.search(
                r"(chamar\s+atendente|"
                r"quero\s+falar\s+com\s+(algu[eé]m|atendente|humano)|"
                r"preciso\s+de\s+(um\s+)?(humano|atendente)|"
                r"atendente\s+humano|"
                r"quero\s+atendimento\s+humano|"
                r"falar\s+com\s+atendente|"
                r"ligar\s+atendente|"
                r"chama\s+(algu[eé]m|atendente)\s+para\s+mi)",
                msg,
                re.IGNORECASE,
            )
        )
    except Exception:
        return False


def _is_pedido_cardapio(message_text: Optional[str]) -> bool:
    """
    Detecta se a mensagem é um pedido explícito de cardápio.
    Exemplos: "pode me mandar o cardápio", "quero ver o cardápio", "me manda o cardápio", etc.
    """
    if not message_text:
        return False
    msg = str(message_text).lower().strip()
    if not msg:
        return False
    
    # Padrões que indicam pedido de cardápio
    padroes_cardapio = [
        # "pode me mandar o cardápio", "poderia me mandar o cardápio"
        r'(?:pode|poderia)(?:\s+me)?\s+(?:me\s+)?(?:mandar|manda|enviar|envia|mostrar|mostra|passar|passa)\s+(?:o\s+)?(?:cardapio|cardápio|menu)',
        # "quero ver o cardápio", "gostaria de ver o cardápio"
        r'(?:quero|gostaria|gostaria de|queria|queria de)\s+(?:ver|ver o|receber|receber o|ter|ter o)\s+(?:cardapio|cardápio|menu)',
        # "me manda o cardápio", "manda o cardápio"
        r'(?:me\s+)?(?:manda|mandar|envia|enviar|mostra|mostrar|passa|passar)\s+(?:o\s+)?(?:cardapio|cardápio|menu)',
        # "manda aí o cardápio", "envia pra mim o cardápio"
        r'(?:manda|mandar|envia|enviar|mostra|mostrar|passa|passar)\s+(?:ai|aí|pra mim|para mim)\s+(?:o\s+)?(?:cardapio|cardápio|menu)',
        # Apenas "cardápio" ou "menu"
        r'^(?:cardapio|cardápio|menu)$',
        # "mostra o cardápio", "ver o cardápio"
        r'^(?:mostra|mostrar|ver|quero ver)\s+(?:o\s+)?(?:cardapio|cardápio|menu)$',
    ]
    
    for padrao in padroes_cardapio:
        if re.search(padrao, msg, re.IGNORECASE):
            return True
    
    return False


def _is_saudacao_intent(message_text: Optional[str]) -> bool:
    """
    Detecta se a mensagem é uma saudação/entrada ("oi", "olá", "menu", "cardápio", etc).
    Usado para roteamento de fluxo (ex.: quando pedidos no WhatsApp estão desativados,
    a saudação deve responder com o link/redirecionamento).
    """
    if not message_text:
        return False
    msg = str(message_text).lower().strip()
    if not msg:
        return False

    saudacoes = {
        "oi",
        "ola",
        "olá",
        "oie",
        "eai",
        "e aí",
        "bom dia",
        "boa tarde",
        "boa noite",
        "menu",
        "cardapio",
        "cardápio",
        "inicio",
        "início",
        "começar",
        "comecar",
        "start",
    }
    if msg in saudacoes:
        return True

    # Ex.: "oi tudo bem", "bom dia!"
    if any(msg.startswith(s + " ") for s in ("oi", "ola", "olá", "bom dia", "boa tarde", "boa noite")):
        return True

    return False


def _montar_mensagem_redirecionamento(db: Session, empresa_id: int, config) -> str:
    link_cardapio = "https://chatbot.mensuraapi.com.br"
    try:
        empresa_query = text("""
            SELECT nome, cardapio_link
            FROM cadastros.empresas
            WHERE id = :empresa_id
        """)
        result_empresa = db.execute(empresa_query, {"empresa_id": empresa_id})
        empresa = result_empresa.fetchone()
        link_cardapio = empresa[1] if empresa and empresa[1] else link_cardapio
    except Exception:
        pass

    if config and config.mensagem_redirecionamento:
        return config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
    return (
        "📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n"
        f"👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
    )


def _compact_json_line(value) -> str:
    """Compacta dict/list para log em uma única linha."""
    try:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return str(value)
    except Exception:
        return str(value)


def _log_whatsapp_out(*, sender: str, recipient: str, body, empresa_id=None) -> None:
    """
    Log único e limpo para envio de mensagens WhatsApp.

    - sender: "chatbot" | "humano"
    - recipient: telefone destino (normalizado quando possível)
    - body: payload relevante (request/response)
    """
    logger.info(
        "[whatsapp.out] empresa_id=%s from=%s to=%s body=%s",
        empresa_id,
        sender,
        recipient,
        _compact_json_line(body),
    )


async def _send_whatsapp_and_log(
    db: Session,
    phone_number: str,
    contact_name: Optional[str],
    empresa_id: str,
    empresa_id_int: int,
    user_message: str,
    response_message: str,
    prompt_key: str,
    model: str,
    message_id: Optional[str] = None,
    buttons: Optional[List[Dict[str, str]]] = None,
):
    notifier = OrderNotification()
    
    # Se tiver botões, envia mensagem com botões
    if buttons:
        result = await notifier.send_whatsapp_message_with_buttons(
            phone_number, 
            response_message, 
            buttons, 
            empresa_id=empresa_id
        )
    else:
        result = await notifier.send_whatsapp_message(phone_number, response_message, empresa_id=empresa_id)

    if isinstance(result, dict) and result.get("success"):
        conversations = chatbot_db.get_conversations_by_user(db, phone_number, empresa_id_int)
        if conversations:
            conversation_id = conversations[0]["id"]
        else:
            conversation_id = chatbot_db.create_conversation(
                db=db,
                session_id=f"whatsapp_{phone_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                user_id=phone_number,
                prompt_key=prompt_key,
                model=model,
                contact_name=contact_name,
                empresa_id=empresa_id_int
            )
        chatbot_db.create_message(db, conversation_id, "user", user_message, whatsapp_message_id=message_id)
        # Salva o message_id retornado pelo WhatsApp na mensagem do assistente (para identificar que foi o chatbot que enviou)
        whatsapp_response_message_id = result.get("message_id")
        chatbot_db.create_message(db, conversation_id, "assistant", response_message, whatsapp_message_id=whatsapp_response_message_id)

        _log_whatsapp_out(
            sender="chatbot",
            recipient=phone_number,
            empresa_id=empresa_id,
            body={
                "message": response_message,
                "buttons": buttons,
                "whatsapp_message_id": whatsapp_response_message_id,
            },
        )
    else:
        _log_whatsapp_out(
            sender="chatbot",
            recipient=phone_number,
            empresa_id=empresa_id,
            body={
                "message": response_message,
                "buttons": buttons,
                "error": result.get("error") if isinstance(result, dict) else str(result),
            },
        )

    return result


async def _enviar_notificacao_empresa(
    db: Session,
    empresa_id: str,
    empresa_id_int: int,
    cliente_phone: str,
    cliente_nome: Optional[str],
    tipo_solicitacao: str,  # "chamar_atendente"
):
    """
    Envia notificação para o WhatsApp da empresa quando cliente chama atendente.
    Também envia notificação via WebSocket para o frontend.
    """
    try:
        # Busca nome da empresa
        empresa_query = text("""
            SELECT nome
            FROM cadastros.empresas
            WHERE id = :empresa_id
        """)
        result_empresa = db.execute(empresa_query, {"empresa_id": empresa_id_int})
        empresa = result_empresa.fetchone()
        nome_empresa = empresa[0] if empresa and empresa[0] else "Empresa"
        
        # Monta mensagem de notificação
        mensagem = f"🔔 *Solicitação de Atendimento Humano*\n\n"
        mensagem += f"Cliente *{cliente_nome or cliente_phone}* está solicitando atendimento de um humano.\n\n"
        
        mensagem += f"📱 Telefone: {cliente_phone}\n"
        if cliente_nome:
            mensagem += f"👤 Nome: {cliente_nome}\n"
        mensagem += f"🏢 Empresa: {nome_empresa}\n\n"
        mensagem += f"💬 Entre em contato com o cliente para atendê-lo."
        
        # ===== ENVIA NOTIFICAÇÃO VIA WEBSOCKET PARA O FRONTEND =====
        try:
            from ..core.notifications import send_chatbot_websocket_notification
            from datetime import datetime
            
            # Monta dados da notificação WebSocket
            notification_data = {
                "cliente_phone": cliente_phone,
                "cliente_nome": cliente_nome,
                "tipo": "chamar_atendente",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Título e mensagem para o WebSocket
            title = "🔔 Solicitação de Atendimento Humano"
            message_ws = f"Cliente {cliente_nome or cliente_phone} está solicitando atendimento de um humano.\n\n📱 Telefone: {cliente_phone}"
            if cliente_nome:
                message_ws += f"\n👤 Nome: {cliente_nome}"
            
            # Envia notificação WebSocket
            sent_count = await send_chatbot_websocket_notification(
                empresa_id=empresa_id_int,
                notification_type="chamar_atendente",
                title=title,
                message=message_ws,
                data=notification_data
            )
        except Exception as e_ws:
            logger.error(f"❌ Erro ao enviar notificação WebSocket: {e_ws}", exc_info=True)
            # Continua mesmo se falhar o WebSocket, pois ainda pode enviar via WhatsApp
        
        # Envia notificação para o número da empresa (usando o mesmo sistema de envio)
        # O número da empresa é o display_phone_number da configuração do WhatsApp
        # Mas como não temos acesso direto, vamos usar o sistema de notificação interno
        # ou enviar para um número configurado. Por enquanto, vamos usar o mesmo empresa_id
        # para enviar a notificação (a API do WhatsApp vai usar a configuração da empresa)
        
        # Busca display_phone_number da configuração do WhatsApp da empresa
        from app.api.notifications.repositories.whatsapp_config_repository import WhatsAppConfigRepository
        repo_whatsapp = WhatsAppConfigRepository(db)
        config_whatsapp = repo_whatsapp.get_active_by_empresa(empresa_id)
        
        if config_whatsapp and config_whatsapp.display_phone_number:
            # Envia notificação para o número da empresa
            notifier = OrderNotification()
            # Formata o número da empresa
            from app.api.chatbot.core.config_whatsapp import format_phone_number
            empresa_phone = format_phone_number(config_whatsapp.display_phone_number)
            
            result = await notifier.send_whatsapp_message(empresa_phone, mensagem, empresa_id=empresa_id)
            
            if result.get("success"):
                return {"success": True, "message": "Notificação enviada com sucesso"}
            else:
                logger.error(f"❌ Erro ao enviar notificação WhatsApp para empresa: {result.get('error')}")
                return {"success": False, "error": result.get("error")}
        else:
            # Mesmo sem WhatsApp, a notificação WebSocket já foi enviada
            return {"success": True, "message": "Notificação WebSocket enviada (WhatsApp não configurado)"}
            
    except Exception as e:
        logger.error(f"❌ Erro ao enviar notificação para empresa: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

# Router
router = APIRouter(
    prefix="/api/chatbot",
    tags=["API - Chatbot"]
)

# Incluir router de configurações do chatbot
from .router_chatbot_config import router as router_chatbot_config
from .router_gestor_admin import router as router_gestor_admin
from app.core.admin_dependencies import require_admin
from app.core.authorization import require_permissions
router.include_router(router_chatbot_config)
router.include_router(
    router_gestor_admin,
    dependencies=[Depends(require_admin), Depends(require_permissions(["route:/chatbot"]))],
)

# Incluir router do carrinho
from .router_carrinho import router as router_carrinho
router.include_router(router_carrinho)


# ==================== ENDPOINTS BÁSICOS ====================

@router.get("/health")
async def health_check():
    """Verifica se a API Groq está acessível"""
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY não configurada")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            )
            if response.status_code == 200:
                models = response.json().get("data", [])
                model_names = [m.get("id") for m in models if m.get("id")]
                return {"groq": "online", "models_disponiveis": model_names}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Groq indisponível. Erro: {str(e)}")


# ==================== CHAT ====================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Endpoint principal do chat"""
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY não configurada")

    # Se o modelo for "notification-system", significa que é uma conversa de notificação
    # Vamos mudar para o modelo padrão para permitir chat normal
    actual_model = request.model
    if request.model == "notification-system":
        actual_model = DEFAULT_MODEL

    # Usa o system prompt customizado se fornecido, caso contrário usa o padrão
    # e injeta guardrails anti-alucinação para reduzir "chutes".
    system_prompt_raw = request.system_prompt if request.system_prompt else SYSTEM_PROMPT
    system_prompt = build_system_prompt(system_prompt_raw, require_json_object=False)

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

    # Chama a Groq (API compatível com OpenAI)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "model": actual_model or MODEL_NAME,
                "messages": messages,
                "stream": False,
                "temperature": clamp_temperature(request.temperature),
                "top_p": 0.9,
            }
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            response = await client.post(GROQ_API_URL, json=payload, headers=headers)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Erro na Groq: {response.text}"
                )

            result = response.json()
            assistant_message = result["choices"][0]["message"]["content"]

            return ChatResponse(
                response=assistant_message,
                model=actual_model
            )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Timeout ao aguardar resposta da Groq"
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
async def get_user_conversations(
    user_id: str,
    db: Session = Depends(get_db),
    empresa_id: Optional[int] = None,
    data_inicio: Optional[date] = Query(
        default=None,
        description="Data inicial (YYYY-MM-DD) para filtrar por última mensagem (MAX(messages.created_at)).",
    ),
    data_fim: Optional[date] = Query(
        default=None,
        description="Data final (YYYY-MM-DD) para filtrar por última mensagem (MAX(messages.created_at)). Inclusiva.",
    ),
):
    """Lista todas as conversas de um usuário (com filtro opcional por data)."""
    conversations = chatbot_db.get_conversations_by_user(
        db,
        user_id,
        empresa_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    # Anexa status do bot (pausado/ativo) para cada conversa baseada no telefone (user_id)
    try:
        for conv in conversations:
            try:
                conv["bot_status"] = chatbot_db.get_bot_status(db, conv.get("user_id"))
            except Exception:
                conv["bot_status"] = {"phone_number": conv.get("user_id"), "is_active": True}
    except Exception:
        # Não falhar a rota se algo der errado ao buscar status
        pass
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
    # Anexa status do bot (pausado/ativo) para a conversa retornada
    try:
        latest_conversation["bot_status"] = chatbot_db.get_bot_status(db, latest_conversation.get("user_id"))
    except Exception:
        latest_conversation["bot_status"] = {"phone_number": latest_conversation.get("user_id"), "is_active": True}

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
        # Anexa status do bot para cada conversa (se possível)
        try:
            for conv in conversations:
                try:
                    conv["bot_status"] = chatbot_db.get_bot_status(db, conv.get("user_id"))
                except Exception:
                    conv["bot_status"] = {"phone_number": conv.get("user_id"), "is_active": True}
        except Exception:
            pass
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
    pausar: bool,
    paused_by: Optional[str] = None,
    empresa_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Ativa ou desativa o bot para um número específico. Ao pausar, destrava em 3h."""
    # Se já estiver pausado e pedirem "pausar", cancela (evita re-pausar / reescrever)
    try:
        current = chatbot_db.get_bot_status(db, phone_number) or {}
        if pausar and not current.get("is_active", True):
            pausar = False
    except Exception:
        pass

    desativa_em = chatbot_db.get_auto_pause_until() if pausar else None
    result = chatbot_db.set_bot_status(
        db,
        phone_number,
        paused_by=paused_by if pausar else None,
        empresa_id=empresa_id,
        desativa_chatbot_em=desativa_em,
    )
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
    pausar: bool,
    paused_by: Optional[str] = None,
    empresa_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Ativa ou desativa o bot para TODOS os números de uma vez"""
    # Se já estiver pausado globalmente e pedirem "pausar", cancela (evita re-pausar / reescrever)
    try:
        current = chatbot_db.get_global_bot_status(db, empresa_id) or {}
        if pausar and not current.get("is_active", True):
            pausar = False
    except Exception:
        pass

    result = chatbot_db.set_global_bot_status(
        db,
        paused_by=paused_by if pausar else None,
        empresa_id=empresa_id,
        desativa_chatbot_em="infinity" if pausar else None,
    )
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

    # Normaliza o telefone (remove caracteres não numéricos para garantir consistência)
    phone_normalized = ''.join(filter(str.isdigit, phone))

    # Envia via WhatsApp
    notifier = OrderNotification()
    result = await notifier.send_whatsapp_message(phone, message)

    if result.get("success"):
        # Salva a mensagem enviada no histórico da conversa
        # PAUSA O CHATBOT POR 3 HORAS quando atendente responde
        # IMPORTANTE: Pausa SEMPRE, mesmo se não houver conversa no histórico
        try:
            destrava_em = chatbot_db.get_auto_pause_until()
            
            # Tenta obter empresa_id da conversa, mas não é obrigatório
            empresa_id = None
            try:
                # Tenta buscar conversa com telefone normalizado e original
                phone_to_search = phone_normalized if 'phone_normalized' in locals() else phone
                conversations = chatbot_db.get_conversations_by_user(db, phone_to_search)
                
                # Se não encontrou, tenta com o telefone original também
                if not conversations:
                    conversations = chatbot_db.get_conversations_by_user(db, phone)
                
                conversation_id = None
                if conversations:
                    conversation = conversations[0]
                    conversation_id = conversation.get('id')
                    empresa_id = conversation.get('empresa_id') or empresa_id  # Mantém empresa_id se já tinha
                else:
                    # Cria nova conversa se não existir para salvar a mensagem
                    from datetime import datetime as dt
                    # Se não tem empresa_id, usa 1 como padrão
                    empresa_id_final = empresa_id if empresa_id else 1
                    # Garante prompt default
                    prompt_key = "atendimento-pedido-whatsapp"
                    if not chatbot_db.get_prompt(db, prompt_key, empresa_id=empresa_id_final):
                        chatbot_db.create_prompt(
                            db=db,
                            key=prompt_key,
                            name="Atendimento WhatsApp",
                            content="Atendimento via WhatsApp",
                            is_default=False,
                            empresa_id=empresa_id_final
                        )
                    
                    conversation_id = chatbot_db.create_conversation(
                        db=db,
                        session_id=f"whatsapp_{phone_to_search}_{dt.now().strftime('%Y%m%d%H%M%S')}",
                        user_id=phone_to_search,
                        prompt_key=prompt_key,
                        model="groq-sales",
                        empresa_id=empresa_id_final
                    )
                    empresa_id = empresa_id_final  # Atualiza empresa_id para usar depois
                
                # Salva mensagem no histórico COM o message_id do WhatsApp
                # IMPORTANTE: Salva o message_id para que o webhook possa identificar que foi o atendente que enviou
                whatsapp_message_id = result.get("message_id") if isinstance(result, dict) else None
                try:
                    from app.api.chatbot.adapters.message_persistence_adapter import ChatMessagePersistenceAdapter
                    from app.api.chatbot.contracts.message_persistence_contract import (
                        ChatMessageSenderType,
                        ChatMessageSourceType,
                        PersistChatMessageCommand,
                    )

                    persistence = ChatMessagePersistenceAdapter(db)
                    persistence.persist_message(
                        PersistChatMessageCommand(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=message,
                            empresa_id=int(empresa_id) if empresa_id is not None else None,
                            whatsapp_message_id=whatsapp_message_id,
                            source_type=ChatMessageSourceType.WHATSAPP_NOTIFICATION,
                            sender_type=ChatMessageSenderType.HUMAN,
                            metadata={"source": "send-notification"},
                        )
                    )
                except Exception:
                    chatbot_db.create_message(
                        db=db,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=message,
                        whatsapp_message_id=whatsapp_message_id,
                        extra_metadata={"sender": "human", "source": "send-notification"},
                    )
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar/salvar conversa: {e}", exc_info=True)

            # Log limpo: HUMANO -> cliente (body + destino)
            _log_whatsapp_out(
                sender="humano",
                recipient=phone_normalized or phone,
                empresa_id=empresa_id,
                body={
                    "phone": phone,
                    "message": message,
                    "whatsapp_message_id": result.get("message_id") if isinstance(result, dict) else None,
                },
            )

            # Cancela a tentativa de pause se já estiver pausado
            if chatbot_db.is_bot_active_for_phone(db, phone_normalized):
                pause_result = chatbot_db.set_bot_status(
                    db=db,
                    phone_number=phone_normalized,
                    paused_by="atendente_respondeu",
                    empresa_id=empresa_id,
                    desativa_chatbot_em=destrava_em,
                )
                if not pause_result.get("success"):
                    logger.error(f"❌ Falha ao pausar chatbot: {pause_result.get('error')}")
        except Exception as e:
            logger.error(f"❌ Erro ao pausar chatbot após resposta do atendente: {e}", exc_info=True)

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
                # PAUSA O CHATBOT POR 3 HORAS quando atendente envia mídia
                # IMPORTANTE: Pausa SEMPRE, mesmo se não houver conversa no histórico
                try:
                    destrava_em = chatbot_db.get_auto_pause_until()
                    
                    # Tenta obter empresa_id da conversa, mas não é obrigatório
                    empresa_id = None
                    try:
                        conversations = chatbot_db.get_conversations_by_user(db, phone)
                        if conversations:
                            conversation = conversations[0]
                            conversation_id = conversation.get('id')
                            empresa_id = conversation.get('empresa_id')
                            
                            # Salva como JSON para o frontend poder renderizar a mídia
                            media_content = json.dumps({
                                "type": "media",
                                "media_type": media_type,
                                "media_url": media_url,
                                "caption": caption or ""
                            })
                            chatbot_db.create_message(
                                db=db,
                                conversation_id=conversation_id,
                                role="assistant",
                                content=media_content
                            )
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao buscar/salvar conversa: {e}")
                    
                    # PAUSA O CHATBOT (sempre, mesmo sem conversa)
                    # Usa telefone normalizado para garantir consistência
                    phone_clean_media = ''.join(filter(str.isdigit, phone))

                    # Log limpo: HUMANO -> cliente (mídia)
                    _log_whatsapp_out(
                        sender="humano",
                        recipient=phone_clean_media,
                        empresa_id=empresa_id,
                        body={
                            "phone": phone,
                            "media_url": media_url,
                            "media_type": media_type,
                            "caption": caption,
                            "whatsapp_message_id": result.get("messages", [{}])[0].get("id"),
                        },
                    )

                    # Cancela a tentativa de pause se já estiver pausado
                    if chatbot_db.is_bot_active_for_phone(db, phone_clean_media):
                        pause_result = chatbot_db.set_bot_status(
                            db=db,
                            phone_number=phone_clean_media,
                            paused_by="atendente_respondeu",
                            empresa_id=empresa_id,
                            desativa_chatbot_em=destrava_em,
                        )
                        if not pause_result.get("success"):
                            logger.error(f"❌ Falha ao pausar chatbot após mídia: {pause_result.get('error')}")
                except Exception as e:
                    logger.error(f"❌ Erro ao pausar chatbot após envio de mídia pelo atendente: {e}", exc_info=True)

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

def _pretty_json_for_log(data) -> str:
    """
    Serializa JSON "bonitinho" para log (multi-linha).
    Mantém acentos (ensure_ascii=False) e ordena chaves para facilitar diffs.
    """
    try:
        return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception:
        # Fallback defensivo: não quebra o webhook por causa de log
        return str(data)


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


def _digits_only(value: Optional[str]) -> str:
    if not value:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


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
    try:
        # Lê o body de forma segura
        try:
            body_bytes = await request.body()
        except Exception as e:
            logger.error(f"Erro ao ler body da requisição: {e}")
            # Retorna 200 OK imediatamente mesmo com erro (requisito da 360Dialog)
            return {"status": "ok", "message": "Erro ao ler body, mas webhook recebido"}
        
        # Verifica se há body
        if not body_bytes or len(body_bytes) == 0:
            logger.debug("Webhook 360dialog recebido sem body.")
            # Retorna 200 OK imediatamente (requisito da 360Dialog)
            return {"status": "ok", "message": "Webhook recebido sem body"}
        
        # Tenta parsear JSON
        try:
            body_text = body_bytes.decode('utf-8')
            if not body_text.strip():
                logger.debug("Webhook 360dialog recebido com body vazio.")
                # Retorna 200 OK imediatamente (requisito da 360Dialog)
                return {"status": "ok", "message": "Webhook recebido com body vazio"}
            body = json.loads(body_text)
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON do webhook: {e}")
            # Retorna 200 OK imediatamente mesmo com erro de JSON (requisito da 360Dialog)
            return {"status": "ok", "message": "Webhook recebido (JSON inválido, mas processado)"}

        # Mantém headers_info apenas para passar ao processamento em background
        headers_info = {
            "x_cliente": request.headers.get("x-cliente"),
            "host": request.headers.get("host"),
        }

        # Verifica status global do bot (depois do log do webhook)
        try:
            global_status = chatbot_db.get_global_bot_status(db)
            if not global_status.get("is_active", True):
                # Bot desligado: retorna OK sem processar nada
                return {"status": "ok", "message": "Chatbot desligado"}
        except Exception:
            # Se falhar ao verificar status, assume que está ligado para não bloquear webhooks
            pass

        # CRÍTICO: Retorna 200 OK IMEDIATAMENTE antes de processar
        # Conforme documentação 360Dialog: "acknowledge immediately after receiving the webhook"
        # Processa tudo em background para não violar o limite de 5 segundos
        
        # Adiciona processamento em background
        # IMPORTANTE: Não passa a sessão do banco diretamente, cria nova sessão na função
        background_tasks.add_task(process_webhook_background, body, headers_info)

        # Retorna 200 OK imediatamente (requisito crítico da 360Dialog)
        return {"status": "ok"}

    except Exception as e:
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
                        contact_wa_id = None
                        if contacts and len(contacts) > 0:
                            profile = contacts[0].get("profile", {})
                            contact_name = profile.get("name")
                            contact_wa_id = contacts[0].get("wa_id")

                        for message in messages:
                            # Dados da mensagem
                            from_number = message.get("from")
                            to_number = message.get("to")
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
                                # Detecta se a mensagem foi enviada pelo HUMANO (WhatsApp Web) vs CLIENTE.
                                # Alguns provedores enviam mensagens "outgoing" no bloco `messages`.
                                # Regras (heurísticas):
                                # - Se `from` == metadata.phone_number_id => empresa enviou
                                # - Se `from` (digits) == metadata.display_phone_number (digits) => empresa enviou
                                # - Se existir `to`, e `from` parece ser o remetente da empresa => empresa enviou
                                business_phone_number_id = str(metadata.get("phone_number_id") or "").strip()
                                business_display_phone = str(metadata.get("display_phone_number") or "").strip()

                                from_digits = _digits_only(from_number)
                                to_digits = _digits_only(to_number)
                                business_id_digits = _digits_only(business_phone_number_id)
                                business_display_digits = _digits_only(business_display_phone)

                                is_outgoing_human = False
                                if business_phone_number_id and str(from_number).strip() == business_phone_number_id:
                                    is_outgoing_human = True
                                elif business_display_digits and from_digits and from_digits == business_display_digits:
                                    is_outgoing_human = True
                                elif message.get("from_me") is True:
                                    is_outgoing_human = True

                                if is_outgoing_human:
                                    # Determina o cliente (destinatário) para salvar no histórico correto
                                    cliente_phone = None
                                    if to_digits and to_digits != business_id_digits and to_digits != business_display_digits:
                                        cliente_phone = to_digits
                                    elif contact_wa_id:
                                        cliente_phone = _digits_only(contact_wa_id) or str(contact_wa_id).strip()
                                    # fallback: se não conseguiu, tenta usar to_number bruto
                                    if not cliente_phone and to_number:
                                        cliente_phone = str(to_number).strip()

                                    if not cliente_phone:
                                        import logging
                                        logger = logging.getLogger(__name__)
                                        logger.warning(
                                            f"⚠️ Webhook recebeu mensagem outgoing (humano), mas não conseguiu identificar cliente. "
                                            f"from={from_number}, to={to_number}, empresa_id={empresa_id}"
                                        )
                                        continue

                                    try:
                                        import logging
                                        from datetime import datetime as dt
                                        logger = logging.getLogger(__name__)

                                        empresa_id_int = int(empresa_id) if empresa_id else 1

                                        # Busca ou cria conversa do cliente
                                        conversations = chatbot_db.get_conversations_by_user(db, cliente_phone, empresa_id=empresa_id_int)
                                        if not conversations:
                                            conversations = chatbot_db.get_conversations_by_user(db, cliente_phone)

                                        conversation_id = None
                                        if conversations:
                                            conversation_id = conversations[0]["id"]
                                        else:
                                            prompt_key = "atendimento-pedido-whatsapp"
                                            if not chatbot_db.get_prompt(db, prompt_key, empresa_id=empresa_id_int):
                                                chatbot_db.create_prompt(
                                                    db=db,
                                                    key=prompt_key,
                                                    name="Atendimento WhatsApp",
                                                    content="Atendimento via WhatsApp",
                                                    is_default=False,
                                                    empresa_id=empresa_id_int,
                                                )
                                            conversation_id = chatbot_db.create_conversation(
                                                db=db,
                                                session_id=f"whatsapp_{cliente_phone}_{dt.now().strftime('%Y%m%d%H%M%S')}",
                                                user_id=cliente_phone,
                                                prompt_key=prompt_key,
                                                model="groq-sales",
                                                empresa_id=empresa_id_int,
                                                contact_name=contact_name,
                                            )

                                        # Salva o conteúdo real enviado pelo humano (WhatsApp Web)
                                        try:
                                            from app.api.chatbot.adapters.message_persistence_adapter import ChatMessagePersistenceAdapter
                                            from app.api.chatbot.contracts.message_persistence_contract import (
                                                ChatMessageSenderType,
                                                ChatMessageSourceType,
                                                PersistChatMessageCommand,
                                            )

                                            persistence = ChatMessagePersistenceAdapter(db)
                                            persistence.persist_message(
                                                PersistChatMessageCommand(
                                                    conversation_id=conversation_id,
                                                    role="assistant",
                                                    content=message_text,
                                                    empresa_id=empresa_id_int,
                                                    whatsapp_message_id=message_id,
                                                    source_type=ChatMessageSourceType.WHATSAPP_WEB,
                                                    sender_type=ChatMessageSenderType.HUMAN,
                                                    metadata={"source": "whatsapp_web", "sender": "human"},
                                                )
                                            )
                                        except Exception:
                                            chatbot_db.create_message(
                                                db=db,
                                                conversation_id=conversation_id,
                                                role="assistant",
                                                content=message_text,
                                                whatsapp_message_id=message_id,
                                                extra_metadata={"sender": "human", "source": "whatsapp_web"},
                                            )

                                        # Log limpo: HUMANO -> cliente (WhatsApp Web / Coexistence)
                                        _log_whatsapp_out(
                                            sender="humano",
                                            recipient=str(cliente_phone),
                                            empresa_id=empresa_id_int,
                                            body={
                                                "message": message_text,
                                                "whatsapp_message_id": message_id,
                                                "source": "whatsapp_web",
                                            },
                                        )

                                        # Cancela a tentativa de pause se já estiver pausado
                                        if chatbot_db.is_bot_active_for_phone(db, cliente_phone):
                                            destrava_em = chatbot_db.get_auto_pause_until()
                                            pause_result = chatbot_db.set_bot_status(
                                                db=db,
                                                phone_number=cliente_phone,
                                                paused_by="atendente_respondeu",
                                                empresa_id=empresa_id_int,
                                                desativa_chatbot_em=destrava_em,
                                            )
                                            if not pause_result.get("success"):
                                                logger.error(
                                                    f"Falha ao pausar chatbot após mensagem humana (WhatsApp Web): {pause_result.get('error')}"
                                                )
                                    except Exception as e:
                                        logger.error(
                                            f"❌ Erro ao processar mensagem outgoing (humano) do WhatsApp Web: {e}",
                                            exc_info=True,
                                        )
                                    # Não deve cair no fluxo de IA para mensagens enviadas pelo humano
                                    continue

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

                    # Processa MESSAGE ECHOES (360dialog coexistence) - mensagens OUTGOING que saíram do número da empresa
                    # Esse payload costuma chegar como field="smb_message_echoes" com value.message_echoes[]
                    # Objetivo: detectar quando foi HUMANO respondendo pelo WhatsApp (app/web) e PAUSAR o bot.
                    message_echoes = value.get("message_echoes", [])
                    if message_echoes:
                        for echo in message_echoes:
                            try:
                                import logging
                                from sqlalchemy import text
                                from datetime import datetime as dt

                                logger = logging.getLogger(__name__)

                                echo_id = echo.get("id")
                                echo_type = (echo.get("type") or "").lower()
                                echo_from = echo.get("from")
                                echo_to = echo.get("to")  # cliente
                                echo_timestamp = echo.get("timestamp")

                                # Conteúdo (prioriza texto)
                                echo_text = None
                                if echo_type == "text":
                                    echo_text = echo.get("text", {}).get("body")
                                elif echo.get("text", {}).get("body"):
                                    # fallback defensivo: alguns payloads ainda trazem text.body
                                    echo_text = echo.get("text", {}).get("body")
                                else:
                                    # Sem texto: registra algo mínimo para auditoria
                                    echo_text = f"[mensagem_outgoing tipo={echo_type or 'desconhecido'}]"

                                # Determina o cliente (destinatário)
                                cliente_phone = _digits_only(echo_to) or (str(echo_to).strip() if echo_to else None)
                                if not cliente_phone:
                                    logger.warning(
                                        f"⚠️ smb_message_echoes recebido, mas sem destinatário (to). "
                                        f"id={echo_id}, from={echo_from}, to={echo_to}, empresa_id={empresa_id}"
                                    )
                                    continue

                                # Identifica se o echo foi do chatbot (pelo whatsapp_message_id persistido)
                                foi_chatbot = False
                                if echo_id:
                                    try:
                                        query_check_bot = text("""
                                            SELECT m.id
                                            FROM chatbot.messages m
                                            JOIN chatbot.conversations c ON m.conversation_id = c.id
                                            WHERE m.metadata->>'whatsapp_message_id' = :message_id
                                            AND m.role = 'assistant'
                                            AND (m.metadata->>'sender' IS NULL OR m.metadata->>'sender' = 'chatbot')
                                            AND c.user_id = :recipient_id
                                            ORDER BY m.created_at DESC
                                            LIMIT 1
                                        """)
                                        result = db.execute(query_check_bot, {
                                            "message_id": echo_id,
                                            "recipient_id": cliente_phone,
                                        })
                                        foi_chatbot = bool(result.fetchone())
                                    except Exception as e:
                                        logger.warning(
                                            f"⚠️ Erro ao verificar smb_message_echoes no banco (assumindo humano): {e}",
                                            exc_info=True,
                                        )
                                        foi_chatbot = False

                                if foi_chatbot:
                                    continue

                                # Se chegou aqui: é HUMANO respondendo pelo WhatsApp (coexistence)
                                _log_whatsapp_out(
                                    sender="humano",
                                    recipient=str(cliente_phone),
                                    empresa_id=int(empresa_id) if empresa_id else 1,
                                    body={
                                        "message": echo_text or "",
                                        "whatsapp_message_id": echo_id,
                                        "timestamp": str(echo_timestamp) if echo_timestamp is not None else None,
                                        "source": "smb_message_echoes",
                                    },
                                )

                                empresa_id_int = int(empresa_id) if empresa_id else 1

                                # Busca ou cria conversa do cliente
                                conversations = chatbot_db.get_conversations_by_user(db, cliente_phone, empresa_id=empresa_id_int)
                                if not conversations:
                                    conversations = chatbot_db.get_conversations_by_user(db, cliente_phone)

                                conversation_id = None
                                if conversations:
                                    conversation_id = conversations[0]["id"]
                                else:
                                    prompt_key = "atendimento-pedido-whatsapp"
                                    if not chatbot_db.get_prompt(db, prompt_key, empresa_id=empresa_id_int):
                                        chatbot_db.create_prompt(
                                            db=db,
                                            key=prompt_key,
                                            name="Atendimento WhatsApp",
                                            content="Atendimento via WhatsApp",
                                            is_default=False,
                                            empresa_id=empresa_id_int,
                                        )
                                    conversation_id = chatbot_db.create_conversation(
                                        db=db,
                                        session_id=f"whatsapp_{cliente_phone}_{dt.now().strftime('%Y%m%d%H%M%S')}",
                                        user_id=cliente_phone,
                                        prompt_key=prompt_key,
                                        model="groq-sales",
                                        empresa_id=empresa_id_int,
                                    )

                                # Persiste a mensagem humana enviada pelo WhatsApp (coexistence echo)
                                try:
                                    from app.api.chatbot.adapters.message_persistence_adapter import ChatMessagePersistenceAdapter
                                    from app.api.chatbot.contracts.message_persistence_contract import (
                                        ChatMessageSenderType,
                                        ChatMessageSourceType,
                                        PersistChatMessageCommand,
                                    )

                                    persistence = ChatMessagePersistenceAdapter(db)
                                    persistence.persist_message(
                                        PersistChatMessageCommand(
                                            conversation_id=conversation_id,
                                            role="assistant",
                                            content=echo_text or "",
                                            empresa_id=empresa_id_int,
                                            whatsapp_message_id=echo_id,
                                            source_type=ChatMessageSourceType.WHATSAPP_WEB,
                                            sender_type=ChatMessageSenderType.HUMAN,
                                            metadata={
                                                "sender": "human",
                                                "source": "smb_message_echoes",
                                                "from": str(echo_from) if echo_from is not None else None,
                                                "to": str(echo_to) if echo_to is not None else None,
                                                "type": echo_type,
                                                "timestamp": str(echo_timestamp) if echo_timestamp is not None else None,
                                            },
                                        )
                                    )
                                except Exception:
                                    chatbot_db.create_message(
                                        db=db,
                                        conversation_id=conversation_id,
                                        role="assistant",
                                        content=echo_text or "",
                                        whatsapp_message_id=echo_id,
                                        extra_metadata={
                                            "sender": "human",
                                            "source": "smb_message_echoes",
                                            "from": str(echo_from) if echo_from is not None else None,
                                            "to": str(echo_to) if echo_to is not None else None,
                                            "type": echo_type,
                                            "timestamp": str(echo_timestamp) if echo_timestamp is not None else None,
                                        },
                                    )

                                # Log limpo: HUMANO -> cliente (conteúdo do echo)
                                _log_whatsapp_out(
                                    sender="humano",
                                    recipient=str(cliente_phone),
                                    empresa_id=empresa_id_int,
                                    body={
                                        "message": echo_text or "",
                                        "whatsapp_message_id": echo_id,
                                        "source": "smb_message_echoes",
                                    },
                                )

                                # Cancela a tentativa de pause se já estiver pausado
                                if chatbot_db.is_bot_active_for_phone(db, cliente_phone):
                                    destrava_em = chatbot_db.get_auto_pause_until()
                                    pause_result = chatbot_db.set_bot_status(
                                        db=db,
                                        phone_number=cliente_phone,
                                        paused_by="atendente_respondeu",
                                        empresa_id=empresa_id_int,
                                        desativa_chatbot_em=destrava_em,
                                    )
                                    if not pause_result.get("success"):
                                        logger.error(
                                            f"Falha ao pausar chatbot após smb_message_echoes humano: {pause_result.get('error')}"
                                        )
                            except Exception as e:
                                logger.error(f"❌ Erro ao processar smb_message_echoes: {e}", exc_info=True)

                    # Processa STATUSES (status de mensagens enviadas: sent, delivered, read)
                    # IMPORTANTE: Este bloco só processa quando a EMPRESA envia mensagem para o cliente
                    # Quando o CLIENTE envia mensagem, vem no bloco "messages" acima (linha 1618)
                    # e é processado normalmente sem pausar o chatbot
                    statuses = value.get("statuses", [])
                    if statuses:
                        for status in statuses:
                            status_type = status.get("status")  # sent, delivered, read, failed
                            recipient_id = status.get("recipient_id")  # Número do destinatário (cliente)
                            
                            # Quando status é "sent"/"delivered"/"read", significa que a EMPRESA enviou mensagem para o cliente
                            # (dependendo do provedor, o primeiro status pode vir como delivered/read, então não podemos depender só de "sent").
                            # IMPORTANTE: Só pausa se foi um HUMANO que enviou, não o chatbot.
                            # Verifica se o message_id do status corresponde a uma mensagem do assistente (chatbot).
                            OUTGOING_STATUS_TYPES = {"sent", "delivered", "read"}
                            if (status_type or "").lower() in OUTGOING_STATUS_TYPES and recipient_id:
                                try:
                                    from sqlalchemy import text
                                    
                                    # Pega o message_id do status (é o mesmo retornado quando enviamos a mensagem)
                                    status_message_id = status.get("id")
                                    if not status_message_id:
                                        continue

                                    # Idempotência / anti-alucinação:
                                    # Se já existe QUALQUER mensagem no banco com esse whatsapp_message_id, então essa saída
                                    # já foi persistida (ex.: /send-notification, envio do chatbot, ou até echo). Não devemos
                                    # criar o placeholder "[Mensagem enviada pelo atendente...]" nem pausar de novo.
                                    try:
                                        q_any = text(
                                            """
                                            SELECT 1
                                            FROM chatbot.messages m
                                            WHERE m.metadata->>'whatsapp_message_id' = :message_id
                                            LIMIT 1
                                            """
                                        )
                                        already_persisted = db.execute(
                                            q_any, {"message_id": str(status_message_id)}
                                        ).fetchone()
                                        if already_persisted:
                                            continue
                                    except Exception as e:
                                        logger.warning(
                                            f"⚠️ Erro ao verificar duplicidade por whatsapp_message_id (continuando): {e}",
                                            exc_info=True,
                                        )
                                    
                                    # Verifica se esse message_id corresponde a uma mensagem do assistente (chatbot)
                                    foi_chatbot = False
                                    if status_message_id:
                                        try:
                                            # Busca no banco se existe uma mensagem do assistente com esse message_id
                                            # Não restringimos por janela curta de tempo aqui, pois alguns provedores podem
                                            # atrasar o primeiro status (ex.: "delivered"/"read"). A identificação correta
                                            # é pela combinação message_id + c.user_id.
                                            query_check_bot = text("""
                                                SELECT m.id, m.role, m.created_at, m.metadata
                                                FROM chatbot.messages m
                                                JOIN chatbot.conversations c ON m.conversation_id = c.id
                                                WHERE m.metadata->>'whatsapp_message_id' = :message_id
                                                AND m.role = 'assistant'
                                                AND c.user_id = :recipient_id
                                                ORDER BY m.created_at DESC
                                                LIMIT 1
                                            """)
                                            result = db.execute(query_check_bot, {
                                                "message_id": status_message_id,
                                                "recipient_id": recipient_id
                                            })
                                            mensagem_assistente = result.fetchone()
                                            
                                            if mensagem_assistente:
                                                # Encontrou mensagem do assistente com esse message_id = foi o chatbot
                                                foi_chatbot = True
                                            else:
                                                # NÃO encontrou no banco = foi HUMANO que enviou pelo WhatsApp
                                                foi_chatbot = False
                                        except Exception as e:
                                            logger.warning(f"⚠️ Erro ao verificar se foi chatbot pelo message_id: {e}", exc_info=True)
                                            # Em caso de erro, assume que foi humano (mais seguro)
                                            foi_chatbot = False
                                    else:
                                        # Sem message_id = assume que foi humano
                                        foi_chatbot = False
                                    
                                    # PAUSA se NÃO foi o chatbot que enviou
                                    if not foi_chatbot:
                                        empresa_id_int = int(empresa_id) if empresa_id else None
                                        _log_whatsapp_out(
                                            sender="humano",
                                            recipient=str(recipient_id),
                                            empresa_id=empresa_id_int,
                                            body={
                                                "whatsapp_message_id": status_message_id,
                                                "status": status_type,
                                                "message": "[Mensagem enviada pelo atendente via WhatsApp]",
                                                "source": "whatsapp_status",
                                            },
                                        )
                                        
                                        # SALVA A MENSAGEM NO BANCO quando atendente envia pelo WhatsApp
                                        try:
                                            # Busca ou cria conversa para salvar a mensagem
                                            conversations = chatbot_db.get_conversations_by_user(db, recipient_id, empresa_id=empresa_id_int)
                                            
                                            if not conversations:
                                                # Tenta buscar sem empresa_id também
                                                conversations = chatbot_db.get_conversations_by_user(db, recipient_id)
                                            
                                            conversation_id = None
                                            if conversations:
                                                conversation_id = conversations[0]['id']
                                                # Atualiza empresa_id_int se não tinha
                                                if not empresa_id_int:
                                                    empresa_id_int = conversations[0].get('empresa_id') or 1
                                            else:
                                                # Cria nova conversa se não existir
                                                from datetime import datetime as dt
                                                # Se não tem empresa_id, usa 1 como padrão
                                                empresa_id_final = empresa_id_int if empresa_id_int else 1
                                                # Garante prompt default
                                                prompt_key = "atendimento-pedido-whatsapp"
                                                if not chatbot_db.get_prompt(db, prompt_key, empresa_id=empresa_id_final):
                                                    chatbot_db.create_prompt(
                                                        db=db,
                                                        key=prompt_key,
                                                        name="Atendimento WhatsApp",
                                                        content="Atendimento via WhatsApp",
                                                        is_default=False,
                                                        empresa_id=empresa_id_final
                                                    )
                                                
                                                conversation_id = chatbot_db.create_conversation(
                                                    db=db,
                                                    session_id=f"whatsapp_{recipient_id}_{dt.now().strftime('%Y%m%d%H%M%S')}",
                                                    user_id=recipient_id,
                                                    prompt_key=prompt_key,
                                                    model="groq-sales",
                                                    empresa_id=empresa_id_final
                                                )
                                                empresa_id_int = empresa_id_final  # Atualiza para usar depois
                                            
                                            # Salva mensagem indicando que foi enviada pelo atendente
                                            # O webhook de status não traz o conteúdo, então salvamos uma referência
                                            mensagem_conteudo = "[Mensagem enviada pelo atendente via WhatsApp]"
                                            
                                            chatbot_db.create_message(
                                                db=db,
                                                conversation_id=conversation_id,
                                                role="assistant",
                                                content=mensagem_conteudo,
                                                whatsapp_message_id=status_message_id,
                                                extra_metadata={"sender": "human", "source": "whatsapp_status"},
                                            )
                                        except Exception as e:
                                            logger.warning(f"⚠️ Erro ao salvar mensagem do atendente no banco: {e}", exc_info=True)

                                        # Cancela a tentativa de pause se já estiver pausado
                                        if chatbot_db.is_bot_active_for_phone(db, recipient_id):
                                            destrava_em = chatbot_db.get_auto_pause_until()
                                            pause_result = chatbot_db.set_bot_status(
                                                db=db,
                                                phone_number=recipient_id,
                                                paused_by="atendente_respondeu",
                                                empresa_id=empresa_id_int,
                                                desativa_chatbot_em=destrava_em,
                                            )
                                            if not pause_result.get("success"):
                                                logger.error(
                                                    f"Falha ao pausar chatbot após envio pelo humano: {pause_result.get('error')}"
                                                )
                                except Exception as e:
                                    logger.error(f"❌ Erro ao processar status 'sent': {e}", exc_info=True)
                            
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
        # IMPORTANTE:
        # Há vários blocos dentro desta função que fazem `logger = logging.getLogger(__name__)`.
        # Além disso, há `import logging` dentro da função, o que torna `logging` uma variável LOCAL
        # no escopo inteiro da função em Python. Por isso, aqui usamos um alias para evitar
        # `UnboundLocalError` ao acessar `logging` antes desses imports internos.
        import logging as py_logging
        logger = py_logging.getLogger(__name__)

        empresa_id_int = int(empresa_id) if empresa_id else 1
        user_id = phone_number
        
        # VERIFICA SE É MENSAGEM DE ENTREGADOR/MOTOBOY - IGNORA
        # Quando motoboy envia mensagem para o estabelecimento, o chatbot deve ignorar
        try:
            from sqlalchemy import text
            # Normaliza o telefone para busca (remove caracteres não numéricos)
            phone_clean = ''.join(filter(str.isdigit, phone_number))
            # Tenta diferentes formatos de telefone
            phone_patterns = [
                phone_clean,
                phone_clean[2:] if len(phone_clean) > 11 and phone_clean.startswith('55') else None,  # Remove código do país
                f"%{phone_clean[-9:]}" if len(phone_clean) >= 9 else None,  # Últimos 9 dígitos
                f"%{phone_clean[-8:]}" if len(phone_clean) >= 8 else None,  # Últimos 8 dígitos
            ]
            phone_patterns = [p for p in phone_patterns if p]
            
            for pattern in phone_patterns:
                entregador_query = text("""
                    SELECT id, nome, telefone
                    FROM cadastros.entregadores_dv
                    WHERE telefone LIKE :pattern
                    LIMIT 1
                """)
                result = db.execute(entregador_query, {"pattern": pattern})
                entregador = result.fetchone()
                
                if entregador:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"🚫 Mensagem de entregador ignorada - ID: {entregador[0]}, Nome: {entregador[1]}, Telefone: {entregador[2]}")
                    # Ignora a mensagem - não processa
                    return
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao verificar se é entregador: {e}", exc_info=True)
            # Em caso de erro, continua o processamento normal (não bloqueia)
        
        # VERIFICA SE O BOT ESTÁ ATIVO PARA ESTE NÚMERO (ANTES de qualquer resposta/cadastro)
        # Motivo: quando o cliente NÃO tem cadastro, o fluxo de "cadastro rápido" retornava antes
        # da checagem de pausa e o bot acabava respondendo mesmo com o número pausado.
        if not chatbot_db.is_bot_active_for_phone(db, phone_number):
            # Log explícito: este é um "return silencioso" (não responde ao cliente).
            try:
                status_info = chatbot_db.get_bot_status(db, phone_number) or {}
            except Exception:
                status_info = {}
            logger.info(
                f"Bot pausado para o número (early-check) - phone={phone_number}, empresa_id={empresa_id_int}, status={status_info}"
            )

            # Mesmo pausado, ainda capturamos "chamar atendente" e notificamos o dashboard via WebSocket
            try:
                if _is_chamar_atendente_intent(message_text, button_id):
                    from datetime import datetime
                    from ..core.notifications import send_chatbot_websocket_notification

                    notification_data = {
                        "cliente_phone": phone_number,
                        "cliente_nome": contact_name,
                        "tipo": "chamar_atendente",
                        "timestamp": datetime.utcnow().isoformat(),
                        "bot_pausado": True,
                        "paused_by": (status_info or {}).get("paused_by"),
                        "chatbot_destrava_em": (status_info or {}).get("chatbot_destrava_em"),
                    }

                    title = "🔔 Solicitação de Atendimento Humano"
                    message_ws = (
                        f"Cliente {contact_name or phone_number} solicitou atendimento humano "
                        f"(bot está pausado).\n\n📱 Telefone: {phone_number}"
                    )
                    if contact_name:
                        message_ws += f"\n👤 Nome: {contact_name}"

                    sent_count = await send_chatbot_websocket_notification(
                        empresa_id=empresa_id_int,
                        notification_type="chamar_atendente",
                        title=title,
                        message=message_ws,
                        data=notification_data,
                    )

                    if sent_count > 0:
                        logger.info(
                            f"✅ Notificação WebSocket (chamar_atendente) enviada mesmo com bot pausado - "
                            f"empresa_id={empresa_id_int}, conexões={sent_count}, phone={phone_number}"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Nenhuma conexão WebSocket ativa ao notificar chamar_atendente (bot pausado) - "
                            f"empresa_id={empresa_id_int}, phone={phone_number}"
                        )
            except Exception as e_ws:
                logger.error(
                    f"❌ Erro ao enviar notificação WebSocket de chamar_atendente com bot pausado: {e_ws}",
                    exc_info=True,
                )

            # Salva a mensagem no histórico mesmo pausado (para auditoria/preview)
            try:
                conversations_paused = chatbot_db.get_conversations_by_user(db, user_id, empresa_id_int)
                if conversations_paused:
                    chatbot_db.create_message(
                        db=db,
                        conversation_id=conversations_paused[0]["id"],
                        role="user",
                        content=message_text,
                        whatsapp_message_id=message_id,
                    )
                    # Atualiza o nome do contato se disponível
                    if contact_name and not conversations_paused[0].get("contact_name"):
                        chatbot_db.update_conversation_contact_name(db, conversations_paused[0]["id"], contact_name)
                else:
                    conversation_id = chatbot_db.create_conversation(
                        db=db,
                        session_id=f"whatsapp_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        user_id=user_id,
                        prompt_key=PROMPT_ATENDIMENTO,
                        model=DEFAULT_MODEL,
                        contact_name=contact_name,
                        empresa_id=empresa_id_int,
                    )
                    chatbot_db.create_message(
                        db=db,
                        conversation_id=conversation_id,
                        role="user",
                        content=message_text,
                        whatsapp_message_id=message_id,
                    )
            except Exception as e_hist:
                logger.warning(f"⚠️ Falha ao salvar histórico com bot pausado: {e_hist}", exc_info=True)

            return  # Não responde, apenas registra/aciona WS

        
        # VERIFICA INTENÇÃO ANTES DO CADASTRO (usando agentes de IA)
        # Se detectar pedido de cardápio, responde direto sem pedir cadastro
        from ..core.intention_agents import IntentionRouter, IntentionType
        import unicodedata
        
        def normalizar_mensagem(texto: str) -> str:
            """Normaliza mensagem para comparação (lowercase, remove acentos)"""
            if not texto:
                return ""
            texto = texto.lower().strip()
            # Remove acentos
            texto = unicodedata.normalize('NFD', texto)
            texto = ''.join(char for char in texto if unicodedata.category(char) != 'Mn')
            return texto
        
        mensagem_normalizada = normalizar_mensagem(message_text)
        intention_router = IntentionRouter()
        intencao = intention_router.detect_intention(message_text, mensagem_normalizada)
        
        # Se detectou intenção de ver cardápio, responde direto sem pedir cadastro
        # Verifica tanto pelo enum quanto pela função retornada
        intencao_detectada = intencao and (
            intencao.get("intention") == IntentionType.VER_CARDAPIO or
            intencao.get("funcao") == "ver_cardapio"
        )
        
        if intencao_detectada:
            from datetime import datetime
            conversations = chatbot_db.get_conversations_by_user(db, user_id, empresa_id_int)
            
            # Cria conversa se não existir
            if not conversations:
                conversation_id = chatbot_db.create_conversation(
                    db=db,
                    session_id=f"whatsapp_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    user_id=user_id,
                    prompt_key="atendimento-pedido-whatsapp",
                    model="groq-sales",
                    empresa_id=empresa_id_int
                )
            else:
                conversation_id = conversations[0]['id']
            
            # Salva mensagem do usuário
            chatbot_db.create_message(db, conversation_id, "user", message_text, whatsapp_message_id=message_id)
            
            # Busca configuração do chatbot para usar mensagem personalizada se existir
            config = None
            try:
                config_repo = ChatbotConfigRepository(db)
                config = config_repo.get_by_empresa_id(empresa_id_int)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Erro ao buscar configuração do chatbot: {e}")
            
            # Monta resposta com link do cardápio
            resposta_cardapio = _montar_mensagem_redirecionamento(db, empresa_id_int, config)
            
            # Envia resposta via WhatsApp
            notifier = OrderNotification()
            result = await notifier.send_whatsapp_message(phone_number, resposta_cardapio, empresa_id=empresa_id)
            
            # Salva a mensagem do assistente
            if isinstance(result, dict) and result.get("success"):
                whatsapp_message_id = result.get("message_id")
                chatbot_db.create_message(db, conversation_id, "assistant", resposta_cardapio, whatsapp_message_id=whatsapp_message_id)
                db.commit()
            
            return

        # CONTEXTO BASE (precisa existir ANTES de qualquer fluxo que retorne)
        empresa_id_int = int(empresa_id) if empresa_id else 1
        user_id = phone_number
        conversations = chatbot_db.get_conversations_by_user(db, user_id, empresa_id_int)

        # DETECTA INTENÇÃO "ACOMPANHAR PEDIDO" (responde sem pedir cadastro)
        intencao_acompanhar = intencao and (
            intencao.get("intention") == IntentionType.ACOMPANHAR_PEDIDO or
            intencao.get("funcao") == "acompanhar_pedido"
        )
        if intencao_acompanhar:
            from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
            from datetime import datetime

            pedido_repo = PedidoRepository(db)

            # Cria conversa se não existir
            if conversations:
                conversation_id = conversations[0]['id']
            else:
                conversation_id = chatbot_db.create_conversation(
                    db=db,
                    session_id=f"whatsapp_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    user_id=user_id,
                    prompt_key=PROMPT_ATENDIMENTO_PEDIDO_WHATSAPP,
                    model="groq-sales",
                    contact_name=contact_name,
                    empresa_id=empresa_id_int
                )

            # Salva mensagem do usuário
            chatbot_db.create_message(db, conversation_id, "user", message_text, whatsapp_message_id=message_id)

            resposta = None
            try:
                cliente = pedido_repo.get_cliente(phone_number)
                if cliente:
                    pedidos_abertos = pedido_repo.list_abertos_by_cliente_id(cliente.id, empresa_id=empresa_id_int)
                    if pedidos_abertos:
                        pedido = pedidos_abertos[0]  # já ordenado por created_at.desc()
                        # Monta resumo simples dos itens
                        itens_lines = []
                        for it in getattr(pedido, "itens", [])[:10]:
                            nome = getattr(it, "produto_descricao_snapshot", None) or getattr(it, "produto_descricao_snapshot", "") or ""
                            qtd = int(getattr(it, "quantidade", 1) or 1)
                            itens_lines.append(f"{qtd}x {nome}")
                        itens_text = "\n".join(itens_lines) if itens_lines else "Sem itens registrados."
                        status_nome = pedido_repo._status_para_nome(pedido.status) if hasattr(pedido_repo, "_status_para_nome") else str(getattr(pedido, "status", ""))
                        total = getattr(pedido, "valor_total", 0) or 0
                        resposta = (
                            f"Encontrei {len(pedidos_abertos)} pedido(s) em aberto. Último pedido:\n"
                            f"Pedido: {getattr(pedido,'numero_pedido','-')}\n"
                            f"Status: {status_nome}\n"
                            f"Itens:\n{itens_text}\n"
                            f"Total: R$ {total}"
                        )
                    else:
                        resposta = "Não encontrei pedidos em aberto vinculados ao seu número."
                else:
                    resposta = "Não consegui localizar um cadastro para este número. Você pode me informar o nome ou o telefone cadastrado?"
            except Exception as e:
                logger.exception(f"Erro ao consultar pedidos para acompanhamento: {e}")
                resposta = "Desculpe, não foi possível consultar seus pedidos agora. Tente novamente mais tarde."

            notifier = OrderNotification()
            result = await notifier.send_whatsapp_message(phone_number, resposta, empresa_id=empresa_id)
            if isinstance(result, dict) and result.get("success"):
                whatsapp_message_id = result.get("message_id")
                chatbot_db.create_message(db, conversation_id, "assistant", resposta, whatsapp_message_id=whatsapp_message_id)
                db.commit()
            return

        # VERIFICA DUPLICAÇÃO: Usa message_id do WhatsApp (único por mensagem) para detectar duplicatas reais
        # Se não tiver message_id, usa verificação por conteúdo apenas para mensagens longas (>3 chars)
        # para evitar bloquear respostas curtas legítimas como "1", "sim", "ok"
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

        # CARREGA CONFIGURAÇÃO DO CHATBOT (para separar agentes)
        repo_config = ChatbotConfigRepository(db)
        config = repo_config.get_by_empresa_id(empresa_id_int)
        # Se config existe e aceita_pedidos_whatsapp é explicitamente False, então não aceita
        # Caso contrário (config None ou aceita_pedidos_whatsapp True/None), aceita por padrão
        aceita_pedidos_whatsapp = True  # Padrão: aceita pedidos
        # OBS: não use `is False` aqui; em alguns drivers/bancos o valor pode vir como 0/1.
        if config is not None and not config.aceita_pedidos_whatsapp:
            aceita_pedidos_whatsapp = False

        # Log para debug
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔧 Config chatbot - empresa_id: {empresa_id_int}, aceita_pedidos_whatsapp: {aceita_pedidos_whatsapp}, config existe: {config is not None}, config.aceita_pedidos_whatsapp: {config.aceita_pedidos_whatsapp if config else 'N/A'}")

        prompt_key_sales = PROMPT_ATENDIMENTO_PEDIDO_WHATSAPP
        prompt_key_support = PROMPT_ATENDIMENTO

        # DETECTA PERGUNTA "TÁ ABERTO?" (deve responder SEM pedir nome antes)
        def _eh_pergunta_aberto_fechado(txt: str) -> bool:
            import re

            s = (txt or "").strip().lower()
            if not s:
                return False
            # Padrões comuns no WhatsApp
            padroes = [
                r"\bta\s+aberto\b",
                r"\btá\s+aberto\b",
                r"\besta\s+aberto\b",
                r"\bestá\s+aberto\b",
                r"\bvoc[eê]s\s+tao\s+abertos\b",
                r"\bvoc[eê]s\s+t[aã]o\s+abertos\b",
                r"\bvoc[eê]s\s+est[aã]o\s+abertos\b",
                r"\best[aá]\s+aberto\s+agora\b",
                r"\baberto\s+agora\b",
                r"\best[aá]\s+fechado\b",
                r"\bta\s+fechado\b",
                r"\btá\s+fechado\b",
                r"\bfechado\s+agora\b",
            ]
            return any(re.search(p, s, re.IGNORECASE) for p in padroes)

        perguntou_aberto = _eh_pergunta_aberto_fechado(message_text)

        # VERIFICA SE A LOJA ESTÁ ABERTA (prioridade máxima, antes de cadastro)
        esta_aberta = None  # Variável para verificar depois se precisa enviar boas-vindas
        try:
            from app.api.empresas.models.empresa_model import EmpresaModel
            from app.utils.horarios_funcionamento import (
                empresa_esta_aberta_agora,
                montar_mensagem_status_funcionamento,
            )
            from datetime import datetime

            empresa = db.query(EmpresaModel).filter(EmpresaModel.id == empresa_id_int).first()
            nome_empresa = empresa.nome if empresa and empresa.nome else "[Nome da Empresa]"
            timezone_empresa = (empresa.timezone if empresa and getattr(empresa, "timezone", None) else None) or "America/Sao_Paulo"

            if empresa and empresa.horarios_funcionamento:
                esta_aberta = empresa_esta_aberta_agora(
                    horarios_funcionamento=empresa.horarios_funcionamento,
                    timezone=timezone_empresa
                )

            # Resposta curta e direta para "tá aberto?"
            if perguntou_aberto:
                prompt_key_em_uso = prompt_key_sales if aceita_pedidos_whatsapp else prompt_key_support
                model_em_uso = "groq-sales" if aceita_pedidos_whatsapp else DEFAULT_MODEL

                # Cria conversa se não existir
                if conversations:
                    conversation_id = conversations[0]['id']
                else:
                    conversation_id = chatbot_db.create_conversation(
                        db=db,
                        session_id=f"whatsapp_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        user_id=user_id,
                        prompt_key=prompt_key_em_uso,
                        model=model_em_uso,
                        contact_name=contact_name,
                        empresa_id=empresa_id_int
                    )

                chatbot_db.create_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="user",
                    content=message_text,
                    whatsapp_message_id=message_id,
                )

                msg_status = montar_mensagem_status_funcionamento(
                    nome_empresa=nome_empresa,
                    esta_aberta=esta_aberta,
                    horarios_funcionamento=getattr(empresa, "horarios_funcionamento", None),
                    timezone=timezone_empresa,
                    now=datetime.now(),
                    incluir_horarios=True,
                )

                notifier = OrderNotification()
                result = await notifier.send_whatsapp_message(phone_number, msg_status, empresa_id=empresa_id)

                whatsapp_message_id = None
                if isinstance(result, dict) and result.get("success"):
                    whatsapp_message_id = result.get("message_id")
                chatbot_db.create_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=msg_status,
                    whatsapp_message_id=whatsapp_message_id,
                )

                return

            # Se a loja estiver fechada, responde imediatamente e NÃO inicia cadastro
            if esta_aberta is False:
                prompt_key_em_uso = prompt_key_sales if aceita_pedidos_whatsapp else prompt_key_support
                model_em_uso = "groq-sales" if aceita_pedidos_whatsapp else DEFAULT_MODEL

                if conversations:
                    conversation_id = conversations[0]['id']
                else:
                    conversation_id = chatbot_db.create_conversation(
                        db=db,
                        session_id=f"whatsapp_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        user_id=user_id,
                        prompt_key=prompt_key_em_uso,
                        model=model_em_uso,
                        contact_name=contact_name,
                        empresa_id=empresa_id_int
                    )

                chatbot_db.create_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="user",
                    content=message_text,
                    whatsapp_message_id=message_id
                )

                msg_fechado = montar_mensagem_status_funcionamento(
                    nome_empresa=nome_empresa,
                    esta_aberta=False,
                    horarios_funcionamento=getattr(empresa, "horarios_funcionamento", None),
                    timezone=timezone_empresa,
                    now=datetime.now(),
                    incluir_horarios=True,
                )

                notifier = OrderNotification()
                result = await notifier.send_whatsapp_message(phone_number, msg_fechado, empresa_id=empresa_id)

                whatsapp_message_id = None
                if isinstance(result, dict) and result.get("success"):
                    whatsapp_message_id = result.get("message_id")
                chatbot_db.create_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=msg_fechado,
                    whatsapp_message_id=whatsapp_message_id,
                )

                if not isinstance(result, dict) or not result.get("success"):
                    error_msg = result.get("error") if isinstance(result, dict) else str(result)
                    logger.error(f"Erro ao enviar mensagem de horários: {error_msg}")

                return

        except Exception as e:
            logger.error(f"Erro ao verificar horário de funcionamento: {e}", exc_info=True)
            # Continua processando normalmente em caso de erro

        # VERIFICA SE CLIENTE JÁ ESTÁ CADASTRADO
        from ..core.address_service import ChatbotAddressService
        address_service = ChatbotAddressService(db, empresa_id_int)
        cliente = address_service.get_cliente_by_telefone(phone_number)
        cliente_id = None
        precisa_cadastrar = False
        
        if cliente:
            cliente_id = cliente.get('id')
            nome_cliente = cliente.get('nome', '')
            # Se cliente existe mas tem nome genérico, precisa cadastrar nome
            if nome_cliente in ['Cliente WhatsApp', 'Cliente', ''] or len(nome_cliente.split()) < 2:
                precisa_cadastrar = True
        else:
            # Cliente não existe - precisa cadastrar
            precisa_cadastrar = True
        
        # Se precisa cadastrar, verifica se já está aguardando nome
        if precisa_cadastrar:
            conversations = chatbot_db.get_conversations_by_user(db, user_id, empresa_id_int)
            
            # Verifica se já está no estado de cadastro de nome
            estado_atual = None
            if conversations:
                from sqlalchemy import text
                estado_query = text("""
                    SELECT metadata->>'sales_state' as estado
                    FROM chatbot.conversations
                    WHERE id = :conversation_id
                    LIMIT 1
                """)
                try:
                    result = db.execute(estado_query, {"conversation_id": conversations[0]['id']})
                    row = result.fetchone()
                    if row and row[0]:
                        estado_atual = row[0]
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Erro ao verificar estado de cadastro: {e}")
            
            # Em vez de pedir o nome, cadastra o cliente automaticamente com nome NULL (sem bloqueio)
            # e cria a conversa/registro da mensagem para continuar o fluxo normalmente.
            try:
                # Garante que exista um cliente (nome ficará NULL)
                cliente_criado = address_service.criar_cliente_se_nao_existe(phone_number, nome=None)
                if cliente_criado:
                    cliente_id = cliente_criado.get("id")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Erro ao criar cliente automaticamente: {e}", exc_info=True)

            # Cria conversa se não existir
            from datetime import datetime
            if not conversations:
                conversation_id = chatbot_db.create_conversation(
                    db=db,
                    session_id=f"whatsapp_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    user_id=user_id,
                    prompt_key="atendimento-pedido-whatsapp",
                    model="groq-sales",
                    empresa_id=empresa_id_int
                )
            else:
                conversation_id = conversations[0]['id']

            # Salva a mensagem do usuário imediatamente
            try:
                chatbot_db.create_message(db, conversation_id, "user", message_text, whatsapp_message_id=message_id)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Erro ao salvar mensagem do usuário após cadastro automático: {e}", exc_info=True)
            # Continua o processamento normal (não retorna aqui) para que o fluxo de IA
            # processe a mensagem como de costume.

        # VERIFICA PEDIDOS EM ABERTO para este cliente
        pedido_aberto = None
        if cliente_id:
            try:
                from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
                pedido_repo = PedidoRepository(db)
                pedidos_abertos = pedido_repo.list_abertos_by_cliente_id(
                    cliente_id=cliente_id,
                    empresa_id=empresa_id_int
                )
                if pedidos_abertos:
                    # Pega o pedido mais recente
                    pedido_aberto = pedidos_abertos[0]
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"📦 Pedido em aberto encontrado para cliente {cliente_id}: pedido_id={pedido_aberto.id}, numero_pedido={pedido_aberto.numero_pedido}, status={pedido_aberto.status}")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Erro ao verificar pedidos em aberto: {e}", exc_info=True)


        # VERIFICA SE O BOT ESTÁ ATIVO PARA ESTE NÚMERO
        if not chatbot_db.is_bot_active_for_phone(db, phone_number):
            # Log explícito: este é um "return silencioso" (não responde ao cliente).
            try:
                status_info = chatbot_db.get_bot_status(db, phone_number) or {}
            except Exception:
                status_info = {}
            logger.debug(
                f"Bot pausado para o número - phone={phone_number}, empresa_id={empresa_id_int}, status={status_info}"
            )
            # IMPORTANTE: Mesmo pausado, ainda queremos capturar a intenção "chamar atendente"
            # (ex: clique no botão "chamar_atendente") e notificar o dashboard via WebSocket.
            try:
                mensagem_lower = (message_text or "").lower().strip()
                chamou_atendente = (
                    button_id == "chamar_atendente"
                    or mensagem_lower == "chamar_atendente"
                    or "chamar_atendente" in mensagem_lower
                    or mensagem_lower == "chamar atendente"
                    or "chamar atendente" in mensagem_lower
                    or "chamar um atendente" in mensagem_lower
                )

                if chamou_atendente:
                    from datetime import datetime
                    from ..core.notifications import send_chatbot_websocket_notification

                    notification_data = {
                        "cliente_phone": phone_number,
                        "cliente_nome": contact_name,
                        "tipo": "chamar_atendente",
                        "timestamp": datetime.utcnow().isoformat(),
                        "bot_pausado": True,
                        "paused_by": (status_info or {}).get("paused_by"),
                        "chatbot_destrava_em": (status_info or {}).get("chatbot_destrava_em"),
                    }

                    title = "🔔 Solicitação de Atendimento Humano"
                    message_ws = (
                        f"Cliente {contact_name or phone_number} solicitou atendimento humano "
                        f"(bot está pausado).\n\n📱 Telefone: {phone_number}"
                    )
                    if contact_name:
                        message_ws += f"\n👤 Nome: {contact_name}"

                    sent_count = await send_chatbot_websocket_notification(
                        empresa_id=empresa_id_int,
                        notification_type="chamar_atendente",
                        title=title,
                        message=message_ws,
                        data=notification_data,
                    )

                    if sent_count > 0:
                        logger.info(
                            f"✅ Notificação WebSocket (chamar_atendente) enviada mesmo com bot pausado - "
                            f"empresa_id={empresa_id_int}, conexões={sent_count}, phone={phone_number}"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Nenhuma conexão WebSocket ativa ao notificar chamar_atendente (bot pausado) - "
                            f"empresa_id={empresa_id_int}, phone={phone_number}"
                        )
            except Exception as e_ws:
                logger.error(
                    f"❌ Erro ao enviar notificação WebSocket de chamar_atendente com bot pausado: {e_ws}",
                    exc_info=True,
                )
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
                prompt_key_em_uso = prompt_key_sales if aceita_pedidos_whatsapp else prompt_key_support
                model_em_uso = "groq-sales" if aceita_pedidos_whatsapp else DEFAULT_MODEL
                conversation_id = chatbot_db.create_conversation(
                    db=db,
                    session_id=f"whatsapp_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    user_id=user_id,
                    prompt_key=prompt_key_em_uso,
                    model=model_em_uso,
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
        USE_SALES_HANDLER = aceita_pedidos_whatsapp  # Só usa vendas se permitido

        # Intenções simples para roteamento rápido
        is_saudacao = _is_saudacao_intent(message_text)

        # Prioridade: "chamar atendente" deve ser tratado mesmo com pedidos via WhatsApp desativados
        if _is_chamar_atendente_intent(message_text, button_id):
            await _enviar_notificacao_empresa(
                db=db,
                empresa_id=empresa_id,
                empresa_id_int=empresa_id_int,
                cliente_phone=phone_number,
                cliente_nome=contact_name,
                tipo_solicitacao="chamar_atendente",
            )

            # PAUSA O CHATBOT PARA ESTE CLIENTE (por conta própria - 3 horas)
            try:
                if chatbot_db.is_bot_active_for_phone(db, phone_number):
                    destrava_em = chatbot_db.get_auto_pause_until()
                    chatbot_db.set_bot_status(
                        db=db,
                        phone_number=phone_number,
                        paused_by="cliente_chamou_atendente",
                        empresa_id=empresa_id_int,
                        desativa_chatbot_em=destrava_em,
                    )
            except Exception as e:
                logger.error(f"❌ Erro ao pausar chatbot (chamar_atendente): {e}", exc_info=True)

            resposta = (
                "✅ *Solicitação enviada!*\n\n"
                "Nossa equipe foi notificada e entrará em contato com você em breve.\n\n"
                "Enquanto isso, posso te ajudar com alguma dúvida? 😊"
            )
            await _send_whatsapp_and_log(
                db=db,
                phone_number=phone_number,
                contact_name=contact_name,
                empresa_id=empresa_id,
                empresa_id_int=empresa_id_int,
                user_message=message_text,
                response_message=resposta,
                prompt_key=prompt_key_support,
                model=DEFAULT_MODEL,
                message_id=message_id,
                buttons=None,
            )
            return

        # Se não aceita pedidos pelo WhatsApp, uma saudação deve responder com o link/cardápio (sem cair em IA/vendas)
        if not aceita_pedidos_whatsapp and is_saudacao:
            resposta = _montar_mensagem_redirecionamento(db, empresa_id_int, config)
            buttons = [
                {"id": "chamar_atendente", "title": "Chamar um atendente"}
            ]
            await _send_whatsapp_and_log(
                db=db,
                phone_number=phone_number,
                contact_name=contact_name,
                empresa_id=empresa_id,
                empresa_id_int=empresa_id_int,
                user_message=message_text,
                response_message=resposta,
                prompt_key=prompt_key_support,
                model=DEFAULT_MODEL,
                message_id=message_id,
                buttons=buttons
            )
            return

        # Se não aceita pedidos pelo WhatsApp, intercepta tentativas de pedido
        is_pedido_intent = _is_pedido_intent(message_text)
        if not aceita_pedidos_whatsapp and (button_id == "pedir_whatsapp" or is_pedido_intent):
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🚫 Interceptando tentativa de pedido - aceita_pedidos_whatsapp: {aceita_pedidos_whatsapp}, button_id: {button_id}, is_pedido_intent: {is_pedido_intent}, mensagem: {message_text[:50]}")
            
            resposta = _montar_mensagem_redirecionamento(db, empresa_id_int, config)
            # Adiciona botões quando não aceita pedidos
            buttons = [
                {"id": "chamar_atendente", "title": "Chamar um atendente"}
            ]
            await _send_whatsapp_and_log(
                db=db,
                phone_number=phone_number,
                contact_name=contact_name,
                empresa_id=empresa_id,
                empresa_id_int=empresa_id_int,
                user_message=message_text,
                response_message=resposta,
                prompt_key=prompt_key_support,
                model=DEFAULT_MODEL,
                message_id=message_id,
                buttons=buttons
            )
            return

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
                    prompt_key=prompt_key_sales,
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

            # Se for nova sessão (sem histórico ou >16h) E a loja estiver aberta (ou horários não configurados) E a mensagem for uma saudação,
            # envia mensagem com botões.
            # Se esta_aberta for False, não envia boas-vindas (já foi enviada mensagem de horários).
            #
            # BUGFIX: evitar mandar "boas-vindas" indevidas após pausar/despausar (ou quando a empresa_id do webhook falha e cai no fallback),
            # situação em que `conversations` pode vir vazio para a empresa atual, mas o número já tem histórico no sistema.
            #
            # IMPORTANTE: Só envia boas-vindas se a mensagem for uma saudação, para evitar enviar boas-vindas quando
            # o usuário já está tentando fazer um pedido diretamente (ex: "Gostaria de fazer um pedido").
            #
            # Observação: não queremos bloquear o "boas-vindas" legítimo de "nova sessão após 16h";
            # só suprimimos quando NÃO encontramos conversa para a empresa atual (provável mismatch de empresa/telefone),
            # mas o número já tem histórico em alguma conversa.
            no_conversations_for_empresa = not conversations
            has_any_conversation_for_phone = bool(chatbot_db.get_conversations_by_user(db, user_id))
            should_suppress_welcome = no_conversations_for_empresa and has_any_conversation_for_phone
            if is_new_session and esta_aberta is not False and not should_suppress_welcome and is_saudacao:
                # IMPORTANTE: Salva a mensagem do usuário ANTES de enviar boas-vindas
                chatbot_db.create_message(db, conversation_id, "user", message_text, whatsapp_message_id=message_id)
                
                # Mensagem "antiga" de boas-vindas (com nome/link) + botões
                handler = GroqSalesHandler(db, empresa_id_int, prompt_key=prompt_key_sales)
                mensagem_boas_vindas = handler._gerar_mensagem_boas_vindas_conversacional()
                
                # Define os botões
                buttons = []
                if aceita_pedidos_whatsapp:
                    buttons.append({"id": "pedir_whatsapp", "title": "Pedir pelo WhatsApp"})
                buttons.append({"id": "pedir_link", "title": "Pedir pelo link"})
                buttons.append({"id": "chamar_atendente", "title": "Chamar um atendente"})
                
                # Envia mensagem com botões (WhatsApp exige um corpo de texto)
                notifier = OrderNotification()
                result = await notifier.send_whatsapp_message_with_buttons(
                    phone_number, 
                    mensagem_boas_vindas,
                    buttons, 
                    empresa_id=empresa_id
                )
                
                if isinstance(result, dict) and result.get("success"):
                    # Salva o message_id retornado pelo WhatsApp na mensagem do assistente
                    whatsapp_message_id = result.get("message_id")
                    chatbot_db.create_message(db, conversation_id, "assistant", mensagem_boas_vindas, whatsapp_message_id=whatsapp_message_id)
                    return  # Não processa a mensagem do usuário ainda, aguarda clique no botão
                else:
                    logger.error(f"Erro ao enviar mensagem com botões: {result.get('error') if isinstance(result, dict) else result}")

            # Detecta se a mensagem é uma resposta de botão
            # O WhatsApp pode enviar o ID do botão diretamente ou o texto do botão
            mensagem_lower = (message_text or "").lower().strip()
            botao_clicado = None
            
            # Log para debug
            logger.debug(f"Verificando botão - button_id={button_id}, message_text='{message_text}', mensagem_lower='{mensagem_lower}'")
            
            # Primeiro verifica se veio o button_id diretamente do webhook
            if button_id:
                botao_clicado = button_id
                logger.debug(f"Botão detectado via button_id: {botao_clicado}")
            # Se não, verifica pelo texto da mensagem
            elif "pedir pelo whatsapp" in mensagem_lower or mensagem_lower == "pedir pelo whatsapp":
                botao_clicado = "pedir_whatsapp"
                logger.debug(f"Botão detectado via texto: {botao_clicado}")
            elif "pedir pelo link" in mensagem_lower or mensagem_lower == "pedir pelo link":
                botao_clicado = "pedir_link"
                logger.debug(f"Botão detectado via texto: {botao_clicado}")
            elif (
                mensagem_lower == "chamar_atendente"
                or "chamar_atendente" in mensagem_lower
                or "chamar atendente" in mensagem_lower
                or mensagem_lower == "chamar atendente"
                or "chamar um atendente" in mensagem_lower
            ):
                botao_clicado = "chamar_atendente"
                logger.debug(f"Botão detectado via texto: {botao_clicado}")
            
            # Se for clique em botão, processa a resposta
            if botao_clicado:
                logger.debug(f"Botão clicado: {botao_clicado}")
                if botao_clicado == "pedir_whatsapp":
                    # VERIFICA SE ACEITA PEDIDOS PELO WHATSAPP
                    if config and not config.aceita_pedidos_whatsapp:
                        # Não aceita pedidos - redireciona para cardápio
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
                        
                        if config.mensagem_redirecionamento:
                            resposta = config.mensagem_redirecionamento.replace("{link_cardapio}", link_cardapio)
                        else:
                            resposta = f"📲 Para fazer seu pedido, acesse nosso cardápio completo pelo link:\n\n👉 {link_cardapio}\n\nDepois é só fazer seu pedido pelo site! 😊"
                    else:
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
                elif botao_clicado == "chamar_atendente":
                    # Cliente quer chamar atendente humano
                    # Envia notificação para a empresa
                    await _enviar_notificacao_empresa(
                        db=db,
                        empresa_id=empresa_id,
                        empresa_id_int=empresa_id_int,
                        cliente_phone=phone_number,
                        cliente_nome=contact_name,
                        tipo_solicitacao="chamar_atendente"
                    )
                    
                    # PAUSA O CHATBOT PARA ESTE CLIENTE (por conta própria - 3 horas)
                    try:
                        # Evita re-pausar quando já está pausado
                        if chatbot_db.is_bot_active_for_phone(db, phone_number):
                            destrava_em = chatbot_db.get_auto_pause_until()
                            chatbot_db.set_bot_status(
                                db=db,
                                phone_number=phone_number,
                                paused_by="cliente_chamou_atendente",
                                empresa_id=empresa_id_int,
                                desativa_chatbot_em=destrava_em,
                            )
                    except Exception as e:
                        logger.error(f"❌ Erro ao pausar chatbot: {e}", exc_info=True)
                    
                    resposta = "✅ *Solicitação enviada!*\n\nNossa equipe foi notificada e entrará em contato com você em breve.\n\nEnquanto isso, posso te ajudar com alguma dúvida? 😊"
                
                # IMPORTANTE: Salva a mensagem do usuário ANTES de enviar a resposta.
                # Motivo: se o envio falhar (ex.: janela de 24h / re-engagement), ainda assim queremos
                # registrar o inbound no histórico.
                try:
                    chatbot_db.create_message(
                        db=db,
                        conversation_id=conversation_id,
                        role="user",
                        content=message_text,
                        whatsapp_message_id=message_id,
                    )
                except Exception as e:
                    # Se já foi salva (duplicata), ignora e continua.
                    logger.warning(f"⚠️ Mensagem do usuário pode já ter sido salva (botão): {e}")

                # Envia a resposta
                notifier = OrderNotification()
                result = await notifier.send_whatsapp_message(phone_number, resposta, empresa_id=empresa_id)
                
                if isinstance(result, dict) and result.get("success"):
                    # Salva o message_id retornado pelo WhatsApp na mensagem do assistente
                    whatsapp_response_message_id = result.get("message_id")
                    chatbot_db.create_message(db, conversation_id, "assistant", resposta, whatsapp_message_id=whatsapp_response_message_id)
                
                # Se foi "pedir pelo whatsapp", continua o fluxo normalmente na próxima mensagem
                return

            # IMPORTANTE: Verifica novamente se a loja está fechada antes de processar
            # (pode ser que a conversa já exista, mas a loja fechou depois)
            if esta_aberta is False:
                return  # Não processa mensagem quando loja está fechada
            
            # IMPORTANTE: Verifica novamente se é "chamar atendente" antes de processar pela IA
            # Isso garante que mesmo se a detecção anterior falhar, não processe como busca de produto
            mensagem_lower_check = (message_text or "").lower().strip()
            is_chamar_atendente = (
                button_id == "chamar_atendente"
                or mensagem_lower_check == "chamar_atendente"
                or "chamar_atendente" in mensagem_lower_check
                or mensagem_lower_check == "chamar atendente"
                or mensagem_lower_check == "chamar um atendente"
                or "chamar atendente" in mensagem_lower_check
                or "chamar um atendente" in mensagem_lower_check
            )
            
            if is_chamar_atendente:
                # Cliente quer chamar atendente humano - processa diretamente sem passar pela IA
                logger.debug(f"Detectado 'chamar atendente' antes do processamento IA - button_id={button_id}, message_text={message_text}")
                await _enviar_notificacao_empresa(
                    db=db,
                    empresa_id=empresa_id,
                    empresa_id_int=empresa_id_int,
                    cliente_phone=phone_number,
                    cliente_nome=contact_name,
                    tipo_solicitacao="chamar_atendente"
                )
                
                # PAUSA O CHATBOT PARA ESTE CLIENTE (por conta própria - 3 horas)
                try:
                    # Evita re-pausar quando já está pausado
                    if chatbot_db.is_bot_active_for_phone(db, phone_number):
                        destrava_em = chatbot_db.get_auto_pause_until()
                        chatbot_db.set_bot_status(
                            db=db,
                            phone_number=phone_number,
                            paused_by="cliente_chamou_atendente",
                            empresa_id=empresa_id_int,
                            desativa_chatbot_em=destrava_em,
                        )
                except Exception as e:
                    logger.error(f"❌ Erro ao pausar chatbot: {e}", exc_info=True)
                
                resposta = "✅ *Solicitação enviada!*\n\nNossa equipe foi notificada e entrará em contato com você em breve.\n\nEnquanto isso, posso te ajudar com alguma dúvida? 😊"
                
                # IMPORTANTE: Salva a mensagem do usuário ANTES de enviar a resposta.
                # Motivo: se o envio falhar (ex.: janela de 24h / re-engagement), ainda assim queremos
                # registrar o inbound no histórico.
                try:
                    chatbot_db.create_message(
                        db=db,
                        conversation_id=conversation_id,
                        role="user",
                        content=message_text,
                        whatsapp_message_id=message_id,
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Mensagem do usuário pode já ter sido salva (chamar_atendente): {e}")

                # Envia a resposta
                notifier = OrderNotification()
                result = await notifier.send_whatsapp_message(phone_number, resposta, empresa_id=empresa_id)
                
                if isinstance(result, dict) and result.get("success"):
                    whatsapp_response_message_id = result.get("message_id")
                    chatbot_db.create_message(db, conversation_id, "assistant", resposta, whatsapp_message_id=whatsapp_response_message_id)
                
                return  # Não processa pela IA
            
            # IMPORTANTE: Salva a mensagem do usuário ANTES de processar (garante que sempre será salva)
            # A função processar_mensagem_groq também salva, mas garantir aqui evita perdas em caso de erro
            try:
                chatbot_db.create_message(db, conversation_id, "user", message_text, whatsapp_message_id=message_id)
            except Exception as e:
                # Se já foi salva (duplicata), ignora o erro e continua
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"⚠️ Mensagem do usuário pode já ter sido salva: {e}")
            
            # Processa com o sistema de vendas usando Groq/LLaMA
            # Passa informações sobre pedido em aberto se houver
            pedido_aberto_info = None
            if pedido_aberto:
                # Busca o pedido completo com itens para exibir na mensagem
                from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
                pedido_repo = PedidoRepository(db)
                pedido_completo = pedido_repo.get_pedido(pedido_aberto.id)
                
                # Formata itens do pedido
                itens_formatados = []
                if pedido_completo and pedido_completo.itens:
                    for item in pedido_completo.itens:
                        # Usa o método get_descricao_item() para obter o nome do item
                        try:
                            if hasattr(item, 'get_descricao_item'):
                                nome_item = item.get_descricao_item()
                            elif hasattr(item, 'produto_descricao_snapshot') and item.produto_descricao_snapshot:
                                nome_item = item.produto_descricao_snapshot
                            elif hasattr(item, 'produto') and item.produto:
                                nome_item = getattr(item.produto, 'descricao', None) or getattr(item.produto, 'nome', None) or "Produto"
                            elif hasattr(item, 'combo') and item.combo:
                                nome_item = getattr(item.combo, 'descricao', None) or getattr(item.combo, 'titulo', None) or "Combo"
                            elif hasattr(item, 'receita') and item.receita:
                                nome_item = getattr(item.receita, 'descricao', None) or getattr(item.receita, 'nome', None) or "Receita"
                            elif hasattr(item, 'produto_cod_barras') and item.produto_cod_barras:
                                nome_item = item.produto_cod_barras
                            else:
                                nome_item = "Item"
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Erro ao obter nome do item: {e}", exc_info=True)
                            nome_item = "Item"
                        quantidade = item.quantidade or 1
                        preco_unit = float(item.preco_unitario) if item.preco_unitario else 0.0
                        preco_total = float(item.preco_total) if item.preco_total else (preco_unit * quantidade)
                        itens_formatados.append({
                            "nome": nome_item,
                            "quantidade": quantidade,
                            "preco_unitario": preco_unit,
                            "preco_total": preco_total
                        })
                
                # Formata endereço se for delivery
                endereco_formatado = None
                tipo_entrega_str = pedido_aberto.tipo_entrega.value if hasattr(pedido_aberto.tipo_entrega, 'value') else str(pedido_aberto.tipo_entrega)
                if tipo_entrega_str == "DELIVERY":
                    if pedido_completo and pedido_completo.endereco:
                        end = pedido_completo.endereco
                        endereco_formatado = {
                            "rua": end.logradouro or "",
                            "numero": end.numero or "",
                            "complemento": end.complemento or "",
                            "bairro": end.bairro or "",
                            "cidade": end.cidade or "",
                            "cep": end.cep or ""
                        }
                    elif pedido_completo and pedido_completo.endereco_snapshot:
                        # Usa snapshot se endereço não estiver carregado
                        snap = pedido_completo.endereco_snapshot
                        if isinstance(snap, dict):
                            # Tenta logradouro primeiro, depois rua (compatibilidade)
                            endereco_formatado = {
                                "rua": snap.get("logradouro") or snap.get("rua", ""),
                                "numero": snap.get("numero", ""),
                                "complemento": snap.get("complemento", ""),
                                "bairro": snap.get("bairro", ""),
                                "cidade": snap.get("cidade", ""),
                                "cep": snap.get("cep", "")
                            }
                
                # Formata meio de pagamento
                meio_pagamento_nome = None
                if pedido_completo and pedido_completo.meio_pagamento:
                    meio_pagamento_nome = pedido_completo.meio_pagamento.nome
                
                pedido_aberto_info = {
                    "pedido_id": pedido_aberto.id,
                    "numero_pedido": pedido_aberto.numero_pedido,
                    "status": pedido_aberto.status,
                    "valor_total": float(pedido_aberto.valor_total) if pedido_aberto.valor_total else 0.0,
                    "subtotal": float(pedido_aberto.subtotal) if pedido_aberto.subtotal else 0.0,
                    "taxa_entrega": float(pedido_aberto.taxa_entrega) if pedido_aberto.taxa_entrega else 0.0,
                    "desconto": float(pedido_aberto.desconto) if pedido_aberto.desconto else 0.0,
                    "tipo_entrega": tipo_entrega_str,
                    "created_at": pedido_aberto.created_at.isoformat() if pedido_aberto.created_at else None,
                    "itens": itens_formatados,
                    "endereco": endereco_formatado,
                    "meio_pagamento": meio_pagamento_nome,
                    "mesa_codigo": pedido_completo.mesa.codigo if (pedido_completo and pedido_completo.mesa and hasattr(pedido_completo.mesa, 'codigo')) else None
                }
            
            resposta = await processar_mensagem_groq(
                db=db,
                user_id=phone_number,
                mensagem=message_text,
                empresa_id=int(empresa_id) if empresa_id else 1,
                emit_welcome_message=is_saudacao,
                prompt_key=prompt_key_sales,
                pedido_aberto=pedido_aberto_info
            )
            
            # Se vier vazio, tenta novamente permitindo boas-vindas (mantém "inteligência", sem fallback hardcoded).
            if not resposta or not str(resposta).strip():
                resposta = await processar_mensagem_groq(
                    db=db,
                    user_id=phone_number,
                    mensagem=message_text,
                    empresa_id=int(empresa_id) if empresa_id else 1,
                    emit_welcome_message=True,
                    prompt_key=prompt_key_sales
                )
                if not resposta or not str(resposta).strip():
                    return

            # Se não aceita pedidos, verifica se a resposta é de redirecionamento e adiciona botões
            buttons = None
            if not aceita_pedidos_whatsapp:
                # Verifica se a resposta contém palavras-chave de redirecionamento
                resposta_lower = resposta.lower()
                palavras_redirecionamento = ["link", "cardápio", "cardapio", "acesse", "site", "online"]
                if any(palavra in resposta_lower for palavra in palavras_redirecionamento):
                    buttons = [
                        {"id": "chamar_atendente", "title": "Chamar um atendente"}
                    ]

            # Envia resposta via WhatsApp
            # Garante que OrderNotificatio está disponível no escopo
            notifier = OrderNotification()
            if buttons:
                result = await notifier.send_whatsapp_message_with_buttons(
                    phone_number, 
                    resposta, 
                    buttons, 
                    empresa_id=empresa_id
                )
            else:
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
            # Garante prompt de atendimento quando pedidos no WhatsApp estão desativados
            if conversation.get('prompt_key') != prompt_key_support:
                update_prompt_query = text("""
                    UPDATE chatbot.conversations
                    SET prompt_key = :prompt_key, updated_at = CURRENT_TIMESTAMP
                    WHERE id = :conversation_id
                """)
                db.execute(update_prompt_query, {
                    "prompt_key": prompt_key_support,
                    "conversation_id": conversation_id
                })
                db.commit()
        else:
            # Cria nova conversa
            empresa_id_int = int(empresa_id) if empresa_id else 1
            conversation_id = chatbot_db.create_conversation(
                db=db,
                session_id=f"whatsapp_{phone_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                user_id=user_id,
                prompt_key=prompt_key_support,
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

        # 2.4. Prioridade absoluta: chamar atendente (não deve cair em redirecionamento/IA)
        # Nota: aqui a mensagem do usuário JÁ foi salva acima, então NÃO podemos reutilizar
        # `_send_whatsapp_and_log` (ele salvaria a mensagem do usuário de novo e pode gerar duplicata).
        if _is_chamar_atendente_intent(message_text, button_id):
            await _enviar_notificacao_empresa(
                db=db,
                empresa_id=empresa_id,
                empresa_id_int=empresa_id_int,
                cliente_phone=phone_number,
                cliente_nome=contact_name,
                tipo_solicitacao="chamar_atendente",
            )
            try:
                if chatbot_db.is_bot_active_for_phone(db, phone_number):
                    destrava_em = chatbot_db.get_auto_pause_until()
                    chatbot_db.set_bot_status(
                        db=db,
                        phone_number=phone_number,
                        paused_by="cliente_chamou_atendente",
                        empresa_id=empresa_id_int,
                        desativa_chatbot_em=destrava_em,
                    )
            except Exception as e:
                logger.error(f"❌ Erro ao pausar chatbot (chamar_atendente - fluxo antigo): {e}", exc_info=True)

            resposta = (
                "✅ *Solicitação enviada!*\n\n"
                "Nossa equipe foi notificada e entrará em contato com você em breve.\n\n"
                "Enquanto isso, posso te ajudar com alguma dúvida? 😊"
            )
            notifier = OrderNotification()
            result = await notifier.send_whatsapp_message(phone_number, resposta, empresa_id=empresa_id)

            whatsapp_response_message_id = (
                result.get("message_id") if isinstance(result, dict) and result.get("success") else None
            )
            chatbot_db.create_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=resposta,
                whatsapp_message_id=whatsapp_response_message_id,
            )

            _log_whatsapp_out(
                sender="chatbot",
                recipient=phone_number,
                empresa_id=empresa_id,
                body={
                    "message": resposta,
                    "buttons": None,
                    "whatsapp_message_id": whatsapp_response_message_id,
                },
            )
            return

        # 2.5. VERIFICA SE NÃO ACEITA PEDIDOS E INTERCEPTA TENTATIVAS DE PEDIDO
        # (mesma verificação do fluxo principal para garantir consistência)
        is_pedido_intent = _is_pedido_intent(message_text)
        if not aceita_pedidos_whatsapp and (button_id == "pedir_whatsapp" or is_pedido_intent):
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🚫 [Fluxo Antigo] Interceptando tentativa de pedido - aceita_pedidos_whatsapp: {aceita_pedidos_whatsapp}, button_id: {button_id}, is_pedido_intent: {is_pedido_intent}, mensagem: {message_text[:50]}")
            
            resposta = _montar_mensagem_redirecionamento(db, empresa_id_int, config)
            # Adiciona botões quando não aceita pedidos
            buttons = [
                {"id": "chamar_atendente", "title": "Chamar um atendente"}
            ]
            await _send_whatsapp_and_log(
                db=db,
                phone_number=phone_number,
                contact_name=contact_name,
                empresa_id=empresa_id,
                empresa_id_int=empresa_id_int,
                user_message=message_text,
                response_message=resposta,
                prompt_key=prompt_key_support,
                model=DEFAULT_MODEL,
                message_id=message_id,
                buttons=buttons
            )
            return

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

        empresa_id_int = int(empresa_id) if empresa_id else 1

        # 5. Chama a IA
        # CRÍTICO: quando NÃO aceita pedidos no WhatsApp, NÃO pode usar o GroqSalesHandler (ele possui tool-calling
        # e pode acionar fluxo de checkout). Neste modo usamos apenas chat "texto puro".
        if not aceita_pedidos_whatsapp:
            if not GROQ_API_KEY:
                # Sem chave de LLM: fallback para redirecionamento (modo seguro)
                ai_response = _montar_mensagem_redirecionamento(db, empresa_id_int, config)
            else:
                try:
                    system_prompt = build_system_prompt(prompt_content or SYSTEM_PROMPT, require_json_object=False)
                    messages = [{"role": "system", "content": system_prompt}]
                    for msg in messages_history:
                        role = (msg.get("role") if isinstance(msg, dict) else None) or "user"
                        content = (msg.get("content") if isinstance(msg, dict) else None) or ""
                        if role in ("user", "assistant") and content:
                            messages.append({"role": role, "content": content})

                    async with httpx.AsyncClient(timeout=60.0) as client:
                        payload = {
                            "model": DEFAULT_MODEL or MODEL_NAME,
                            "messages": messages,
                            "stream": False,
                            "temperature": 0.2,
                            "top_p": 0.9,
                        }
                        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
                        response = await client.post(GROQ_API_URL, json=payload, headers=headers)
                        if response.status_code != 200:
                            raise HTTPException(status_code=response.status_code, detail=f"Erro na Groq: {response.text}")
                        result = response.json()
                        ai_response = result["choices"][0]["message"]["content"]
                except Exception:
                    # Falhou LLM: fallback para redirecionamento (modo seguro)
                    ai_response = _montar_mensagem_redirecionamento(db, empresa_id_int, config)

            if not ai_response or not str(ai_response).strip():
                return

            # 6. Envia resposta via WhatsApp
            notifier = OrderNotification()
            result = await notifier.send_whatsapp_message(phone_number, ai_response, empresa_id=empresa_id)

            # Salva resposta do bot JÁ com whatsapp_message_id para o webhook de status não pausar achando que foi humano.
            whatsapp_message_id = result.get("message_id") if isinstance(result, dict) and result.get("success") else None
            chatbot_db.create_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=ai_response,
                whatsapp_message_id=whatsapp_message_id,
            )
            return

        # Caso aceite pedidos, mantém o handler de vendas
        from ..core.groq_sales_handler import processar_mensagem_groq
        ai_response = await processar_mensagem_groq(
            db=db,
            user_id=phone_number,
            mensagem=message_text,
            empresa_id=empresa_id_int,
            emit_welcome_message=False,
            prompt_key=prompt_key
        )

        # Se vier vazio, tenta novamente permitindo boas-vindas (sem fallback fixo).
        if not ai_response or not str(ai_response).strip():
            ai_response = await processar_mensagem_groq(
                db=db,
                user_id=phone_number,
                mensagem=message_text,
                empresa_id=empresa_id_int,
                emit_welcome_message=True,
                prompt_key=prompt_key
            )
            if not ai_response or not str(ai_response).strip():
                return

        # 6. Envia resposta via WhatsApp
        notifier = OrderNotification()
        result = await notifier.send_whatsapp_message(phone_number, ai_response, empresa_id=empresa_id)

        # 6.1. Vincula o whatsapp_message_id à última resposta do bot salva no banco
        # Observação: `processar_mensagem_groq` já salva a resposta do assistente, porém sem o ID
        # retornado pelo WhatsApp. Aqui atualizamos o metadata para evitar duplicar mensagens.
        if isinstance(result, dict) and result.get("success") and result.get("message_id"):
            try:
                from sqlalchemy import text
                whatsapp_response_message_id = result.get("message_id")

                update_whatsapp_id_query = text("""
                    WITH target AS (
                        SELECT id
                        FROM chatbot.messages
                        WHERE conversation_id = :conversation_id
                          AND role = 'assistant'
                          AND content = :content
                          AND created_at > NOW() - INTERVAL '60 seconds'
                        ORDER BY created_at DESC
                        LIMIT 1
                    )
                    UPDATE chatbot.messages
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        '{whatsapp_message_id}',
                        to_jsonb(CAST(:whatsapp_message_id AS text)),
                        true
                    )
                    WHERE id IN (SELECT id FROM target)
                """)

                update_result = db.execute(update_whatsapp_id_query, {
                    "conversation_id": conversation_id,
                    "content": ai_response,
                    "whatsapp_message_id": whatsapp_response_message_id
                })
                db.commit()

                # Fallback: se não encontrou a mensagem recém-salva, cria uma com metadata
                if update_result.rowcount == 0:
                    chatbot_db.create_message(
                        db=db,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=ai_response,
                        whatsapp_message_id=whatsapp_response_message_id
                    )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Erro ao vincular whatsapp_message_id à resposta do bot: {e}", exc_info=True)

        if not isinstance(result, dict) or not result.get("success"):
            import logging
            logger = logging.getLogger(__name__)
            error_msg = result.get("error") if isinstance(result, dict) else str(result)
            status_code = result.get("status_code") if isinstance(result, dict) else None
            logger.error(f"Erro ao enviar resposta via WhatsApp: {error_msg} (status_code: {status_code})")

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

        logger.debug(f"[simulate] from={phone_number} body={message_text}")

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
                prompt_key=PROMPT_ATENDIMENTO_PEDIDO_WHATSAPP,
                model="llm-sales"
            )
            logger.debug(f"[simulate] conversa criada: {conversation_id}")

        # Importa e usa o Groq Sales Handler
        from ..core.groq_sales_handler import processar_mensagem_groq

        # Função de simulação usa empresa_id padrão (1) pois não vem de webhook
        resposta = await processar_mensagem_groq(
            db=db,
            user_id=phone_number,
            mensagem=message_text,
            empresa_id=1,
            prompt_key=PROMPT_ATENDIMENTO_PEDIDO_WHATSAPP
        )

        logger.debug(f"[simulate] resposta_preview={resposta[:100]}")

        return SimulateMessageResponse(
            success=True,
            response=resposta,
            phone_number=phone_number,
            message_sent=message_text
        )

    except Exception as e:
        logger.exception(f"[simulate] erro: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar mensagem: {str(e)}"
        )


# ==================== PEDIDOS DO CLIENTE ====================


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
        from sqlalchemy import text, bindparam
        from app.utils.telefone import (
            variantes_telefone_para_busca,
            normalizar_telefone_para_armazenar,
        )

        # Unificação BR: aceita com/sem 55 e com/sem 9 (celular) na busca,
        # mas mantém o telefone armazenado no formato canônico (55 + DDD + 9 dígitos quando aplicável).
        candidatos = variantes_telefone_para_busca(phone_number)
        if not candidatos:
            telefone_canon = normalizar_telefone_para_armazenar(phone_number)
            if telefone_canon:
                candidatos = [telefone_canon]

        if not candidatos:
            return {
                "success": False,
                "message": "Telefone inválido",
                "pedidos": [],
            }

        cliente_query = (
            text(
                """
                SELECT id, nome, telefone
                FROM cadastros.clientes
                WHERE telefone IN :telefones
                LIMIT 1
                """
            )
            .bindparams(bindparam("telefones", expanding=True))
        )
        cliente = db.execute(cliente_query, {"telefones": candidatos}).fetchone()

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
                EXISTS (
                    SELECT 1
                    FROM cardapio.transacoes_pagamento_dv tx
                    WHERE tx.pedido_id = p.id
                      AND tx.status IN ('PAGO', 'AUTORIZADO')
                ) AS pago,
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
        logger.exception(f"[pedidos-debug] erro ao buscar pedidos: {e}")
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
        from ..core.notifications import enviar_resumo_pedido_whatsapp
        
        result = await enviar_resumo_pedido_whatsapp(
            db=db,
            pedido_id=pedido_id,
            phone_number=phone_number
        )
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Erro ao enviar resumo")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao enviar resumo: {e}")
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
    from sqlalchemy import bindparam, text
    from app.utils.telefone import (
        normalizar_telefone_para_armazenar,
        variantes_telefone_para_busca,
    )

    # Unificação BR: sempre criar/usar cliente com telefone canônico (55 + DDD + 9 dígitos quando aplicável),
    # mas aceitar lookup com/sem o 9 e com/sem 55.
    phone_canon = normalizar_telefone_para_armazenar(phone_number)
    if not phone_canon:
        phone_canon = "".join(filter(str.isdigit, str(phone_number or "")))

    # Para nome de teste (sufixo), usamos os últimos 4 dígitos do número nacional (sem 55).
    phone_without_country = phone_canon[2:] if phone_canon.startswith("55") and len(phone_canon) > 2 else phone_canon

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
        candidatos = variantes_telefone_para_busca(phone_number) or [phone_canon]
        cliente_query = (
            text(
                """
                SELECT id, nome, telefone
                FROM cadastros.clientes
                WHERE telefone IN :telefones
                LIMIT 1
                """
            )
            .bindparams(bindparam("telefones", expanding=True))
        )
        cliente = db.execute(cliente_query, {"telefones": candidatos}).fetchone()

        if not cliente:
            # Criar cliente se não existir
            result = db.execute(text("""
                INSERT INTO cadastros.clientes (nome, telefone, created_at, updated_at)
                VALUES (:nome, :telefone, NOW(), NOW())
                RETURNING id, nome, telefone
            """), {"nome": f"Cliente Teste {phone_without_country[-4:]}", "telefone": phone_canon})
            cliente = result.fetchone()
            db.commit()
            logger.debug(f"[criar-pedidos-teste] cliente criado: id={cliente[0]} nome={cliente[1]}")

        cliente_id = cliente[0]
        logger.debug(f"[criar-pedidos-teste] usando cliente: id={cliente_id} nome={cliente[1]} tel={cliente[2]}")

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
        logger.exception(f"Erro ao criar pedidos de teste: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar pedidos de teste: {str(e)}"
        )
