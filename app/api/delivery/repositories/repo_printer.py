"""
Repository para operações relacionadas à Printer API
"""
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
from app.api.delivery.models.model_pedido_dv import PedidoDeliveryModel
from app.api.delivery.schemas.schema_shared_enums import PedidoStatusEnum
from app.api.delivery.schemas.schema_printer import PedidoParaImpressao, ItemPedidoPrinter
from app.utils.logger import logger


class PrinterRepository:
    """Repository para operações específicas de impressão"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_pedidos_pendentes_impressao(self, empresa_id: int, limite: Optional[int] = None) -> List[PedidoDeliveryModel]:
        """
        Busca pedidos pendentes de impressão (status 'I') de uma empresa
        
        Args:
            empresa_id: ID da empresa
            limite: Número máximo de pedidos (opcional)
            
        Returns:
            Lista de pedidos pendentes de impressão
        """
        query = (
            self.db.query(PedidoDeliveryModel)
            .options(
                joinedload(PedidoDeliveryModel.empresa).joinedload("endereco"),
                joinedload(PedidoDeliveryModel.cliente),
                joinedload(PedidoDeliveryModel.itens),
                joinedload(PedidoDeliveryModel.meio_pagamento)
            )
            .filter(
                and_(
                    PedidoDeliveryModel.empresa_id == empresa_id,
                    PedidoDeliveryModel.status == PedidoStatusEnum.I.value
                )
            )
            .order_by(PedidoDeliveryModel.data_criacao.asc())
        )
        
        if limite:
            query = query.limit(limite)
            
        return query.all()
    
    def get_pedido_para_impressao(self, pedido_id: int) -> Optional[PedidoDeliveryModel]:
        """
        Busca um pedido específico para impressão
        
        Args:
            pedido_id: ID do pedido
            
        Returns:
            Pedido se encontrado e pendente de impressão, None caso contrário
        """
        return (
            self.db.query(PedidoDeliveryModel)
            .filter(
                and_(
                    PedidoDeliveryModel.id == pedido_id,
                    PedidoDeliveryModel.status == PedidoStatusEnum.I.value
                )
            )
            .first()
        )
    
    def marcar_pedido_impresso(self, pedido_id: int) -> bool:
        """
        Marca um pedido como impresso (muda status de 'I' para 'R')
        
        Args:
            pedido_id: ID do pedido
            
        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            pedido = self.get_pedido_para_impressao(pedido_id)
            if not pedido:
                logger.warning(f"[PrinterRepository] Pedido {pedido_id} não encontrado ou não está pendente de impressão")
                return False
            
            pedido.status = PedidoStatusEnum.R.value
            self.db.commit()
            
            logger.info(f"[PrinterRepository] Pedido {pedido_id} marcado como impresso")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"[PrinterRepository] Erro ao marcar pedido {pedido_id} como impresso: {str(e)}")
            return False
    
    def count_pedidos_pendentes_impressao(self, empresa_id: int) -> int:
        """
        Conta quantos pedidos estão pendentes de impressão para uma empresa
        
        Args:
            empresa_id: ID da empresa
            
        Returns:
            Número de pedidos pendentes de impressão
        """
        return (
            self.db.query(PedidoDeliveryModel)
            .filter(
                and_(
                    PedidoDeliveryModel.empresa_id == empresa_id,
                    PedidoDeliveryModel.status == PedidoStatusEnum.I.value
                )
            )
            .count()
        )
    
    def get_pedidos_impressao_por_periodo(
        self, 
        empresa_id: int, 
        data_inicio: Optional[str] = None, 
        data_fim: Optional[str] = None,
        limite: Optional[int] = None
    ) -> List[PedidoDeliveryModel]:
        """
        Busca pedidos para impressão em um período específico
        
        Args:
            empresa_id: ID da empresa
            data_inicio: Data de início (YYYY-MM-DD)
            data_fim: Data de fim (YYYY-MM-DD)
            limite: Número máximo de pedidos
            
        Returns:
            Lista de pedidos do período
        """
        from datetime import datetime
        
        query = (
            self.db.query(PedidoDeliveryModel)
            .filter(PedidoDeliveryModel.empresa_id == empresa_id)
        )
        
        if data_inicio:
            try:
                data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d")
                query = query.filter(PedidoDeliveryModel.data_criacao >= data_inicio_dt)
            except ValueError:
                logger.warning(f"[PrinterRepository] Data início inválida: {data_inicio}")
        
        if data_fim:
            try:
                data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d")
                query = query.filter(PedidoDeliveryModel.data_criacao <= data_fim_dt)
            except ValueError:
                logger.warning(f"[PrinterRepository] Data fim inválida: {data_fim}")
        
        query = query.order_by(desc(PedidoDeliveryModel.data_criacao))
        
        if limite:
            query = query.limit(limite)
            
        return query.all()
    
    def converter_pedido_para_impressao(self, pedido: PedidoDeliveryModel) -> PedidoParaImpressao:
        """
        Converte um pedido do banco para formato de impressão
        
        Args:
            pedido: Pedido do banco de dados
            
        Returns:
            Pedido formatado para impressão
        """
        # Converte itens
        itens = []
        for item in pedido.itens:
            itens.append(ItemPedidoPrinter(
                descricao=item.produto_descricao_snapshot or f"Produto {item.produto_cod_barras}",
                quantidade=item.quantidade,
                preco=float(item.preco_unitario),
                observacao=item.observacao
            ))
        
        # Monta endereço
        endereco_str = None
        if pedido.endereco_snapshot:
            endereco = pedido.endereco_snapshot
            endereco_str = ", ".join(filter(None, [
                endereco.get("logradouro"),
                endereco.get("numero"),
                endereco.get("bairro"),
                endereco.get("cidade"),
                endereco.get("cep"),
                endereco.get("complemento")
            ]))
        elif pedido.cliente and pedido.cliente.enderecos:
            endereco = pedido.cliente.enderecos[0]
            endereco_str = ", ".join(filter(None, [
                endereco.logradouro,
                endereco.numero,
                endereco.bairro,
                endereco.cidade,
                endereco.cep,
                endereco.complemento
            ]))
        
        return PedidoParaImpressao(
            id=pedido.id,
            status=pedido.status,
            cliente_nome=pedido.cliente.nome if pedido.cliente else "Cliente não informado",
            cliente_telefone=pedido.cliente.telefone if pedido.cliente else None,
            valor_total=float(pedido.valor_total or 0),
            data_criacao=pedido.data_criacao,
            endereco_cliente=endereco_str,
            meio_pagamento_descricao=pedido.meio_pagamento.display() if pedido.meio_pagamento else None,
            observacao_geral=pedido.observacao_geral,
            itens=itens
        )
    
    def get_estatisticas_impressao(self, empresa_id: int) -> dict:
        """
        Retorna estatísticas de impressão para uma empresa
        
        Args:
            empresa_id: ID da empresa
            
        Returns:
            Dicionário com estatísticas
        """
        from sqlalchemy import func
        
        stats = {}
        
        # Total de pedidos pendentes de impressão
        stats['pendentes_impressao'] = self.count_pedidos_pendentes_impressao(empresa_id)
        
        # Total de pedidos impressos hoje
        from datetime import datetime, timedelta
        hoje = datetime.now().date()
        stats['impressos_hoje'] = (
            self.db.query(PedidoDeliveryModel)
            .filter(
                and_(
                    PedidoDeliveryModel.empresa_id == empresa_id,
                    PedidoDeliveryModel.status == PedidoStatusEnum.R.value,
                    func.date(PedidoDeliveryModel.data_atualizacao) == hoje
                )
            )
            .count()
        )
        
        # Total de pedidos do dia
        stats['total_hoje'] = (
            self.db.query(PedidoDeliveryModel)
            .filter(
                and_(
                    PedidoDeliveryModel.empresa_id == empresa_id,
                    func.date(PedidoDeliveryModel.data_criacao) == hoje
                )
            )
            .count()
        )
        
        return stats
