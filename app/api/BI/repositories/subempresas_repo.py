from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.public.models.subempresas_public_model import SubEmpresaPublicModel


class SubEmpresasPublicRepository:
    def __init__(self, db: Session):
        self.db = db


    def get_all_isvendas(self):
        stmt = select(SubEmpresaPublicModel).where(SubEmpresaPublicModel.sube_vendas == 'S')
        result = self.db.execute(stmt)

        return result.scalars().all()
