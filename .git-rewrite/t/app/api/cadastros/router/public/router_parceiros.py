from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.api.cadastros.schemas.schema_parceiros import (
    ParceiroOut, BannerParceiroOut, ParceiroCompletoOut
)
from app.api.cadastros.schemas.schema_cupom import CupomParceiroOut
from app.api.cadastros.services.service_parceiros import ParceirosService
from app.database.db_connection import get_db

router = APIRouter(prefix="/api/cadastros/public/parceiros", tags=["Public - Cadastros - Parceiros"])

# ======================================================================
# ========================= ENDPOINTS PÚBLICOS =========================
# ======================================================================

@router.get("/", response_model=list[ParceiroOut])
def list_parceiros(db: Session = Depends(get_db)):
    """
    Lista todos os parceiros (endpoint público)
    """
    return ParceirosService(db).list_parceiros()


@router.get("/banners", response_model=list[BannerParceiroOut])
def list_banners(parceiro_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    """
    Lista banners para clientes (endpoint público)
    """
    return ParceirosService(db).list_banners(parceiro_id)

@router.get("/{parceiro_id}/full", response_model=ParceiroCompletoOut)
def get_parceiro_completo(parceiro_id: int, db: Session = Depends(get_db)):
    """
    Retorna parceiro completo com banners e cupons (endpoint público)
    """
    parceiro = ParceirosService(db).get_parceiro_completo(parceiro_id)
    return ParceiroCompletoOut(
        id=parceiro.id,
        nome=parceiro.nome,
        ativo=parceiro.ativo,
        telefone=parceiro.telefone,
        cupons=[
            CupomParceiroOut(
                id=c.id,
                codigo=c.codigo,
                descricao=c.descricao,
                desconto_valor=float(c.desconto_valor) if c.desconto_valor is not None else None,
                desconto_percentual=float(c.desconto_percentual) if c.desconto_percentual is not None else None,
                ativo=c.ativo,
                monetizado=c.monetizado,
                valor_por_lead=float(c.valor_por_lead) if c.valor_por_lead is not None else None,
                link_redirecionamento=c.link_redirecionamento
            ) for c in parceiro.cupons
        ],
        banners=[
            BannerParceiroOut(
                id=b.id,
                nome=b.nome,
                ativo=b.ativo,
                tipo_banner=b.tipo_banner,
                imagem=b.imagem,
                categoria_id=b.categoria_id,
                 link_redirecionamento=b.link_redirecionamento,
                 redireciona_categoria=b.redireciona_categoria,
                href_destino=b.href_destino
            ) for b in parceiro.banners
        ]
    )
