from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional

from app.api.delivery.models.pedido_dv_model import PedidoDeliveryModel
from app.api.delivery.models.pedido_item_dv_model import PedidoItemModel
from app.api.delivery.models.pedido_status_historico_dv_model import PedidoStatusHistoricoModel
from app.api.delivery.models.cliente_dv_model import ClienteDeliveryModel
from app.api.delivery.models.endereco_dv_model import EnderecoDeliveryModel
from app.api.mensura.models.cadprod_emp_model import ProdutoEmpModel
from app.api.delivery.models.cupom_dv_model import CupomDescontoModel
from app.api.delivery.models.transacao_pagamento_dv_model import TransacaoPagamentoModel

class PedidoRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Cliente ---
    def get_cliente_por_telefone(self, telefone: str) -> Optional[ClienteDeliveryModel]:
        return self.db.query(ClienteDeliveryModel).filter_by(telefone=telefone).first()

    def criar_cliente_telefone(self, telefone: str, nome: str) -> ClienteDeliveryModel:
        cliente = ClienteDeliveryModel(telefone=telefone, nome=nome, ativo=True)
        self.db.add(cliente)
        self.db.flush()
        return cliente

    # --- Endereço ---
    def get_endereco_por_dados(self, cliente_id: int, endereco) -> Optional[EnderecoDeliveryModel]:
        return (
            self.db.query(EnderecoDeliveryModel)
            .filter_by(
                cliente_id=cliente_id,
                logradouro=endereco.rua,
                numero=endereco.numero,
                bairro=endereco.bairro,
                cidade=endereco.cidade,
                uf=endereco.uf,
                cep=endereco.cep
            )
            .first()
        )

    def criar_endereco(self, cliente_id: int, endereco) -> EnderecoDeliveryModel:
        end = EnderecoDeliveryModel(
            cliente_id=cliente_id,
            logradouro=endereco.rua,
            numero=endereco.numero,
            complemento=endereco.complemento,
            bairro=endereco.bairro,
            cidade=endereco.cidade,
            uf=endereco.uf,
            cep=endereco.cep,
        )
        self.db.add(end)
        self.db.flush()
        return end

    # --- Pedido / Itens ---
    def criar_pedido(self, *, cliente_id: int, empresa_id: int, endereco_id: int, status: str,
                      tipo_entrega: str, origem: str, meio_pagamento: str) -> PedidoDeliveryModel:
        pedido = PedidoDeliveryModel(
            cliente_id=cliente_id,
            empresa_id=empresa_id,
            endereco_id=endereco_id,
            status=status,
            tipo_entrega=tipo_entrega,
            origem=origem,
            meio_pagamento=meio_pagamento,
            subtotal=Decimal("0"),
            desconto=Decimal("0"),
            taxa_entrega=Decimal("0"),
            taxa_servico=Decimal("0"),
            valor_total=Decimal("0"),
        )
        self.db.add(pedido)
        self.db.flush()
        self.add_status_historico(pedido.id, status, motivo="Pedido criado")
        return pedido

    def adicionar_item(self, *, pedido_id: int, cod_barras: str, quantidade: int,
                       preco_unitario: Decimal, observacao: str | None,
                       produto_descricao_snapshot: str | None, produto_imagem_snapshot: str | None) -> PedidoItemModel:
        item = PedidoItemModel(
            pedido_id=pedido_id,
            produto_cod_barras=cod_barras,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            observacao=observacao,
            produto_descricao_snapshot=produto_descricao_snapshot,
            produto_imagem_snapshot=produto_imagem_snapshot,
        )
        self.db.add(item)
        return item

    def atualizar_totais(self, pedido: PedidoDeliveryModel, *, subtotal: Decimal,
                         desconto: Decimal, taxa_entrega: Decimal, taxa_servico: Decimal):
        pedido.subtotal = subtotal
        pedido.desconto = desconto
        pedido.taxa_entrega = taxa_entrega
        pedido.taxa_servico = taxa_servico
        pedido.valor_total = subtotal - desconto + taxa_entrega + taxa_servico
        if pedido.valor_total < 0:
            pedido.valor_total = Decimal("0")

    # --- Status ---
    def add_status_historico(self, pedido_id: int, status: str, motivo: str | None = None, criado_por: str | None = "system"):
        hist = PedidoStatusHistoricoModel(pedido_id=pedido_id, status=status, motivo=motivo, criado_por=criado_por)
        self.db.add(hist)

    def atualizar_status_pedido(self, pedido: PedidoDeliveryModel, novo_status: str, motivo: str | None = None):
        pedido.status = novo_status
        self.add_status_historico(pedido.id, novo_status, motivo=motivo)

    # --- Produto ---
    def get_produto_emp(self, empresa_id: int, cod_barras: str) -> Optional[ProdutoEmpModel]:
        return (
            self.db.query(ProdutoEmpModel)
            .options(joinedload(ProdutoEmpModel.produto))
            .filter(
                ProdutoEmpModel.empresa_id == empresa_id,
                ProdutoEmpModel.cod_barras == cod_barras,
            )
            .first()
        )

    # --- Cupom ---
    def get_cupom(self, cupom_id: int) -> Optional[CupomDescontoModel]:
        return self.db.get(CupomDescontoModel, cupom_id)

    # --- Pedido completo ---
    def get_pedido(self, pedido_id: int) -> Optional[PedidoDeliveryModel]:
        return (
            self.db.query(PedidoDeliveryModel)
            .options(joinedload(PedidoDeliveryModel.itens), joinedload(PedidoDeliveryModel.transacao))
            .filter(PedidoDeliveryModel.id == pedido_id)
            .first()
        )

    # --- Transação ---
    def criar_transacao_pagamento(self, *, pedido_id: int, gateway: str, metodo: str, valor: Decimal, moeda: str = "BRL") -> TransacaoPagamentoModel:
        tx = TransacaoPagamentoModel(
            pedido_id=pedido_id, gateway=gateway, metodo=metodo, valor=valor, moeda=moeda, status="PENDENTE"
        )
        self.db.add(tx)
        self.db.flush()
        return tx

    def atualizar_transacao_status(self, tx: TransacaoPagamentoModel, *, status: str, provider_transaction_id: str | None = None,
                                   payload_retorno: dict | None = None, qr_code: str | None = None, qr_code_base64: str | None = None,
                                   timestamp_field: str | None = None):
        tx.status = status
        if provider_transaction_id is not None:
            tx.provider_transaction_id = provider_transaction_id
        if payload_retorno is not None:
            tx.payload_retorno = payload_retorno
        if qr_code is not None:
            tx.qr_code = qr_code
        if qr_code_base64 is not None:
            tx.qr_code_base64 = qr_code_base64
        if timestamp_field:
            setattr(tx, timestamp_field, func.now())

    # --- Commit / Rollback ---
    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
