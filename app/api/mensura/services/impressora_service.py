# app/api/mensura/services/impressora_service.py
from sqlalchemy.orm import Session
from typing import List, Optional
from app.api.mensura.repositories.impressora_repo import ImpressoraRepository
from app.api.mensura.schemas.schema_impressora import ImpressoraCreate, ImpressoraUpdate, ImpressoraResponse
from app.api.mensura.repositories.empresa_repo import EmpresaRepository

class ImpressoraService:
    def __init__(self, db: Session):
        self.db = db
        self.impressora_repo = ImpressoraRepository(db)
        self.empresa_repo = EmpresaRepository(db)

    def create_impressora(self, impressora_data: ImpressoraCreate) -> ImpressoraResponse:
        # Verificar se a empresa existe
        empresa = self.empresa_repo.get_empresa_by_id(impressora_data.empresa_id)
        if not empresa:
            raise ValueError("Empresa não encontrada")

        # Atualizar o nome_estabelecimento na config com o nome da empresa
        impressora_data.config.nome_estabelecimento = empresa.nome

        db_impressora = self.impressora_repo.create_impressora(impressora_data)
        return ImpressoraResponse(
            id=db_impressora.id,
            nome=db_impressora.nome,
            config=db_impressora.config,
            empresa_id=db_impressora.empresa_id,
            empresa_nome=empresa.nome
        )

    def get_impressora(self, impressora_id: int) -> Optional[ImpressoraResponse]:
        db_impressora = self.impressora_repo.get_impressora_by_id(impressora_id)
        if not db_impressora:
            return None

        empresa = self.empresa_repo.get_empresa_by_id(db_impressora.empresa_id)
        return ImpressoraResponse(
            id=db_impressora.id,
            nome=db_impressora.nome,
            config=db_impressora.config,
            empresa_id=db_impressora.empresa_id,
            empresa_nome=empresa.nome if empresa else None
        )

    def get_impressoras_by_empresa(self, empresa_id: int) -> List[ImpressoraResponse]:
        db_impressoras = self.impressora_repo.get_impressoras_by_empresa(empresa_id)
        empresa = self.empresa_repo.get_empresa_by_id(empresa_id)
        
        return [
            ImpressoraResponse(
                id=impressora.id,
                nome=impressora.nome,
                config=impressora.config,
                empresa_id=impressora.empresa_id,
                empresa_nome=empresa.nome if empresa else None
            )
            for impressora in db_impressoras
        ]

    def update_impressora(self, impressora_id: int, impressora_data: ImpressoraUpdate) -> Optional[ImpressoraResponse]:
        db_impressora = self.impressora_repo.update_impressora(impressora_id, impressora_data)
        if not db_impressora:
            return None

        empresa = self.empresa_repo.get_empresa_by_id(db_impressora.empresa_id)
        return ImpressoraResponse(
            id=db_impressora.id,
            nome=db_impressora.nome,
            config=db_impressora.config,
            empresa_id=db_impressora.empresa_id,
            empresa_nome=empresa.nome if empresa else None
        )

    def delete_impressora(self, impressora_id: int) -> bool:
        return self.impressora_repo.delete_impressora(impressora_id)

    def list_impressoras(self, skip: int = 0, limit: int = 100) -> List[ImpressoraResponse]:
        db_impressoras = self.impressora_repo.list_impressoras(skip, limit)
        
        # Buscar empresas para popular o nome_estabelecimento
        empresa_ids = list(set(impressora.empresa_id for impressora in db_impressoras))
        empresas = {empresa.id: empresa for empresa in self.empresa_repo.list_by_ids(empresa_ids)}
        
        return [
            ImpressoraResponse(
                id=impressora.id,
                nome=impressora.nome,
                config=impressora.config,
                empresa_id=impressora.empresa_id,
                empresa_nome=empresas.get(impressora.empresa_id).nome if empresas.get(impressora.empresa_id) else None
            )
            for impressora in db_impressoras
        ]