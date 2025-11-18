from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text

from ..repositories.event_repository import EventRepository
from ..repositories.notification_repository import NotificationRepository
from ..repositories.subscription_repository import SubscriptionRepository
from ..core.event_publisher import EventPublisher
from ..core.event_bus import EventType

logger = logging.getLogger(__name__)

class HistoricoService:
    """Serviço unificado para gerenciar todo o histórico do sistema"""
    
    def __init__(self, db: Session):
        self.db = db
        self.event_repo = EventRepository(db)
        self.notification_repo = NotificationRepository(db)
        self.subscription_repo = SubscriptionRepository(db)
        self.event_publisher = EventPublisher()
    
    # ========================================
    # MÉTODOS PARA REGISTRAR HISTÓRICO
    # ========================================
    
    async def registrar_pedido_status_change(
        self,
        empresa_id: str,
        pedido_id: str,
        status_anterior: str,
        status_novo: str,
        usuario_id: str,
        motivo: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Registra mudança de status de pedido"""
        try:
            event_id = await self.event_publisher.publish_event(
                empresa_id=empresa_id,
                event_type=EventType.PEDIDO_STATUS_CHANGED,
                data={
                    "pedido_id": pedido_id,
                    "status_anterior": status_anterior,
                    "status_novo": status_novo,
                    "usuario_id": usuario_id,
                    "motivo": motivo,
                    "timestamp": datetime.utcnow().isoformat()
                },
                event_id=pedido_id,
                event_metadata=event_metadata
            )
            
            logger.info(f"Histórico de mudança de status registrado: {pedido_id} - {status_anterior} → {status_novo}")
            return event_id
            
        except Exception as e:
            logger.error(f"Erro ao registrar mudança de status do pedido {pedido_id}: {e}")
            raise
    
    async def registrar_usuario_login(
        self,
        empresa_id: str,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Registra login de usuário"""
        try:
            event_id = await self.event_publisher.publish_event(
                empresa_id=empresa_id,
                event_type=EventType.USUARIO_LOGIN,
                data={
                    "user_id": user_id,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "timestamp": datetime.utcnow().isoformat()
                },
                event_id=user_id,
                event_metadata=event_metadata
            )
            
            logger.info(f"Histórico de login registrado: {user_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Erro ao registrar login do usuário {user_id}: {e}")
            raise
    
    async def registrar_usuario_logout(
        self,
        empresa_id: str,
        user_id: str,
        session_duration: Optional[int] = None,
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Registra logout de usuário"""
        try:
            event_id = await self.event_publisher.publish_event(
                empresa_id=empresa_id,
                event_type=EventType.USUARIO_LOGOUT,
                data={
                    "user_id": user_id,
                    "session_duration": session_duration,
                    "timestamp": datetime.utcnow().isoformat()
                },
                event_id=user_id,
                event_metadata=event_metadata
            )
            
            logger.info(f"Histórico de logout registrado: {user_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Erro ao registrar logout do usuário {user_id}: {e}")
            raise
    
    async def registrar_sistema_log(
        self,
        empresa_id: str,
        modulo: str,
        nivel: str,
        mensagem: str,
        erro: Optional[str] = None,
        stack_trace: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Registra log do sistema"""
        try:
            event_type_map = {
                "error": EventType.SISTEMA_ERRO,
                "warning": EventType.SISTEMA_WARNING,
                "info": EventType.SISTEMA_INFO,
                "debug": EventType.SISTEMA_DEBUG
            }
            
            event_type = event_type_map.get(nivel, EventType.SISTEMA_INFO)
            
            event_id = await self.event_publisher.publish_event(
                empresa_id=empresa_id,
                event_type=event_type,
                data={
                    "modulo": modulo,
                    "nivel": nivel,
                    "mensagem": mensagem,
                    "erro": erro,
                    "stack_trace": stack_trace,
                    "timestamp": datetime.utcnow().isoformat()
                },
                event_metadata=event_metadata
            )
            
            logger.info(f"Log do sistema registrado: {modulo} - {nivel}")
            return event_id
            
        except Exception as e:
            logger.error(f"Erro ao registrar log do sistema: {e}")
            raise
    
    async def registrar_auditoria(
        self,
        empresa_id: str,
        usuario_id: str,
        acao: str,
        recurso: str,
        recurso_id: str,
        dados_anteriores: Optional[Dict[str, Any]] = None,
        dados_novos: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Registra evento de auditoria"""
        try:
            event_id = await self.event_publisher.publish_event(
                empresa_id=empresa_id,
                event_type=EventType.AUDITORIA_ALTERACAO,
                data={
                    "usuario_id": usuario_id,
                    "acao": acao,
                    "recurso": recurso,
                    "recurso_id": recurso_id,
                    "dados_anteriores": dados_anteriores,
                    "dados_novos": dados_novos,
                    "ip_address": ip_address,
                    "timestamp": datetime.utcnow().isoformat()
                },
                event_id=recurso_id,
                event_metadata=event_metadata
            )
            
            logger.info(f"Auditoria registrada: {acao} em {recurso} {recurso_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Erro ao registrar auditoria: {e}")
            raise
    
    # ========================================
    # MÉTODOS PARA CONSULTAR HISTÓRICO
    # ========================================
    
    async def get_historico_empresa(
        self,
        empresa_id: str,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        tipos_evento: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Busca histórico completo da empresa"""
        try:
            # Busca eventos
            eventos = self.event_repo.filter_events(
                filters={
                    "empresa_id": empresa_id,
                    "event_type": tipos_evento[0] if tipos_evento and len(tipos_evento) == 1 else None,
                    "created_from": data_inicio,
                    "created_to": data_fim
                },
                limit=limit,
                offset=offset
            )
            
            # Busca notificações relacionadas
            notificacoes = self.notification_repo.filter_notifications(
                filters={
                    "empresa_id": empresa_id,
                    "event_type": tipos_evento[0] if tipos_evento and len(tipos_evento) == 1 else None,
                    "created_from": data_inicio,
                    "created_to": data_fim
                },
                limit=limit,
                offset=offset
            )
            
            # Estatísticas
            stats = await self.get_estatisticas_empresa(empresa_id, data_inicio, data_fim)
            
            return {
                "eventos": eventos,
                "notificacoes": notificacoes,
                "estatisticas": stats,
                "total_eventos": len(eventos),
                "total_notificacoes": len(notificacoes)
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar histórico da empresa {empresa_id}: {e}")
            raise
    
    async def get_historico_pedido(
        self,
        empresa_id: str,
        pedido_id: str
    ) -> Dict[str, Any]:
        """Busca histórico completo de um pedido"""
        try:
            # Busca todos os eventos relacionados ao pedido
            eventos = self.event_repo.get_events_by_empresa_and_type(
                empresa_id=empresa_id,
                event_type="pedido_%",  # Busca todos os eventos de pedido
                limit=1000
            )
            
            # Filtra eventos específicos do pedido
            eventos_pedido = [
                evento for evento in eventos 
                if evento.event_id == pedido_id or 
                   (evento.data and evento.data.get("pedido_id") == pedido_id)
            ]
            
            # Busca notificações relacionadas
            notificacoes = self.notification_repo.filter_notifications(
                filters={
                    "empresa_id": empresa_id,
                    "event_type": "pedido_%"
                },
                limit=1000,
                offset=0
            )
            
            notificacoes_pedido = [
                notif for notif in notificacoes
                if notif.event_data and notif.event_data.get("pedido_id") == pedido_id
            ]
            
            return {
                "pedido_id": pedido_id,
                "eventos": eventos_pedido,
                "notificacoes": notificacoes_pedido,
                "total_eventos": len(eventos_pedido),
                "total_notificacoes": len(notificacoes_pedido)
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar histórico do pedido {pedido_id}: {e}")
            raise
    
    async def get_historico_usuario(
        self,
        empresa_id: str,
        user_id: str,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Busca histórico completo de um usuário"""
        try:
            # Busca eventos do usuário
            eventos = self.event_repo.filter_events(
                filters={
                    "empresa_id": empresa_id,
                    "created_from": data_inicio,
                    "created_to": data_fim
                },
                limit=1000,
                offset=0
            )
            
            # Filtra eventos específicos do usuário
            eventos_usuario = [
                evento for evento in eventos
                if evento.event_id == user_id or
                   (evento.data and evento.data.get("user_id") == user_id)
            ]
            
            # Busca notificações do usuário
            notificacoes = self.notification_repo.filter_notifications(
                filters={
                    "empresa_id": empresa_id,
                    "user_id": user_id,
                    "created_from": data_inicio,
                    "created_to": data_fim
                },
                limit=1000,
                offset=0
            )
            
            return {
                "user_id": user_id,
                "eventos": eventos_usuario,
                "notificacoes": notificacoes,
                "total_eventos": len(eventos_usuario),
                "total_notificacoes": len(notificacoes)
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar histórico do usuário {user_id}: {e}")
            raise
    
    async def get_estatisticas_empresa(
        self,
        empresa_id: str,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Busca estatísticas da empresa"""
        try:
            # Estatísticas de eventos
            eventos_stats = self.event_repo.get_event_statistics(empresa_id, 30)
            
            # Estatísticas de notificações
            notificacoes_stats = {
                "total": self.notification_repo.count_notifications({"empresa_id": empresa_id}),
                "enviadas": self.notification_repo.count_notifications({
                    "empresa_id": empresa_id,
                    "status": "sent"
                }),
                "falharam": self.notification_repo.count_notifications({
                    "empresa_id": empresa_id,
                    "status": "failed"
                }),
                "pendentes": self.notification_repo.count_notifications({
                    "empresa_id": empresa_id,
                    "status": "pending"
                })
            }
            
            # Estatísticas de assinaturas
            assinaturas_stats = self.subscription_repo.get_subscription_statistics(empresa_id)
            
            return {
                "eventos": eventos_stats,
                "notificacoes": notificacoes_stats,
                "assinaturas": assinaturas_stats,
                "periodo": {
                    "inicio": data_inicio.isoformat() if data_inicio else None,
                    "fim": data_fim.isoformat() if data_fim else None
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas da empresa {empresa_id}: {e}")
            raise
    
    async def get_dashboard_empresa(
        self,
        empresa_id: str,
        periodo_dias: int = 30
    ) -> Dict[str, Any]:
        """Busca dados para dashboard da empresa"""
        try:
            data_fim = datetime.utcnow()
            data_inicio = data_fim - timedelta(days=periodo_dias)
            
            # Dados básicos
            stats = await self.get_estatisticas_empresa(empresa_id, data_inicio, data_fim)
            
            # Atividade recente
            atividade_recente = self.event_repo.filter_events(
                filters={"empresa_id": empresa_id, "created_from": data_inicio},
                limit=50,
                offset=0
            )
            
            # Top eventos
            top_eventos = self._get_top_eventos(empresa_id, data_inicio, data_fim)
            
            # Saúde do sistema
            saude_sistema = self._get_saude_sistema(empresa_id, data_inicio, data_fim)
            
            return {
                "empresa_id": empresa_id,
                "periodo": {
                    "dias": periodo_dias,
                    "inicio": data_inicio.isoformat(),
                    "fim": data_fim.isoformat()
                },
                "estatisticas": stats,
                "atividade_recente": atividade_recente,
                "top_eventos": top_eventos,
                "saude_sistema": saude_sistema
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dashboard da empresa {empresa_id}: {e}")
            raise
    
    def _get_top_eventos(
        self,
        empresa_id: str,
        data_inicio: datetime,
        data_fim: datetime
    ) -> List[Dict[str, Any]]:
        """Busca eventos mais frequentes"""
        try:
            # Query SQL para contar eventos por tipo
            query = text("""
                SELECT event_type, COUNT(*) as total
                FROM events 
                WHERE empresa_id = :empresa_id 
                AND created_at >= :data_inicio 
                AND created_at <= :data_fim
                GROUP BY event_type 
                ORDER BY total DESC 
                LIMIT 10
            """)
            
            result = self.db.execute(query, {
                "empresa_id": empresa_id,
                "data_inicio": data_inicio,
                "data_fim": data_fim
            }).fetchall()
            
            return [{"event_type": row[0], "total": row[1]} for row in result]
            
        except Exception as e:
            logger.error(f"Erro ao buscar top eventos: {e}")
            return []
    
    def _get_saude_sistema(
        self,
        empresa_id: str,
        data_inicio: datetime,
        data_fim: datetime
    ) -> Dict[str, Any]:
        """Avalia saúde do sistema"""
        try:
            # Conta erros do sistema
            erros = self.event_repo.count_events({
                "empresa_id": empresa_id,
                "event_type": "sistema_erro",
                "created_from": data_inicio,
                "created_to": data_fim
            })
            
            # Conta warnings
            warnings = self.event_repo.count_events({
                "empresa_id": empresa_id,
                "event_type": "sistema_warning",
                "created_from": data_inicio,
                "created_to": data_fim
            })
            
            # Conta notificações falhadas
            notificacoes_falhadas = self.notification_repo.count_notifications({
                "empresa_id": empresa_id,
                "status": "failed",
                "created_from": data_inicio,
                "created_to": data_fim
            })
            
            # Calcula score de saúde (0-100)
            total_eventos = self.event_repo.count_events({
                "empresa_id": empresa_id,
                "created_from": data_inicio,
                "created_to": data_fim
            })
            
            if total_eventos == 0:
                score_saude = 100
            else:
                problemas = erros + warnings + notificacoes_falhadas
                score_saude = max(0, 100 - (problemas / total_eventos * 100))
            
            return {
                "score_saude": round(score_saude, 2),
                "erros": erros,
                "warnings": warnings,
                "notificacoes_falhadas": notificacoes_falhadas,
                "status": "excelente" if score_saude >= 90 else "bom" if score_saude >= 70 else "atencao" if score_saude >= 50 else "critico"
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular saúde do sistema: {e}")
            return {"score_saude": 0, "status": "erro"}
