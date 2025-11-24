from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.cadastros.schemas.schema_shared_enums import TipoEntregaEnum
from app.api.pedidos.services.service_pedido_helpers import _dec
from app.utils.logger import logger
from app.api.empresas.contracts.empresa_contract import IEmpresaContract
from app.api.cadastros.contracts.regiao_entrega_contract import IRegiaoEntregaContract
from app.api.empresas.adapters.empresa_adapter import EmpresaAdapter
from app.api.cadastros.adapters.regiao_entrega_adapter import RegiaoEntregaAdapter
from app.api.localizacao.contracts.geolocalizacao_contract import IGeolocalizacaoService
from app.api.localizacao.models.coordenadas import Coordenadas


class TaxaService:
    """Serviço responsável pelo cálculo de taxas, faixas de entrega e cupons."""

    def __init__(
        self,
        db: Session,
        empresa_contract: IEmpresaContract | None = None,
        regiao_contract: IRegiaoEntregaContract | None = None,
        geolocalizacao_service: IGeolocalizacaoService | None = None
    ):
        self.db = db
        self.empresa_contract: IEmpresaContract = empresa_contract or EmpresaAdapter(db)
        self.regiao_contract: IRegiaoEntregaContract = regiao_contract or RegiaoEntregaAdapter(db)
        
        # Usa o serviço de geolocalização se fornecido, senão cria um padrão
        if geolocalizacao_service is None:
            from app.api.localizacao.adapters.google_maps_adapter import GoogleMapsAdapter
            from app.api.localizacao.adapters.cache_adapter import CacheAdapter
            from app.api.localizacao.services.geolocalizacao_service import GeolocalizacaoService
            
            google_adapter = GoogleMapsAdapter()
            cache = CacheAdapter()
            geolocalizacao_service = GeolocalizacaoService(
                geocodificacao_provider=google_adapter,
                distancia_provider=google_adapter,
                cache=cache
            )
        
        self.geo_service = geolocalizacao_service

        # Cache de regiões (específico deste serviço)
        self._cache_regioes: dict[int, bool] = {}

    def calcular_taxas(
        self,
        *,
        tipo_entrega: TipoEntregaEnum,
        subtotal: Decimal,
        endereco=None,
        empresa_id: int | None = None,
    ) -> tuple[Decimal, Decimal, Optional[Decimal], Optional[int]]:
        """Calcula taxa de entrega, taxa de serviço, distância em km e tempo estimado (minutos)."""

        taxa_entrega = _dec(0)
        distancia_km: Optional[Decimal] = None
        tempo_estimado_min: Optional[int] = None

        if tipo_entrega == TipoEntregaEnum.DELIVERY:
            if not empresa_id:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Empresa é obrigatória para calcular entrega em modo delivery.",
                )

            if endereco is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Endereço é obrigatório para calcular entrega em modo delivery.",
                )

            if not self.verificar_regioes_cadastradas(empresa_id):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Nenhuma faixa de entrega cadastrada para esta empresa.",
                )

            distancia_km = self._calcular_distancia_km(empresa_id, endereco)
            if distancia_km is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Não foi possível calcular a distância para o endereço informado.",
                )

            regiao_encontrada = self.regiao_contract.obter_regiao_por_distancia(empresa_id, distancia_km)
            if not regiao_encontrada:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Não entregamos nesta distância. Distância calculada: {distancia_km} km.",
                )

            taxa_entrega = _dec(regiao_encontrada.taxa_entrega)
            # Tempo estimado configurado na região (minutos)
            tempo_estimado_min = getattr(regiao_encontrada, "tempo_estimado_min", None)

        taxa_servico = (subtotal * Decimal("0.01")).quantize(Decimal("0.01"))
        return taxa_entrega, taxa_servico, distancia_km, tempo_estimado_min

    def _calcular_distancia_km(self, empresa_id: int, endereco) -> Optional[Decimal]:
        origem_coords = self._obter_coordenadas_empresa(empresa_id)
        destino_coords = self._obter_coordenadas_destino(endereco)

        if origem_coords is None or destino_coords is None:
            logger.warning(
                "[TaxaService] Coordenadas ausentes para cálculo de distância | origem=%s destino=%s",
                origem_coords,
                destino_coords,
            )
            return None

        distancia_float = self.geo_service.calcular_distancia(origem_coords, destino_coords)
        if distancia_float is None:
            logger.warning(
                "[TaxaService] Não foi possível calcular distância para origem=%s destino=%s",
                origem_coords.to_tuple(),
                destino_coords.to_tuple(),
            )
            return None

        return self._quantizar_distancia(distancia_float)

    def _obter_coordenadas_empresa(self, empresa_id: int) -> Optional[Coordenadas]:
        empresa = self.empresa_contract.obter_empresa(empresa_id)
        if not empresa:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

        # Tenta obter coordenadas já armazenadas na empresa
        latitude = self._to_float(getattr(empresa, "latitude", None))
        longitude = self._to_float(getattr(empresa, "longitude", None))
        if latitude is not None and longitude is not None:
            coords = Coordenadas(latitude=latitude, longitude=longitude)
            # Armazena no cache do serviço para futuras consultas
            cache_key = f"empresa:{empresa_id}"
            self.geo_service.cache.set(cache_key, coords.to_tuple())
            return coords

        # Se não tem coordenadas, resolve via geocodificação
        endereco_str = self._montar_endereco_str(empresa)
        if not endereco_str:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Endereço da empresa incompleto para cálculo de entrega.",
            )

        cache_key = f"empresa:{empresa_id}"
        coords = self.geo_service.obter_coordenadas(endereco_str, cache_key=cache_key)
        return coords

    def _obter_coordenadas_destino(self, endereco) -> Optional[Coordenadas]:
        # Tenta obter coordenadas já armazenadas no endereço
        lat = self._to_float(self._get_attr(endereco, "latitude"))
        lon = self._to_float(self._get_attr(endereco, "longitude"))
        if lat is not None and lon is not None:
            return Coordenadas(latitude=lat, longitude=lon)

        # Se não tem coordenadas, resolve via geocodificação
        endereco_str = self._montar_endereco_str(endereco)
        if not endereco_str:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Endereço incompleto para cálculo da entrega.",
            )

        coords = self.geo_service.obter_coordenadas(endereco_str, cache_key=endereco_str)
        return coords

    def obter_coordenadas_empresa(self, empresa_id: int) -> Tuple[Optional[float], Optional[float]]:
        """
        Interface pública para obter coordenadas da empresa com cache.
        Mantido para compatibilidade retroativa - retorna tupla.
        """
        coords = self._obter_coordenadas_empresa(empresa_id)
        if coords is None:
            return None, None
        return coords.to_tuple()

    def obter_coordenadas_endereco(self, endereco) -> Tuple[Optional[float], Optional[float]]:
        """
        Interface pública para obter coordenadas de um endereço.
        Mantido para compatibilidade retroativa - retorna tupla.
        """
        coords = self._obter_coordenadas_destino(endereco)
        if coords is None:
            return None, None
        return coords.to_tuple()

    def verificar_regioes_cadastradas(self, empresa_id: int) -> bool:
        """Verifica se existem faixas de entrega cadastradas para a empresa."""
        cache_key = empresa_id
        if cache_key in self._cache_regioes:
            return self._cache_regioes[cache_key]

        # Heurística: se há alguma região retornável para 0 km, consideramos que existe configuração de faixa.
        try:
            from decimal import Decimal as _Dec
            exists = self.regiao_contract.obter_regiao_por_distancia(empresa_id, _Dec("0")) is not None
        except Exception:
            exists = False

        self._cache_regioes[cache_key] = exists
        return exists

    def limpar_cache_regioes(self, empresa_id: int | None = None):
        """Limpa o cache de faixas de entrega e coordenadas."""
        if empresa_id is not None:
            self._cache_regioes.pop(empresa_id, None)
            self.geo_service.limpar_cache(cache_key=f"empresa:{empresa_id}")
        else:
            self._cache_regioes.clear()
            self.geo_service.limpar_cache()  # Limpa todo o cache de coordenadas

    def aplicar_cupom(
        self,
        *,
        cupom_id: Optional[int],
        subtotal: Decimal,
        empresa_id: int,
        repo,
    ) -> Decimal:
        """Aplica cupom de desconto ao subtotal."""
        if not cupom_id:
            return _dec(0)
        cupom = repo.get_cupom(cupom_id)
        if not cupom or not cupom.ativo:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cupom inválido ou inativo")
        if cupom.empresa_id != empresa_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cupom não pertence a esta empresa")

        # validade e mínimo
        if cupom.validade_inicio and cupom.validade_fim:
            from datetime import datetime, timezone

            now = datetime.now(tz=timezone.utc)
            if not (cupom.validade_inicio <= now <= cupom.validade_fim):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cupom fora de validade")
        if cupom.minimo_compra and subtotal < cupom.minimo_compra:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Subtotal abaixo do mínimo do cupom")

        desconto = Decimal("0")
        if cupom.desconto_valor:
            desconto += _dec(cupom.desconto_valor)
        if cupom.desconto_percentual:
            desconto += (
                subtotal * (Decimal(cupom.desconto_percentual) / Decimal("100"))
            ).quantize(Decimal("0.01"))

        return min(desconto, subtotal)

    def _montar_endereco_str(self, endereco) -> Optional[str]:
        logradouro = self._sanitize(self._get_attr(endereco, "logradouro"))
        numero = self._sanitize(self._get_attr(endereco, "numero"))
        bairro = self._sanitize(self._get_attr(endereco, "bairro"))
        cidade = self._sanitize(
            self._get_attr(endereco, "cidade") or self._get_attr(endereco, "localidade")
        )
        estado = self._sanitize(
            self._get_attr(endereco, "estado") or self._get_attr(endereco, "uf")
        )
        cep = self._sanitize(self._get_attr(endereco, "cep"))

        partes: list[str] = []
        if logradouro and numero:
            partes.append(f"{logradouro}, {numero}")
        elif logradouro:
            partes.append(logradouro)

        if bairro:
            partes.append(bairro)

        if cidade and estado:
            partes.append(f"{cidade} - {estado}")
        elif cidade:
            partes.append(cidade)
        elif estado:
            partes.append(estado)

        if cep:
            partes.append(cep)

        endereco_str = ", ".join(partes)
        return endereco_str or None

    @staticmethod
    def _sanitize(value) -> Optional[str]:
        if value is None:
            return None
        value_str = str(value).strip()
        return value_str or None

    @staticmethod
    def _get_attr(source, attr: str):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(attr)
        return getattr(source, attr, None)

    @staticmethod
    def _to_float(value) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _quantizar_distancia(distancia_km: float) -> Decimal:
        return Decimal(str(distancia_km)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

