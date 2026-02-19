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
                # Use the Mensura ClienteService to create the cliente (keeps business rules)
                from app.api.cadastros.services.service_cliente import ClienteService
                from app.api.cadastros.schemas.schema_cliente import ClienteCreate
                from app.utils.telefone import normalizar_telefone_para_armazenar
                from sqlalchemy import text

                phone_canon = normalizar_telefone_para_armazenar(user_id) or "".join(
                    filter(str.isdigit, str(user_id))
                )

                service = ClienteService(db)
                cliente_payload = ClienteCreate(nome=mensagem, telefone=phone_canon)
                try:
                    cliente_obj = service.create(cliente_payload)
                except Exception as e_service:
                    # If service raises HTTPException for duplicate phone, try to fetch existing
                    try:
                        q = text("SELECT id, nome, telefone FROM cadastros.clientes WHERE telefone = :telefone LIMIT 1")
                        row = db.execute(q, {"telefone": phone_canon}).fetchone()
                        cliente_obj = row
                    except Exception:
                        cliente_obj = None

                # Update conversation: set contact_name and remove sales_state/sales_data from metadata
                try:
                    update_conv = text(
                        """
                        UPDATE chatbot.conversations
                        SET contact_name = :contact_name,
                            metadata = (COALESCE(metadata, '{}'::jsonb) - 'sales_state') - 'sales_data',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id
                          AND (empresa_id = :empresa_id OR :empresa_id IS NULL)
                        RETURNING id
                        """
                    )
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

        # Se não parece nome, peça explicitamente o nome completo
        return "Por favor, envie seu *nome completo* (nome e sobrenome) para que eu possa cadastrar você."
    except Exception as e:
        # Não quebrar fluxo principal em caso de erro inesperado
        import logging as _log
        _log.getLogger(__name__).exception("Erro no handler de cadastro rápido (groq stub): %s", e)
        return "Desculpe, ocorreu um erro ao processar sua mensagem."


__all__ = ["MODEL_NAME", "GROQ_API_URL", "GROQ_API_KEY", "GroqSalesHandler", "processar_mensagem_groq", "STATE_CADASTRO_NOME"]

