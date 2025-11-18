from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.cadastros.models.model_regiao_entrega import RegiaoEntregaModel
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.cadastros.repositories.repo_regiao_entrega import RegiaoEntregaRepository
from app.api.cadastros.schemas.schema_regiao_entrega import (
    RegiaoEntregaCreate,
    RegiaoEntregaUpdate,
)
from app.utils.logger import logger


class RegiaoEntregaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RegiaoEntregaRepository(db)
        self.empresa_repo = EmpresaRepository(db)

    async def create(self, payload: RegiaoEntregaCreate):
        logger.info(f"[RegiaoEntregaService] Criando faixa de entrega: {payload}")

        # Verifica se a empresa existe
        empresa = self.empresa_repo.get_empresa_by_id(payload.empresa_id)
        if not empresa:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Empresa com ID {payload.empresa_id} não encontrada",
            )

        # Verifica sobreposição de faixas
        if self.repo.existe_faixa_sobreposta(
            empresa_id=payload.empresa_id,
            distancia_max_km=payload.distancia_max_km,
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Já existe uma faixa de distância cadastrada que conflita com estes valores.",
            )

        # Cria a faixa
        regiao = RegiaoEntregaModel(
            empresa_id=payload.empresa_id,
            descricao=None,
            distancia_min_km=Decimal("0"),
            distancia_max_km=Decimal(payload.distancia_max_km)
            if payload.distancia_max_km is not None
            else None,
            taxa_entrega=payload.taxa_entrega,
            tempo_estimado_min=payload.tempo_estimado_min,
            ativo=True,
        )

        return self.repo.create(regiao)

    async def update(self, regiao_id: int, payload: RegiaoEntregaUpdate):
        regiao = self.repo.get(regiao_id)
        if not regiao:
            raise HTTPException(404, "Região não encontrada")

        data = payload.model_dump(exclude_unset=True)

        distancia_max_para_validar = data.get("distancia_max_km", regiao.distancia_max_km)

        if self.repo.existe_faixa_sobreposta(
            empresa_id=regiao.empresa_id,
            distancia_max_km=distancia_max_para_validar,
            ignorar_id=regiao.id,
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Já existe uma faixa de distância cadastrada que conflita com estes valores.",
            )

        if "distancia_max_km" in data:
            distancia_max_value = data["distancia_max_km"]
            data["distancia_max_km"] = (
                Decimal(distancia_max_value) if distancia_max_value is not None else None
            )

        data["distancia_min_km"] = Decimal("0")
        data["ativo"] = True

        updated = self.repo.update(regiao, data)
        return updated

    def list(self, empresa_id: int):
        results = self.repo.list_by_empresa(empresa_id)
        return results

    def get(self, regiao_id: int):
        regiao = self.repo.get(regiao_id)
        if not regiao:
            raise HTTPException(404, "Região não encontrada")
        return regiao

    def delete(self, regiao_id: int):
        regiao = self.repo.get(regiao_id)
        if not regiao:
            raise HTTPException(404, "Região não encontrada")
        self.repo.delete(regiao)
        return {"message": "Região removida com sucesso"}

