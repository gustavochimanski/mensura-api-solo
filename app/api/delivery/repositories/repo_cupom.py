from typing import Optional, List
from sqlalchemy.orm import Session
from app.api.delivery.models.model_cupom_dv import CupomDescontoModel, CupomLinkModel

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

    # ---------------- LINKS ----------------
    def list_links(self, cupom_id: int) -> List[CupomLinkModel]:
        cupom = self.get(cupom_id)
        return cupom.links if cupom else []

    def add_link(self, cupom: CupomDescontoModel, titulo: str, url: str) -> CupomLinkModel:
        link = CupomLinkModel(cupom=cupom, titulo=titulo, url=url)
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def update_link(self, link: CupomLinkModel, titulo: Optional[str] = None, url: Optional[str] = None) -> CupomLinkModel:
        if titulo:
            link.titulo = titulo
        if url:
            link.url = url
        self.db.commit()
        self.db.refresh(link)
        return link

    def delete_link(self, link: CupomLinkModel):
        self.db.delete(link)
        self.db.commit()
