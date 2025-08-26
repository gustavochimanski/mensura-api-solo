from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List
from app.api.delivery.repositories.repo_pedidos import PedidoRepository
from app.api.delivery.schemas.schema_pedido_dv import (
    FinalizarPedidoRequest, ItemPedidoRequest, PedidoResponse, ItemPedidoResponse
)
from app.api.delivery.schemas.schema_shared_enums import (
    PedidoStatusEnum, TipoEntregaEnum, OrigemPedidoEnum
)

from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.delivery.services.service_pagamento_gateway import PaymentGatewayClient

QTD_MAX_ITENS = 200

def _dec(value: float | Decimal | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class PedidoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PedidoRepository(db)
        self.gateway = PaymentGatewayClient()  # MOCK

    # ---------- Helper ----------
    def _pedido_to_response(self, pedido) -> PedidoResponse:
        return PedidoResponse(
            id=pedido.id,
            status=PedidoStatusEnum(pedido.status),
            cliente_id=pedido.cliente_id,
            empresa_id=pedido.empresa_id,
            entregador_id=getattr(pedido, "entregador_id", None),
            endereco_id=pedido.endereco_id,
            tipo_entrega=(pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                          else TipoEntregaEnum(pedido.tipo_entrega)),
            origem=(pedido.origem if isinstance(pedido.origem, OrigemPedidoEnum)
                    else OrigemPedidoEnum(pedido.origem)),
            meio_pagamento=pedido.meio_pagamento,
            subtotal=float(pedido.subtotal or 0),
            desconto=float(pedido.desconto or 0),
            taxa_entrega=float(pedido.taxa_entrega or 0),
            taxa_servico=float(pedido.taxa_servico or 0),
            valor_total=float(pedido.valor_total or 0),
            previsao_entrega=getattr(pedido, "previsao_entrega", None),
            distancia_km=(float(pedido.distancia_km) if getattr(pedido, "distancia_km", None) else None),
            observacao_geral=getattr(pedido, "observacao_geral", None),
            troco_para=(float(pedido.troco_para) if getattr(pedido, "troco_para", None) else None),
            cupom_id=getattr(pedido, "cupom_id", None),
            data_criacao=getattr(pedido, "data_criacao", getattr(pedido, "created_at", None)),
            data_atualizacao=getattr(pedido, "data_atualizacao", getattr(pedido, "updated_at", None)),
            itens=[ItemPedidoResponse(
                id=it.id,
                produto_cod_barras=it.produto_cod_barras,
                quantidade=it.quantidade,
                preco_unitario=float(it.preco_unitario),
                observacao=it.observacao,
                produto_descricao_snapshot=it.produto_descricao_snapshot,
                produto_imagem_snapshot=it.produto_imagem_snapshot
            ) for it in pedido.itens]
        )

    # ---------- Fluxo checkout ----------
    def finalizar_pedido(self, payload: FinalizarPedidoRequest) -> PedidoResponse:
        if not payload.itens:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido vazio")
        if len(payload.itens) > QTD_MAX_ITENS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Itens demais no pedido")

        # Cliente
        cliente = self.repo.get_cliente_por_telefone(payload.cliente_number)
        if not cliente:
            cliente = self.repo.criar_cliente_telefone(payload.cliente_number)

        # Endereço
        endereco = self.repo.get_endereco_por_dados(cliente.id, payload.endereco)
        if not endereco:
            endereco = self.repo.criar_endereco(cliente.id, payload.endereco)

        try:
            pedido = self.repo.criar_pedido(
                cliente_id=cliente.id,
                empresa_id=payload.empresa_id,
                endereco_id=endereco.id,
                status=PedidoStatusEnum.P.value,
                tipo_entrega=payload.tipo_entrega.value,
                origem=payload.origem.value,
                meio_pagamento=payload.meio_pagamento,
            )

            subtotal = Decimal("0")
            for it in payload.itens:
                pe = self.repo.get_produto_emp(payload.empresa_id, it.produto_cod_barras)
                if not pe or not pe.disponivel or not (pe.produto and pe.produto.ativo):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Produto indisponível: {it.produto_cod_barras}")
                preco = _dec(pe.preco_venda)
                subtotal += preco * it.quantidade

                self.repo.adicionar_item(
                    pedido_id=pedido.id,
                    cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    preco_unitario=preco,
                    observacao=it.observacao,
                    produto_descricao_snapshot=pe.produto.descricao if pe.produto else None,
                    produto_imagem_snapshot=pe.produto.imagem if pe.produto else None,
                )

            # cupom e taxas
            desconto = Decimal("0")
            taxa_entrega = _dec(8.90) if payload.tipo_entrega == TipoEntregaEnum.DELIVERY else _dec(0)
            taxa_servico = (subtotal * Decimal("0.05")).quantize(Decimal("0.01"))

            self.repo.atualizar_totais(pedido, subtotal=subtotal, desconto=desconto,
                                       taxa_entrega=taxa_entrega, taxa_servico=taxa_servico)

            pedido.observacao_geral = payload.observacao_geral
            if payload.troco_para:
                pedido.troco_para = _dec(payload.troco_para)

            self.repo.commit()
            self.db.refresh(pedido)

        except Exception as e:
            self.repo.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao finalizar pedido: {e}")

        return self._pedido_to_response(pedido)
