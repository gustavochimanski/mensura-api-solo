from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class WhatsAppTemplateSpec(BaseModel):
    """
    Especificação de mensagem template do WhatsApp.

    Observação:
    - Para enviar mensagem fora da janela de 24h (ou sem interação prévia do cliente),
      normalmente é necessário usar template aprovado no WhatsApp Manager.
    - `components` é aceito como "raw" (lista de dicts) para flexibilidade.
    - Como atalho, é possível informar `body_parameters` (strings) para montar automaticamente
      o componente "body".
    """

    name: str = Field(..., min_length=1, description="Nome do template aprovado no WhatsApp")
    language: str = Field("pt_BR", min_length=2, description="Código de idioma (ex: pt_BR)")

    # Se informado, o canal monta automaticamente components=[{type: body, parameters: ...}]
    body_parameters: Optional[List[str]] = Field(
        default=None,
        description="Parâmetros (strings) para o componente body do template",
    )

    # Payload raw (opcional) para casos avançados (header/buttons/etc)
    components: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Components do template (raw dicts) no formato da API do WhatsApp",
    )

    @model_validator(mode="after")
    def _ensure_components_or_body_params(self):
        if self.components is None and self.body_parameters is None:
            # Permitimos components/body_parameters ausentes para templates sem variáveis.
            return self
        return self


class WhatsAppNotificationMessageSpec(BaseModel):
    """
    Contract de mensagem WhatsApp usada pelo sistema de notificações.

    - mode=text: envia mensagem de texto comum (pode falhar sem janela de conversa).
    - mode=template: envia template aprovado (suporta envio sem interação prévia).
    """

    mode: Literal["text", "template"] = Field("text", description="Modo de envio do WhatsApp")
    preview_url: bool = Field(False, description="preview_url (apenas para texto, Meta Cloud API)")
    template: Optional[WhatsAppTemplateSpec] = Field(
        default=None,
        description="Especificação de template (obrigatória quando mode=template)",
    )

    @model_validator(mode="after")
    def _validate_template_required(self):
        if self.mode == "template" and not self.template:
            raise ValueError("template é obrigatório quando mode='template'")
        return self
