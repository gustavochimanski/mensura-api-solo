"""
Dependencies para services de pedidos.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.pedidos.services.service_pedidos import PedidoService
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.cadastros.contracts.dependencies import get_produto_contract


def get_pedido_service(
    db: Session = Depends(get_db),
    produto_contract: IProdutoContract = Depends(get_produto_contract),
) -> PedidoService:
    """Retorna uma instância do PedidoService."""
    return PedidoService(db=db, produto_contract=produto_contract)

