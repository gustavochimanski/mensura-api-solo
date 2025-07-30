from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.api.mensura.models.empresa_model import EmpresaModel
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.mensura.schemas.empresa_schema import EmpresaCreate, EmpresaUpdate

class EmpresaService:
    def __init__(self, db: Session):
        self.repo_emp = EmpresaRepository(db)

    def get_empresa(self, id: int):
        empresa = self.repo_emp.get_empresa_by_id(id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        return empresa

    def list_empresas(self, skip: int = 0, limit: int = 0):
        return self.repo_emp.list(skip, limit)

    def create_empresa(self, data: EmpresaCreate):
        # Verifica se já existe uma empresa com o mesmo CNPJ
        empresa_existente = self.repo_emp.get_emp_by_cnpj(data.cnpj)
        if empresa_existente:
            raise HTTPException(status_code=400, detail="Empresa já cadastrada")

        # Cria a nova empresa
        empresa = EmpresaModel(**data.dict())
        return self.repo_emp.create(empresa)

    def update_empresa(self, id: int, data: EmpresaUpdate):
        empresa = self.get_empresa(id)
        # Verifica se o CNPJ está sendo alterado
        if data.cnpj and data.cnpj != empresa.cnpj:
            existente = self.repo_emp.get_emp_by_cnpj(data.cnpj)
            if existente and existente.id != id:
                raise HTTPException(status_code=400, detail="CNPJ já cadastrado em outra empresa")

        return self.repo_emp.update(empresa, data.dict(exclude_unset=True))

    def delete_empresa(self, id: int):
        empresa = self.get_empresa(id)
        self.repo_emp.delete(empresa)

