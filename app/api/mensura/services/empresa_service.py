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

    def create_empresa(self, data: EmpresaCreate, logo: UploadFile | None = None):
        # 1️⃣ Salva o endereço primeiro
        endereco = self.endereco_service.create_endereco(data.endereco)

        # 2️⃣ Cria a empresa usando o id do endereço persistido
        empresa = EmpresaModel(
            nome=data.nome,
            cnpj=data.cnpj,
            slug=data.slug,
            endereco_id=endereco.id,
            cardapio_tema=data.cardapio_tema,
        )
        empresa = self.repo_emp.create(empresa)

        # 3️⃣ Upload da logo
        if logo:
            empresa.logo = upload_file_to_minio(self.db, empresa.id, logo, "logo")

        # 4️⃣ Upload do cardápio se for string (ou UploadFile, se você quiser suportar)
        if data.cardapio_link:
            if isinstance(data.cardapio_link, UploadFile):
                empresa.cardapio_link = upload_file_to_minio(self.db, empresa.id, data.cardapio_link, "cardapio")
            else:
                empresa.cardapio_link = data.cardapio_link

        self.db.commit()
        self.db.refresh(empresa)
        return empresa

    def update_empresa(self, id: int, data: EmpresaUpdate, logo: UploadFile | None = None):
        empresa = self.get_empresa(id)
        payload = data.model_dump(exclude_unset=True)

        # 1️⃣ Atualiza dados normais
        update_data = {k: v for k, v in payload.items() if k not in ("endereco_id", "cardapio_link")}
        empresa = self.repo_emp.update(empresa, update_data)

        # 2️⃣ Atualiza logo se vier novo UploadFile
        if logo:
            if empresa.logo:
                remover_arquivo_minio(empresa.logo)
            empresa.logo = upload_file_to_minio(self.db, empresa.id, logo, "logo")

        # 3️⃣ Atualiza cardápio
        cardapio = payload.get("cardapio_link")
        if cardapio:
            if isinstance(cardapio, UploadFile):
                if empresa.cardapio_link:
                    remover_arquivo_minio(empresa.cardapio_link)
                empresa.cardapio_link = upload_file_to_minio(self.db, empresa.id, cardapio, "cardapio")
            elif isinstance(cardapio, str):
                empresa.cardapio_link = cardapio

        self.db.commit()
        self.db.refresh(empresa)
        return empresa
