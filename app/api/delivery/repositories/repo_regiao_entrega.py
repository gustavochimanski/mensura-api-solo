from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.api.delivery.models.model_regiao_entrega import RegiaoEntregaModel

class RegiaoEntregaRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, regiao: RegiaoEntregaModel):
        self.db.add(regiao)
        self.db.commit()
        self.db.refresh(regiao)
        return regiao

    def get(self, regiao_id: int):
        return self.db.query(RegiaoEntregaModel).filter(RegiaoEntregaModel.id == regiao_id).first()

    def update(self, regiao: RegiaoEntregaModel, data: dict):
        for key, value in data.items():
            setattr(regiao, key, value)
        self.db.commit()
        self.db.refresh(regiao)
        return regiao

    def delete(self, regiao: RegiaoEntregaModel):
        self.db.delete(regiao)
        self.db.commit()

    def list_by_empresa(self, empresa_id: int):
        return self.db.query(RegiaoEntregaModel).filter(RegiaoEntregaModel.empresa_id == empresa_id).all()

    def search(self, empresa_id: int, query: str):
        q = f"%{query}%"
        return (
            self.db.query(RegiaoEntregaModel)
            .filter(
                RegiaoEntregaModel.empresa_id == empresa_id,
                or_(
                    RegiaoEntregaModel.bairro.ilike(q),
                    RegiaoEntregaModel.cidade.ilike(q),
                    RegiaoEntregaModel.uf.ilike(q),
                    RegiaoEntregaModel.cep.ilike(q),
                ),
            )
            .all()
        )
