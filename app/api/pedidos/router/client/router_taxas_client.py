from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Body, Depends, status, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database.db_connection import get_db
from app.api.cadastros.schemas.schema_endereco import EnderecoBase
from app.api.shared.schemas.schema_shared_enums import TipoEntregaEnum
from app.api.pedidos.services.service_pedido_taxas import TaxaService

router = APIRouter(prefix="/api/pedidos/client", tags=["Client - Pedidos"])


class CalcularTaxaRequest(BaseModel):
    empresa_id: int
    subtotal: Decimal
    endereco: Optional[EnderecoBase] = None
    tipo_entrega: TipoEntregaEnum = TipoEntregaEnum.DELIVERY

    model_config = ConfigDict(extra="forbid")


class CalcularTaxaResponse(BaseModel):
    taxa_entrega: float
    taxa_servico: float
    distancia_km: Optional[float] = None
    tempo_estimado_minutos: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "/taxa/calc",
    response_model=CalcularTaxaResponse,
    status_code=status.HTTP_200_OK,
)
def calcular_taxa(
    payload: CalcularTaxaRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Calcula apenas as taxas associadas a um pedido (taxa de entrega e taxa de serviço),
    além da distância estimada e tempo de entrega quando aplicável.

    - `empresa_id` é obrigatório quando `tipo_entrega` for DELIVERY.
    - `endereco` é obrigatório quando `tipo_entrega` for DELIVERY.
    """
    # validações leves (TaxaService já lança HTTPException quando necessário)
    try:
        taxa_entrega, taxa_servico, distancia_km, tempo_estimado = TaxaService(db).calcular_taxas(
            tipo_entrega=payload.tipo_entrega,
            subtotal=payload.subtotal,
            endereco=payload.endereco,
            empresa_id=payload.empresa_id,
        )
    except HTTPException:
        # propaga exceções do serviço para o cliente
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))

    return CalcularTaxaResponse(
        taxa_entrega=float(taxa_entrega) if taxa_entrega is not None else 0.0,
        taxa_servico=float(taxa_servico) if taxa_servico is not None else 0.0,
        distancia_km=float(distancia_km) if distancia_km is not None else None,
        tempo_estimado_minutos=int(tempo_estimado) if tempo_estimado is not None else None,
    )

