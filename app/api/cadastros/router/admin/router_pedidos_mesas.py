from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.pedidos.models.model_pedido_unificado import TipoEntrega
from app.api.cadastros.schemas.schema_mesa import PedidoAbertoMesa
from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from decimal import Decimal

router = APIRouter(
    prefix="/api/mesas/admin/pedidos",
    tags=["Admin - Pedidos Mesas"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/", response_model=List[PedidoAbertoMesa])
def listar_pedidos_mesas(
    empresa_id: int = Query(..., description="ID da empresa", gt=0),
    mesa_id: Optional[int] = Query(None, description="ID da mesa para filtrar"),
    db: Session = Depends(get_db),
):
    """
    Lista pedidos abertos de mesas.
    
    - **empresa_id**: ID da empresa (obrigatório)
    - **mesa_id**: ID da mesa para filtrar (opcional). Se não informado, retorna pedidos de todas as mesas.
    
    Retorna lista de pedidos abertos (mesa e balcão) associados às mesas da empresa.
    """
    pedido_repo = PedidoRepository(db)
    
    todos_pedidos = []
    
    if mesa_id:
        # Lista pedidos de uma mesa específica
        pedidos_mesa = pedido_repo.list_abertos_by_mesa(
            mesa_id, TipoEntrega.MESA, empresa_id=empresa_id
        )
        pedidos_balcao = pedido_repo.list_abertos_by_mesa(
            mesa_id, TipoEntrega.BALCAO, empresa_id=empresa_id
        )
        
        # Adiciona pedidos de mesa
        for pedido in pedidos_mesa:
            todos_pedidos.append(
                PedidoAbertoMesa(
                    id=pedido.id,
                    numero_pedido=getattr(pedido, "numero_pedido", None) or str(pedido.id),
                    status=pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status),
                    num_pessoas=pedido.num_pessoas if hasattr(pedido, "num_pessoas") else None,
                    valor_total=pedido.valor_total or Decimal("0"),
                    cliente_id=pedido.cliente_id,
                    cliente_nome=pedido.cliente.nome if pedido.cliente else None,
                )
            )
        
        # Adiciona pedidos de balcão
        for pedido in pedidos_balcao:
            todos_pedidos.append(
                PedidoAbertoMesa(
                    id=pedido.id,
                    numero_pedido=getattr(pedido, "numero_pedido", None) or str(pedido.id),
                    status=pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status),
                    num_pessoas=None,  # Balcão geralmente não tem num_pessoas
                    valor_total=pedido.valor_total or Decimal("0"),
                    cliente_id=pedido.cliente_id,
                    cliente_nome=pedido.cliente.nome if pedido.cliente else None,
                )
            )
    else:
        # Lista todos os pedidos abertos de mesas da empresa
        pedidos_mesa = pedido_repo.list_abertos_all(TipoEntrega.MESA, empresa_id=empresa_id)
        pedidos_balcao = pedido_repo.list_abertos_all(TipoEntrega.BALCAO, empresa_id=empresa_id)
        
        # Adiciona pedidos de mesa
        for pedido in pedidos_mesa:
            todos_pedidos.append(
                PedidoAbertoMesa(
                    id=pedido.id,
                    numero_pedido=getattr(pedido, "numero_pedido", None) or str(pedido.id),
                    status=pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status),
                    num_pessoas=pedido.num_pessoas if hasattr(pedido, "num_pessoas") else None,
                    valor_total=pedido.valor_total or Decimal("0"),
                    cliente_id=pedido.cliente_id,
                    cliente_nome=pedido.cliente.nome if pedido.cliente else None,
                )
            )
        
        # Adiciona pedidos de balcão
        for pedido in pedidos_balcao:
            todos_pedidos.append(
                PedidoAbertoMesa(
                    id=pedido.id,
                    numero_pedido=getattr(pedido, "numero_pedido", None) or str(pedido.id),
                    status=pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status),
                    num_pessoas=None,  # Balcão geralmente não tem num_pessoas
                    valor_total=pedido.valor_total or Decimal("0"),
                    cliente_id=pedido.cliente_id,
                    cliente_nome=pedido.cliente.nome if pedido.cliente else None,
                )
            )
    
    return todos_pedidos

