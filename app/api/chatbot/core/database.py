"""
Módulo de acesso ao banco de dados PostgreSQL para o Chatbot
Schema: chatbot
Suporte multi-empresa
Integrado com o sistema de DB do Mensura
"""
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import logging
import json
from datetime import datetime, timedelta, timezone

# Logger do módulo
logger = logging.getLogger(__name__)

# Schema do chatbot
CHATBOT_SCHEMA = "chatbot"

# ==================== JANELA DE CONVERSA (WHATSAPP 24H) ====================

def cliente_conversou_nas_ultimas_horas(
    db: Session,
    phone_number: str,
    *,
    empresa_id: Optional[int] = None,
    horas: int = 24,
) -> bool:
    """
    Retorna True se existe mensagem do cliente (role='user') nas últimas `horas`.

    Motivo:
    - WhatsApp (Cloud API / 360dialog) só permite mensagens "livres" fora de template
      dentro da janela de 24h desde a última mensagem do cliente.
    """
    try:
        if not phone_number or not str(phone_number).strip():
            return False

        user_id = _normalize_phone_number(str(phone_number).strip())
        if not user_id:
            return False

        # Se empresa_id for informado, tentamos respeitar o escopo da empresa.
        # Ainda assim, mantemos compatibilidade com conversas legadas sem empresa_id (NULL).
        if empresa_id is not None:
            q = text(
                f"""
                SELECT MAX(m.created_at) AS last_user_message_at
                FROM {CHATBOT_SCHEMA}.conversations c
                JOIN {CHATBOT_SCHEMA}.messages m ON m.conversation_id = c.id
                WHERE c.user_id = :user_id
                  AND (c.empresa_id = :empresa_id OR c.empresa_id IS NULL)
                  AND m.role = 'user'
                """
            )
            row = db.execute(q, {"user_id": user_id, "empresa_id": int(empresa_id)}).fetchone()
        else:
            q = text(
                f"""
                SELECT MAX(m.created_at) AS last_user_message_at
                FROM {CHATBOT_SCHEMA}.conversations c
                JOIN {CHATBOT_SCHEMA}.messages m ON m.conversation_id = c.id
                WHERE c.user_id = :user_id
                  AND m.role = 'user'
                """
            )
            row = db.execute(q, {"user_id": user_id}).fetchone()

        last_at = row[0] if row else None
        last_dt = _parse_timestamp(last_at)
        if not last_dt:
            return False

        limite = _utcnow() - timedelta(hours=max(int(horas), 0))
        return last_dt >= limite
    except Exception:
        # fallback conservador: se der erro, não envia WhatsApp (evita violar janela).
        return False

# ==================== CONSTANTES DE PAUSA ====================
# Tempo de pausa automática quando o chatbot pausa por conta própria
AUTO_PAUSE_HOURS = 3

def get_auto_pause_until() -> datetime:
    """
    Retorna o datetime até quando o bot deve ficar pausado quando pausa automaticamente.
    Usado quando o chatbot pausa por conta própria (sistema_nao_entendeu, cliente_chamou_atendente).
    
    Returns:
        datetime: Data/hora até quando o bot deve ficar pausado (3 horas a partir de agora)
    """
    # IMPORTANT: usar UTC para evitar drift por timezone entre app/DB
    return datetime.utcnow() + timedelta(hours=AUTO_PAUSE_HOURS)


def _utcnow() -> datetime:
    """Agora em UTC (naive), para comparar com TIMESTAMP sem timezone."""
    return datetime.utcnow()


def _is_infinite_timestamp(value) -> bool:
    """Detecta o valor especial 'infinity' retornado pelo Postgres para TIMESTAMP."""
    return isinstance(value, str) and value.lower() == "infinity"


def _parse_timestamp(value) -> Optional[datetime]:
    """Converte TIMESTAMP retornado do banco (datetime/str) para datetime (naive) quando possível."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if _is_infinite_timestamp(value):
        return None
    if isinstance(value, str):
        try:
            # cobre strings ISO com ou sem timezone
            v = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(v)
            # normaliza para naive (assumimos que TIMESTAMP do banco representa UTC)
            if dt.tzinfo:
                return dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except Exception:
            return None
    return None


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
                contact_name VARCHAR(255),
                prompt_key VARCHAR(100),
                model VARCHAR(100) NOT NULL,
                empresa_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prompt_key) REFERENCES {CHATBOT_SCHEMA}.prompts(key)
            )
        """))

        # Adiciona coluna contact_name se não existir (para bancos já existentes)
        db.execute(text(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = '{CHATBOT_SCHEMA}'
                    AND table_name = 'conversations'
                    AND column_name = 'contact_name'
                ) THEN
                    ALTER TABLE {CHATBOT_SCHEMA}.conversations ADD COLUMN contact_name VARCHAR(255);
                END IF;
            END $$;
        """))
        
        # Adiciona coluna profile_picture_url se não existir
        db.execute(text(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = '{CHATBOT_SCHEMA}'
                    AND table_name = 'conversations'
                    AND column_name = 'profile_picture_url'
                ) THEN
                    ALTER TABLE {CHATBOT_SCHEMA}.conversations ADD COLUMN profile_picture_url TEXT;
                END IF;
            END $$;
        """))

        # Adiciona coluna metadata se não existir
        db.execute(text(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = '{CHATBOT_SCHEMA}'
                    AND table_name = 'conversations'
                    AND column_name = 'metadata'
                ) THEN
                    ALTER TABLE {CHATBOT_SCHEMA}.conversations ADD COLUMN metadata JSONB;
                END IF;
            END $$;
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
        
        # Adiciona coluna metadata se não existir (para armazenar whatsapp_message_id)
        db.execute(text(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = '{CHATBOT_SCHEMA}'
                    AND table_name = 'messages'
                    AND column_name = 'metadata'
                ) THEN
                    ALTER TABLE {CHATBOT_SCHEMA}.messages ADD COLUMN metadata JSONB;
                END IF;
            END $$;
        """))

        # Tabela de status do bot por número (ativo/pausado)
        db.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {CHATBOT_SCHEMA}.bot_status (
                id SERIAL PRIMARY KEY,
                phone_number VARCHAR(50) UNIQUE NOT NULL,
                paused_at TIMESTAMP,
                paused_until TIMESTAMP,
                paused_by VARCHAR(255),
                empresa_id INTEGER,
                -- Fonte de verdade para pausa: se NULL, bot está ativo; se no futuro, bot está pausado até a data;
                -- se 'infinity', bot está pausado indefinidamente.
                desativa_chatbot_em TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Adiciona coluna paused_until se não existir (migration legada)
        db.execute(text(f"""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema = '{CHATBOT_SCHEMA}'
                    AND table_name = 'bot_status'
                    AND column_name = 'paused_until'
                ) THEN
                    ALTER TABLE {CHATBOT_SCHEMA}.bot_status ADD COLUMN paused_until TIMESTAMP;
                END IF;
            END $$;
        """))

        # Coluna oficial da pausa: data/hora em que o chatbot destrava (volta a responder)
        db.execute(text(f"""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema = '{CHATBOT_SCHEMA}'
                    AND table_name = 'bot_status'
                    AND column_name = 'chatbot_destrava_em'
                ) THEN
                    ALTER TABLE {CHATBOT_SCHEMA}.bot_status ADD COLUMN chatbot_destrava_em TIMESTAMP;
                END IF;
            END $$;
        """))

        # Nova coluna oficial: desativa_chatbot_em (substitui is_active como fonte de verdade)
        db.execute(text(f"""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema = '{CHATBOT_SCHEMA}'
                    AND table_name = 'bot_status'
                    AND column_name = 'desativa_chatbot_em'
                ) THEN
                    ALTER TABLE {CHATBOT_SCHEMA}.bot_status ADD COLUMN desativa_chatbot_em TIMESTAMP;
                END IF;
            END $$;
        """))

        # Migra dados legados para desativa_chatbot_em:
        # - Se existir chatbot_destrava_em, usa ele (pausa até data).
        # - Se existir paused_until, usa ele (legado).
        # - Se is_active=false e não houver data de destravar, marca como pausa indefinida ('infinity').
        # - Se is_active=true, garante NULL (ativo).
        db.execute(text(f"""
            DO $$
            BEGIN
                -- Preenche a partir de chatbot_destrava_em quando existir
                UPDATE {CHATBOT_SCHEMA}.bot_status
                SET desativa_chatbot_em = chatbot_destrava_em
                WHERE chatbot_destrava_em IS NOT NULL
                  AND (desativa_chatbot_em IS NULL OR desativa_chatbot_em <> chatbot_destrava_em);

                -- Preenche a partir de paused_until (legado) quando existir
                UPDATE {CHATBOT_SCHEMA}.bot_status
                SET desativa_chatbot_em = paused_until
                WHERE paused_until IS NOT NULL
                  AND desativa_chatbot_em IS NULL;

                -- Se is_active existir, migra estados
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = '{CHATBOT_SCHEMA}'
                      AND table_name = 'bot_status'
                      AND column_name = 'is_active'
                ) THEN
                    -- Pausa indefinida: is_active=false e sem data
                    UPDATE {CHATBOT_SCHEMA}.bot_status
                    SET desativa_chatbot_em = 'infinity'::timestamp
                    WHERE is_active = false
                      AND desativa_chatbot_em IS NULL;

                    -- Ativo: is_active=true força NULL
                    UPDATE {CHATBOT_SCHEMA}.bot_status
                    SET desativa_chatbot_em = NULL
                    WHERE is_active = true
                      AND desativa_chatbot_em IS NOT NULL
                      AND desativa_chatbot_em <> 'infinity'::timestamp;

                    -- Remove coluna antiga (ativado)
                    ALTER TABLE {CHATBOT_SCHEMA}.bot_status DROP COLUMN is_active;
                END IF;
            END $$;
        """))

        # Mantém chatbot_destrava_em sincronizado para compatibilidade (response legado)
        db.execute(text(f"""
            UPDATE {CHATBOT_SCHEMA}.bot_status
            SET chatbot_destrava_em = desativa_chatbot_em
            WHERE desativa_chatbot_em IS NOT NULL
              AND (chatbot_destrava_em IS NULL OR chatbot_destrava_em <> desativa_chatbot_em);
        """))
        # Migra paused_until -> chatbot_destrava_em para registros existentes
        db.execute(text(f"""
            UPDATE {CHATBOT_SCHEMA}.bot_status
            SET chatbot_destrava_em = paused_until
            WHERE paused_until IS NOT NULL AND chatbot_destrava_em IS NULL;
        """))

        # Índices para performance
        db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_conversations_session ON {CHATBOT_SCHEMA}.conversations(session_id)"))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_conversations_user ON {CHATBOT_SCHEMA}.conversations(user_id)"))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_conversations_empresa ON {CHATBOT_SCHEMA}.conversations(empresa_id)"))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_messages_conversation ON {CHATBOT_SCHEMA}.messages(conversation_id)"))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_prompts_key ON {CHATBOT_SCHEMA}.prompts(key)"))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_prompts_empresa ON {CHATBOT_SCHEMA}.prompts(empresa_id)"))
        db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_bot_status_phone ON {CHATBOT_SCHEMA}.bot_status(phone_number)"))

        db.commit()
        logger.info("Schema e tabelas do chatbot criadas no PostgreSQL.")
        return True
    except Exception as e:
        db.rollback()
        logger.exception(f"Erro ao inicializar banco do chatbot: {e}")
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
        logger.exception(f"Erro ao criar prompt: {e}")
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

def create_conversation(db: Session, session_id: str, user_id: str, prompt_key: str, model: str, empresa_id: Optional[int] = None, contact_name: Optional[str] = None, profile_picture_url: Optional[str] = None) -> Optional[int]:
    """Cria uma nova conversa"""
    query = text(f"""
        INSERT INTO {CHATBOT_SCHEMA}.conversations (session_id, user_id, prompt_key, model, empresa_id, contact_name, profile_picture_url)
        VALUES (:session_id, :user_id, :prompt_key, :model, :empresa_id, :contact_name, :profile_picture_url)
        RETURNING id
    """)
    result = db.execute(query, {
        "session_id": session_id,
        "user_id": user_id,
        "prompt_key": prompt_key,
        "model": model,
        "empresa_id": empresa_id,
        "contact_name": contact_name,
        "profile_picture_url": profile_picture_url
    })
    db.commit()
    row = result.fetchone()
    return row[0] if row else None


def update_conversation_contact_name(db: Session, conversation_id: int, contact_name: str) -> bool:
    """Atualiza o nome do contato de uma conversa"""
    try:
        query = text(f"""
            UPDATE {CHATBOT_SCHEMA}.conversations
            SET contact_name = :contact_name, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """)
        db.execute(query, {"id": conversation_id, "contact_name": contact_name})
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.exception(f"Erro ao atualizar contact_name: {e}")
        return False


def update_conversation_profile_picture(db: Session, conversation_id: int, profile_picture_url: str) -> bool:
    """Atualiza a foto de perfil de uma conversa"""
    try:
        query = text(f"""
            UPDATE {CHATBOT_SCHEMA}.conversations
            SET profile_picture_url = :profile_picture_url, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """)
        db.execute(query, {"id": conversation_id, "profile_picture_url": profile_picture_url})
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.exception(f"Erro ao atualizar profile_picture_url: {e}")
        return False


def get_conversation(db: Session, conversation_id: int) -> Optional[Dict]:
    """Busca uma conversa pelo ID"""
    query = text(f"""
        SELECT id, session_id, user_id, contact_name, prompt_key, model, empresa_id, profile_picture_url, created_at, updated_at
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
            "contact_name": row[3],
            "prompt_key": row[4],
            "model": row[5],
            "empresa_id": row[6],
            "profile_picture_url": row[7],
            "created_at": row[8],
            "updated_at": row[9]
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
            SELECT id, session_id, user_id, contact_name, prompt_key, model, empresa_id, profile_picture_url, created_at, updated_at
            FROM {CHATBOT_SCHEMA}.conversations
            WHERE user_id = :user_id AND empresa_id = :empresa_id
            ORDER BY updated_at DESC
        """)
        result = db.execute(query, {"user_id": user_id, "empresa_id": empresa_id})
    else:
        query = text(f"""
            SELECT id, session_id, user_id, contact_name, prompt_key, model, empresa_id, profile_picture_url, created_at, updated_at
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
            "contact_name": row[3],
            "prompt_key": row[4],
            "model": row[5],
            "empresa_id": row[6],
            "profile_picture_url": row[7],
            "created_at": row[8],
            "updated_at": row[9]
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

def create_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
    whatsapp_message_id: Optional[str] = None,
    extra_metadata: Optional[dict] = None,
) -> Optional[int]:
    """Adiciona uma mensagem à conversa
    
    Args:
        db: Sessão do banco de dados
        conversation_id: ID da conversa
        role: Papel da mensagem ('user' ou 'assistant')
        content: Conteúdo da mensagem
        whatsapp_message_id: ID único da mensagem do WhatsApp (opcional, usado para detectar duplicatas)
        extra_metadata: Metadados adicionais (opcional). Será mesclado com whatsapp_message_id.
    """
    # Prepara metadata (jsonb) se houver whatsapp_message_id e/ou extra_metadata
    metadata_json = None
    metadata_obj = {}
    if whatsapp_message_id:
        metadata_obj["whatsapp_message_id"] = whatsapp_message_id
    if extra_metadata:
        # Garante que é dict e mescla sem quebrar chamadas legadas
        try:
            if isinstance(extra_metadata, dict):
                metadata_obj.update(extra_metadata)
        except Exception:
            # Se vier algo inválido, ignora silenciosamente para não quebrar fluxo
            pass
    if metadata_obj:
        import json
        metadata_json = json.dumps(metadata_obj)

    from sqlalchemy.exc import SQLAlchemyError

    def _insert():
        if metadata_json:
            query = text(f"""
                INSERT INTO {CHATBOT_SCHEMA}.messages (conversation_id, role, content, metadata)
                VALUES (:conversation_id, :role, :content, CAST(:metadata AS jsonb))
                RETURNING id
            """)
            return db.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "role": role,
                    "content": content,
                    "metadata": metadata_json,
                },
            )

        query = text(f"""
            INSERT INTO {CHATBOT_SCHEMA}.messages (conversation_id, role, content)
            VALUES (:conversation_id, :role, :content)
            RETURNING id
        """)
        return db.execute(
            query,
            {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
            },
        )

    # Se a sessão estiver em transação abortada (InFailedSqlTransaction), precisamos de rollback
    # antes de conseguir inserir a mensagem.
    try:
        result = _insert()
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        result = _insert()
        db.commit()

    # Atualiza timestamp da conversa (não deve impedir o retorno da mensagem)
    try:
        update_conversation(db, conversation_id)
    except SQLAlchemyError:
        db.rollback()

    row = result.fetchone()
    return row[0] if row else None


def get_messages(db: Session, conversation_id: int) -> List[Dict]:
    """Retorna todas as mensagens de uma conversa"""
    query = text(f"""
        SELECT id, conversation_id, role, content, created_at, metadata
        FROM {CHATBOT_SCHEMA}.messages
        WHERE conversation_id = :conversation_id
        ORDER BY created_at ASC
    """)
    result = db.execute(query, {"conversation_id": conversation_id})

    mensagens: List[Dict] = []
    for row in result.fetchall():
        metadata = row[5]
        # Alguns drivers podem devolver JSONB como str
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = None
        mensagens.append(
            {
                "id": row[0],
                "conversation_id": row[1],
                "role": row[2],
                "content": row[3],
                "created_at": row[4],
                "timestamp": row[4],  # Alias para compatibilidade com frontend
                "metadata": metadata,
            }
        )
    return mensagens


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
        },
        {
            "key": "atendimento",
            "name": "Atendimento (Suporte)",
            "content": """Você é um atendente humano de suporte ao cliente de um restaurante/delivery.

Características da sua personalidade:
- Você é amigável, paciente e prestativo
- Usa linguagem natural e casual
- Não revela que é uma IA
- Mantém o contexto da conversa anterior

IMPORTANTE - Pedidos via WhatsApp:
- Não aceite pedidos pelo WhatsApp
- Quando o cliente quiser fazer pedido, direcione para o link do cardápio informado pela empresa
- Seja educado e claro ao orientar

Tom de conversa:
- Natural e conversacional
- Frases curtas e diretas
- Emojis com moderação"""
        },
        {
            "key": "atendimento-pedido-whatsapp",
            "name": "Atendimento (Pedido via WhatsApp)",
            "content": """Você é um atendente humano especializado em pedidos via WhatsApp para um restaurante/delivery.

Objetivo:
- Ajudar o cliente a montar o pedido com clareza
- Confirmar itens e quantidades quando necessário
- Coletar dados essenciais de entrega/retirada com perguntas objetivas

Tom de conversa:
- Natural e conversacional
- Direto e prestativo
- Emojis com moderação"""
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
            logger.info(f"Prompt padrão inserido: {prompt_data['name']}")


# ==================== BOT STATUS (PAUSAR/ATIVAR) ====================

def _normalize_phone_number(phone_number: Optional[str]) -> Optional[str]:
    """
    Normaliza telefone para formato consistente no banco.

    Regras:
    - Remove tudo que não for dígito.
    - Se não começar com 55 e tiver 10/11 dígitos (DDD + número), prefixa 55.
    - Não altera o registro global (`GLOBAL_BOT_PHONE`).

    Isso evita que endpoints consultem `+55...`/`11...` enquanto o banco guarda `5511...`,
    o que fazia retornar "ativo por padrão" indevidamente.
    """
    if phone_number is None:
        return None

    phone_str = str(phone_number).strip()
    # Mantém o registro global
    if "GLOBAL_BOT_PHONE" in globals() and phone_str == GLOBAL_BOT_PHONE:
        return phone_str

    digits = "".join(ch for ch in phone_str if ch.isdigit())
    if not digits:
        return phone_str

    # Remove prefixo internacional "00" quando vier (ex: 0055...)
    if digits.startswith("00") and len(digits) > 2:
        digits = digits[2:]

    if digits.startswith("55"):
        return digits

    if len(digits) in (10, 11):
        return f"55{digits}"

    return digits


def get_bot_status(db: Session, phone_number: str) -> Optional[Dict]:
    """Verifica se o bot está ativo para um número específico"""
    try:
        phone_normalized = _normalize_phone_number(phone_number)
        query = text(f"""
            SELECT id, phone_number, paused_at, paused_by, empresa_id, desativa_chatbot_em
            FROM {CHATBOT_SCHEMA}.bot_status
            WHERE phone_number = :phone
        """)
        result = db.execute(query, {"phone": phone_normalized}).fetchone()

        if result:
            desativa_em_dt = _parse_timestamp(result[5])
            # Regra: ativo se NULL (ou timestamp expirado)
            now = _utcnow()
            is_active = True
            if _is_infinite_timestamp(result[5]):
                is_active = False
            elif desativa_em_dt and now < desativa_em_dt:
                is_active = False
            return {
                "id": result[0],
                "phone_number": result[1],
                "is_active": is_active,
                "paused_at": result[2].isoformat() if result[2] else None,
                "paused_by": result[3],
                "empresa_id": result[4],
                # Mantém chave legada no response
                "chatbot_destrava_em": desativa_em_dt.isoformat() if desativa_em_dt else None,
            }
        # Se não existe registro, o bot está ativo por padrão
        return {"phone_number": phone_normalized, "is_active": True}
    except Exception as e:
        logger.exception(f"Erro ao verificar status do bot: {e}")
        return {"phone_number": phone_number, "is_active": True}


def is_bot_active_for_phone(db: Session, phone_number: str) -> bool:
    """Retorna True se o bot está ativo para o número, False se pausado.
    Também verifica o status global - se o bot global estiver pausado, retorna False.
    Verifica se desativa_chatbot_em já passou - se sim, considera ativo novamente.
    """
    # Primeiro verifica o status global
    global_status = get_global_bot_status(db)
    if not global_status.get("is_active", True):
        return False  # Bot global pausado, nenhum número responde

    phone_normalized = _normalize_phone_number(phone_number)

    # Depois verifica o status individual
    try:
        row = db.execute(
            text(f"""
                SELECT empresa_id, desativa_chatbot_em
                FROM {CHATBOT_SCHEMA}.bot_status
                WHERE phone_number = :phone
            """),
            {"phone": phone_normalized},
        ).fetchone()
        if not row:
            return True

        empresa_id = row[0]
        desativa_raw = row[1]
        if _is_infinite_timestamp(desativa_raw):
            return False

        desativa_dt = _parse_timestamp(desativa_raw)
        if not desativa_dt:
            return True

        now = _utcnow()
        if now >= desativa_dt:
            # Já expirou: despausa limpando a coluna
            set_bot_status(db, phone_normalized, paused_by=None, empresa_id=empresa_id, desativa_chatbot_em=None)
            return True
        return False
    except Exception as e:
        logger.exception(f"Erro ao verificar desativa_chatbot_em: {e}")
        # fallback conservador: se der erro, assume ativo para não travar atendimento
        return True


def set_bot_status(
    db: Session,
    phone_number: str,
    paused_by: str = None,
    empresa_id: int = None,
    desativa_chatbot_em=None,
) -> Dict:
    """Define o status do bot para um número específico.

    Args:
        desativa_chatbot_em: Fonte de verdade. Se None => ativo. Se datetime => pausado até a data.
            Se string 'infinity' => pausado indefinidamente.
    """
    try:
        phone_number = _normalize_phone_number(phone_number)
        is_paused = desativa_chatbot_em is not None
        desativa_is_infinity = _is_infinite_timestamp(desativa_chatbot_em) or (
            isinstance(desativa_chatbot_em, str) and desativa_chatbot_em.lower() == "infinity"
        )

        existing = db.execute(
            text(f"SELECT id FROM {CHATBOT_SCHEMA}.bot_status WHERE phone_number = :phone"),
            {"phone": phone_number},
        ).fetchone()

        if existing:
            query = text(f"""
                UPDATE {CHATBOT_SCHEMA}.bot_status
                SET paused_at = CASE WHEN :is_paused THEN CURRENT_TIMESTAMP ELSE NULL END,
                    paused_by = CASE WHEN :is_paused THEN :paused_by ELSE NULL END,
                    desativa_chatbot_em = CASE
                        WHEN :is_paused AND :desativa_is_infinity THEN 'infinity'::timestamp
                        WHEN :is_paused THEN CAST(:desativa_chatbot_em AS TIMESTAMP)
                        ELSE NULL
                    END,
                    -- Campo legado para response/compatibilidade: apenas quando tem data finita
                    chatbot_destrava_em = CASE
                        WHEN :is_paused AND :desativa_is_infinity THEN NULL
                        WHEN :is_paused THEN CAST(:desativa_chatbot_em AS TIMESTAMP)
                        ELSE NULL
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE phone_number = :phone
                RETURNING id, phone_number, paused_at, paused_by, empresa_id, desativa_chatbot_em
            """)
        else:
            query = text(f"""
                INSERT INTO {CHATBOT_SCHEMA}.bot_status (phone_number, paused_at, paused_by, empresa_id, desativa_chatbot_em, chatbot_destrava_em)
                VALUES (
                    :phone,
                    CASE WHEN :is_paused THEN CURRENT_TIMESTAMP ELSE NULL END,
                    CASE WHEN :is_paused THEN :paused_by ELSE NULL END,
                    :empresa_id,
                    CASE
                        WHEN :is_paused AND :desativa_is_infinity THEN 'infinity'::timestamp
                        WHEN :is_paused THEN CAST(:desativa_chatbot_em AS TIMESTAMP)
                        ELSE NULL
                    END,
                    CASE
                        WHEN :is_paused AND :desativa_is_infinity THEN NULL
                        WHEN :is_paused THEN CAST(:desativa_chatbot_em AS TIMESTAMP)
                        ELSE NULL
                    END
                )
                RETURNING id, phone_number, paused_at, paused_by, empresa_id, desativa_chatbot_em
            """)

        result = db.execute(
            query,
            {
                "phone": phone_number,
                "is_paused": is_paused,
                "paused_by": paused_by,
                "empresa_id": empresa_id,
                "desativa_chatbot_em": desativa_chatbot_em if not desativa_is_infinity else None,
                "desativa_is_infinity": desativa_is_infinity,
            },
        ).fetchone()
        db.commit()

        desativa_dt = _parse_timestamp(result[5])
        computed_is_active = True
        if _is_infinite_timestamp(result[5]):
            computed_is_active = False
        elif desativa_dt and _utcnow() < desativa_dt:
            computed_is_active = False

        return {
            "success": True,
            "id": result[0],
            "phone_number": result[1],
            # Mantém resposta no formato antigo
            "is_active": computed_is_active,
            "paused_at": result[2].isoformat() if result[2] else None,
            "paused_by": result[3],
            "chatbot_destrava_em": desativa_dt.isoformat() if desativa_dt else None,
        }
    except Exception as e:
        db.rollback()
        logger.exception(f"Erro ao definir status do bot: {e}")
        return {"success": False, "error": str(e)}


def get_all_bot_statuses(db: Session, empresa_id: int = None) -> List[Dict]:
    """Lista todos os status de bot (números pausados)"""
    try:
        if empresa_id:
            query = text(f"""
                SELECT id, phone_number, paused_at, paused_by, empresa_id, desativa_chatbot_em
                FROM {CHATBOT_SCHEMA}.bot_status
                WHERE empresa_id = :empresa_id
                ORDER BY updated_at DESC
            """)
            result = db.execute(query, {"empresa_id": empresa_id})
        else:
            query = text(f"""
                SELECT id, phone_number, paused_at, paused_by, empresa_id, desativa_chatbot_em
                FROM {CHATBOT_SCHEMA}.bot_status
                ORDER BY updated_at DESC
            """)
            result = db.execute(query)

        return [
            {
                "id": row[0],
                "phone_number": row[1],
                "is_active": (False if _is_infinite_timestamp(row[5]) else (False if (_parse_timestamp(row[5]) and _utcnow() < _parse_timestamp(row[5])) else True)),
                "paused_at": row[2].isoformat() if row[2] else None,
                "paused_by": row[3],
                "empresa_id": row[4],
                # Mantém chave legada no response
                "chatbot_destrava_em": (_parse_timestamp(row[5]).isoformat() if _parse_timestamp(row[5]) else None),
            }
            for row in result.fetchall()
        ]
    except Exception as e:
        logger.exception(f"Erro ao listar status do bot: {e}")
        return []


# ==================== BOT STATUS GLOBAL ====================

GLOBAL_BOT_PHONE = "_GLOBAL_BOT_"

def get_global_bot_status(db: Session, empresa_id: int = None) -> Dict:
    """Verifica se o bot global está ativo (afeta todos os números)"""
    try:
        query = text(f"""
            SELECT id, phone_number, paused_at, paused_by, empresa_id, desativa_chatbot_em
            FROM {CHATBOT_SCHEMA}.bot_status
            WHERE phone_number = :phone
        """)
        result = db.execute(query, {"phone": GLOBAL_BOT_PHONE}).fetchone()

        if result:
            desativa_raw = result[5]
            if _is_infinite_timestamp(desativa_raw):
                is_active = False
            else:
                desativa_dt = _parse_timestamp(desativa_raw)
                is_active = True if not desativa_dt else (_utcnow() >= desativa_dt)
            return {
                "id": result[0],
                "phone_number": result[1],
                "is_active": is_active,
                "paused_at": result[2].isoformat() if result[2] else None,
                "paused_by": result[3],
                "empresa_id": result[4]
            }
        # Se não existe registro, o bot global está ativo por padrão
        return {"phone_number": GLOBAL_BOT_PHONE, "is_active": True}
    except Exception as e:
        logger.exception(f"Erro ao verificar status global do bot: {e}")
        return {"phone_number": GLOBAL_BOT_PHONE, "is_active": True}


def set_global_bot_status(db: Session, paused_by: str = None, empresa_id: int = None, desativa_chatbot_em=None) -> Dict:
    """Define o status global do bot (afeta todos os números)"""
    try:
        is_paused = desativa_chatbot_em is not None
        desativa_is_infinity = _is_infinite_timestamp(desativa_chatbot_em) or (
            isinstance(desativa_chatbot_em, str) and desativa_chatbot_em.lower() == "infinity"
        )
        # Verifica se já existe
        existing = db.execute(
            text(f"SELECT id FROM {CHATBOT_SCHEMA}.bot_status WHERE phone_number = :phone"),
            {"phone": GLOBAL_BOT_PHONE}
        ).fetchone()

        if existing:
            # Atualiza
            query = text(f"""
                UPDATE {CHATBOT_SCHEMA}.bot_status
                SET paused_at = CASE WHEN :is_paused THEN CURRENT_TIMESTAMP ELSE NULL END,
                    paused_by = CASE WHEN :is_paused THEN :paused_by ELSE NULL END,
                    desativa_chatbot_em = CASE
                        WHEN :is_paused AND :desativa_is_infinity THEN 'infinity'::timestamp
                        WHEN :is_paused THEN CAST(:desativa_chatbot_em AS TIMESTAMP)
                        ELSE NULL
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE phone_number = :phone
                RETURNING id, phone_number, paused_at, paused_by, empresa_id, desativa_chatbot_em
            """)
        else:
            # Insere novo
            query = text(f"""
                INSERT INTO {CHATBOT_SCHEMA}.bot_status (phone_number, paused_at, paused_by, empresa_id, desativa_chatbot_em)
                VALUES (
                    :phone,
                    CASE WHEN :is_paused THEN CURRENT_TIMESTAMP ELSE NULL END,
                    CASE WHEN :is_paused THEN :paused_by ELSE NULL END,
                    :empresa_id,
                    CASE
                        WHEN :is_paused AND :desativa_is_infinity THEN 'infinity'::timestamp
                        WHEN :is_paused THEN CAST(:desativa_chatbot_em AS TIMESTAMP)
                        ELSE NULL
                    END
                )
                RETURNING id, phone_number, paused_at, paused_by, empresa_id, desativa_chatbot_em
            """)

        result = db.execute(query, {
            "phone": GLOBAL_BOT_PHONE,
            "is_paused": is_paused,
            "paused_by": paused_by,
            "empresa_id": empresa_id,
            "desativa_chatbot_em": desativa_chatbot_em if not desativa_is_infinity else None,
            "desativa_is_infinity": desativa_is_infinity,
        }).fetchone()
        db.commit()

        computed_is_active = not _is_infinite_timestamp(result[5])
        return {
            "success": True,
            "id": result[0],
            "phone_number": result[1],
            "is_active": computed_is_active,
            "paused_at": result[2].isoformat() if result[2] else None,
            "paused_by": result[3]
        }
    except Exception as e:
        db.rollback()
        logger.exception(f"Erro ao definir status global do bot: {e}")
        return {"success": False, "error": str(e)}


def is_bot_globally_active(db: Session) -> bool:
    """Retorna True se o bot global está ativo, False se pausado"""
    status = get_global_bot_status(db)
    return status.get("is_active", True)
