from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.api.delivery.models.model_regiao_entrega import RegiaoEntregaModel
from app.api.delivery.repositories.repo_regiao_entrega import RegiaoEntregaRepository
from app.api.delivery.schemas.schema_regiao_entrega import RegiaoEntregaCreate, RegiaoEntregaUpdate
from app.utils.logger import logger


class RegiaoEntregaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RegiaoEntregaRepository(db)

    async def create(self, payload: RegiaoEntregaCreate):
        logger.info(f"[RegiaoEntregaService] Criando região: {payload}")

        bairro, cidade, uf = payload.bairro, payload.cidade, payload.uf

        # Bairro é obrigatório
        if not bairro:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bairro é obrigatório")

        # Verifica duplicidade (bairro + cidade + uf)
        existing = self.repo.get_by_location(payload.empresa_id, bairro, cidade, uf)
        if existing:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Essa região já está cadastrada (bairro/cidade/uf)"
            )

        # Verifica duplicidade por coordenadas
        if payload.latitude and payload.longitude:
            existing_coords = self.repo.get_by_coordinates(payload.empresa_id, payload.latitude, payload.longitude)
            if existing_coords:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Essa região já está cadastrada (coordenadas próximas)"
                )

        # Cria a região
        regiao = RegiaoEntregaModel(
            empresa_id=payload.empresa_id,
            cep=payload.cep,
            bairro=bairro,
            cidade=cidade,
            uf=uf,
            latitude=payload.latitude,
            longitude=payload.longitude,
            raio_km=payload.raio_km,
            taxa_entrega=payload.taxa_entrega,
            ativo=payload.ativo,
        )

        created = self.repo.create(regiao)
        return created

    async def update(self, regiao_id: int, payload: RegiaoEntregaUpdate):

        regiao = self.repo.get(regiao_id)
        if not regiao:
            raise HTTPException(404, "Região não encontrada")

        data = payload.model_dump(exclude_unset=True)

        # Bairro é obrigatório
        bairro_final = data.get("bairro") or regiao.bairro
        if not bairro_final:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bairro é obrigatório")
        data["bairro"] = bairro_final

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
