from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.pedidos.services.service_pedido import PedidoService
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
# Migrado para modelos unificados - contratos de mesa e balcão não são mais necessários


def get_pedido_service(
    db: Session = Depends(get_db),
    empresa_contract: IEmpresaContract = Depends(get_empresa_contract),
    regiao_contract: IRegiaoEntregaContract = Depends(get_regiao_entrega_contract),
    produto_contract: IProdutoContract = Depends(get_produto_contract),
    adicional_contract: IAdicionalContract = Depends(get_adicional_contract),
    combo_contract: IComboContract = Depends(get_combo_contract),
) -> PedidoService:
    return PedidoService(
        db,
        empresa_contract=empresa_contract,
        regiao_contract=regiao_contract,
        produto_contract=produto_contract,
        adicional_contract=adicional_contract,
        combo_contract=combo_contract,
    )


