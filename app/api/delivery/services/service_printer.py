from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from app.api.delivery.repositories.repo_printer import PrinterRepository
from app.api.delivery.schemas.schema_printer import (
    PedidoPendenteImpressaoResponse,
    RespostaImpressaoPrinter,
)


class PrinterService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PrinterRepository(db)

    def get_pedidos_pendentes_para_impressao(self, empresa_id: int, limite: int | None = None) -> List[PedidoPendenteImpressaoResponse]:
        pedidos = self.repo.get_pedidos_pendentes_impressao(empresa_id=empresa_id, limite=limite)
        # Converter para resposta simplificada
        resposta: List[PedidoPendenteImpressaoResponse] = []
        for p in pedidos:
            resposta.append(
                PedidoPendenteImpressaoResponse(
                    id=p.id,
                    status=p.status,
                    cliente_nome=p.cliente.nome if p.cliente else "Cliente não informado",
                    cliente_telefone=p.cliente.telefone if p.cliente else None,
                    valor_total=float(p.valor_total or 0),
                    data_criacao=p.data_criacao,
                    endereco=None,  # endereço completo não é necessário nesta listagem simplificada
                    meio_pagamento_descricao=p.meio_pagamento.display() if p.meio_pagamento else None,
                )
            )
        return resposta

    def marcar_pedido_impresso_manual(self, pedido_id: int) -> RespostaImpressaoPrinter:
        ok = self.repo.marcar_pedido_impresso(pedido_id)
        if ok:
            return RespostaImpressaoPrinter(
                sucesso=True,
                mensagem=f"Pedido {pedido_id} marcado como impresso",
                numero_pedido=pedido_id,
            )
        return RespostaImpressaoPrinter(
            sucesso=False,
            mensagem=f"Não foi possível marcar o pedido {pedido_id} como impresso",
            numero_pedido=pedido_id,
        )

    def get_estatisticas_impressao(self, empresa_id: int) -> dict:
        return self.repo.get_estatisticas_impressao(empresa_id)


