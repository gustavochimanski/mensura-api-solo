from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.mesas.services.service_pedidos_mesa import PedidoMesaService
from app.api.mesas.contracts.pedidos_mesa_contract import IMesaPedidosContract
from app.api.mesas.adapters.pedidos_mesa_adapter import MesaPedidosAdapter
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.catalogo.contracts.adicional_contract import IAdicionalContract
from app.api.catalogo.contracts.combo_contract import IComboContract
from app.api.cadastros.contracts.dependencies import (
    get_produto_contract, 
    get_adicional_contract,
    get_combo_contract,
)


def get_mesa_pedidos_contract(db: Session = Depends(get_db)) -> IMesaPedidosContract:
    """Dependency para obter o contrato de pedidos de mesa"""
    return MesaPedidosAdapter(db)


def get_pedido_mesa_service(
    db: Session = Depends(get_db),
    produto_contract: IProdutoContract = Depends(get_produto_contract),
    adicional_contract: IAdicionalContract = Depends(get_adicional_contract),
    combo_contract: IComboContract = Depends(get_combo_contract),
) -> PedidoMesaService:
    return PedidoMesaService(
        db,
        produto_contract=produto_contract,
        adicional_contract=adicional_contract,
        combo_contract=combo_contract,
    )


