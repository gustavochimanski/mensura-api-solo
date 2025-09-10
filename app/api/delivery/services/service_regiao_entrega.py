import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.api.delivery.models.model_regiao_entrega import RegiaoEntregaModel
from app.api.delivery.repositories.repo_regiao_entrega import RegiaoEntregaRepository
from app.api.delivery.schemas.schema_regiao_entrega import RegiaoEntregaCreate, RegiaoEntregaUpdate
from app.config import settings


class RegiaoEntregaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RegiaoEntregaRepository(db)

    async def _via_cep(self, cep: str):
        """Consulta ViaCEP e retorna dados normalizados"""
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"https://viacep.com.br/ws/{cep}/json/")
                if r.status_code != 200 or "erro" in r.json():
                    raise ValueError("CEP inválido")
                return r.json()
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Erro ao consultar ViaCEP")

    async def _geoapify(self, bairro: str, cidade: str, uf: str):
        """Consulta Geoapify e retorna latitude/longitude"""
        try:
            query = f"{bairro}, {cidade} - {uf}, Brasil"
            url = "https://api.geoapify.com/v1/geocode/search"
            async with httpx.AsyncClient() as client:
                r = await client.get(url, params={"text": query, "apiKey": settings.GEOAPIFY_KEY})
                data = r.json()
                if not data.get("features"):
                    return None, None
                coords = data["features"][0]["geometry"]["coordinates"]
                return coords[1], coords[0]  # lat, lon
        except Exception:
            return None, None

    async def create(self, payload: RegiaoEntregaCreate):
        bairro, cidade, uf = payload.bairro, payload.cidade, payload.uf

        # se vier CEP, tenta preencher dados via ViaCEP
        if payload.cep:
            data = await self._via_cep(payload.cep.replace("-", ""))
            bairro = data.get("bairro", bairro)
            cidade = data.get("localidade", cidade)
            uf = data.get("uf", uf)

        lat, lon = await self._geoapify(bairro, cidade, uf)

        regiao = RegiaoEntregaModel(
            empresa_id=payload.empresa_id,
            cep=payload.cep,
            bairro=bairro,
            cidade=cidade,
            uf=uf,
            latitude=lat,
            longitude=lon,
            taxa_entrega=payload.taxa_entrega,
            ativo=payload.ativo,
        )
        return self.repo.create(regiao)

    async def update(self, regiao_id: int, payload: RegiaoEntregaUpdate):
        regiao = self.repo.get(regiao_id)
        if not regiao:
            raise HTTPException(404, "Região não encontrada")

        data = payload.model_dump(exclude_unset=True)

        if "cep" in data and data["cep"]:
            via_cep = await self._via_cep(data["cep"].replace("-", ""))
            data["bairro"] = via_cep.get("bairro", data.get("bairro"))
            data["cidade"] = via_cep.get("localidade", data.get("cidade"))
            data["uf"] = via_cep.get("uf", data.get("uf"))

        if "bairro" in data or "cidade" in data or "uf" in data:
            lat, lon = await self._geoapify(
                data.get("bairro", regiao.bairro),
                data.get("cidade", regiao.cidade),
                data.get("uf", regiao.uf),
            )
            data["latitude"], data["longitude"] = lat, lon

        return self.repo.update(regiao, data)

    def list(self, empresa_id: int):
        return self.repo.list_by_empresa(empresa_id)

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
