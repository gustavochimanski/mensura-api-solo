from app.api.mensura.models.empresa_model import EmpresaModel
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List

class EmpresaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_empresa_by_id(self, empresa_id: int) -> Optional[EmpresaModel]:
        return (self.db.query(EmpresaModel)
                .options(joinedload(EmpresaModel.endereco))
                .filter(EmpresaModel.id == empresa_id).first())

    def get_cnpj_by_id(self, emp_id: int) -> Optional[str]:
        return self.db.query(EmpresaModel.cnpj).filter(EmpresaModel.id == emp_id).scalar()

    def get_emp_by_cnpj(self, cnpj: str) -> Optional[EmpresaModel]:
        return (
            self.db.query(EmpresaModel)
            .options(joinedload(EmpresaModel.endereco))
            .filter(EmpresaModel.cnpj == cnpj)
            .first()
        )

    def list(self, skip: int = 0, limit: int = 100) -> List[EmpresaModel]:
        return (
            self.db.query(EmpresaModel)
            .options(joinedload(EmpresaModel.endereco))
            .offset(skip)
            .limit(limit)
            .distinct()
            .all()
        )

    def list_by_ids(self, ids: List[int]) -> List[EmpresaModel]:
        return (
            self.db
            .query(EmpresaModel)
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