from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database.db_connection import get_db
from .schemas import ProductQueryOut, TaxaRequest, TaxaResponse, CadastroRequest, ResumoRequest
from .services import ProductFAQService, DeliveryFeeService, CustomerService, OrderSummaryService

router = APIRouter(prefix="/api/chatbot", tags=["API - Chatbot Minimal"])


@router.get("/product", response_model=Optional[ProductQueryOut])
def product_info(q: str, empresa_id: int = 1, db: Session = Depends(get_db)):
    svc = ProductFAQService(db)
    prod = svc.find_product(empresa_id, q)
    if not prod:
        return None
    return ProductQueryOut(
        cod_barras=prod.get("cod_barras"),
        descricao=prod.get("descricao"),
        preco_venda=prod.get("preco_venda"),
        imagem=prod.get("imagem"),
        disponivel=prod.get("disponivel"),
    )


@router.post("/taxa", response_model=TaxaResponse)
def calcular_taxa(body: TaxaRequest, db: Session = Depends(get_db)):
    svc = DeliveryFeeService(db)
    try:
        out = svc.calcular(body.empresa_id, body.endereco, body.tipo_entrega)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return TaxaResponse(**out)


@router.post("/cadastro")
def cadastro_rapido(body: CadastroRequest, db: Session = Depends(get_db)):
    svc = CustomerService(db)
    try:
        cliente = svc.cadastrar_rapido(body.nome, body.telefone, body.email)
        return {"success": True, "cliente_id": getattr(cliente, "id", None), "nome": getattr(cliente, "nome", None)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resumo")
def enviar_resumo(body: ResumoRequest, db: Session = Depends(get_db)):
    svc = OrderSummaryService(db)
    msg = svc.build_summary(body.pedido_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    # Por ora apenas retorna a mensagem formatada; integrações externas podem enviar via WhatsApp
    return {"mensagem": msg}

