# app/api/pedidos/service.py

from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.delivery.models.pedido_dv_model import PedidoDeliveryModel
from app.api.delivery.repositories.pedidos_repo import PedidoRepository
from app.api.delivery.schemas.pedidos_schema import FinalizarPedidoRequest


class PedidoService:
    def __init__(self, db: Session):
        self.repo = PedidoRepository(db)

    def finalizar_pedido(self, payload: FinalizarPedidoRequest) -> PedidoDeliveryModel:
        if not payload.itens:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível finalizar um pedido vazio.",
            )

        # 1) criar pedido
        pedido = self.repo.criar_pedido(
            cliente_id=payload.cliente_id,
            empresa_id=payload.empresa_id,
            endereco_id=payload.endereco_id,
        )

        total = Decimal("0.00")

        # 2) para cada item, buscar produto e criar item de pedido
        for item_req in payload.itens:
            produto = self.repo.buscar_produto(item_req.produto_cod_barras)
            if not produto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Produto {item_req.produto_cod_barras} não encontrado.",
                )

            preco_unitario = produto.preco_venda  # ajuste conforme seu campo real
            total += preco_unitario * item_req.quantidade

            self.repo.criar_item(pedido.id, item_req, preco_unitario)

        # 3) atualizar total (e observação, se tiver campo)
        pedido.valor_total = total
        # pedido.observacao = payload.observacao_geral

        # 4) persistir tudo
        self.repo.commit()
        self.repo.refresh(pedido)
        return pedido
