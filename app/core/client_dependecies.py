from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.api.delivery.models.model_cliente_dv import ClienteDeliveryModel
from app.database.db_connection import get_db

def get_cliente_by_super_token(
    x_super_token: str = Header(...),
    db: Session = Depends(get_db)
) -> ClienteDeliveryModel:
    cliente = db.query(ClienteDeliveryModel).filter_by(super_token=x_super_token).first()
    if not cliente:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    return cliente
