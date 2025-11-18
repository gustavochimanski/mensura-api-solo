from sqlalchemy.orm import Session
from app.api.cadastros.models.model_cupom import CupomDescontoModel

class CupomRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------------- CUPOM ----------------
    def get(self, id_: int):
        return (
            self.db.query(CupomDescontoModel)
            .filter(CupomDescontoModel.id == id_)
            .first()
        )

    def get_by_code(self, codigo: str, empresa_id: int | None = None):
        query = self.db.query(CupomDescontoModel).filter(CupomDescontoModel.codigo == codigo)
        if empresa_id is not None:
            query = query.filter(CupomDescontoModel.empresa_id == empresa_id)
        return query.first()

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
