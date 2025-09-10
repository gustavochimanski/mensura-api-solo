# app/api/mensura/services/empresa_service.py
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from app.api.mensura.models.empresa_model import EmpresaModel
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.mensura.schemas.schema_empresa import EmpresaCreate, EmpresaUpdate
from app.api.mensura.services.endereco_service import EnderecoService
from app.utils.logger import logger
from app.utils.minio_client import upload_file_to_minio, remover_arquivo_minio


class EmpresaService:
    def __init__(self, db: Session):
        self.repo_emp = EmpresaRepository(db)
        self.endereco_service = EnderecoService(db)
        self.db = db

    # Recupera empresa
    def get_empresa(self, id: int) -> EmpresaModel:
        empresa = self.repo_emp.get_empresa_by_id(id)
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        return empresa

    # Lista empresas
    def list_empresas(self, skip: int = 0, limit: int = 100) -> list[EmpresaModel]:
        return self.repo_emp.list(skip, limit)

    # Cria empresa
    def create_empresa(self, data: EmpresaCreate, logo: UploadFile | None = None):
        # Checa se CNPJ já existe
        if data.cnpj and self.repo_emp.get_emp_by_cnpj(data.cnpj):
            raise HTTPException(status_code=400, detail="Empresa já cadastrada (CNPJ)")

        # Cria endereço
        endereco = self.endereco_service.create_endereco(data.endereco)

        # Cria empresa
        empresa = EmpresaModel(
            nome=data.nome,
            cnpj=data.cnpj,
            slug=data.slug,
            endereco_id=endereco.id,
            cardapio_tema=data.cardapio_tema,
            aceita_pedido_automatico=str(data.aceita_pedido_automatico).lower() == "true",
            tempo_entrega_maximo=data.tempo_entrega_maximo,
            taxa_minima_entrega=data.taxa_minima_entrega
        )
        empresa = self.repo_emp.create(empresa)

        # Upload da logo
        if logo:
            empresa.logo = upload_file_to_minio(self.db, empresa.id, logo, "logo")

        # Upload do cardápio
        if data.cardapio_link:
            if isinstance(data.cardapio_link, UploadFile):
                empresa.cardapio_link = upload_file_to_minio(self.db, empresa.id, data.cardapio_link, "cardapio")
            else:
                empresa.cardapio_link = data.cardapio_link

        try:
            self.db.commit()
            self.db.refresh(empresa)
        except IntegrityError as e:
            self.db.rollback()
            # verifica se é duplicidade de cardapio_link
            if 'empresas_cardapio_link_key' in str(e.orig):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cardápio link '{data.cardapio_link}' já existe."
                )
            # outros erros de integridade
            raise HTTPException(status_code=400, detail=str(e.orig))

        return empresa

    # Atualiza empresa
    def update_empresa(self, id: int, data: EmpresaUpdate, logo: UploadFile | None = None):
        empresa = self.get_empresa(id)
        payload = data.model_dump(exclude_unset=True)

        # Atualiza dados da empresa (exceto endereço e cardapio_link)
        update_data = {k: v for k, v in payload.items() if k not in ("cardapio_link", "endereco")}
        for key, value in update_data.items():
            setattr(empresa, key, value)

        # Atualiza endereço
        # Atualiza endereço
        if payload.get("endereco") and payload.get("endereco_id"):
            self.endereco_service.update_endereco(payload["endereco_id"], payload["endereco"])

        # Atualiza logo
        if logo:
            if empresa.logo:
                remover_arquivo_minio(empresa.logo)
            empresa.logo = upload_file_to_minio(self.db, empresa.id, logo, "logo")

        if "aceita_pedido_automatico" in payload:
            empresa.aceita_pedido_automatico = str(payload["aceita_pedido_automatico"]).lower() == "true"

        # Atualiza cardápio
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

    # Deleta empresa
    def delete_empresa(self, id: int):
        empresa = self.get_empresa(id)

        if empresa.usuarios and len(empresa.usuarios) > 0:
            raise HTTPException(status_code=400, detail="Empresa possui usuários vinculados.")

        # Remove arquivos
        if empresa.logo:
            remover_arquivo_minio(empresa.logo)
        if empresa.cardapio_link:
            remover_arquivo_minio(empresa.cardapio_link)

        endereco_id = empresa.endereco_id
        self.repo_emp.delete(empresa)

        # Remove endereço se ninguém mais usa
        if endereco_id:
            count = (
                self.repo_emp.db.query(EmpresaModel)
                .filter(EmpresaModel.endereco_id == endereco_id)
                .count()
            )
            if count == 0:
                self.endereco_service.delete_endereco(endereco_id)
