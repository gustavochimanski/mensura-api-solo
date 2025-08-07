# app/api/pedidos/repository.py

from decimal import Decimal
from sqlalchemy.orm import Session

from app.api.delivery.models.cadprod_dv_model import ProdutoDeliveryModel
from app.api.delivery.models.cadprod_emp_dv_model import ProdutoEmpDeliveryModel
from app.api.delivery.models.pedido_dv_model import PedidoDeliveryModel
from app.api.delivery.models.pedido_item_dv_model import PedidoItemModel
from app.api.delivery.schemas.pedidos_schema import ItemPedidoRequest


class PedidoRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar_pedido(self, cliente_id: int | None, empresa_id: int, endereco_id: int | None) -> PedidoDeliveryModel:
        pedido = PedidoDeliveryModel(
            cliente_id=cliente_id,
            empresa_id=empresa_id,
            endereco_id=endereco_id,
            status="P",
            valor_total=Decimal("0.00"),
        )
        self.db.add(pedido)
        self.db.flush()  # gera pedido.id
        return pedido

    def buscar_produto(self, cod_barras: str, empresa_id: int) -> ProdutoEmpDeliveryModel | None:
        return (
            self.db.query(ProdutoEmpDeliveryModel)
            .filter_by(cod_barras=cod_barras, empresa_id=empresa_id)
            .first()
        )

    def criar_item(
        self,
        pedido_id: int,
        item_req: ItemPedidoRequest,
        preco_unitario: Decimal,
    ) -> PedidoItemModel:
        item = PedidoItemModel(
            pedido_id=pedido_id,
            produto_cod_barras=item_req.produto_cod_barras,
            quantidade=item_req.quantidade,
            preco_unitario=preco_unitario,
        )
        # se você tiver coluna observacao no model:
        # item.observacao = item_req.observacao
        self.db.add(item)
        return item

    def commit(self):
        self.db.commit()

    def refresh(self, obj):
        self.db.refresh(obj)
