from sqlalchemy.orm import Session
from app.api.delivery.models.model_cupom_dv import CupomDescontoModel

class CupomRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------------- CUPOM ----------------
    def get(self, id_: int):
        return self.db.get(CupomDescontoModel, id_)

    def get_by_code(self, codigo: str):
        return self.db.query(CupomDescontoModel).filter(CupomDescontoModel.codigo == codigo).first()

    def create(self, obj: CupomDescontoModel):
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: CupomDescontoModel):
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: CupomDescontoModel):
        self.db.delete(obj)
        self.db.commit()

    # ---------------- LINKS (legacy removed) ----------------
