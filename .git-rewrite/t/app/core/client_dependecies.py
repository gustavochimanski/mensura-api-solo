from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.database.db_connection import get_db

def get_cliente_by_super_token(
    x_super_token: str = Header(...),
    db: Session = Depends(get_db)
) -> ClienteModel:
    cliente = db.query(ClienteModel).filter_by(super_token=x_super_token).first()
    if not cliente:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    return cliente

def get_cliente_by_super_token_optional(
    x_super_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[ClienteModel]:
    """
    Versão opcional que retorna None se não houver token ou se o token for inválido.
    Útil para endpoints que aceitam tanto admin quanto cliente.
    """
    if not x_super_token:
        return None
    
    cliente = db.query(ClienteModel).filter_by(super_token=x_super_token).first()
    return cliente if cliente else None
