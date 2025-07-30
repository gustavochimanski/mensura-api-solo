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
        payload = data.dict(exclude_unset=True)

        # Verifica duplicidade de CNPJ
        novo_cnpj = payload.get("cnpj")
        if novo_cnpj and novo_cnpj != empresa.cnpj:
            existente = self.repo_emp.get_emp_by_cnpj(novo_cnpj)
            if existente and existente.id != id:
                raise HTTPException(status_code=400, detail="CNPJ já cadastrado em outra empresa")

        # Valida e aplica novo endereço, se enviado
        if "endereco_id" in payload:
            endereco = self.endereco_service.get_endereco(payload["endereco_id"])
            empresa.endereco_id = endereco.id

        if "slug" in payload and payload["slug"] != empresa.slug:
            existente = self.repo_emp.get_emp_by_slug(payload["slug"])
            if existente and existente.id != id:
                raise HTTPException(status_code=400, detail="Slug já está em uso por outra empresa")

        # Atualiza demais campos
        update_data = {k: v for k, v in payload.items() if k != "endereco_id"}
        return self.repo_emp.update(empresa, update_data)

    def delete_empresa(self, id: int):
        empresa = self.get_empresa(id)
        self.repo_emp.delete(empresa)