from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.api.mensura.models.empresa_model import EmpresaModel
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.mensura.schemas.empresa_schema import EmpresaCreate, EmpresaUpdate
from app.api.mensura.services.endereco_service import EnderecoService


class EmpresaService:
    def __init__(self, db: Session):
        self.repo_emp = EmpresaRepository(db)
        self.endereco_service = EnderecoService(db)

    def get_empresa(self, id: int):
        empresa = self.repo_emp.get_empresa_by_id(id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        return empresa

    def list_empresas(self, skip: int = 0, limit: int = 0):
        return self.repo_emp.list(skip, limit)

    def create_empresa(self, data: EmpresaCreate):
        # 🔁 Valida duplicidade de CNPJ
        if self.repo_emp.get_emp_by_cnpj(data.cnpj):
            raise HTTPException(status_code=400, detail="Empresa já cadastrada")

        # 🏠 Cria o endereço primeiro
        endereco = self.endereco_service.create_endereco(data.endereco)

        # 🏢 Cria empresa vinculando o endereço
        empresa = EmpresaModel(
            nome=data.nome,
            cnpj=data.cnpj,
            slug=data.slug,
            logo=data.logo,
            endereco_id=endereco.id
        )

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