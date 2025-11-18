from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.cardapio.services.pedidos.service_pedido import PedidoService
from app.api.empresas.contracts.empresa_contract import IEmpresaContract
from app.api.cadastros.contracts.regiao_entrega_contract import IRegiaoEntregaContract
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.cadastros.contracts.dependencies import (
    get_empresa_contract,
    get_regiao_entrega_contract,
    get_produto_contract,
    get_adicional_contract,
    get_combo_contract,
)
from app.api.catalogo.contracts.adicional_contract import IAdicionalContract
from app.api.catalogo.contracts.combo_contract import IComboContract
from app.api.mesas.contracts.pedidos_mesa_contract import IMesaPedidosContract
from app.api.mesas.services.dependencies import get_mesa_pedidos_contract
from app.api.balcao.contracts.pedidos_balcao_contract import IBalcaoPedidosContract
from app.api.balcao.adapters.pedidos_balcao_adapter import BalcaoPedidosAdapter


def get_balcao_pedidos_contract(db: Session = Depends(get_db)) -> IBalcaoPedidosContract:
    """Dependency para obter o contrato de pedidos de balcão"""
    return BalcaoPedidosAdapter(db)


def get_pedido_service(
    db: Session = Depends(get_db),
    empresa_contract: IEmpresaContract = Depends(get_empresa_contract),
    regiao_contract: IRegiaoEntregaContract = Depends(get_regiao_entrega_contract),
    produto_contract: IProdutoContract = Depends(get_produto_contract),
    adicional_contract: IAdicionalContract = Depends(get_adicional_contract),
    combo_contract: IComboContract = Depends(get_combo_contract),
    mesa_contract: IMesaPedidosContract = Depends(get_mesa_pedidos_contract),
    balcao_contract: IBalcaoPedidosContract = Depends(get_balcao_pedidos_contract),
) -> PedidoService:
    return PedidoService(
        db,
        empresa_contract=empresa_contract,
        regiao_contract=regiao_contract,
        produto_contract=produto_contract,
        adicional_contract=adicional_contract,
        combo_contract=combo_contract,
        mesa_contract=mesa_contract,
        balcao_contract=balcao_contract,
    )


