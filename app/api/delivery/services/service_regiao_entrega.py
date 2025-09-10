import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.api.delivery.models.model_regiao_entrega import RegiaoEntregaModel
from app.api.delivery.repositories.repo_regiao_entrega import RegiaoEntregaRepository
from app.api.delivery.schemas.schema_regiao_entrega import RegiaoEntregaCreate, RegiaoEntregaUpdate
from app.config import settings
from app.utils.geopapify_client import GeoapifyClient
from app.utils.logger import logger


class RegiaoEntregaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RegiaoEntregaRepository(db)

    async def _via_cep(self, cep: str):
        """Consulta ViaCEP e retorna dados normalizados"""
        logger.info(f"[ViaCEP] Consultando CEP: {cep}")
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"https://viacep.com.br/ws/{cep}/json/")
                logger.info(f"[ViaCEP] Status: {r.status_code}, Response: {r.text}")
                if r.status_code != 200 or "erro" in r.json():
                    raise ValueError("CEP inválido")
                return r.json()
        except Exception as e:
            logger.error(f"[ViaCEP] Erro ao consultar CEP {cep}: {e}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Erro ao consultar ViaCEP")

    async def _geoapify(self, bairro: str, cidade: str, uf: str):
        """Consulta Geoapify e retorna latitude/longitude"""
        query = f"{bairro}, {cidade} - {uf}, Brasil"
        logger.info(f"[Geoapify] Consultando coordenadas para: {query}")
        try:
            url = "https://api.geoapify.com/v1/geocode/search"
            async with httpx.AsyncClient() as client:
                r = await client.get(url, params={"text": query, "apiKey": settings.GEOAPIFY_KEY})
                logger.info(f"[Geoapify] Status: {r.status_code}, Response: {r.text}")
                data = r.json()
                if not data.get("features"):
                    logger.warning(f"[Geoapify] Nenhuma coordenada encontrada para {query}")
                    return None, None
                coords = data["features"][0]["geometry"]["coordinates"]
                return coords[1], coords[0]  # lat, lon
        except Exception as e:
            logger.error(f"[Geoapify] Erro ao consultar coordenadas para {query}: {e}")
            return None, None

    async def create(self, payload: RegiaoEntregaCreate):
        logger.info(f"[RegiaoEntregaService] Criando região: {payload}")

        bairro, cidade, uf = payload.bairro, payload.cidade, payload.uf

        # se vier CEP → normaliza
        if payload.cep:
            data_cep = await self._via_cep(payload.cep.replace("-", ""))
            bairro = data_cep.get("bairro") or bairro
            cidade = data_cep.get("localidade") or cidade
            uf = data_cep.get("uf") or uf
            logger.info(f"[RegiaoEntregaService] Dados ViaCEP: bairro={bairro}, cidade={cidade}, uf={uf}")

        # bairro é obrigatório
        if not bairro:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bairro é obrigatório")

        # consulta coordenadas
        query = f"{bairro}, {cidade} - {uf}, Brasil"
        geo = GeoapifyClient()
        lat, lon = await geo.get_coordinates(query)

        # checa duplicidade por localização textual
        existing = self.repo.get_by_location(payload.empresa_id, bairro, cidade, uf)
        if existing:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Essa região já está cadastrada (bairro/cidade/uf)")

        # checa duplicidade por coordenadas (caso mesmo bairro venha grafado diferente)
        if lat and lon:
            existing_coords = self.repo.get_by_coordinates(payload.empresa_id, lat, lon)
            if existing_coords:
                raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                    "Essa região já está cadastrada (coordenadas próximas)")

        # cria registro
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

        created = self.repo.create(regiao)
        return created

    async def update(self, regiao_id: int, payload: RegiaoEntregaUpdate):
        logger.info(f"[RegiaoEntregaService] Atualizando região {regiao_id} com {payload}")

        regiao = self.repo.get(regiao_id)
        if not regiao:
            logger.warning(f"[RegiaoEntregaService] Região {regiao_id} não encontrada")
            raise HTTPException(404, "Região não encontrada")

        data = payload.model_dump(exclude_unset=True)

        # Atualiza dados via CEP se fornecido
        if "cep" in data and data["cep"]:
            via_cep = await self._via_cep(data["cep"].replace("-", ""))
            data["bairro"] = via_cep.get("bairro") or data.get("bairro")
            data["cidade"] = via_cep.get("localidade") or data.get("cidade")
            data["uf"] = via_cep.get("uf") or data.get("uf")
            logger.info(f"[RegiaoEntregaService] Dados ViaCEP atualizados: {data}")

        # ✅ bairro é obrigatório
        bairro_final = data.get("bairro") or regiao.bairro
        if not bairro_final:
            logger.error(f"[RegiaoEntregaService] Bairro obrigatório ausente na atualização")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bairro é obrigatório")
        data["bairro"] = bairro_final

        # Atualiza coordenadas
        lat, lon = await self._geoapify(
            data.get("bairro"),
            data.get("cidade") or regiao.cidade,
            data.get("uf") or regiao.uf,
        )
        data["latitude"], data["longitude"] = lat, lon
        logger.info(f"[RegiaoEntregaService] Coordenadas Geoapify atualizadas: lat={lat}, lon={lon}")

        updated = self.repo.update(regiao, data)
        logger.info(f"[RegiaoEntregaService] Região atualizada: {updated.id}")
        return updated

    def list(self, empresa_id: int):
        logger.info(f"[RegiaoEntregaService] Listando regiões para empresa_id={empresa_id}")
        results = self.repo.list_by_empresa(empresa_id)
        logger.info(f"[RegiaoEntregaService] Total de regiões encontradas: {len(results)}")
        return results

    def get(self, regiao_id: int):
        logger.info(f"[RegiaoEntregaService] Buscando região {regiao_id}")
        regiao = self.repo.get(regiao_id)
        if not regiao:
            logger.warning(f"[RegiaoEntregaService] Região {regiao_id} não encontrada")
            raise HTTPException(404, "Região não encontrada")
        return regiao

    def delete(self, regiao_id: int):
        logger.info(f"[RegiaoEntregaService] Removendo região {regiao_id}")
        regiao = self.repo.get(regiao_id)
        if not regiao:
            logger.warning(f"[RegiaoEntregaService] Região {regiao_id} não encontrada")
            raise HTTPException(404, "Região não encontrada")
        self.repo.delete(regiao)
        logger.info(f"[RegiaoEntregaService] Região {regiao_id} removida com sucesso")
        return {"message": "Região removida com sucesso"}
