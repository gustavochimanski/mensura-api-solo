from sqlalchemy.orm import Session

from app.api.delivery.models.pedido_dv_model import PedidoDeliveryModel


class PedidoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, id: int) -> PedidoDeliveryModel:
        return self.db.query(PedidoDeliveryModel).filter_by(id=id).first()

    def atualizar_status(self, pedido: PedidoDeliveryModel, novo_status: str):
        pedido.status = novo_status
        self.db.commit()
        self.db.refresh(pedido)
        return pedido
