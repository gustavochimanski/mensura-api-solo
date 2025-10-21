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
            # Converte itens
            itens = []
            for item in p.itens:
                from app.api.delivery.schemas.schema_printer import ItemPedidoPrinter
                itens.append(ItemPedidoPrinter(
                    descricao=item.produto_descricao_snapshot or f"Produto {item.produto_cod_barras}",
                    quantidade=item.quantidade,
                    preco=float(item.preco_unitario),
                    observacao=item.observacao
                ))
            
            # Monta endereço
            endereco_str = None
            if p.endereco_snapshot:
                endereco = p.endereco_snapshot
                endereco_str = ", ".join(filter(None, [
                    endereco.get("logradouro"),
                    endereco.get("numero"),
                    endereco.get("bairro"),
                    endereco.get("cidade"),
                    endereco.get("cep"),
                    endereco.get("complemento")
                ]))
            elif p.cliente and p.cliente.enderecos:
                endereco = p.cliente.enderecos[0]
                endereco_str = ", ".join(filter(None, [
                    endereco.logradouro,
                    endereco.numero,
                    endereco.bairro,
                    endereco.cidade,
                    endereco.cep,
                    endereco.complemento
                ]))
            
            # Dados da empresa
            from app.api.delivery.schemas.schema_printer import DadosEmpresaPrinter
            empresa_data = DadosEmpresaPrinter(
                cnpj=p.empresa.cnpj if p.empresa else None,
                endereco=None,  # Não é necessário para impressão
                telefone=p.empresa.telefone if p.empresa else None
            )
            
            resposta.append(
                PedidoPendenteImpressaoResponse(
                    numero=p.id,
                    status=p.status,
                    cliente=p.cliente.nome if p.cliente else "Cliente não informado",
                    telefone_cliente=p.cliente.telefone if p.cliente else None,
                    itens=itens,
                    subtotal=float(p.subtotal or 0),
                    desconto=float(p.desconto or 0),
                    taxa_entrega=float(p.taxa_entrega or 0),
                    taxa_servico=float(p.taxa_servico or 0),
                    total=float(p.valor_total or 0),
                    tipo_pagamento=p.meio_pagamento.display() if p.meio_pagamento else "Não informado",
                    troco=float(p.troco_para - p.valor_total) if p.troco_para and p.troco_para > 0 else None,
                    observacao_geral=p.observacao_geral,
                    endereco=endereco_str,
                    data_criacao=p.data_criacao,
                    empresa=empresa_data
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


