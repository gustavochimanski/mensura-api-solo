from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, case

from app.api.caixas.models.model_caixa import CaixaModel
from app.utils.logger import logger


class CaixaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, caixa_id: int) -> Optional[CaixaModel]:
        """Busca um caixa por ID com relacionamentos"""
        return (
            self.db.query(CaixaModel)
            .options(
                joinedload(CaixaModel.empresa),
                joinedload(CaixaModel.usuario_abertura),
                joinedload(CaixaModel.usuario_fechamento)
            )
            .filter(CaixaModel.id == caixa_id)
            .first()
        )

    def get_caixa_aberto(self, empresa_id: int) -> Optional[CaixaModel]:
        """Busca o caixa aberto de uma empresa"""
        return (
            self.db.query(CaixaModel)
            .options(
                joinedload(CaixaModel.empresa),
                joinedload(CaixaModel.usuario_abertura)
            )
            .filter(
                and_(
                    CaixaModel.empresa_id == empresa_id,
                    CaixaModel.status == "ABERTO"
                )
            )
            .first()
        )

    def list(
        self,
        empresa_id: Optional[int] = None,
        status: Optional[str] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[CaixaModel]:
        """Lista caixas com filtros opcionais"""
        query = (
            self.db.query(CaixaModel)
            .options(
                joinedload(CaixaModel.empresa),
                joinedload(CaixaModel.usuario_abertura),
                joinedload(CaixaModel.usuario_fechamento)
            )
        )

        if empresa_id:
            query = query.filter(CaixaModel.empresa_id == empresa_id)
        
        if status:
            query = query.filter(CaixaModel.status == status)
        
        if data_inicio:
            query = query.filter(CaixaModel.data_abertura >= datetime.combine(data_inicio, datetime.min.time()))
        
        if data_fim:
            query = query.filter(CaixaModel.data_abertura <= datetime.combine(data_fim, datetime.max.time()))

        query = query.order_by(CaixaModel.data_abertura.desc())
        query = query.offset(skip)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()

    def create(self, **data) -> CaixaModel:
        """Cria um novo caixa"""
        from app.utils.database_utils import now_trimmed
        
        # Se data_hora_abertura não foi fornecida, usa timestamp atual
        if 'data_hora_abertura' not in data or data['data_hora_abertura'] is None:
            data['data_hora_abertura'] = now_trimmed()
        
        caixa = CaixaModel(**data)
        self.db.add(caixa)
        self.db.commit()
        self.db.refresh(caixa)
        logger.info(f"[Caixa] Criado caixa_id={caixa.id} empresa_id={caixa.empresa_id} data_hora_abertura={caixa.data_hora_abertura}")
        return caixa

    def update(self, caixa: CaixaModel, **data) -> CaixaModel:
        """Atualiza um caixa existente"""
        for key, value in data.items():
            if hasattr(caixa, key) and value is not None:
                setattr(caixa, key, value)
        self.db.commit()
        self.db.refresh(caixa)
        return caixa

    def fechar_caixa(
        self,
        caixa: CaixaModel,
        saldo_real: Decimal,
        data_hora_fechamento: Optional[datetime],
        observacoes_fechamento: Optional[str],
        usuario_id_fechamento: int
    ) -> CaixaModel:
        """Fecha um caixa"""
        from app.utils.database_utils import now_trimmed
        
        caixa.status = "FECHADO"
        caixa.saldo_real = saldo_real
        caixa.valor_final = saldo_real
        caixa.data_hora_fechamento = data_hora_fechamento if data_hora_fechamento else now_trimmed()
        caixa.observacoes_fechamento = observacoes_fechamento
        caixa.usuario_id_fechamento = usuario_id_fechamento
        caixa.data_fechamento = now_trimmed()  # Timestamp automático
        
        # Calcula diferença
        if caixa.saldo_esperado is not None:
            caixa.diferenca = saldo_real - caixa.saldo_esperado
        
        self.db.commit()
        self.db.refresh(caixa)
        logger.info(f"[Caixa] Fechado caixa_id={caixa.id} saldo_real={saldo_real} data_hora_fechamento={caixa.data_hora_fechamento} diferenca={caixa.diferenca}")
        return caixa

    def calcular_saldo_esperado(
        self,
        caixa_id: int,
        empresa_id: int
    ) -> Decimal:
        """
        Calcula o saldo esperado do caixa baseado em:
        - Valor inicial
        + Entradas (pedidos entregues e pagos em dinheiro no período da abertura)
        - Saídas (trocos dados, etc.)
        """
        from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel, TipoEntrega, StatusPedido
        from app.api.cardapio.models.model_transacao_pagamento_dv import TransacaoPagamentoModel
        from app.api.cadastros.models.model_meio_pagamento import MeioPagamentoModel
        from app.api.shared.schemas.schema_shared_enums import PagamentoStatusEnum
        
        caixa = self.get_by_id(caixa_id)
        if not caixa:
            raise ValueError("Caixa não encontrado")
        
        saldo = Decimal(str(caixa.valor_inicial))

        # Captura um timestamp único para evitar pequenas discrepâncias entre consultas
        data_fim = caixa.data_fechamento if caixa.data_fechamento else datetime.utcnow()
        ts_pagamento = func.coalesce(TransacaoPagamentoModel.pago_em, TransacaoPagamentoModel.created_at)

        # Calcula total pago em DINHEIRO por pedido (soma das transações),
        # e limita por pedido ao valor_total do pedido para evitar inflar por múltiplas transações.
        pagos_por_pedido_sq = (
            self.db.query(
                TransacaoPagamentoModel.pedido_id.label("pedido_id"),
                PedidoUnificadoModel.valor_total.label("valor_total_pedido"),
                func.sum(
                    case(
                        (MeioPagamentoModel.tipo == "DINHEIRO", TransacaoPagamentoModel.valor),
                        else_=0
                    )
                ).label("total_pago_dinheiro"),
            )
            .join(PedidoUnificadoModel, TransacaoPagamentoModel.pedido_id == PedidoUnificadoModel.id)
            .join(MeioPagamentoModel, TransacaoPagamentoModel.meio_pagamento_id == MeioPagamentoModel.id)
            .filter(
                and_(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    ts_pagamento >= caixa.data_abertura,
                    ts_pagamento <= data_fim,
                    PedidoUnificadoModel.status == StatusPedido.ENTREGUE.value,
                    TransacaoPagamentoModel.status == PagamentoStatusEnum.PAGO.value,
                    MeioPagamentoModel.tipo == "DINHEIRO",
                )
            )
            .group_by(TransacaoPagamentoModel.pedido_id, PedidoUnificadoModel.valor_total)
            .subquery()
        )

        # Soma os valores por pedido, limitando cada pedido ao seu valor_total (evita duplicidade/overpay)
        total_entradas_q = (
            self.db.query(
                func.sum(func.least(pagos_por_pedido_sq.c.total_pago_dinheiro, pagos_por_pedido_sq.c.valor_total_pedido))
            ).scalar()
        )
        total_entradas = Decimal(str(total_entradas_q or 0))

        # Saídas: trocos dados (troco real) para os mesmos pedidos considerados acima
        pedidos_com_pagamento_dinheiro_sq = (
            self.db.query(pagos_por_pedido_sq.c.pedido_id).subquery()
        )
        query_saidas = (
            self.db.query(func.sum(PedidoUnificadoModel.troco_para - PedidoUnificadoModel.valor_total))
            .filter(
                and_(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.id.in_(self.db.query(pedidos_com_pagamento_dinheiro_sq.c.pedido_id)),
                    PedidoUnificadoModel.status == StatusPedido.ENTREGUE.value,
                    PedidoUnificadoModel.troco_para.isnot(None),
                    PedidoUnificadoModel.troco_para > PedidoUnificadoModel.valor_total,
                )
            )
        )
        total_saidas = Decimal(str(query_saidas.scalar() or 0))
        
        # Retiradas: sangrias e despesas
        from app.api.caixas.models.model_retirada import RetiradaModel
        query_retiradas = (
            self.db.query(func.sum(RetiradaModel.valor))
            .filter(RetiradaModel.caixa_id == caixa_id)
        )
        total_retiradas = Decimal(str(query_retiradas.scalar() or 0))
        
        saldo_esperado = saldo + total_entradas - total_saidas - total_retiradas
        
        # Atualiza o saldo esperado no caixa
        # Atualiza o saldo esperado no caixa (mantendo Decimal internamente)
        caixa.saldo_esperado = saldo_esperado
        self.db.commit()
        return saldo_esperado

    def calcular_valores_esperados_por_meio(
        self,
        caixa_id: int,
        empresa_id: int
    ) -> List[dict]:
        """
        Calcula valores esperados por tipo de meio de pagamento.
        Retorna lista com informações de cada meio de pagamento usado no período.
        Considera apenas pedidos entregues no período da abertura.
        """
        from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel, TipoEntrega, StatusPedido
        from app.api.cardapio.models.model_transacao_pagamento_dv import TransacaoPagamentoModel
        from app.api.cadastros.models.model_meio_pagamento import MeioPagamentoModel
        from app.api.shared.schemas.schema_shared_enums import PagamentoStatusEnum
        
        caixa = self.get_by_id(caixa_id)
        if not caixa:
            raise ValueError("Caixa não encontrado")
        
        data_fim = caixa.data_fechamento if caixa.data_fechamento else datetime.utcnow()
        ts_pagamento = func.coalesce(TransacaoPagamentoModel.pago_em, TransacaoPagamentoModel.created_at)

        # Valor por transação; para DINHEIRO consideramos o valor da transação (pode representar valor recebido),
        # mas consolidaremos por pedido somando transações e limitando por pedido ao seu valor_total.
        valor_para_soma = case(
            (MeioPagamentoModel.tipo == "DINHEIRO", TransacaoPagamentoModel.valor),
            else_=TransacaoPagamentoModel.valor,
        )

        # Consolida por (meio, pedido) somando todas as transações válidas do período.
        # Também traz o valor_total do pedido para permitir cap por pedido quando o meio for DINHEIRO.
        por_pedido_meio_sq = (
            self.db.query(
                MeioPagamentoModel.id.label("meio_pagamento_id"),
                MeioPagamentoModel.nome.label("meio_pagamento_nome"),
                MeioPagamentoModel.tipo.label("meio_pagamento_tipo"),
                TransacaoPagamentoModel.pedido_id.label("pedido_id"),
                PedidoUnificadoModel.valor_total.label("valor_total_pedido"),
                func.sum(valor_para_soma).label("valor_por_pedido"),
            )
            .join(TransacaoPagamentoModel, MeioPagamentoModel.id == TransacaoPagamentoModel.meio_pagamento_id)
            .join(PedidoUnificadoModel, TransacaoPagamentoModel.pedido_id == PedidoUnificadoModel.id)
            .filter(
                and_(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    ts_pagamento >= caixa.data_abertura,
                    ts_pagamento <= data_fim,
                    PedidoUnificadoModel.status == StatusPedido.ENTREGUE.value,
                    TransacaoPagamentoModel.status == PagamentoStatusEnum.PAGO.value,
                )
            )
            .group_by(
                MeioPagamentoModel.id,
                MeioPagamentoModel.nome,
                MeioPagamentoModel.tipo,
                TransacaoPagamentoModel.pedido_id,
                PedidoUnificadoModel.valor_total,
            )
            .subquery()
        )

        # Ao agregar por meio, para DINHEIRO limitamos o valor por pedido ao valor_total do pedido.
        query = (
            self.db.query(
                por_pedido_meio_sq.c.meio_pagamento_id.label("id"),
                por_pedido_meio_sq.c.meio_pagamento_nome.label("nome"),
                por_pedido_meio_sq.c.meio_pagamento_tipo.label("tipo"),
                func.sum(
                    case(
                        (por_pedido_meio_sq.c.meio_pagamento_tipo == "DINHEIRO",
                         func.least(por_pedido_meio_sq.c.valor_por_pedido, por_pedido_meio_sq.c.valor_total_pedido)),
                        else_=por_pedido_meio_sq.c.valor_por_pedido
                    )
                ).label("valor_total"),
                func.count(por_pedido_meio_sq.c.pedido_id).label("quantidade"),
            )
            .group_by(
                por_pedido_meio_sq.c.meio_pagamento_id,
                por_pedido_meio_sq.c.meio_pagamento_nome,
                por_pedido_meio_sq.c.meio_pagamento_tipo,
            )
        )
        
        resultados = query.all()
        
        # Formata resultado
        valores_por_meio = []
        for row in resultados:
            valores_por_meio.append({
                'meio_pagamento_id': row.id,
                'meio_pagamento_nome': row.nome,
                'meio_pagamento_tipo': row.tipo.value if hasattr(row.tipo, 'value') else str(row.tipo),
                'valor_esperado': float(row.valor_total or 0),
                'quantidade_transacoes': row.quantidade or 0
            })
        
        return valores_por_meio

    def criar_conferencias(
        self,
        caixa_id: int,
        conferencias: List[dict]
    ) -> List:
        """
        Cria registros de conferência para cada meio de pagamento.
        conferencias: Lista com dicts contendo meio_pagamento_id, valor_conferido, valor_esperado, observacoes
        """
        from app.api.financeiro.models.model_caixa_conferencia import CaixaConferenciaModel
        
        conferencias_criadas = []
        
        for conf in conferencias:
            conferencia = CaixaConferenciaModel(
                caixa_id=caixa_id,
                meio_pagamento_id=conf['meio_pagamento_id'],
                valor_esperado=conf['valor_esperado'],
                valor_conferido=conf['valor_conferido'],
                diferenca=conf['valor_conferido'] - conf['valor_esperado'],
                quantidade_transacoes=conf.get('quantidade_transacoes', 0),
                observacoes=conf.get('observacoes')
            )
            self.db.add(conferencia)
            conferencias_criadas.append(conferencia)
        
        self.db.commit()
        
        # Recarrega com relacionamentos
        for conf in conferencias_criadas:
            self.db.refresh(conf)
        
        return conferencias_criadas

    def get_conferencias_by_caixa(self, caixa_id: int) -> List:
        """Busca todas as conferências de um caixa"""
        from app.api.financeiro.models.model_caixa_conferencia import CaixaConferenciaModel
        
        return (
            self.db.query(CaixaConferenciaModel)
            .options(joinedload(CaixaConferenciaModel.meio_pagamento))
            .filter(CaixaConferenciaModel.caixa_id == caixa_id)
            .all()
        )

