from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.pedidos.services.service_pedido import PedidoService
from app.api.pedidos.services.service_pedidos_mesa import PedidoMesaService
from app.api.pedidos.services.service_pedidos_balcao import PedidoBalcaoService
from app.api.pedidos.services.service_pedido_admin import PedidoAdminService
from app.api.empresas.contracts.empresa_contract import IEmpresaContract
from app.api.cadastros.contracts.regiao_entrega_contract import IRegiaoEntregaContract
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.cadastros.contracts.dependencies import (
    get_empresa_contract,
    get_regiao_entrega_contract,
    get_produto_contract,
    get_adicional_contract,
    get_complemento_contract,
    get_combo_contract,
)
from app.api.catalogo.contracts.adicional_contract import IAdicionalContract
from app.api.catalogo.contracts.complemento_contract import IComplementoContract
from app.api.catalogo.contracts.combo_contract import IComboContract
# Migrado para modelos unificados - contratos de mesa e balcão não são mais necessários


def get_pedido_service(
    db: Session = Depends(get_db),
    empresa_contract: IEmpresaContract = Depends(get_empresa_contract),
    regiao_contract: IRegiaoEntregaContract = Depends(get_regiao_entrega_contract),
    produto_contract: IProdutoContract = Depends(get_produto_contract),
    adicional_contract: IAdicionalContract = Depends(get_adicional_contract),
    complemento_contract: IComplementoContract = Depends(get_complemento_contract),
    combo_contract: IComboContract = Depends(get_combo_contract),
) -> PedidoService:
    return PedidoService(
        db,
        empresa_contract=empresa_contract,
        regiao_contract=regiao_contract,
        produto_contract=produto_contract,
        adicional_contract=adicional_contract,
        complemento_contract=complemento_contract,
        combo_contract=combo_contract,
    )


def get_pedido_mesa_service(
    db: Session = Depends(get_db),
    produto_contract: IProdutoContract = Depends(get_produto_contract),
    adicional_contract: IAdicionalContract = Depends(get_adicional_contract),
    complemento_contract: IComplementoContract = Depends(get_complemento_contract),
    combo_contract: IComboContract = Depends(get_combo_contract),
) -> PedidoMesaService:
    return PedidoMesaService(
        db,
        produto_contract=produto_contract,
        adicional_contract=adicional_contract,
        complemento_contract=complemento_contract,
        combo_contract=combo_contract,
    )


def get_pedido_balcao_service(
    db: Session = Depends(get_db),
    produto_contract: IProdutoContract = Depends(get_produto_contract),
    adicional_contract: IAdicionalContract = Depends(get_adicional_contract),
    complemento_contract: IComplementoContract = Depends(get_complemento_contract),
    combo_contract: IComboContract = Depends(get_combo_contract),
) -> PedidoBalcaoService:
    return PedidoBalcaoService(
        db,
        produto_contract=produto_contract,
        adicional_contract=adicional_contract,
        complemento_contract=complemento_contract,
        combo_contract=combo_contract,
    )


def get_pedido_admin_service(
    db: Session = Depends(get_db),
    empresa_contract: IEmpresaContract = Depends(get_empresa_contract),
    regiao_contract: IRegiaoEntregaContract = Depends(get_regiao_entrega_contract),
    produto_contract: IProdutoContract = Depends(get_produto_contract),
    adicional_contract: IAdicionalContract = Depends(get_adicional_contract),
    complemento_contract: IComplementoContract = Depends(get_complemento_contract),
    combo_contract: IComboContract = Depends(get_combo_contract),
) -> PedidoAdminService:
    pedido_service = PedidoService(
        db,
        empresa_contract=empresa_contract,
        regiao_contract=regiao_contract,
        produto_contract=produto_contract,
        adicional_contract=adicional_contract,
        complemento_contract=complemento_contract,
        combo_contract=combo_contract,
    )
    mesa_service = PedidoMesaService(
        db,
        produto_contract=produto_contract,
        adicional_contract=adicional_contract,
        complemento_contract=complemento_contract,
        combo_contract=combo_contract,
    )
    balcao_service = PedidoBalcaoService(
        db,
        produto_contract=produto_contract,
        adicional_contract=adicional_contract,
        complemento_contract=complemento_contract,
        combo_contract=combo_contract,
    )
    return PedidoAdminService(
        db=db,
        pedido_service=pedido_service,
        mesa_service=mesa_service,
        balcao_service=balcao_service,
    )


