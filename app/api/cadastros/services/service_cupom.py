from typing import List
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from app.api.cadastros.models.model_cupom import CupomDescontoModel
from app.api.cadastros.models.model_parceiros import ParceiroModel
from app.api.cadastros.repositories.repo_cupom import CupomRepository

from app.api.cadastros.schemas.schema_cupom import CupomCreate, CupomUpdate
from app.api.empresas.models.empresa_model import EmpresaModel

class CuponsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CupomRepository(db)

    # ---------------- CUPOM ---------------- 
    def create(self, data: CupomCreate) -> CupomDescontoModel:
        cupom_data = data.model_dump()

        empresa_ids = cupom_data.pop("empresa_ids", None)
        if not empresa_ids:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Informe ao menos uma empresa")

        # Se monetizado=True, valida parceiro
        if cupom_data.get("monetizado"):
            parceiro = self.db.get(ParceiroModel, cupom_data.get("parceiro_id"))
            if not parceiro or not parceiro.ativo:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parceiro inválido ou inativo")
        else:
            cupom_data["parceiro_id"] = None  # ignora parceiro se não monetizado

        cupom = CupomDescontoModel(**cupom_data)
        cupom.empresas = self._get_empresas(empresa_ids)
        self.repo.create(cupom)
        return cupom

    def update(self, cupom_id: int, data: CupomUpdate) -> CupomDescontoModel:
        cupom = self.repo.get(cupom_id)
        if not cupom:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cupom não encontrado")

        payload = data.model_dump(exclude_none=True)
        empresa_ids = payload.pop("empresa_ids", None)

        # Só atualiza parceiro se monetizado=True
        if payload.get("monetizado") or (payload.get("parceiro_id") and cupom.monetizado):
            parceiro_id = payload.get("parceiro_id")
            if parceiro_id:
                parceiro = self.db.get(ParceiroModel, parceiro_id)
                if not parceiro or not parceiro.ativo:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parceiro inválido ou inativo")
        else:
            payload["parceiro_id"] = None  # ignora parceiro se não monetizado

        for key, value in payload.items():
            setattr(cupom, key, value)

        if empresa_ids is not None:
            if not empresa_ids:
                cupom.empresas = []
            else:
                cupom.empresas = self._get_empresas(empresa_ids)

        self.repo.update(cupom)
        return cupom

    # ---------------- LIST COM LINKS ---------------- 
    def list(self) -> List[CupomDescontoModel]:
        return (
            self.db.query(CupomDescontoModel)
            .options(joinedload(CupomDescontoModel.empresas))
            .all()
        )

    def list_by_parceiro(self, parceiro_id: int) -> List[CupomDescontoModel]:
        parceiro = self.db.get(ParceiroModel, parceiro_id)
        if not parceiro:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Parceiro não encontrado")

        return (
            self.db.query(CupomDescontoModel)
            .options(joinedload(CupomDescontoModel.empresas))
            .filter(CupomDescontoModel.parceiro_id == parceiro_id)
            .all()
        )

    def get(self, cupom_id: int) -> CupomDescontoModel:
        cupom = (
            self.db.query(CupomDescontoModel)
            .options(joinedload(CupomDescontoModel.empresas))
            .filter(CupomDescontoModel.id == cupom_id)
            .first()
        )
        if not cupom:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cupom não encontrado")
        return cupom

    def delete(self, cupom_id: int):
        cupom = self.repo.get(cupom_id)
        if not cupom:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cupom não encontrado")
        self.repo.delete(cupom)

    def _get_empresas(self, empresa_ids: List[int]):
        empresas = (
            self.db.query(EmpresaModel)
            .filter(EmpresaModel.id.in_(empresa_ids))
            .all()
        )

        if len(empresas) != len(set(empresa_ids)):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Alguma empresa informada é inválida")

        return empresas

