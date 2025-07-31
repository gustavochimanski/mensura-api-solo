from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.delivery.repositories.pedido_repo import PedidoRepository
from app.api.pagarme.schemas_pagarme import PagamentoRequest, PagamentoResponse
from app.api.pagarme.service_pagarme import PagamentoService
from app.database.db_connection import get_db
from app.api.pagarme.repositories.transacao_repo import TransacaoPagamentoRepository


router = APIRouter(prefix="/pagamentos", tags=["Pagamentos"])

@router.post("/", response_model=PagamentoResponse)
def criar_pagamento(payload: PagamentoRequest, db: Session = Depends(get_db)):
    service = PagamentoService(db)
    return service.processar_pagamento(payload)

@router.post("/webhook")
def receber_webhook(payload: dict, db: Session = Depends(get_db)):
    evento = payload.get("event")
    transacao = payload.get("transaction", {})

    if not evento or not transacao:
        raise HTTPException(status_code=400, detail="Webhook malformado")

    pedido_id = transacao.get("metadata", {}).get("pedido_id")
    transacao_id = transacao.get("id")
    novo_status = transacao.get("status")

    if not pedido_id or not transacao_id or not novo_status:
        raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes")

    # Atualiza status do pedido
    repo = PedidoRepository(db)
    pedido = repo.get_by_id(pedido_id)
    if pedido:
        repo.atualizar_status(pedido, novo_status)

    # Atualiza status da transação
    repo_transacao = TransacaoPagamentoRepository(db)
    repo_transacao.atualizar_status(transacao_id, novo_status)

    return {"ok": True}
