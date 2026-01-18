from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.api.caixas.models.model_caixa_abertura import CaixaAberturaModel
from app.utils.logger import logger


class CaixaAberturaRepository:
    """Repository para aberturas de caixa"""
    
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, caixa_abertura_id: int) -> Optional[CaixaAberturaModel]:
        """Busca uma abertura de caixa por ID com relacionamentos"""
        return (
            self.db.query(CaixaAberturaModel)
            .options(
                joinedload(CaixaAberturaModel.empresa),
                joinedload(CaixaAberturaModel.caixa),
                joinedload(CaixaAberturaModel.usuario_abertura),
                joinedload(CaixaAberturaModel.usuario_fechamento)
            )
            .filter(CaixaAberturaModel.id == caixa_abertura_id)
            .first()
        )

    def get_caixa_aberto(self, empresa_id: int, caixa_id: Optional[int] = None) -> Optional[CaixaAberturaModel]:
        """Busca a abertura de caixa aberta de uma empresa (e opcionalmente de um caixa específico)"""
        query = (
            self.db.query(CaixaAberturaModel)
            .options(
                joinedload(CaixaAberturaModel.empresa),
                joinedload(CaixaAberturaModel.caixa),
                joinedload(CaixaAberturaModel.usuario_abertura)
            )
            .filter(
                and_(
                    CaixaAberturaModel.empresa_id == empresa_id,
                    CaixaAberturaModel.status == "ABERTO"
                )
            )
        )
        
        if caixa_id:
            query = query.filter(CaixaAberturaModel.caixa_id == caixa_id)
        
        return query.first()

    def list(
        self,
        empresa_id: Optional[int] = None,
        caixa_id: Optional[int] = None,
        status: Optional[str] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[CaixaAberturaModel]:
        """Lista aberturas de caixa com filtros opcionais"""
        query = (
            self.db.query(CaixaAberturaModel)
            .options(
                joinedload(CaixaAberturaModel.empresa),
                joinedload(CaixaAberturaModel.caixa),
                joinedload(CaixaAberturaModel.usuario_abertura),
                joinedload(CaixaAberturaModel.usuario_fechamento)
            )
        )

        if empresa_id:
            query = query.filter(CaixaAberturaModel.empresa_id == empresa_id)
        
        if caixa_id:
            query = query.filter(CaixaAberturaModel.caixa_id == caixa_id)
        
        if status:
            query = query.filter(CaixaAberturaModel.status == status)
        
        if data_inicio:
            query = query.filter(CaixaAberturaModel.data_abertura >= datetime.combine(data_inicio, datetime.min.time()))
        
        if data_fim:
            query = query.filter(CaixaAberturaModel.data_abertura <= datetime.combine(data_fim, datetime.max.time()))

        query = query.order_by(CaixaAberturaModel.data_abertura.desc())
        query = query.offset(skip)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()

    def create(self, **data) -> CaixaAberturaModel:
        """Cria uma nova abertura de caixa"""
        from app.utils.database_utils import now_trimmed
        
        # Se data_hora_abertura não foi fornecida, usa timestamp atual
        if 'data_hora_abertura' not in data or data['data_hora_abertura'] is None:
            data['data_hora_abertura'] = now_trimmed()
        
        caixa_abertura = CaixaAberturaModel(**data)
        self.db.add(caixa_abertura)
        self.db.commit()
        self.db.refresh(caixa_abertura)
        logger.info(f"[CaixaAbertura] Criado caixa_abertura_id={caixa_abertura.id} caixa_id={caixa_abertura.caixa_id} empresa_id={caixa_abertura.empresa_id}")
        return caixa_abertura

    def update(self, caixa_abertura: CaixaAberturaModel, **data) -> CaixaAberturaModel:
        """Atualiza uma abertura de caixa existente"""
        for key, value in data.items():
            if hasattr(caixa_abertura, key) and value is not None:
                setattr(caixa_abertura, key, value)
        self.db.commit()
        self.db.refresh(caixa_abertura)
        return caixa_abertura

    def fechar_caixa(
        self,
        caixa_abertura: CaixaAberturaModel,
        saldo_real: Decimal,
        data_hora_fechamento: Optional[datetime],
        observacoes_fechamento: Optional[str],
        usuario_id_fechamento: int
    ) -> CaixaAberturaModel:
        """Fecha uma abertura de caixa"""
        from app.utils.database_utils import now_trimmed
        
        caixa_abertura.status = "FECHADO"
        caixa_abertura.saldo_real = saldo_real
        caixa_abertura.valor_final = saldo_real
        caixa_abertura.data_hora_fechamento = data_hora_fechamento if data_hora_fechamento else now_trimmed()
        caixa_abertura.observacoes_fechamento = observacoes_fechamento
        caixa_abertura.usuario_id_fechamento = usuario_id_fechamento
        caixa_abertura.data_fechamento = now_trimmed()  # Timestamp automático
        
        # Calcula diferença
        if caixa_abertura.saldo_esperado is not None:
            caixa_abertura.diferenca = saldo_real - caixa_abertura.saldo_esperado
        
        self.db.commit()
        self.db.refresh(caixa_abertura)
        logger.info(f"[CaixaAbertura] Fechado caixa_abertura_id={caixa_abertura.id} saldo_real={saldo_real} diferenca={caixa_abertura.diferenca}")
        return caixa_abertura

    def calcular_saldo_esperado(
        self,
        caixa_abertura_id: int,
        empresa_id: int
    ) -> Decimal:
        """
        Calcula o saldo esperado da abertura de caixa baseado em:
        - Valor inicial
        + Entradas (pedidos pagos em dinheiro)
        - Saídas (trocos dados, etc.)
        """
        from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel
        from app.api.cardapio.models.model_transacao_pagamento_dv import TransacaoPagamentoModel
        from app.api.cadastros.models.model_meio_pagamento import MeioPagamentoModel
        from app.api.shared.schemas.schema_shared_enums import PagamentoStatusEnum
        
        caixa_abertura = self.get_by_id(caixa_abertura_id)
        if not caixa_abertura:
            raise ValueError("Abertura de caixa não encontrada")
        
        saldo = Decimal(str(caixa_abertura.valor_inicial))
        
        # Busca pedidos pagos em dinheiro entre a abertura e agora (ou fechamento)
        data_fim = caixa_abertura.data_fechamento if caixa_abertura.data_fechamento else datetime.utcnow()
        
        # Entradas: pedidos pagos em dinheiro através de transações
        query_entradas = (
            self.db.query(func.sum(TransacaoPagamentoModel.valor))
            .join(PedidoUnificadoModel, TransacaoPagamentoModel.pedido_id == PedidoUnificadoModel.id)
            .join(MeioPagamentoModel, TransacaoPagamentoModel.meio_pagamento_id == MeioPagamentoModel.id)
            .filter(
                and_(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.created_at >= caixa_abertura.data_abertura,
                    PedidoUnificadoModel.created_at <= data_fim,
                    TransacaoPagamentoModel.status == PagamentoStatusEnum.PAGO.value,
                    MeioPagamentoModel.tipo == "DINHEIRO"
                )
            )
        )
        total_entradas = query_entradas.scalar() or Decimal("0")
        
        # Saídas: trocos dados (troco_para - valor_total, quando troco_para > valor_total)
        # Calcula o troco real dado para pedidos pagos em dinheiro com troco
        query_saidas = (
            self.db.query(func.sum(PedidoUnificadoModel.troco_para - PedidoUnificadoModel.valor_total))
            .join(TransacaoPagamentoModel, TransacaoPagamentoModel.pedido_id == PedidoUnificadoModel.id)
            .join(MeioPagamentoModel, TransacaoPagamentoModel.meio_pagamento_id == MeioPagamentoModel.id)
            .filter(
                and_(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.created_at >= caixa_abertura.data_abertura,
                    PedidoUnificadoModel.created_at <= data_fim,
                    PedidoUnificadoModel.troco_para.isnot(None),
                    PedidoUnificadoModel.troco_para > PedidoUnificadoModel.valor_total,
                    TransacaoPagamentoModel.status == PagamentoStatusEnum.PAGO.value,
                    MeioPagamentoModel.tipo == "DINHEIRO"
                )
            )
        )
        total_saidas = query_saidas.scalar() or Decimal("0")
        
        # Retiradas: sangrias e despesas
        from app.api.caixas.models.model_retirada import RetiradaModel
        query_retiradas = (
            self.db.query(func.sum(RetiradaModel.valor))
            .filter(
                and_(
                    RetiradaModel.empresa_id == empresa_id,
                    RetiradaModel.caixa_abertura_id == caixa_abertura_id
                )
            )
        )
        total_retiradas = query_retiradas.scalar() or Decimal("0")
        
        saldo_esperado = saldo + total_entradas - total_saidas - total_retiradas
        
        logger.info(
            f"[CaixaAbertura] Cálculo saldo esperado - caixa_abertura_id={caixa_abertura_id} "
            f"valor_inicial={saldo} entradas={total_entradas} saidas={total_saidas} "
            f"retiradas={total_retiradas} saldo_esperado={saldo_esperado}"
        )
        
        # Atualiza o saldo esperado
        caixa_abertura.saldo_esperado = saldo_esperado
        self.db.commit()
        
        return saldo_esperado

    def calcular_valores_esperados_por_meio(
        self,
        caixa_abertura_id: int,
        empresa_id: int
    ) -> List[dict]:
        """
        Calcula valores esperados por tipo de meio de pagamento.
        Retorna lista com informações de cada meio de pagamento usado no período.
        """
        from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel
        from app.api.cardapio.models.model_transacao_pagamento_dv import TransacaoPagamentoModel
        from app.api.cadastros.models.model_meio_pagamento import MeioPagamentoModel
        from app.api.shared.schemas.schema_shared_enums import PagamentoStatusEnum
        
        caixa_abertura = self.get_by_id(caixa_abertura_id)
        if not caixa_abertura:
            raise ValueError("Abertura de caixa não encontrada")
        
        data_fim = caixa_abertura.data_fechamento if caixa_abertura.data_fechamento else datetime.utcnow()
        
        # Busca valores agrupados por meio de pagamento
        query = (
            self.db.query(
                MeioPagamentoModel.id,
                MeioPagamentoModel.nome,
                MeioPagamentoModel.tipo,
                func.sum(TransacaoPagamentoModel.valor).label('valor_total'),
                func.count(TransacaoPagamentoModel.id).label('quantidade')
            )
            .join(
                TransacaoPagamentoModel,
                MeioPagamentoModel.id == TransacaoPagamentoModel.meio_pagamento_id
            )
            .join(
                PedidoUnificadoModel,
                TransacaoPagamentoModel.pedido_id == PedidoUnificadoModel.id
            )
            .filter(
                and_(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.created_at >= caixa_abertura.data_abertura,
                    PedidoUnificadoModel.created_at <= data_fim,
                    TransacaoPagamentoModel.status == PagamentoStatusEnum.PAGO.value
                )
            )
            .group_by(
                MeioPagamentoModel.id,
                MeioPagamentoModel.nome,
                MeioPagamentoModel.tipo
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
        caixa_abertura_id: int,
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
                caixa_abertura_id=caixa_abertura_id,
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

    def get_conferencias_by_caixa_abertura(self, caixa_abertura_id: int) -> List:
        """Busca todas as conferências de uma abertura de caixa"""
        from app.api.financeiro.models.model_caixa_conferencia import CaixaConferenciaModel
        
        return (
            self.db.query(CaixaConferenciaModel)
            .options(joinedload(CaixaConferenciaModel.meio_pagamento))
            .filter(CaixaConferenciaModel.caixa_abertura_id == caixa_abertura_id)
            .all()
        )

