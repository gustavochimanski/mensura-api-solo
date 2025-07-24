from app.api.mensura.models.empresas_model import EmpresaModel
from sqlalchemy.orm import Session
from typing import Optional

class EmpresaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_empresa_by_id(self, empresa_id: int) -> Optional[EmpresaModel]:
        return self.db.query(EmpresaModel).filter(EmpresaModel.id == empresa_id).first()

    def get_cnpj_by_id(self, emp_id: int) -> Optional[str]:
        return self.db.query(EmpresaModel.cnpj).filter(EmpresaModel.id == emp_id).scalar()
