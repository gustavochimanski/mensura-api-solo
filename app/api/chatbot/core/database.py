"""
Módulo de acesso ao banco de dados PostgreSQL para o Chatbot
Schema: chatbot
Suporte multi-empresa
Integrado com o sistema de DB do Mensura
"""
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import json
from datetime import datetime

# Schema do chatbot
CHATBOT_SCHEMA = "chatbot"


def init_database(db: Session):
    """Inicializa o schema e cria as tabelas do chatbot"""
    try:
        # Criar schema se não existir
        db.execute(text(f"CREATE SCHEMA IF NOT EXISTS {CHATBOT_SCHEMA}"))

        # Definir search_path para o schema
        db.execute(text(f"SET search_path TO {CHATBOT_SCHEMA}, public"))

        # Tabela de prompts
        db.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {CHATBOT_SCHEMA}.prompts (
                id SERIAL PRIMARY KEY,
                key VARCHAR(100) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                is_default BOOLEAN DEFAULT FALSE,
                empresa_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Tabela de conversas
        db.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {CHATBOT_SCHEMA}.conversations (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                prompt_key VARCHAR(100),
                model VARCHAR(100) NOT NULL,
                empresa_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prompt_key) REFERENCES {CHATBOT_SCHEMA}.prompts(key)
            )
        """))

        # Tabela de mensagens
        db.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {CHATBOT_SCHEMA}.messages (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER NOT NULL,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES {CHATBOT_SCHEMA}.conversations(id) ON DELETE CASCADE
            )
        """))

        # Índices para performance
        db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_conversations_session ON {CHATBOT_SCHEMA}.conversations(session_id)"))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_conversations_user ON {CHATBOT_SCHEMA}.conversations(user_id)"))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_conversations_empresa ON {CHATBOT_SCHEMA}.conversations(empresa_id)"))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_messages_conversation ON {CHATBOT_SCHEMA}.messages(conversation_id)"))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_prompts_key ON {CHATBOT_SCHEMA}.prompts(key)"))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_prompts_empresa ON {CHATBOT_SCHEMA}.prompts(empresa_id)"))

        db.commit()
        print("✅ Schema e tabelas do chatbot criadas no PostgreSQL!")
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao inicializar banco do chatbot: {e}")
        return False


# ==================== PROMPTS ====================

def create_prompt(db: Session, key: str, name: str, content: str, is_default: bool = False, empresa_id: Optional[int] = None) -> Optional[Dict]:
    """Cria um novo prompt"""
    try:
        query = text(f"""
            INSERT INTO {CHATBOT_SCHEMA}.prompts (key, name, content, is_default, empresa_id)
            VALUES (:key, :name, :content, :is_default, :empresa_id)
            RETURNING id, key, name, content, is_default, empresa_id
        """)
        result = db.execute(query, {
            "key": key,
            "name": name,
            "content": content,
            "is_default": is_default,
            "empresa_id": empresa_id
        })
        db.commit()
        row = result.fetchone()
        if row:
            return {
                "id": row[0],
                "key": row[1],
                "name": row[2],
                "content": row[3],
                "is_default": row[4],
                "empresa_id": row[5]
            }
        return None
    except Exception as e:
        db.rollback()
        print(f"Erro ao criar prompt: {e}")
        return None


def get_prompt(db: Session, key: str, empresa_id: Optional[int] = None) -> Optional[Dict]:
    """Busca um prompt pela chave"""
    query = text(f"""
        SELECT id, key, name, content, is_default, empresa_id, created_at, updated_at
        FROM {CHATBOT_SCHEMA}.prompts
        WHERE key = :key AND (empresa_id = :empresa_id OR empresa_id IS NULL OR :empresa_id IS NULL)
        ORDER BY empresa_id DESC NULLS LAST
        LIMIT 1
    """)
    result = db.execute(query, {"key": key, "empresa_id": empresa_id})
    row = result.fetchone()
    if row:
        return {
            "id": row[0],
            "key": row[1],
            "name": row[2],
            "content": row[3],
            "is_default": row[4],
            "empresa_id": row[5],
            "created_at": row[6],
            "updated_at": row[7]
        }
    return None


def get_all_prompts(db: Session, empresa_id: Optional[int] = None) -> List[Dict]:
    """Retorna todos os prompts"""
    if empresa_id:
        query = text(f"""
            SELECT id, key, name, content, is_default, empresa_id, created_at, updated_at
            FROM {CHATBOT_SCHEMA}.prompts
            WHERE empresa_id = :empresa_id OR empresa_id IS NULL
            ORDER BY is_default DESC, created_at DESC
        """)
        result = db.execute(query, {"empresa_id": empresa_id})
    else:
        query = text(f"""
            SELECT id, key, name, content, is_default, empresa_id, created_at, updated_at
            FROM {CHATBOT_SCHEMA}.prompts
            ORDER BY is_default DESC, created_at DESC
        """)
        result = db.execute(query)

    return [
        {
            "id": row[0],
            "key": row[1],
            "name": row[2],
            "content": row[3],
            "is_default": row[4],
            "empresa_id": row[5],
            "created_at": row[6],
            "updated_at": row[7]
        }
        for row in result.fetchall()
    ]


def update_prompt(db: Session, key: str, name: str, content: str, empresa_id: Optional[int] = None) -> bool:
    """Atualiza um prompt existente"""
    query = text(f"""
        UPDATE {CHATBOT_SCHEMA}.prompts
        SET name = :name, content = :content, updated_at = CURRENT_TIMESTAMP
        WHERE key = :key AND is_default = FALSE
        AND (empresa_id = :empresa_id OR (empresa_id IS NULL AND :empresa_id IS NULL))
    """)
    result = db.execute(query, {
        "name": name,
        "content": content,
        "key": key,
        "empresa_id": empresa_id
    })
    db.commit()
    return result.rowcount > 0


def delete_prompt(db: Session, key: str, empresa_id: Optional[int] = None) -> bool:
    """Deleta um prompt (apenas customizados)"""
    query = text(f"""
        DELETE FROM {CHATBOT_SCHEMA}.prompts
        WHERE key = :key AND is_default = FALSE
        AND (empresa_id = :empresa_id OR (empresa_id IS NULL AND :empresa_id IS NULL))
    """)
    result = db.execute(query, {"key": key, "empresa_id": empresa_id})
    db.commit()
    return result.rowcount > 0


# ==================== CONVERSAS ====================

def create_conversation(db: Session, session_id: str, user_id: str, prompt_key: str, model: str, empresa_id: Optional[int] = None) -> Optional[int]:
    """Cria uma nova conversa"""
    query = text(f"""
        INSERT INTO {CHATBOT_SCHEMA}.conversations (session_id, user_id, prompt_key, model, empresa_id)
        VALUES (:session_id, :user_id, :prompt_key, :model, :empresa_id)
        RETURNING id
    """)
    result = db.execute(query, {
        "session_id": session_id,
        "user_id": user_id,
        "prompt_key": prompt_key,
        "model": model,
        "empresa_id": empresa_id
    })
    db.commit()
    row = result.fetchone()
    return row[0] if row else None


def get_conversation(db: Session, conversation_id: int) -> Optional[Dict]:
    """Busca uma conversa pelo ID"""
    query = text(f"""
        SELECT id, session_id, user_id, prompt_key, model, empresa_id, created_at, updated_at
        FROM {CHATBOT_SCHEMA}.conversations
        WHERE id = :id
    """)
    result = db.execute(query, {"id": conversation_id})
    row = result.fetchone()
    if row:
        return {
            "id": row[0],
            "session_id": row[1],
            "user_id": row[2],
            "prompt_key": row[3],
            "model": row[4],
            "empresa_id": row[5],
            "created_at": row[6],
            "updated_at": row[7]
        }
    return None


def get_conversations_by_session(db: Session, session_id: str, empresa_id: Optional[int] = None) -> List[Dict]:
    """Retorna todas as conversas de uma sessão"""
    if empresa_id:
        query = text(f"""
            SELECT id, session_id, user_id, prompt_key, model, empresa_id, created_at, updated_at
            FROM {CHATBOT_SCHEMA}.conversations
            WHERE session_id = :session_id AND empresa_id = :empresa_id
            ORDER BY created_at DESC
        """)
        result = db.execute(query, {"session_id": session_id, "empresa_id": empresa_id})
    else:
        query = text(f"""
            SELECT id, session_id, user_id, prompt_key, model, empresa_id, created_at, updated_at
            FROM {CHATBOT_SCHEMA}.conversations
            WHERE session_id = :session_id
            ORDER BY created_at DESC
        """)
        result = db.execute(query, {"session_id": session_id})

    return [
        {
            "id": row[0],
            "session_id": row[1],
            "user_id": row[2],
            "prompt_key": row[3],
            "model": row[4],
            "empresa_id": row[5],
            "created_at": row[6],
            "updated_at": row[7]
        }
        for row in result.fetchall()
    ]


def get_conversations_by_user(db: Session, user_id: str, empresa_id: Optional[int] = None) -> List[Dict]:
    """Retorna todas as conversas de um usuário"""
    if empresa_id:
        query = text(f"""
            SELECT id, session_id, user_id, prompt_key, model, empresa_id, created_at, updated_at
            FROM {CHATBOT_SCHEMA}.conversations
            WHERE user_id = :user_id AND empresa_id = :empresa_id
            ORDER BY updated_at DESC
        """)
        result = db.execute(query, {"user_id": user_id, "empresa_id": empresa_id})
    else:
        query = text(f"""
            SELECT id, session_id, user_id, prompt_key, model, empresa_id, created_at, updated_at
            FROM {CHATBOT_SCHEMA}.conversations
            WHERE user_id = :user_id
            ORDER BY updated_at DESC
        """)
        result = db.execute(query, {"user_id": user_id})

    return [
        {
            "id": row[0],
            "session_id": row[1],
            "user_id": row[2],
            "prompt_key": row[3],
            "model": row[4],
            "empresa_id": row[5],
            "created_at": row[6],
            "updated_at": row[7]
        }
        for row in result.fetchall()
    ]


def update_conversation(db: Session, conversation_id: int):
    """Atualiza o timestamp da conversa"""
    query = text(f"""
        UPDATE {CHATBOT_SCHEMA}.conversations
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = :id
    """)
    db.execute(query, {"id": conversation_id})
    db.commit()


def update_conversation_model(db: Session, conversation_id: int, model: str) -> bool:
    """Atualiza o modelo de uma conversa"""
    query = text(f"""
        UPDATE {CHATBOT_SCHEMA}.conversations
        SET model = :model, updated_at = CURRENT_TIMESTAMP
        WHERE id = :id
    """)
    result = db.execute(query, {"model": model, "id": conversation_id})
    db.commit()
    return result.rowcount > 0


def delete_conversation(db: Session, conversation_id: int) -> bool:
    """Deleta uma conversa e suas mensagens"""
    query = text(f"DELETE FROM {CHATBOT_SCHEMA}.conversations WHERE id = :id")
    result = db.execute(query, {"id": conversation_id})
    db.commit()
    return result.rowcount > 0


# ==================== MENSAGENS ====================

def create_message(db: Session, conversation_id: int, role: str, content: str) -> Optional[int]:
    """Adiciona uma mensagem à conversa"""
    query = text(f"""
        INSERT INTO {CHATBOT_SCHEMA}.messages (conversation_id, role, content)
        VALUES (:conversation_id, :role, :content)
        RETURNING id
    """)
    result = db.execute(query, {
        "conversation_id": conversation_id,
        "role": role,
        "content": content
    })
    db.commit()

    # Atualiza timestamp da conversa
    update_conversation(db, conversation_id)

    row = result.fetchone()
    return row[0] if row else None


def get_messages(db: Session, conversation_id: int) -> List[Dict]:
    """Retorna todas as mensagens de uma conversa"""
    query = text(f"""
        SELECT id, conversation_id, role, content, created_at
        FROM {CHATBOT_SCHEMA}.messages
        WHERE conversation_id = :conversation_id
        ORDER BY created_at ASC
    """)
    result = db.execute(query, {"conversation_id": conversation_id})

    return [
        {
            "id": row[0],
            "conversation_id": row[1],
            "role": row[2],
            "content": row[3],
            "created_at": row[4]
        }
        for row in result.fetchall()
    ]


def get_conversation_with_messages(db: Session, conversation_id: int) -> Optional[Dict]:
    """Retorna conversa completa com todas as mensagens"""
    conversation = get_conversation(db, conversation_id)
    if not conversation:
        return None

    messages = get_messages(db, conversation_id)
    conversation['messages'] = messages

    return conversation


# ==================== UTILIDADES ====================

def get_stats(db: Session, empresa_id: Optional[int] = None) -> Dict:
    """Retorna estatísticas do banco"""
    if empresa_id:
        custom_prompts_query = text(f"SELECT COUNT(*) FROM {CHATBOT_SCHEMA}.prompts WHERE is_default = FALSE AND empresa_id = :empresa_id")
        custom_prompts = db.execute(custom_prompts_query, {"empresa_id": empresa_id}).scalar()

        default_prompts_query = text(f"SELECT COUNT(*) FROM {CHATBOT_SCHEMA}.prompts WHERE is_default = TRUE")
        default_prompts = db.execute(default_prompts_query).scalar()

        conversations_query = text(f"SELECT COUNT(*) FROM {CHATBOT_SCHEMA}.conversations WHERE empresa_id = :empresa_id")
        conversations = db.execute(conversations_query, {"empresa_id": empresa_id}).scalar()

        messages_query = text(f"""
            SELECT COUNT(*) FROM {CHATBOT_SCHEMA}.messages m
            JOIN {CHATBOT_SCHEMA}.conversations c ON m.conversation_id = c.id
            WHERE c.empresa_id = :empresa_id
        """)
        messages = db.execute(messages_query, {"empresa_id": empresa_id}).scalar()
    else:
        custom_prompts_query = text(f"SELECT COUNT(*) FROM {CHATBOT_SCHEMA}.prompts WHERE is_default = FALSE")
        custom_prompts = db.execute(custom_prompts_query).scalar()

        default_prompts_query = text(f"SELECT COUNT(*) FROM {CHATBOT_SCHEMA}.prompts WHERE is_default = TRUE")
        default_prompts = db.execute(default_prompts_query).scalar()

        conversations_query = text(f"SELECT COUNT(*) FROM {CHATBOT_SCHEMA}.conversations")
        conversations = db.execute(conversations_query).scalar()

        messages_query = text(f"SELECT COUNT(*) FROM {CHATBOT_SCHEMA}.messages")
        messages = db.execute(messages_query).scalar()

    return {
        "custom_prompts": custom_prompts or 0,
        "default_prompts": default_prompts or 0,
        "conversations": conversations or 0,
        "messages": messages or 0
    }


def seed_default_prompts(db: Session):
    """Insere prompts padrão no banco (se não existirem)"""
    default_prompts = [
        {
            "key": "default",
            "name": "Padrão (Alex - Suporte)",
            "content": """Você é um atendente humano chamado Alex, que trabalha no suporte ao cliente de uma empresa de restaurante/delivery.

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

IMPORTANTE - Como reagir a notificações de pedidos:
- Se você vê no histórico que enviou uma notificação de pedido confirmado recentemente, você DEVE se lembrar disso
- Quando o cliente responder após receber a notificação, reconheça naturalmente o pedido dele
- Exemplos de como reagir:
  * Cliente: "oi" → Você: "Oi! Vi que confirmei seu pedido agora mesmo 😊 Alguma dúvida sobre ele?"
  * Cliente: "quanto tempo vai demorar?" → Você: "Olha, coloquei lá na confirmação que seria [tempo estimado]. Tá dentro do previsto ainda!"
  * Cliente: "pode trocar o endereço?" → Você: "Claro! Deixa eu ver aqui... qual seria o novo endereço?"
  * Cliente: "esqueci o que pedi" → Você: "Sem problema! Você pediu: [itens do pedido]. Total de [valor]"
- Mantenha a consistência: se a notificação mencionou tempo estimado, número do pedido, mesa, etc., use essas informações
- Seja proativo em oferecer ajuda relacionada ao pedido (alterações, dúvidas, rastreamento)
- Se o cliente perguntar sobre status, informe que o pedido está confirmado e em preparação

Tipos de pedidos que você gerencia:
1. **Delivery/Cardápio**: Pedidos com entrega - fique atento a endereço e tempo estimado
2. **Mesa**: Pedidos para consumo no local - fique atento ao número da mesa
3. **Balcão**: Pedidos para retirada no balcão - fique atento ao tempo de preparo

Lembre-se: você é Alex, um humano real ajudando outro humano. Seja genuíno e prestativo!"""
        }
    ]

    for prompt_data in default_prompts:
        existing = get_prompt(db, prompt_data["key"])
        if not existing:
            create_prompt(
                db=db,
                key=prompt_data["key"],
                name=prompt_data["name"],
                content=prompt_data["content"],
                is_default=True
            )
            print(f"✅ Prompt padrão '{prompt_data['name']}' inserido")
