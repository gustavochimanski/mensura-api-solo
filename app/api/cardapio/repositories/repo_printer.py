"""
Repository para operações relacionadas à Printer API
"""
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.api.cardapio.models.model_pedido_dv import PedidoDeliveryModel
from app.api.empresas.models.empresa_model import EmpresaModel
from app.api.cadastros.schemas.schema_shared_enums import PedidoStatusEnum
from app.api.cardapio.schemas.schema_printer import (
    ItemPedidoPrinter,
    PedidoParaImpressao,
    TipoPedidoPrinterEnum,
)
from app.api.mesas.models.model_pedido_mesa import PedidoMesaModel, StatusPedidoMesa
from app.api.mesas.repositories.repo_pedidos_mesa import PedidoMesaRepository
from app.api.balcao.models.model_pedido_balcao import PedidoBalcaoModel, StatusPedidoBalcao
from app.api.balcao.models.model_pedido_balcao_historico import TipoOperacaoPedidoBalcao
from app.api.balcao.repositories.repo_pedidos_balcao import PedidoBalcaoRepository
from app.utils.logger import logger


class PrinterRepository:
    """Repository para operações específicas de impressão"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_pedidos_pendentes_impressao(self, empresa_id: int, limite: Optional[int] = None) -> List[PedidoDeliveryModel]:
        """
        Busca pedidos pendentes de impressão (status 'I' e 'D') de uma empresa
        Exclui pedidos ENTREGUE e CANCELADO
        
        Args:
            empresa_id: ID da empresa
            limite: Número máximo de pedidos (opcional)
            
        Returns:
            Lista de pedidos pendentes de impressão
        """
        query = (
            self.db.query(PedidoDeliveryModel)
            .options(
                joinedload(PedidoDeliveryModel.empresa),
                joinedload(PedidoDeliveryModel.cliente),
                joinedload(PedidoDeliveryModel.itens),
                joinedload(PedidoDeliveryModel.meio_pagamento)
            )
            .filter(
                and_(
                    PedidoDeliveryModel.empresa_id == empresa_id,
                    PedidoDeliveryModel.status == PedidoStatusEnum.I.value,
                    PedidoDeliveryModel.status != PedidoStatusEnum.E.value,  # Exclui ENTREGUE
                    PedidoDeliveryModel.status != PedidoStatusEnum.C.value,   # Exclui CANCELADO
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
        from sqlalchemy import or_
        
        return (
            self.db.query(PedidoDeliveryModel)
            .filter(
                and_(
                    PedidoDeliveryModel.id == pedido_id,
                    or_(
                        PedidoDeliveryModel.status == PedidoStatusEnum.I.value,
                        PedidoDeliveryModel.status == PedidoStatusEnum.D.value
                    )
                )
            )
            .first()
        )
    
    def marcar_pedido_impresso(
        self,
        pedido_id: int,
        tipo_pedido: TipoPedidoPrinterEnum,
    ) -> bool:
        """
        Marca um pedido como impresso (muda status de 'I' ou 'D' para 'R')
        
        Args:
            pedido_id: ID do pedido
            
        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            if tipo_pedido == TipoPedidoPrinterEnum.DELIVERY:
                from app.api.cardapio.repositories.repo_pedidos import PedidoRepository

                pedido = self.get_pedido_para_impressao(pedido_id)
                if not pedido:
                    logger.warning(f"[PrinterRepository] Pedido delivery {pedido_id} não encontrado ou não está pendente de impressão")
                    return False

                pedido_repo = PedidoRepository(self.db)
                pedido_repo.atualizar_status_pedido(
                    pedido=pedido,
                    novo_status=PedidoStatusEnum.R.value,
                    motivo="Pedido impresso",
                )
                self.db.commit()
                logger.info(f"[PrinterRepository] Pedido delivery {pedido_id} marcado como impresso")
                return True

            if tipo_pedido == TipoPedidoPrinterEnum.MESA:
                mesa_repo = PedidoMesaRepository(self.db)
                pedido: Optional[PedidoMesaModel] = (
                    self.db.query(PedidoMesaModel).filter(PedidoMesaModel.id == pedido_id).first()
                )
                if not pedido:
                    logger.warning(f"[PrinterRepository] Pedido mesa {pedido_id} não encontrado")
                    return False

                status_atual = (
                    pedido.status
                    if isinstance(pedido.status, str)
                    else getattr(pedido.status, "value", str(pedido.status))
                )
                if status_atual not in {
                    StatusPedidoMesa.IMPRESSAO.value,
                    StatusPedidoMesa.PENDENTE.value,
                }:
                    logger.warning(
                        f"[PrinterRepository] Pedido mesa {pedido_id} com status {status_atual} não pode ser marcado como impresso"
                    )
                    return False

                mesa_repo.atualizar_status(pedido_id, StatusPedidoMesa.PREPARANDO.value)
                logger.info(f"[PrinterRepository] Pedido mesa {pedido_id} marcado como impresso → PREPARANDO")
                return True

            if tipo_pedido == TipoPedidoPrinterEnum.BALCAO:
                balcao_repo = PedidoBalcaoRepository(self.db)
                pedido: Optional[PedidoBalcaoModel] = (
                    self.db.query(PedidoBalcaoModel).filter(PedidoBalcaoModel.id == pedido_id).first()
                )
                if not pedido:
                    logger.warning(f"[PrinterRepository] Pedido balcão {pedido_id} não encontrado")
                    return False

                status_atual = (
                    pedido.status
                    if isinstance(pedido.status, str)
                    else getattr(pedido.status, "value", str(pedido.status))
                )
                if status_atual not in {
                    StatusPedidoBalcao.IMPRESSAO.value,
                    StatusPedidoBalcao.PENDENTE.value,
                }:
                    logger.warning(
                        f"[PrinterRepository] Pedido balcão {pedido_id} com status {status_atual} não pode ser marcado como impresso"
                    )
                    return False

                novo_status = StatusPedidoBalcao.PREPARANDO.value
                balcao_repo.atualizar_status(pedido_id, novo_status)
                balcao_repo.add_historico(
                    pedido_id=pedido_id,
                    tipo_operacao=TipoOperacaoPedidoBalcao.STATUS_ALTERADO,
                    status_anterior=status_atual,
                    status_novo=novo_status,
                    descricao="Pedido marcado como impresso",
                )
                balcao_repo.commit()
                logger.info(f"[PrinterRepository] Pedido balcão {pedido_id} marcado como impresso → PREPARANDO")
                return True

            logger.warning(f"[PrinterRepository] Tipo de pedido '{tipo_pedido}' não reconhecido para marcação de impressão")
            return False
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"[PrinterRepository] Erro ao marcar pedido {pedido_id} como impresso: {str(e)}")
            return False
    
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
            endereco=endereco_str,
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
        from datetime import datetime
        
        stats = {}
        hoje = datetime.now().date()
        
        # Total de pedidos pendentes de impressão
        from sqlalchemy import or_
        
        stats['pendentes_impressao'] = (
            self.db.query(PedidoDeliveryModel)
            .filter(
                and_(
                    PedidoDeliveryModel.empresa_id == empresa_id,
                    or_(
                        PedidoDeliveryModel.status == PedidoStatusEnum.I.value,
                        PedidoDeliveryModel.status == PedidoStatusEnum.D.value
                    )
                )
            )
            .count()
        )
        
        # Total de pedidos impressos hoje
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
