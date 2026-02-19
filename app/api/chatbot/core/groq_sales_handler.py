"""Stub implementation for groq_sales_handler used during migration.
This provides minimal constants and functions so the router can import
the names without failing. Replace with real implementation when available.
"""
from app.config.settings import MODEL_NAME, GROQ_API_URL, GROQ_API_KEY, STATE_CADASTRO_NOME
from typing import Optional


class GroqSalesHandler:
    def __init__(self, *args, **kwargs):
        pass


async def processar_mensagem_groq(*args, **kwargs) -> Optional[str]:
    """
    Minimal implementation to support the quick 'cadastro_nome' flow during migration.

    Behavior:
    - If the conversation is in STATE_CADASTRO_NOME, try to interpret `mensagem` as the
      customer's full name, create a `cadastros.clientes` row if not exists, update the
      conversation (contact_name + remove sales_state/sales_data) and return a short
      confirmation string to send to the user.
    - Otherwise returns a simple fallback message.
    """
    try:
        db = kwargs.get("db")
        user_id = kwargs.get("user_id")
        mensagem = (kwargs.get("mensagem") or "").strip()
        empresa_id = kwargs.get("empresa_id")

        # Only handle simple name registration here
        if not db or not user_id or not mensagem:
            return "Desculpe, não consegui processar. Pode repetir?"

        # Heurística simples de nome: pelo menos duas palavras com letras
        parts = [p for p in mensagem.split() if any(ch.isalpha() for ch in p)]
        is_name = len(parts) >= 2 and all(len(p) >= 2 for p in parts)

        if is_name:
            # Normalize phone and try to find or create cliente
            try:
                from app.utils.telefone import normalizar_telefone_para_armazenar, variantes_telefone_para_busca
                from sqlalchemy import text

                phone_canon = normalizar_telefone_para_armazenar(user_id) or "".join(filter(str.isdigit, str(user_id)))
                candidatos = variantes_telefone_para_busca(user_id) or [phone_canon]

                query = text(
                    "SELECT id, nome, telefone FROM cadastros.clientes WHERE telefone = ANY(:telefones) LIMIT 1"
                )
                row = db.execute(query, {"telefones": candidatos}).fetchone()
                if not row:
                    insert = text("""
                        INSERT INTO cadastros.clientes (nome, telefone, created_at, updated_at)
                        VALUES (:nome, :telefone, NOW(), NOW())
                        RETURNING id, nome, telefone
                    """)
                    result = db.execute(insert, {"nome": mensagem, "telefone": phone_canon})
                    cliente = result.fetchone()
                    db.commit()
                else:
                    cliente = row

                # Update conversation: set contact_name and remove sales_state/sales_data from metadata
                try:
                    update_conv = text("""
                        UPDATE chatbot.conversations
                        SET contact_name = :contact_name,
                            metadata = (COALESCE(metadata, '{}'::jsonb) - 'sales_state') - 'sales_data',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id
                          AND (empresa_id = :empresa_id OR :empresa_id IS NULL)
                        RETURNING id
                    """)
                    db.execute(update_conv, {"contact_name": mensagem, "user_id": phone_canon, "empresa_id": empresa_id})
                    db.commit()
                except Exception:
                    try:
                        db.rollback()
                    except Exception:
                        pass

                return f"Obrigado {parts[0]}! Seu cadastro foi realizado com sucesso. Posso te ajudar com o pedido?"
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
                return "Desculpe, houve um erro ao salvar seu cadastro. Tente novamente em instantes."

        # Fallback generic response
        return "Recebi sua mensagem — em breve retorno."
    except Exception as e:
        # Não quebrar fluxo principal em caso de erro inesperado
        import logging as _log
        _log.getLogger(__name__).exception("Erro no handler de cadastro rápido (groq stub): %s", e)
        return "Desculpe, ocorreu um erro ao processar sua mensagem."


__all__ = ["MODEL_NAME", "GROQ_API_URL", "GROQ_API_KEY", "GroqSalesHandler", "processar_mensagem_groq", "STATE_CADASTRO_NOME"]

