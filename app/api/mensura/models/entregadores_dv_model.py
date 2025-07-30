from app.database.db_connection import Base


class EntregadoresDeliveryModel(Base):
    __tablename__ = "entregadores_dv"
    __table_args__ = {"schema": "delivery"}