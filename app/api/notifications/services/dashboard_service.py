from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from ..repositories.event_repository import EventRepository
from ..repositories.notification_repository import NotificationRepository
from ..repositories.subscription_repository import SubscriptionRepository

logger = logging.getLogger(__name__)

class DashboardService:
    """Serviço para dashboard unificado com dados de todo o sistema"""
    
    def __init__(self, db: Session):
        self.db = db
        self.event_repo = EventRepository(db)
        self.notification_repo = NotificationRepository(db)
        self.subscription_repo = SubscriptionRepository(db)
    
    async def get_dashboard_completo(
        self,
        empresa_id: str,
        periodo_dias: int = 30
    ) -> Dict[str, Any]:
        """Dashboard completo com todos os dados da empresa"""
        try:
            data_fim = datetime.utcnow()
            data_inicio = data_fim - timedelta(days=periodo_dias)
            
            # Executa todas as consultas em paralelo
            dados = await self._buscar_dados_dashboard(empresa_id, data_inicio, data_fim)
            
            return {
                "empresa_id": empresa_id,
                "periodo": {
                    "dias": periodo_dias,
                    "inicio": data_inicio.isoformat(),
                    "fim": data_fim.isoformat()
                },
                "resumo": dados["resumo"],
                "atividade": dados["atividade"],
                "pedidos": dados["pedidos"],
                "usuarios": dados["usuarios"],
                "sistema": dados["sistema"],
                "notificacoes": dados["notificacoes"],
                "performance": dados["performance"],
                "alertas": dados["alertas"]
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dashboard completo da empresa {empresa_id}: {e}")
            raise
    
    async def _buscar_dados_dashboard(
        self,
        empresa_id: str,
        data_inicio: datetime,
        data_fim: datetime
    ) -> Dict[str, Any]:
        """Busca todos os dados do dashboard"""
        
        # Resumo geral
        resumo = await self._get_resumo_geral(empresa_id, data_inicio, data_fim)
        
        # Atividade recente
        atividade = await self._get_atividade_recente(empresa_id, data_inicio, data_fim)
        
        # Dados de pedidos
        pedidos = await self._get_dados_pedidos(empresa_id, data_inicio, data_fim)
        
        # Dados de usuários
        usuarios = await self._get_dados_usuarios(empresa_id, data_inicio, data_fim)
        
        # Dados do sistema
        sistema = await self._get_dados_sistema(empresa_id, data_inicio, data_fim)
        
        # Dados de notificações
        notificacoes = await self._get_dados_notificacoes(empresa_id, data_inicio, data_fim)
        
        # Performance
        performance = await self._get_dados_performance(empresa_id, data_inicio, data_fim)
        
        # Alertas
        alertas = await self._get_alertas(empresa_id, data_inicio, data_fim)
        
        return {
            "resumo": resumo,
            "atividade": atividade,
            "pedidos": pedidos,
            "usuarios": usuarios,
            "sistema": sistema,
            "notificacoes": notificacoes,
            "performance": performance,
            "alertas": alertas
        }
    
    async def _get_resumo_geral(
        self,
        empresa_id: str,
        data_inicio: datetime,
        data_fim: datetime
    ) -> Dict[str, Any]:
        """Resumo geral da empresa"""
        try:
            # Total de eventos
            total_eventos = self.event_repo.count_events({
                "empresa_id": empresa_id,
                "created_from": data_inicio,
                "created_to": data_fim
            })
            
            # Total de notificações
            total_notificacoes = self.notification_repo.count_notifications({
                "empresa_id": empresa_id,
                "created_from": data_inicio,
                "created_to": data_fim
            })
            
            # Eventos por tipo
            eventos_por_tipo = self._get_eventos_por_tipo(empresa_id, data_inicio, data_fim)
            
            # Crescimento (comparação com período anterior)
            periodo_anterior_inicio = data_inicio - (data_fim - data_inicio)
            crescimento = self._calcular_crescimento(empresa_id, periodo_anterior_inicio, data_inicio, data_fim)
            
            return {
                "total_eventos": total_eventos,
                "total_notificacoes": total_notificacoes,
                "eventos_por_tipo": eventos_por_tipo,
                "crescimento": crescimento,
                "periodo": {
                    "dias": (data_fim - data_inicio).days,
                    "inicio": data_inicio.isoformat(),
                    "fim": data_fim.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar resumo geral: {e}")
            return {}
    
    async def _get_atividade_recente(
        self,
        empresa_id: str,
        data_inicio: datetime,
        data_fim: datetime
    ) -> Dict[str, Any]:
        """Atividade recente da empresa"""
        try:
            # Últimos eventos
            ultimos_eventos = self.event_repo.filter_events(
                filters={"empresa_id": empresa_id, "created_from": data_inicio},
                limit=20,
                offset=0
            )
            
            # Eventos por hora (últimas 24h)
            eventos_por_hora = self._get_eventos_por_hora(empresa_id, data_fim - timedelta(hours=24), data_fim)
            
            # Usuários ativos
            usuarios_ativos = self._get_usuarios_ativos(empresa_id, data_inicio, data_fim)
            
            return {
                "ultimos_eventos": ultimos_eventos,
                "eventos_por_hora": eventos_por_hora,
                "usuarios_ativos": usuarios_ativos,
                "total_usuarios_ativos": len(usuarios_ativos)
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar atividade recente: {e}")
            return {}
    
    async def _get_dados_pedidos(
        self,
        empresa_id: str,
        data_inicio: datetime,
        data_fim: datetime
    ) -> Dict[str, Any]:
        """Dados específicos de pedidos"""
        try:
            # Conta pedidos por status
            pedidos_por_status = self._get_pedidos_por_status(empresa_id, data_inicio, data_fim)
            
            # Valor total de pedidos
            valor_total = self._get_valor_total_pedidos(empresa_id, data_inicio, data_fim)
            
            # Pedidos por dia
            pedidos_por_dia = self._get_pedidos_por_dia(empresa_id, data_inicio, data_fim)
            
            # Top produtos
            top_produtos = self._get_top_produtos(empresa_id, data_inicio, data_fim)
            
            return {
                "pedidos_por_status": pedidos_por_status,
                "valor_total": valor_total,
                "pedidos_por_dia": pedidos_por_dia,
                "top_produtos": top_produtos
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados de pedidos: {e}")
            return {}
    
    async def _get_dados_usuarios(
        self,
        empresa_id: str,
        data_inicio: datetime,
        data_fim: datetime
    ) -> Dict[str, Any]:
        """Dados específicos de usuários"""
        try:
            # Logins por dia
            logins_por_dia = self._get_logins_por_dia(empresa_id, data_inicio, data_fim)
            
            # Usuários mais ativos
            usuarios_mais_ativos = self._get_usuarios_mais_ativos(empresa_id, data_inicio, data_fim)
            
            # Sessões por duração
            sessoes_por_duracao = self._get_sessoes_por_duracao(empresa_id, data_inicio, data_fim)
            
            return {
                "logins_por_dia": logins_por_dia,
                "usuarios_mais_ativos": usuarios_mais_ativos,
                "sessoes_por_duracao": sessoes_por_duracao
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados de usuários: {e}")
            return {}
    
    async def _get_dados_sistema(
        self,
        empresa_id: str,
        data_inicio: datetime,
        data_fim: datetime
    ) -> Dict[str, Any]:
        """Dados do sistema"""
        try:
            # Logs por nível
            logs_por_nivel = self._get_logs_por_nivel(empresa_id, data_inicio, data_fim)
            
            # Erros por módulo
            erros_por_modulo = self._get_erros_por_modulo(empresa_id, data_inicio, data_fim)
            
            # Saúde do sistema
            saude_sistema = self._get_saude_sistema(empresa_id, data_inicio, data_fim)
            
            return {
                "logs_por_nivel": logs_por_nivel,
                "erros_por_modulo": erros_por_modulo,
                "saude_sistema": saude_sistema
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados do sistema: {e}")
            return {}
    
    async def _get_dados_notificacoes(
        self,
        empresa_id: str,
        data_inicio: datetime,
        data_fim: datetime
    ) -> Dict[str, Any]:
        """Dados de notificações"""
        try:
            # Notificações por canal
            notificacoes_por_canal = self._get_notificacoes_por_canal(empresa_id, data_inicio, data_fim)
            
            # Taxa de sucesso
            taxa_sucesso = self._get_taxa_sucesso_notificacoes(empresa_id, data_inicio, data_fim)
            
            # Notificações por tipo
            notificacoes_por_tipo = self._get_notificacoes_por_tipo(empresa_id, data_inicio, data_fim)
            
            return {
                "notificacoes_por_canal": notificacoes_por_canal,
                "taxa_sucesso": taxa_sucesso,
                "notificacoes_por_tipo": notificacoes_por_tipo
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados de notificações: {e}")
            return {}
    
    async def _get_dados_performance(
        self,
        empresa_id: str,
        data_inicio: datetime,
        data_fim: datetime
    ) -> Dict[str, Any]:
        """Dados de performance"""
        try:
            # Tempo médio de resposta
            tempo_resposta = self._get_tempo_resposta_medio(empresa_id, data_inicio, data_fim)
            
            # Throughput
            throughput = self._get_throughput(empresa_id, data_inicio, data_fim)
            
            # Uptime
            uptime = self._get_uptime(empresa_id, data_inicio, data_fim)
            
            return {
                "tempo_resposta_medio": tempo_resposta,
                "throughput": throughput,
                "uptime": uptime
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados de performance: {e}")
            return {}
    
    async def _get_alertas(
        self,
        empresa_id: str,
        data_inicio: datetime,
        data_fim: datetime
    ) -> List[Dict[str, Any]]:
        """Alertas do sistema"""
        try:
            alertas = []
            
            # Verifica erros críticos
            erros_criticos = self._get_erros_criticos(empresa_id, data_inicio, data_fim)
            if erros_criticos:
                alertas.append({
                    "tipo": "erro_critico",
                    "nivel": "critical",
                    "mensagem": f"{erros_criticos} erros críticos detectados",
                    "acao": "Verificar logs do sistema"
                })
            
            # Verifica notificações falhadas
            notificacoes_falhadas = self._get_notificacoes_falhadas(empresa_id, data_inicio, data_fim)
            if notificacoes_falhadas > 10:
                alertas.append({
                    "tipo": "notificacoes_falhadas",
                    "nivel": "warning",
                    "mensagem": f"{notificacoes_falhadas} notificações falharam",
                    "acao": "Verificar configuração dos canais"
                })
            
            # Verifica estoque baixo
            estoque_baixo = self._get_estoque_baixo(empresa_id, data_inicio, data_fim)
            if estoque_baixo:
                alertas.append({
                    "tipo": "estoque_baixo",
                    "nivel": "info",
                    "mensagem": f"{estoque_baixo} produtos com estoque baixo",
                    "acao": "Verificar estoque"
                })
            
            return alertas
            
        except Exception as e:
            logger.error(f"Erro ao buscar alertas: {e}")
            return []
    
    # Métodos auxiliares para consultas específicas
    def _get_eventos_por_tipo(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> Dict[str, int]:
        """Busca eventos por tipo"""
        try:
            query = text("""
                SELECT event_type, COUNT(*) as total
                FROM events 
                WHERE empresa_id = :empresa_id 
                AND created_at >= :data_inicio 
                AND created_at <= :data_fim
                GROUP BY event_type 
                ORDER BY total DESC
            """)
            
            result = self.db.execute(query, {
                "empresa_id": empresa_id,
                "data_inicio": data_inicio,
                "data_fim": data_fim
            }).fetchall()
            
            return {row[0]: row[1] for row in result}
        except Exception as e:
            logger.error(f"Erro ao buscar eventos por tipo: {e}")
            return {}
    
    def _calcular_crescimento(self, empresa_id: str, periodo_anterior_inicio: datetime, periodo_anterior_fim: datetime, periodo_atual_inicio: datetime, periodo_atual_fim: datetime) -> Dict[str, Any]:
        """Calcula crescimento entre períodos"""
        try:
            # Eventos período anterior
            eventos_anterior = self.event_repo.count_events({
                "empresa_id": empresa_id,
                "created_from": periodo_anterior_inicio,
                "created_to": periodo_anterior_fim
            })
            
            # Eventos período atual
            eventos_atual = self.event_repo.count_events({
                "empresa_id": empresa_id,
                "created_from": periodo_atual_inicio,
                "created_to": periodo_atual_fim
            })
            
            if eventos_anterior == 0:
                crescimento_percentual = 100 if eventos_atual > 0 else 0
            else:
                crescimento_percentual = ((eventos_atual - eventos_anterior) / eventos_anterior) * 100
            
            return {
                "eventos_anterior": eventos_anterior,
                "eventos_atual": eventos_atual,
                "crescimento_percentual": round(crescimento_percentual, 2),
                "tendencia": "crescimento" if crescimento_percentual > 0 else "queda" if crescimento_percentual < 0 else "estavel"
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular crescimento: {e}")
            return {}
    
    def _get_eventos_por_hora(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> List[Dict[str, Any]]:
        """Busca eventos por hora"""
        try:
            query = text("""
                SELECT 
                    DATE_TRUNC('hour', created_at) as hora,
                    COUNT(*) as total
                FROM events 
                WHERE empresa_id = :empresa_id 
                AND created_at >= :data_inicio 
                AND created_at <= :data_fim
                GROUP BY DATE_TRUNC('hour', created_at)
                ORDER BY hora
            """)
            
            result = self.db.execute(query, {
                "empresa_id": empresa_id,
                "data_inicio": data_inicio,
                "data_fim": data_fim
            }).fetchall()
            
            return [{"hora": row[0].isoformat(), "total": row[1]} for row in result]
        except Exception as e:
            logger.error(f"Erro ao buscar eventos por hora: {e}")
            return []
    
    def _get_usuarios_ativos(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> List[str]:
        """Busca usuários ativos"""
        try:
            query = text("""
                SELECT DISTINCT data->>'user_id' as user_id
                FROM events 
                WHERE empresa_id = :empresa_id 
                AND created_at >= :data_inicio 
                AND created_at <= :data_fim
                AND data->>'user_id' IS NOT NULL
            """)
            
            result = self.db.execute(query, {
                "empresa_id": empresa_id,
                "data_inicio": data_inicio,
                "data_fim": data_fim
            }).fetchall()
            
            return [row[0] for row in result if row[0]]
        except Exception as e:
            logger.error(f"Erro ao buscar usuários ativos: {e}")
            return []
    
    # Implementar outros métodos auxiliares conforme necessário...
    def _get_pedidos_por_status(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> Dict[str, int]:
        """Busca pedidos por status"""
        # Implementar consulta específica
        return {}
    
    def _get_valor_total_pedidos(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> float:
        """Busca valor total de pedidos"""
        # Implementar consulta específica
        return 0.0
    
    def _get_pedidos_por_dia(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> List[Dict[str, Any]]:
        """Busca pedidos por dia"""
        # Implementar consulta específica
        return []
    
    def _get_top_produtos(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> List[Dict[str, Any]]:
        """Busca top produtos"""
        # Implementar consulta específica
        return []
    
    def _get_logins_por_dia(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> List[Dict[str, Any]]:
        """Busca logins por dia"""
        # Implementar consulta específica
        return []
    
    def _get_usuarios_mais_ativos(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> List[Dict[str, Any]]:
        """Busca usuários mais ativos"""
        # Implementar consulta específica
        return []
    
    def _get_sessoes_por_duracao(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> List[Dict[str, Any]]:
        """Busca sessões por duração"""
        # Implementar consulta específica
        return []
    
    def _get_logs_por_nivel(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> Dict[str, int]:
        """Busca logs por nível"""
        # Implementar consulta específica
        return {}
    
    def _get_erros_por_modulo(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> Dict[str, int]:
        """Busca erros por módulo"""
        # Implementar consulta específica
        return {}
    
    def _get_saude_sistema(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> Dict[str, Any]:
        """Busca saúde do sistema"""
        # Implementar consulta específica
        return {}
    
    def _get_notificacoes_por_canal(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> Dict[str, int]:
        """Busca notificações por canal"""
        # Implementar consulta específica
        return {}
    
    def _get_taxa_sucesso_notificacoes(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> float:
        """Busca taxa de sucesso de notificações"""
        # Implementar consulta específica
        return 0.0
    
    def _get_notificacoes_por_tipo(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> Dict[str, int]:
        """Busca notificações por tipo"""
        # Implementar consulta específica
        return {}
    
    def _get_tempo_resposta_medio(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> float:
        """Busca tempo médio de resposta"""
        # Implementar consulta específica
        return 0.0
    
    def _get_throughput(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> float:
        """Busca throughput"""
        # Implementar consulta específica
        return 0.0
    
    def _get_uptime(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> float:
        """Busca uptime"""
        # Implementar consulta específica
        return 0.0
    
    def _get_erros_criticos(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> int:
        """Busca erros críticos"""
        # Implementar consulta específica
        return 0
    
    def _get_notificacoes_falhadas(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> int:
        """Busca notificações falhadas"""
        # Implementar consulta específica
        return 0
    
    def _get_estoque_baixo(self, empresa_id: str, data_inicio: datetime, data_fim: datetime) -> int:
        """Busca produtos com estoque baixo"""
        # Implementar consulta específica
        return 0
