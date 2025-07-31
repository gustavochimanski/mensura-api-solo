from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.api.delivery.repositories.pedido_repo import PedidoRepository
from app.api.pagarme.fake_pagarme_client import FakePagarmeClient
from app.api.pagarme.schemas_pagarme import PagamentoRequest, PagamentoResponse
from app.api.pagarme.repositories.transacao_repo import TransacaoPagamentoRepository

class PagamentoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PedidoRepository(db)
        self.repo_transacao = TransacaoPagamentoRepository(db)
        self.pagarme = FakePagarmeClient()

    def processar_pagamento(self, data: PagamentoRequest) -> PagamentoResponse:
        pedido = self.repo.get_by_id(data.pedido_id)
        if not pedido:
            raise HTTPException(404, "Pedido não encontrado")

        if pedido.status != "P":
            raise HTTPException(400, "Pedido já processado")

        resultado = self.pagarme.criar_transacao(pedido, data.metodo_pagamento, data.token_cartao)

        # Salva transação no banco
        self.repo_transacao.criar({
            "pedido_id": pedido.id,
            "metodo": data.metodo_pagamento,
            "status": resultado["status"],
            "boleto_url": resultado.get("boleto_url"),
            "pix_qr_code_url": resultado.get("pix_qr_code_url"),
            "id": resultado["transaction_id"]
        })

        self.repo.atualizar_status(pedido, resultado["status"])

        return PagamentoResponse(
            status=resultado["status"],
            transaction_id=resultado["transaction_id"],
            boleto_url=resultado.get("boleto_url"),
            pix_qr_code_url=resultado.get("pix_qr_code_url"),
        )

