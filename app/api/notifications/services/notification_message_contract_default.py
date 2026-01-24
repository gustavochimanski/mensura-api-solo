from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime, timedelta

from ..contracts.notification_message_contract import INotificationMessageContract
from ..schemas.whatsapp_message_schemas import WhatsAppNotificationMessageSpec


class DefaultNotificationMessageContract(INotificationMessageContract):
    """Implementação padrão do contract de mensagens de notificação."""

    @staticmethod
    def _teve_interacao_cliente_ultimas_24h(*, phone: str, empresa_id: Optional[str]) -> bool:
        """
        Retorna True se houver mensagem do cliente (role='user') nas últimas 24h no chat interno.
        """
        if not empresa_id:
            return False

        try:
            from sqlalchemy import text
            from app.database.db_connection import SessionLocal
            from app.api.chatbot.core.config_whatsapp import format_phone_number

            phone_norm = format_phone_number(phone)
            cutoff = datetime.utcnow() - timedelta(hours=24)

            db = SessionLocal()
            try:
                # Considera interação do cliente como mensagem "user" recente
                q = text(
                    """
                    SELECT 1
                    FROM chatbot.messages m
                    JOIN chatbot.conversations c ON c.id = m.conversation_id
                    WHERE c.user_id = :user_id
                      AND c.empresa_id = :empresa_id
                      AND m.role = 'user'
                      AND m.created_at >= :cutoff
                    LIMIT 1
                    """
                )
                row = db.execute(
                    q,
                    {"user_id": phone_norm, "empresa_id": int(empresa_id), "cutoff": cutoff},
                ).fetchone()
                return row is not None
            finally:
                db.close()
        except Exception:
            # Em caso de erro, não arrisca trocar automaticamente para template
            return False

    def build_whatsapp_payload(
        self,
        *,
        recipient_phone: str,
        title: str,
        message: str,
        is_360: bool,
        channel_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Normaliza spec em channel_metadata["whatsapp"] (mantém compatibilidade)
        raw_spec = (channel_metadata or {}).get("whatsapp") if isinstance(channel_metadata, dict) else None

        # Default: envia texto (modo legado)
        spec = WhatsAppNotificationMessageSpec.model_validate(raw_spec or {"mode": "text"})

        # Se for template, só usa template se NÃO houve interação do cliente nas últimas 24h.
        # Caso tenha havido interação, envia como texto normal (mais simples/barato e evita template desnecessário).
        empresa_id = (channel_metadata or {}).get("_empresa_id") if isinstance(channel_metadata, dict) else None
        teve_interacao = self._teve_interacao_cliente_ultimas_24h(
            phone=recipient_phone,
            empresa_id=str(empresa_id) if empresa_id is not None else None,
        )
        if spec.mode == "template" and teve_interacao:
            spec = WhatsAppNotificationMessageSpec.model_validate({"mode": "text"})

        full_message = f"*{title}*\n\n{message}"

        if spec.mode == "template":
            tpl = spec.template
            components = tpl.components
            if components is None and tpl.body_parameters is not None:
                components = [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": p} for p in tpl.body_parameters],
                    }
                ]
            # Se não há components/body_parameters, enviamos o template "seco" (sem variáveis)
            template_obj: Dict[str, Any] = {
                "name": tpl.name,
                "language": {"code": tpl.language},
            }
            if components is not None:
                template_obj["components"] = components

            # 360dialog e Meta aceitam formato muito similar para template
            payload: Dict[str, Any] = {
                "to": recipient_phone,
                "type": "template",
                "template": template_obj,
            }
            if not is_360:
                payload["messaging_product"] = "whatsapp"
            else:
                # 360dialog costuma aceitar o campo também; manter não atrapalha compatibilidade
                payload.setdefault("messaging_product", "whatsapp")
            return payload

        # mode == "text"
        if is_360:
            return {
                "to": recipient_phone,
                "type": "text",
                "text": {"body": full_message},
            }

        return {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "text",
            "text": {
                "preview_url": bool(spec.preview_url),
                "body": full_message,
            },
        }

