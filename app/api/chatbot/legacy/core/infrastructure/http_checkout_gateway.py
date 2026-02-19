"""
Gateway HTTP de Checkout (Infrastructure).

Extrai a chamada ao endpoint `/api/pedidos/client/checkout` para fora do handler,
mantendo a mesma lógica e mensagens para migração incremental.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Union

import httpx
from sqlalchemy.orm import Session


CheckoutResult = Union[int, Dict[str, Any], None]


class HttpCheckoutGateway:
    def __init__(self, db: Session, *, empresa_id: int, checkout_url: str = "http://localhost:8000/api/pedidos/client/checkout"):
        self.db = db
        self.empresa_id = empresa_id
        self.checkout_url = checkout_url

    async def criar_pedido(self, *, user_id: str, dados: Dict[str, Any], super_token: str, cliente_id: int) -> CheckoutResult:
        """
        Cria pedido via endpoint de checkout.

        OBS: este gateway assume que o carrinho temporário está no banco e que a conversão
        é feita por `CarrinhoService.converter_para_checkout`.
        """
        try:
            from app.api.chatbot.services.service_carrinho import CarrinhoService
            from app.api.catalogo.adapters.produto_adapter import ProdutoAdapter
            from app.api.catalogo.adapters.complemento_adapter import ComplementoAdapter
            from app.api.catalogo.adapters.receitas_adapter import ReceitasAdapter
            from app.api.catalogo.adapters.combo_adapter import ComboAdapter
            from app.api.chatbot.repositories.repo_carrinho import CarrinhoRepository

            produto_contract = ProdutoAdapter(self.db)
            complemento_contract = ComplementoAdapter(self.db)
            receitas_contract = ReceitasAdapter(self.db)
            combo_contract = ComboAdapter(self.db)

            carrinho_service = CarrinhoService(
                db=self.db,
                produto_contract=produto_contract,
                complemento_contract=complemento_contract,
                receitas_contract=receitas_contract,
                combo_contract=combo_contract,
            )

            carrinho = carrinho_service.obter_carrinho(user_id, self.empresa_id)
            if not carrinho:
                return None

            carrinho_repo = CarrinhoRepository(self.db)
            carrinho_model = carrinho_repo.get_by_id(carrinho.id, load_items=True)
            if not carrinho_model:
                return None

            payload = carrinho_service.converter_para_checkout(carrinho_model, cliente_id=cliente_id)

            meio_pagamento_id = dados.get("meio_pagamento_id") or getattr(carrinho_model, "meio_pagamento_id", None)
            if meio_pagamento_id:
                total = float(getattr(carrinho_model, "valor_total", 0.0) or 0.0)
                payload["meios_pagamento"] = [{"id": meio_pagamento_id, "valor": total}]

            # Log útil (mantém a transparência do fluxo atual)
            try:
                _ = json.dumps(payload, indent=2, default=str)
            except Exception:
                pass

            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Content-Type": "application/json", "X-Super-Token": super_token}
                response = await client.post(self.checkout_url, json=payload, headers=headers)

                if response.status_code == 201:
                    result = response.json()
                    pedido_id = result.get("id")
                    if pedido_id:
                        carrinho_service.limpar_carrinho(user_id, self.empresa_id)
                    return pedido_id

                try:
                    error_json = response.json()
                    error_detail = error_json.get("detail", "Erro desconhecido")
                except Exception:
                    error_detail = response.text
                return {"erro": True, "mensagem": error_detail}

        except httpx.TimeoutException:
            return {"erro": True, "mensagem": "Tempo esgotado ao processar pedido. Tente novamente."}
        except Exception:
            return {"erro": True, "mensagem": "Erro interno ao processar pedido."}
