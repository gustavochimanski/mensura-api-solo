"""
Dependencies para contracts de pedidos.
"""
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.pedidos.contracts.pedidos_contract import IPedidosContract
from app.api.pedidos.adapters.pedidos_adapter import PedidosAdapter


def get_pedidos_contract(db: Session = get_db) -> IPedidosContract:
    """Retorna uma instância do contract de pedidos."""
    return PedidosAdapter(db=db)

