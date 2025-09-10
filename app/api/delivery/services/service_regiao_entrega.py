import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.api.delivery.models.model_regiao_entrega import RegiaoEntregaModel
from app.api.delivery.repositories.repo_regiao_entrega import RegiaoEntregaRepository
from app.api.delivery.schemas.schema_regiao_entrega import RegiaoEntregaCreate, RegiaoEntregaUpdate
from app.config import settings
from app.utils.geopapify_client import GeoapifyClient, GeoapifyMini
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

    async def create(self, payload: RegiaoEntregaCreate):
        logger.info(f"[RegiaoEntregaService] Criando região: {payload}")

        bairro, cidade, uf = payload.bairro, payload.cidade, payload.uf
        lat, lon, cep = None, None, payload.cep
        rua, numero = None, None

        # 1️⃣ Consulta Geoapify mini
        query = f"{bairro or ''}, {cidade or ''} - {uf or ''}, Brasil"
        geo = GeoapifyClient()
        mini_list = await geo.geocode_mini(query)

        if mini_list and len(mini_list) > 0:
            mini: GeoapifyMini = mini_list[0]  # pega a primeira feature
            bairro = mini.bairro or bairro
            cidade = mini.cidade or cidade
            uf = mini.codigo_estado or uf
            lat = mini.latitude
            lon = mini.longitude
            cep = mini.cep or cep
            rua = mini.rua
            numero = mini.numero

        # 2️⃣ Bairro é obrigatório
        if not bairro:
            logger.error("[RegiaoEntregaService] Bairro é obrigatório")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bairro é obrigatório")

        # 3️⃣ Se ainda não pegamos coordenadas, tenta buscar com get_coordinates
        if not lat or not lon:
            lat, lon = await geo.get_coordinates(query)
            logger.info(f"[RegiaoEntregaService] Coordenadas Geoapify: lat={lat}, lon={lon}")

        # 4️⃣ Verifica duplicidade (bairro + cidade + uf)
        existing = self.repo.get_by_location(payload.empresa_id, bairro, cidade, uf)
        if existing:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Essa região já está cadastrada (bairro/cidade/uf)"
            )

        # 5️⃣ Verifica duplicidade por coordenadas
        if lat and lon:
            existing_coords = self.repo.get_by_coordinates(payload.empresa_id, lat, lon)
            if existing_coords:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Essa região já está cadastrada (coordenadas próximas)"
                )

        # 6️⃣ Cria a região
        regiao = RegiaoEntregaModel(
            empresa_id=payload.empresa_id,
            cep=cep,
            bairro=bairro,
            cidade=cidade,
            uf=uf,
            rua=rua,
            numero=numero,
            latitude=lat,
            longitude=lon,
            taxa_entrega=payload.taxa_entrega,
            ativo=payload.ativo,
        )

        created = self.repo.create(regiao)
        logger.info(f"[RegiaoEntregaService] Região criada: {created.id}")
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

        # Bairro é obrigatório
        bairro_final = data.get("bairro") or regiao.bairro
        if not bairro_final:
            logger.error(f"[RegiaoEntregaService] Bairro obrigatório ausente na atualização")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bairro é obrigatório")
        data["bairro"] = bairro_final

        # Atualiza coordenadas via Geoapify
        geo = GeoapifyClient()
        query = f"{data.get('bairro')}, {data.get('cidade') or regiao.cidade} - {data.get('uf') or regiao.uf}, Brasil"
        mini_list = await geo.geocode_mini(query)

        if mini_list and len(mini_list) > 0:
            mini: GeoapifyMini = mini_list[0]
            data["latitude"] = mini.latitude
            data["longitude"] = mini.longitude
            data["rua"] = mini.rua
            data["numero"] = mini.numero
            data["cep"] = mini.cep
        else:
            lat, lon = await geo.get_coordinates(query)
            data["latitude"], data["longitude"] = lat, lon

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
