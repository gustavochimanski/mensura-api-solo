"""
Repository para operações relacionadas à Printer API
"""
import asyncio
import threading
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.api.pedidos.models.model_pedido_unificado import (
    PedidoUnificadoModel,
    TipoEntrega,
    StatusPedido,
)
from app.api.empresas.models.empresa_model import EmpresaModel
from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum
from app.api.cardapio.schemas.schema_printer import (
    ItemPedidoPrinter,
    PedidoParaImpressao,
    TipoPedidoPrinterEnum,
)
from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.utils.logger import logger


def _run_async_in_thread(coro, db_session=None):
    """
    Executa uma corrotina em uma thread separada com seu próprio event loop.
    Útil para executar código assíncrono a partir de código síncrono.
    
    Args:
        coro: Corrotina a ser executada
        db_session: Sessão do banco de dados que será fechada após a execução (opcional)
    """
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro)
        except Exception as e:
            logger.error(f"Erro ao executar corrotina em thread: {e}", exc_info=True)
        finally:
            loop.close()
            # Fecha a sessão do banco se foi fornecida
            if db_session:
                try:
                    db_session.close()
                except Exception as e:
                    logger.error(f"Erro ao fechar sessão do banco: {e}")
    
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


class PrinterRepository:
    """Repository para operações específicas de impressão"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_pedidos_pendentes_impressao(self, empresa_id: int, limite: Optional[int] = None) -> List[PedidoUnificadoModel]:
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
            self.db.query(PedidoUnificadoModel)
            .options(
                joinedload(PedidoUnificadoModel.empresa),
                joinedload(PedidoUnificadoModel.cliente),
                joinedload(PedidoUnificadoModel.itens),
                joinedload(PedidoUnificadoModel.meio_pagamento)
            )
            .filter(
                and_(
                    PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value,
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.status == PedidoStatusEnum.I.value,
                    PedidoUnificadoModel.status != PedidoStatusEnum.E.value,  # Exclui ENTREGUE
                    PedidoUnificadoModel.status != PedidoStatusEnum.C.value,   # Exclui CANCELADO
                )
            )
            .order_by(PedidoUnificadoModel.created_at.asc())
        )
        
        if limite:
            query = query.limit(limite)
            
        return query.all()
    
    def get_pedido_para_impressao(self, pedido_id: int) -> Optional[PedidoUnificadoModel]:
        """
        Busca um pedido específico para impressão
        
        Args:
            pedido_id: ID do pedido
            
        Returns:
            Pedido se encontrado e pendente de impressão, None caso contrário
        """
        from sqlalchemy import or_
        
        return (
            self.db.query(PedidoUnificadoModel)
            .filter(
                and_(
                    PedidoUnificadoModel.id == pedido_id,
                    PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value,
                    or_(
                        PedidoUnificadoModel.status == PedidoStatusEnum.I.value,
                        PedidoUnificadoModel.status == PedidoStatusEnum.D.value
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
            pedido_repo = PedidoRepository(self.db)
            
            if tipo_pedido == TipoPedidoPrinterEnum.DELIVERY:
                pedido = self.get_pedido_para_impressao(pedido_id)
                if not pedido:
                    logger.warning(f"[PrinterRepository] Pedido delivery {pedido_id} não encontrado ou não está pendente de impressão")
                    return False

                pedido_repo.atualizar_status_pedido(
                    pedido=pedido,
                    novo_status=PedidoStatusEnum.R.value,
                    motivo="Pedido impresso",
                )
                self.db.commit()
                logger.info(f"[PrinterRepository] Pedido delivery {pedido_id} marcado como impresso")
                
                # Envia resumo do pedido para o cliente via WhatsApp
                try:
                    from app.api.chatbot.core.notifications import enviar_resumo_pedido_whatsapp
                    
                    # Recarrega pedido com cliente para obter telefone
                    pedido_com_cliente = (
                        self.db.query(PedidoUnificadoModel)
                        .options(
                            joinedload(PedidoUnificadoModel.cliente),
                            joinedload(PedidoUnificadoModel.empresa),
                        )
                        .filter(PedidoUnificadoModel.id == pedido_id)
                        .first()
                    )
                    
                    if pedido_com_cliente and pedido_com_cliente.cliente and pedido_com_cliente.cliente.telefone:
                        empresa_id_str = str(pedido_com_cliente.empresa_id) if pedido_com_cliente.empresa_id else None
                        # Cria uma nova sessão do banco para a thread assíncrona
                        from app.database.db_connection import SessionLocal
                        db_session = SessionLocal()
                        
                        _run_async_in_thread(
                            enviar_resumo_pedido_whatsapp(
                                db=db_session,
                                pedido_id=pedido_id,
                                phone_number=pedido_com_cliente.cliente.telefone,
                                empresa_id=empresa_id_str
                            ),
                            db_session=db_session
                        )
                        logger.info(f"[PrinterRepository] Agendado envio de resumo do pedido {pedido_id} para o cliente")
                    else:
                        logger.warning(f"[PrinterRepository] Pedido {pedido_id} não tem cliente ou telefone, não será enviado resumo")
                except Exception as e:
                    logger.error(f"Erro ao agendar envio de resumo para pedido impresso {pedido_id}: {e}", exc_info=True)
                
                # Notifica kanban após marcar como impresso
                try:
                    from app.api.pedidos.utils.pedido_notification_helper import notificar_pedido_impresso
                    # Recarrega pedido com todos os relacionamentos para a notificação (incluindo mesa)
                    pedido_completo = (
                        self.db.query(PedidoUnificadoModel)
                        .options(
                            joinedload(PedidoUnificadoModel.cliente),
                            joinedload(PedidoUnificadoModel.itens),
                            joinedload(PedidoUnificadoModel.mesa),
                            joinedload(PedidoUnificadoModel.empresa),
                        )
                        .filter(PedidoUnificadoModel.id == pedido_id)
                        .first()
                    )
                    if pedido_completo:
                        _run_async_in_thread(notificar_pedido_impresso(pedido_completo))
                except Exception as e:
                    logger.error(f"Erro ao agendar notificação kanban para pedido impresso {pedido_id}: {e}")
                
                return True

            if tipo_pedido == TipoPedidoPrinterEnum.MESA:
                pedido = pedido_repo.get_pedido(pedido_id, TipoEntrega.MESA)
                if not pedido:
                    logger.warning(f"[PrinterRepository] Pedido mesa {pedido_id} não encontrado")
                    return False

                status_atual = (
                    pedido.status
                    if isinstance(pedido.status, str)
                    else getattr(pedido.status, "value", str(pedido.status))
                )
                if status_atual not in {
                    StatusPedido.IMPRESSAO.value,
                    StatusPedido.PENDENTE.value,
                }:
                    logger.warning(
                        f"[PrinterRepository] Pedido mesa {pedido_id} com status {status_atual} não pode ser marcado como impresso"
                    )
                    return False

                pedido_repo.atualizar_status(pedido_id, StatusPedido.PREPARANDO.value)
                self.db.commit()
                logger.info(f"[PrinterRepository] Pedido mesa {pedido_id} marcado como impresso → PREPARANDO")
                
                # Envia resumo do pedido para o cliente via WhatsApp
                try:
                    from app.api.chatbot.core.notifications import enviar_resumo_pedido_whatsapp
                    
                    # Recarrega pedido com cliente para obter telefone
                    pedido_com_cliente = (
                        self.db.query(PedidoUnificadoModel)
                        .options(
                            joinedload(PedidoUnificadoModel.cliente),
                            joinedload(PedidoUnificadoModel.empresa),
                        )
                        .filter(PedidoUnificadoModel.id == pedido_id)
                        .first()
                    )
                    
                    if pedido_com_cliente and pedido_com_cliente.cliente and pedido_com_cliente.cliente.telefone:
                        empresa_id_str = str(pedido_com_cliente.empresa_id) if pedido_com_cliente.empresa_id else None
                        # Cria uma nova sessão do banco para a thread assíncrona
                        from app.database.db_connection import SessionLocal
                        db_session = SessionLocal()
                        
                        _run_async_in_thread(
                            enviar_resumo_pedido_whatsapp(
                                db=db_session,
                                pedido_id=pedido_id,
                                phone_number=pedido_com_cliente.cliente.telefone,
                                empresa_id=empresa_id_str
                            ),
                            db_session=db_session
                        )
                        logger.info(f"[PrinterRepository] Agendado envio de resumo do pedido {pedido_id} para o cliente")
                    else:
                        logger.warning(f"[PrinterRepository] Pedido {pedido_id} não tem cliente ou telefone, não será enviado resumo")
                except Exception as e:
                    logger.error(f"Erro ao agendar envio de resumo para pedido impresso {pedido_id}: {e}", exc_info=True)
                
                # Notifica kanban após marcar como impresso
                try:
                    from app.api.pedidos.utils.pedido_notification_helper import notificar_pedido_impresso
                    # Recarrega pedido com todos os relacionamentos para a notificação (incluindo mesa)
                    pedido_completo = (
                        self.db.query(PedidoUnificadoModel)
                        .options(
                            joinedload(PedidoUnificadoModel.cliente),
                            joinedload(PedidoUnificadoModel.itens),
                            joinedload(PedidoUnificadoModel.mesa),
                            joinedload(PedidoUnificadoModel.empresa),
                        )
                        .filter(PedidoUnificadoModel.id == pedido_id)
                        .first()
                    )
                    if pedido_completo:
                        _run_async_in_thread(notificar_pedido_impresso(pedido_completo))
                except Exception as e:
                    logger.error(f"Erro ao agendar notificação kanban para pedido impresso {pedido_id}: {e}")
                
                return True

            if tipo_pedido == TipoPedidoPrinterEnum.BALCAO:
                pedido_repo = PedidoRepository(self.db)
                pedido = pedido_repo.get_pedido(pedido_id, TipoEntrega.BALCAO)
                if not pedido:
                    logger.warning(f"[PrinterRepository] Pedido balcão {pedido_id} não encontrado")
                    return False

                status_atual = (
                    pedido.status
                    if isinstance(pedido.status, str)
                    else getattr(pedido.status, "value", str(pedido.status))
                )
                if status_atual not in {
                    StatusPedido.IMPRESSAO.value,
                    StatusPedido.PENDENTE.value,
                }:
                    logger.warning(
                        f"[PrinterRepository] Pedido balcão {pedido_id} com status {status_atual} não pode ser marcado como impresso"
                    )
                    return False

                novo_status = StatusPedido.PREPARANDO.value
                pedido_repo.atualizar_status(pedido_id, novo_status)
                from app.api.pedidos.models.model_pedido_historico_unificado import TipoOperacaoPedido
                pedido_repo.add_historico(
                    pedido_id=pedido_id,
                    tipo_operacao=TipoOperacaoPedido.STATUS_ALTERADO,
                    status_anterior=status_atual,
                    status_novo=novo_status,
                    descricao="Pedido marcado como impresso",
                )
                pedido_repo.commit()
                logger.info(f"[PrinterRepository] Pedido balcão {pedido_id} marcado como impresso → PREPARANDO")
                
                # Envia resumo do pedido para o cliente via WhatsApp
                try:
                    from app.api.chatbot.core.notifications import enviar_resumo_pedido_whatsapp
                    
                    # Recarrega pedido com cliente para obter telefone
                    pedido_com_cliente = (
                        self.db.query(PedidoUnificadoModel)
                        .options(
                            joinedload(PedidoUnificadoModel.cliente),
                            joinedload(PedidoUnificadoModel.empresa),
                        )
                        .filter(PedidoUnificadoModel.id == pedido_id)
                        .first()
                    )
                    
                    if pedido_com_cliente and pedido_com_cliente.cliente and pedido_com_cliente.cliente.telefone:
                        empresa_id_str = str(pedido_com_cliente.empresa_id) if pedido_com_cliente.empresa_id else None
                        # Cria uma nova sessão do banco para a thread assíncrona
                        from app.database.db_connection import SessionLocal
                        db_session = SessionLocal()
                        
                        _run_async_in_thread(
                            enviar_resumo_pedido_whatsapp(
                                db=db_session,
                                pedido_id=pedido_id,
                                phone_number=pedido_com_cliente.cliente.telefone,
                                empresa_id=empresa_id_str
                            ),
                            db_session=db_session
                        )
                        logger.info(f"[PrinterRepository] Agendado envio de resumo do pedido {pedido_id} para o cliente")
                    else:
                        logger.warning(f"[PrinterRepository] Pedido {pedido_id} não tem cliente ou telefone, não será enviado resumo")
                except Exception as e:
                    logger.error(f"Erro ao agendar envio de resumo para pedido impresso {pedido_id}: {e}", exc_info=True)
                
                # Notifica kanban após marcar como impresso
                try:
                    from app.api.pedidos.utils.pedido_notification_helper import notificar_pedido_impresso
                    # Recarrega pedido com todos os relacionamentos para a notificação (incluindo mesa)
                    pedido_completo = (
                        self.db.query(PedidoUnificadoModel)
                        .options(
                            joinedload(PedidoUnificadoModel.cliente),
                            joinedload(PedidoUnificadoModel.itens),
                            joinedload(PedidoUnificadoModel.mesa),
                            joinedload(PedidoUnificadoModel.empresa),
                        )
                        .filter(PedidoUnificadoModel.id == pedido_id)
                        .first()
                    )
                    if pedido_completo:
                        _run_async_in_thread(notificar_pedido_impresso(pedido_completo))
                except Exception as e:
                    logger.error(f"Erro ao agendar notificação kanban para pedido impresso {pedido_id}: {e}")
                
                return True

            logger.warning(f"[PrinterRepository] Tipo de pedido '{tipo_pedido}' não reconhecido para marcação de impressão")
            return False
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"[PrinterRepository] Erro ao marcar pedido {pedido_id} como impresso: {str(e)}")
            return False
    
    def converter_pedido_para_impressao(self, pedido: PedidoUnificadoModel) -> PedidoParaImpressao:
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
            data_criacao=pedido.created_at,
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
            self.db.query(PedidoUnificadoModel)
            .filter(
                and_(
                    PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value,
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    or_(
                        PedidoUnificadoModel.status == PedidoStatusEnum.I.value,
                        PedidoUnificadoModel.status == PedidoStatusEnum.D.value
                    )
                )
            )
            .count()
        )
        
        # Total de pedidos impressos hoje
        stats['impressos_hoje'] = (
            self.db.query(PedidoUnificadoModel)
            .filter(
                and_(
                    PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value,
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.status == PedidoStatusEnum.R.value,
                    func.date(PedidoUnificadoModel.updated_at) == hoje
                )
            )
            .count()
        )
        
        # Total de pedidos do dia
        stats['total_hoje'] = (
            self.db.query(PedidoUnificadoModel)
            .filter(
                and_(
                    PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value,
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    func.date(PedidoUnificadoModel.created_at) == hoje
                )
            )
            .count()
        )
        
        return stats
