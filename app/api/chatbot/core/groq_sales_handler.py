"""Real Groq sales handler: integra com a API Groq (chat completions).
Fornece extração de nome por modelo e mantém compatibilidade com o fluxo de
cadastro rápido (STATE_CADASTRO_NOME). Em caso de falha na Groq, usa heurística
local como fallback.
"""
from typing import Optional, Any, Dict
import json
import logging

import httpx

from app.config.settings import MODEL_NAME, GROQ_API_URL, GROQ_API_KEY, STATE_CADASTRO_NOME

logging.getLogger(__name__)


class GroqSalesHandler:
    def __init__(self, model: str = MODEL_NAME, api_url: str = GROQ_API_URL, api_key: str = GROQ_API_KEY, timeout: float = 30.0):
        self.model = model
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout

    async def _call_groq(self, messages: list, temperature: float = 0.0) -> Dict[str, Any]:
        """Chama a Groq (API compatível com OpenAI chat completions)."""
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self.api_url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def extract_full_name(self, mensagem: str) -> Optional[str]:
        """
        Pergunta ao modelo para extrair o nome completo.
        Retorna string com nome completo ou None se não identificado.
        """
        system = (
            "Você é um assistente que extrai nomes completos de mensagens de usuário. "
            "Responda exclusivamente com um JSON válido no formato: {\"full_name\": \"Nome Sobrenome\"} "
            "ou {\"full_name\": null} quando não houver um nome completo. "
            "Não inclua texto adicional."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": mensagem},
        ]
        try:
            result = await self._call_groq(messages, temperature=0.0)
            assistant_message = result["choices"][0]["message"]["content"]
            # Tentar parsear JSON retornado
            parsed = json.loads(assistant_message)
            full_name = parsed.get("full_name")
            if full_name:
                # limpeza simples
                return full_name.strip()
        except Exception:
            # fallback será aplicado pelo chamador
            pass
        return None


async def processar_mensagem_groq(*args, **kwargs) -> Optional[Any]:
    """
    Implementação real:
    - Se ativo fluxo STATE_CADASTRO_NOME, tenta extrair nome via Groq e cria/atualiza cliente.
    - Caso contrário, delega a Groq para gerar uma resposta simples ao usuário.
    """
    db = kwargs.get("db")
    user_id = kwargs.get("user_id")
    mensagem = (kwargs.get("mensagem") or "").strip()
    empresa_id = kwargs.get("empresa_id")
    state = kwargs.get("state") or kwargs.get("sales_state")

    if not mensagem or not user_id or not db:
        return "Desculpe, não consegui processar. Pode repetir?"

    handler = GroqSalesHandler()

    try:
        # Se for fluxo de cadastro por nome, priorizamos extração do nome
        if state == STATE_CADASTRO_NOME:
            # Tentar extrair nome via Groq
            full_name = await handler.extract_full_name(mensagem)

            # Heurística local como fallback (pelo menos duas palavras com letras)
            if not full_name:
                parts = [p for p in mensagem.split() if any(ch.isalpha() for ch in p)]
                if len(parts) >= 2 and all(len(p) >= 2 for p in parts):
                    full_name = " ".join(parts)

            if full_name:
                try:
                    # Cria ou busca cliente usando serviço da aplicação (mantém regras de negócio)
                    from app.api.cadastros.services.service_cliente import ClienteService
                    from app.api.cadastros.schemas.schema_cliente import ClienteCreate
                    from app.utils.telefone import normalizar_telefone_para_armazenar
                    from sqlalchemy import text

                    phone_canon = normalizar_telefone_para_armazenar(user_id) or "".join(filter(str.isdigit, str(user_id)))

                    service = ClienteService(db)
                    cliente_payload = ClienteCreate(nome=full_name, telefone=phone_canon)
                    try:
                        cliente_obj = service.create(cliente_payload)
                    except Exception:
                        # se já existe, tentar buscar diretamente
                        cliente_obj = None
                        try:
                            q = text("SELECT id, nome, telefone FROM cadastros.clientes WHERE telefone = :telefone LIMIT 1")
                            row = db.execute(q, {"telefone": phone_canon}).fetchone()
                            cliente_obj = row
                        except Exception:
                            cliente_obj = None

                    # Atualizar conversa: set contact_name e remover sales_state/sales_data
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
                        db.execute(update_conv, {"contact_name": full_name, "user_id": phone_canon, "empresa_id": empresa_id})
                        db.commit()
                    except Exception:
                        try:
                            db.rollback()
                        except Exception:
                            pass

                    created_info = None
                    try:
                        if hasattr(cliente_obj, "__dict__"):
                            created_info = {"id": getattr(cliente_obj, "id", None), "nome": getattr(cliente_obj, "nome", None), "telefone": getattr(cliente_obj, "telefone", None)}
                        elif isinstance(cliente_obj, (list, tuple)):
                            created_info = {"id": cliente_obj[0], "nome": cliente_obj[1], "telefone": cliente_obj[2] if len(cliente_obj) > 2 else None}
                        elif isinstance(cliente_obj, dict):
                            created_info = {"id": cliente_obj.get("id"), "nome": cliente_obj.get("nome"), "telefone": cliente_obj.get("telefone")}
                    except Exception:
                        created_info = None

                    return {
                        "message": f"Obrigado {full_name.split()[0]}! Seu cadastro foi realizado com sucesso. Posso te ajudar com o pedido?",
                        "created_cliente": created_info,
                    }
                except Exception as e:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                    logging.getLogger(__name__).exception("Erro ao criar cliente: %s", e)
                    return "Desculpe, houve um erro ao salvar seu cadastro. Tente novamente em instantes."

            # Se não identificou nome, pedir explicitamente
            return "Por favor, envie seu *nome completo* (nome e sobrenome) para que eu possa cadastrar você."

        # Fluxo genérico: pedir resposta da Groq para gerar mensagem ao usuário
        system_prompt = (
            "Você é um assistente de vendas que responde de forma curta e educada ao usuário. "
            "Se não souber a resposta, peça esclarecimentos. Responda em português."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": mensagem},
        ]
        try:
            result = await handler._call_groq(messages)
            assistant_message = result["choices"][0]["message"]["content"]
            return assistant_message
        except Exception:
            # fallback simples
            return "Desculpe, não consegui processar sua mensagem agora. Pode repetir?"

    except Exception as e:
        logging.getLogger(__name__).exception("Erro no handler Groq: %s", e)
        return "Desculpe, ocorreu um erro ao processar sua mensagem."


__all__ = ["MODEL_NAME", "GROQ_API_URL", "GROQ_API_KEY", "GroqSalesHandler", "processar_mensagem_groq", "STATE_CADASTRO_NOME"]

