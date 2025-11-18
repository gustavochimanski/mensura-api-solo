from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.db_connection import get_db

from app.api.empresas.contracts.empresa_contract import IEmpresaContract
from .regiao_entrega_contract import IRegiaoEntregaContract
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from .cliente_contract import IClienteContract
from .entregador_contract import IEntregadorContract
from app.api.catalogo.contracts.adicional_contract import IAdicionalContract
from app.api.catalogo.contracts.combo_contract import IComboContract

from app.api.empresas.adapters.empresa_adapter import EmpresaAdapter
from app.api.cadastros.adapters.regiao_entrega_adapter import RegiaoEntregaAdapter
from app.api.catalogo.adapters.produto_adapter import ProdutoAdapter
from app.api.cadastros.adapters.cliente_adapter import ClienteAdapter
from app.api.cadastros.adapters.entregador_adapter import EntregadorAdapter
from app.api.catalogo.adapters.adicional_adapter import AdicionalAdapter
from app.api.catalogo.adapters.combo_adapter import ComboAdapter


def get_empresa_contract(db: Session = Depends(get_db)) -> IEmpresaContract:
    return EmpresaAdapter(db)


def get_regiao_entrega_contract(db: Session = Depends(get_db)) -> IRegiaoEntregaContract:
    return RegiaoEntregaAdapter(db)


def get_produto_contract(db: Session = Depends(get_db)) -> IProdutoContract:
    return ProdutoAdapter(db)


def get_cliente_contract(db: Session = Depends(get_db)) -> IClienteContract:
    return ClienteAdapter(db)


def get_entregador_contract(db: Session = Depends(get_db)) -> IEntregadorContract:
    return EntregadorAdapter(db)


def get_adicional_contract(db: Session = Depends(get_db)) -> IAdicionalContract:
    return AdicionalAdapter(db)


def get_combo_contract(db: Session = Depends(get_db)) -> IComboContract:
    return ComboAdapter(db)


