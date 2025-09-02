# app/api/mensura/services/empresa_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from app.api.mensura.models.empresa_model import EmpresaModel
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.mensura.schemas.schema_empresa import EmpresaCreate, EmpresaUpdate
from app.api.mensura.services.endereco_service import EnderecoService
from app.utils.minio_client import upload_file_to_minio, remover_arquivo_minio


class EmpresaService:
    def __init__(self, db: Session):
        self.repo_emp = EmpresaRepository(db)
        self.endereco_service = EnderecoService(db)
        self.db = db

    def get_empresa(self, id: int):
        empresa = self.repo_emp.get_empresa_by_id(id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        return empresa

    def list_empresas(self, skip: int = 0, limit: int = 100):
        return self.repo_emp.list(skip, limit)

    def create_empresa(self, data: EmpresaCreate, logo: UploadFile | None = None):
        empresa = EmpresaModel(
            nome=data.nome,
            cnpj=data.cnpj,
            slug=data.slug,
            endereco_id=data.endereco.id,
            cardapio_tema=data.cardapio_tema,
        )
        empresa = self.repo_emp.create(empresa)

        if logo:
            logo_url = upload_file_to_minio(self.db, empresa.id, logo, "logo")
            empresa.logo = logo_url

        self.db.commit()
        self.db.refresh(empresa)
        return empresa

    def update_empresa(self, id: int, data: EmpresaUpdate, logo: UploadFile | None = None):
        empresa = self.get_empresa(id)
        payload = data.model_dump(exclude_unset=True)

        # atualiza campos normais
        update_data = {k: v for k, v in payload.items() if k not in ("endereco_id", "cardapio_link")}
        empresa = self.repo_emp.update(empresa, update_data)

        # atualiza logo
        if logo:
            if empresa.logo:
                remover_arquivo_minio(empresa.logo)
            logo_url = upload_file_to_minio(self.db, empresa.id, logo, "logo")
            empresa.logo = logo_url

        # atualiza cardapio_link se for arquivo
        if isinstance(payload.get("cardapio_link"), UploadFile):
            if empresa.cardapio_link:
                remover_arquivo_minio(empresa.cardapio_link)
            cardapio_url = upload_file_to_minio(self.db, empresa.id, payload["cardapio_link"], "cardapio")
            empresa.cardapio_link = cardapio_url
        elif isinstance(payload.get("cardapio_link"), str):
            empresa.cardapio_link = payload["cardapio_link"]

        self.db.commit()
        self.db.refresh(empresa)
        return empresa

        # Se vier cardápio novo
        if isinstance(data.cardapio_link, UploadFile):
            if empresa.cardapio_link:
                remover_arquivo_minio(empresa.cardapio_link)
            cardapio_url = upload_file_to_minio(self.db, empresa.id, data.cardapio_link, "cardapio")
            empresa.cardapio_link = cardapio_url
        elif isinstance(data.cardapio_link, str):
            empresa.cardapio_link = data.cardapio_link

        update_data = {k: v for k, v in payload.items() if k not in ("endereco_id", "logo", "cardapio_link")}
        return self.repo_emp.update(empresa, update_data)

    def delete_empresa(self, id: int):
        empresa = self.get_empresa(id)

        if empresa.usuarios and len(empresa.usuarios) > 0:
            raise HTTPException(status_code=400, detail="Empresa possui usuários vinculados.")

        # remover arquivos do MinIO
        if empresa.logo:
            remover_arquivo_minio(empresa.logo)
        if empresa.cardapio_link:
            remover_arquivo_minio(empresa.cardapio_link)

        endereco_id = empresa.endereco_id

        self.repo_emp.delete(empresa)

        if endereco_id:
            # se nenhuma outra empresa usa esse endereço, apaga
            count = (
                self.repo_emp.db.query(EmpresaModel)
                .filter(EmpresaModel.endereco_id == endereco_id)
                .count()
            )
            if count == 0:
                self.endereco_service.delete_endereco(endereco_id)
