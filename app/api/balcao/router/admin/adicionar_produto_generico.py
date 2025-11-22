from fastapi import APIRouter, Depends, Path, status, Body
from sqlalchemy.orm import Session

from app.core.admin_dependencies import get_current_user
from app.database.db_connection import get_db
from app.api.balcao.schemas.schema_pedido_balcao import (
    PedidoBalcaoOut,
    AdicionarProdutoGenericoRequest,
)
from app.api.balcao.services.service_pedidos_balcao import PedidoBalcaoService
from app.api.balcao.services.dependencies import get_pedido_balcao_service
from app.api.cadastros.models.user_model import UserModel


router = APIRouter(
    prefix="/api/balcao/admin/pedidos",
    tags=["Admin - Balcão - Pedidos"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/{pedido_id:int}/produtos",
    response_model=PedidoBalcaoOut,
    summary="Adicionar produto genérico ao pedido",
    description="""
    Adiciona qualquer tipo de produto ao pedido de balcão (produto normal, receita ou combo).
    O sistema identifica automaticamente o tipo baseado nos campos preenchidos.
    
    **Regras de identificação:**
    - Se `produto_cod_barras` estiver presente → Item normal (produto)
    - Se `receita_id` estiver presente → Receita
    - Se `combo_id` estiver presente → Combo
    
    **Validações:**
    - Pedido deve estar aberto (não pode ser CANCELADO ou ENTREGUE)
    - Apenas um tipo de produto deve ser informado
    - Produto/Receita/Combo deve existir e estar disponível
    - Deve pertencer à empresa do pedido
    - Quantidade deve ser maior que zero
    
    **Adicionais:**
    - Podem ser informados para qualquer tipo de produto
    - Use `adicionais` (novo formato) com quantidade por adicional
    - Ou `adicionais_ids` (legado) com quantidade implícita = 1
    
    **Atualização automática:** O valor total do pedido é recalculado automaticamente.
    """,
    responses={
        200: {"description": "Produto adicionado com sucesso"},
        400: {
            "description": "Pedido fechado/cancelado, dados inválidos ou múltiplos tipos informados"
        },
        404: {"description": "Pedido, produto, receita ou combo não encontrado"}
    }
)
def adicionar_produto_generico(
    pedido_id: int = Path(..., description="ID do pedido", gt=0),
    body: AdicionarProdutoGenericoRequest = Body(
        ..., 
        description="Dados do produto a ser adicionado (produto, receita ou combo)"
    ),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    svc: PedidoBalcaoService = Depends(get_pedido_balcao_service),
):
    """Adiciona um produto genérico (produto, receita ou combo) ao pedido de balcão"""
    return svc.adicionar_produto_generico(pedido_id, body, usuario_id=current_user.id)

