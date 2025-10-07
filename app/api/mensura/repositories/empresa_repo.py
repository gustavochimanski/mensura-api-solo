# app/api/mensura/repositories/empresa_repo.py
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from app.api.mensura.models.empresa_model import EmpresaModel


class EmpresaRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, skip: int = 0, limit: int = 100) -> List[EmpresaModel]:
        q = (
            self.db.query(EmpresaModel)
            .options(joinedload(EmpresaModel.endereco))
            .offset(skip)
        )
        if limit:
            q = q.limit(limit)
        return q.all()

    def list_by_ids(self, ids: List[int]) -> List[EmpresaModel]:
        if not ids:
            return []
        return (
            self.db.query(EmpresaModel)
            .filter(EmpresaModel.id.in_(ids))
            .all()
        )

    def create(self, empresa: EmpresaModel) -> EmpresaModel:
        self.db.add(empresa)
        self.db.commit()
        self.db.refresh(empresa)
        return empresa

    def update(self, empresa: EmpresaModel, data: dict) -> EmpresaModel:
        for key, value in data.items():
            setattr(empresa, key, value)
        self.db.commit()
        self.db.refresh(empresa)
        return empresa

    def delete(self, empresa: EmpresaModel) -> None:
        self.db.delete(empresa)
        self.db.commit()

    def get_empresa_by_id(self, empresa_id: int) -> Optional[EmpresaModel]:
        return (
            self.db.query(EmpresaModel)
            .options(joinedload(EmpresaModel.endereco))
            .filter(EmpresaModel.id == empresa_id)
            .first()
        )

    def get_cnpj_by_id(self, emp_id: int) -> Optional[str]:
        return (
            self.db.query(EmpresaModel.cnpj)
            .filter(EmpresaModel.id == emp_id)
            .scalar()
        )

    def get_emp_by_cnpj(self, cnpj: str | None) -> Optional[EmpresaModel]:
        if not cnpj:
            return None
        return (
            self.db.query(EmpresaModel)
            .options(joinedload(EmpresaModel.endereco))
            .filter(EmpresaModel.cnpj == cnpj)
            .first()
        )

    def get_emp_by_slug(self, slug: str) -> Optional[EmpresaModel]:
        return (
            self.db.query(EmpresaModel)
            .filter(EmpresaModel.slug == slug)
            .first()
        )


    def get_first(self):
        return self.db.query(EmpresaModel).first()

    def list_cardapio_links(self) -> List[tuple[int, str, str, str]]:
        return (
            self.db.query(
                EmpresaModel.id,
                EmpresaModel.nome,
                EmpresaModel.cardapio_link,
                EmpresaModel.cardapio_tema,
            )
            .order_by(EmpresaModel.nome.asc())
            .all()
        )