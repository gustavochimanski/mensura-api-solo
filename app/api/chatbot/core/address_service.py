"""Stub for address/addressing service used by chatbot routes."""
from typing import Dict, Any
from sqlalchemy import text


class ChatbotAddressService:
    def __init__(self, db=None, empresa_id: int = None, *args, **kwargs):
        """
        Simple address / client lookup service used by chatbot.
        Expects a SQLAlchemy connection/session as first argument when used in router.
        """
        self.db = db
        self.empresa_id = empresa_id

    def resolve_address(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # return payload unchanged as a safe default
        return payload or {}

    def get_cliente_by_telefone(self, telefone: str) -> Dict[str, Any] | None:
        """
        Busca cliente por telefone no schema `cadastros`.
        Retorna dict com pelo menos 'id' e 'nome' quando encontrado, ou None.
        """
        if not telefone or not self.db:
            return None
        try:
            # Gera variantes para busca (com/sem 55, com/sem 9)
            from app.utils.telefone import variantes_telefone_para_busca

            candidates = variantes_telefone_para_busca(telefone)
            if not candidates:
                candidates = [telefone]

            # Monta IN params
            params = {}
            ph = []
            for i, v in enumerate(candidates):
                k = f"p{i}"
                ph.append(f":{k}")
                params[k] = v

            query = text(f"""
                SELECT id, nome, telefone
                FROM cadastros.clientes
                WHERE telefone IN ({', '.join(ph)})
                LIMIT 1
            """)
            row = self.db.execute(query, params).fetchone()
            if row:
                return {"id": row[0], "nome": row[1], "telefone": row[2]}
        except Exception:
            # silencioso: não quebrar fluxo principal
            pass
        return None

__all__ = ["ChatbotAddressService"]

