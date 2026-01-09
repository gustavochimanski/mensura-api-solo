from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.api.cadastros.models.model_cliente_dv import ClienteModel

class ClienteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_token(self, token: str) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter_by(super_token=token).first()

    def get_by_telefone(self, telefone: str) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter_by(telefone=telefone).first()

    def get_by_email(self, email: str) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter_by(email=email).first()

    def get_by_cpf(self, cpf: str) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter_by(cpf=cpf).first()

    def get_by_id(self, id: int) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter(ClienteModel.id == id).first()

    def list(self, ativo: Optional[bool] = None) -> List[ClienteModel]:
        stmt = select(ClienteModel)
        if ativo is not None:
            stmt = stmt.where(ClienteModel.ativo.is_(ativo))
        return self.db.execute(stmt).scalars().all()

    def create(self, **data) -> ClienteModel:
        obj = ClienteModel(**data)
        self.db.add(obj)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
        self.db.refresh(obj)
        return obj

    def update(self, db_obj: ClienteModel, **data) -> ClienteModel:
        for k, v in data.items():
            setattr(db_obj, k, v)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def set_ativo(self, token: str, ativo: bool) -> Optional[ClienteModel]:
        obj = self.get_by_token(token)
        if not obj:
            return None
        obj.ativo = ativo
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get_enderecos(self, cliente_id: int) -> List:
        """Busca todos os endereços de um cliente específico por ID"""
        from app.api.cadastros.models.model_endereco_dv import EnderecoModel
        return (
            self.db.query(EnderecoModel)
            .filter(EnderecoModel.cliente_id == cliente_id)
            .order_by(EnderecoModel.created_at.desc())
            .all()
        )
