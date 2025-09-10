from sqlalchemy.orm import Session
from app.api.delivery.models.model_regiao_entrega import RegiaoEntregaModel

class RegiaoEntregaRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_empresa(self, empresa_id: int):
        return self.db.query(RegiaoEntregaModel).filter_by(empresa_id=empresa_id).all()

    def get(self, regiao_id: int):
        return self.db.query(RegiaoEntregaModel).filter_by(id=regiao_id).first()

    def create(self, regiao: RegiaoEntregaModel):
        self.db.add(regiao)
        self.db.commit()
        self.db.refresh(regiao)
        return regiao

    def update(self, regiao: RegiaoEntregaModel, data: dict):
        for k, v in data.items():
            setattr(regiao, k, v)
        self.db.commit()
        self.db.refresh(regiao)
        return regiao

    def delete(self, regiao: RegiaoEntregaModel):
        self.db.delete(regiao)
        self.db.commit()
