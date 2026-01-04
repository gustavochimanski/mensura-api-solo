class WSEvents:
    """
    Contrato central de eventos WebSocket (evita strings soltas e typos).
    Convenção: <dominio>.v1.<acao>
    """

    PEDIDO_CRIADO = "pedido.v1.criado"
    PEDIDO_ATUALIZADO = "pedido.v1.atualizado"
    PEDIDO_APROVADO = "pedido.v1.aprovado"
    PEDIDO_CANCELADO = "pedido.v1.cancelado"
    PEDIDO_ENTREGUE = "pedido.v1.entregue"
    PEDIDO_IMPRESSO = "pedido.v1.impresso"

    MEIOS_PAGAMENTO_ATUALIZADOS = "meios_pagamento.v1.atualizados"


