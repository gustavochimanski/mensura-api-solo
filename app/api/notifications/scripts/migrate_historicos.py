"""
Script de migração para centralizar todos os históricos no sistema de notificações

Este script migra dados de tabelas antigas de histórico para o sistema unificado
de notificações, permitindo eliminar tabelas redundantes.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..services.historico_service import HistoricoService
from ..core.event_bus import EventType

logger = logging.getLogger(__name__)

class MigracaoHistoricos:
    """Classe para migrar dados de tabelas antigas para o sistema de notificações"""
    
    def __init__(self, db: Session):
        self.db = db
        self.historico_service = HistoricoService(db)
        self.migrados = {
            "pedidos": 0,
            "usuarios": 0,
            "sistema_logs": 0,
            "auditoria": 0,
            "erros": 0
        }
    
    async def migrar_todos_historicos(self) -> Dict[str, Any]:
        """Executa migração completa de todos os históricos"""
        logger.info("Iniciando migração completa de históricos...")
        
        try:
            # 1. Migrar histórico de pedidos
            await self.migrar_historico_pedidos()
            
            # 2. Migrar histórico de usuários
            await self.migrar_historico_usuarios()
            
            # 3. Migrar logs do sistema
            await self.migrar_logs_sistema()
            
            # 4. Migrar auditoria
            await self.migrar_auditoria()
            
            # 5. Verificar integridade
            await self.verificar_integridade()
            
            logger.info(f"Migração concluída: {self.migrados}")
            return {
                "sucesso": True,
                "migrados": self.migrados,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro na migração: {e}")
            return {
                "sucesso": False,
                "erro": str(e),
                "migrados": self.migrados,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def migrar_historico_pedidos(self):
        """Migra dados de pedido_status_historico e pedido_historico"""
        logger.info("Migrando histórico de pedidos...")
        
        try:
            # Verifica se tabelas existem
            if not self._tabela_existe("pedido_status_historico"):
                logger.warning("Tabela pedido_status_historico não encontrada")
                return
            
            # Busca dados da tabela antiga
            query = text("""
                SELECT 
                    psh.id,
                    psh.pedido_id,
                    psh.status_anterior,
                    psh.status_novo,
                    psh.usuario_id,
                    psh.motivo,
                    psh.created_at,
                    p.empresa_id
                FROM pedido_status_historico psh
                LEFT JOIN pedidos p ON p.id = psh.pedido_id
                ORDER BY psh.created_at
            """)
            
            resultados = self.db.execute(query).fetchall()
            
            for row in resultados:
                try:
                    await self.historico_service.registrar_pedido_status_change(
                        empresa_id=row.empresa_id or "unknown",
                        pedido_id=row.pedido_id,
                        status_anterior=row.status_anterior,
                        status_novo=row.status_novo,
                        usuario_id=row.usuario_id,
                        motivo=row.motivo,
                        event_metadata={
                            "migrado_de": "pedido_status_historico",
                            "id_original": row.id,
                            "data_original": row.created_at.isoformat()
                        }
                    )
                    self.migrados["pedidos"] += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao migrar pedido {row.pedido_id}: {e}")
                    self.migrados["erros"] += 1
            
            logger.info(f"Migrados {self.migrados['pedidos']} registros de pedidos")
            
        except Exception as e:
            logger.error(f"Erro ao migrar histórico de pedidos: {e}")
            raise
    
    async def migrar_historico_usuarios(self):
        """Migra dados de usuario_historico"""
        logger.info("Migrando histórico de usuários...")
        
        try:
            # Verifica se tabela existe
            if not self._tabela_existe("usuario_historico"):
                logger.warning("Tabela usuario_historico não encontrada")
                return
            
            # Busca dados da tabela antiga
            query = text("""
                SELECT 
                    uh.id,
                    uh.usuario_id,
                    uh.acao,
                    uh.descricao,
                    uh.ip_address,
                    uh.user_agent,
                    uh.created_at,
                    u.empresa_id
                FROM usuario_historico uh
                LEFT JOIN usuarios u ON u.id = uh.usuario_id
                ORDER BY uh.created_at
            """)
            
            resultados = self.db.execute(query).fetchall()
            
            for row in resultados:
                try:
                    # Mapeia ações para eventos
                    evento_map = {
                        "login": EventType.USUARIO_LOGIN,
                        "logout": EventType.USUARIO_LOGOUT,
                        "cadastro": EventType.USUARIO_CADASTRO,
                        "perfil_atualizado": EventType.USUARIO_PERFIL_ATUALIZADO,
                        "senha_alterada": EventType.USUARIO_SENHA_ALTERADA
                    }
                    
                    evento_tipo = evento_map.get(row.acao, EventType.USUARIO_LOGIN)
                    
                    await self.historico_service.event_publisher.publish_event(
                        empresa_id=row.empresa_id or "unknown",
                        event_type=evento_tipo,
                        data={
                            "user_id": row.usuario_id,
                            "acao": row.acao,
                            "descricao": row.descricao,
                            "ip_address": row.ip_address,
                            "user_agent": row.user_agent,
                            "timestamp": row.created_at.isoformat()
                        },
                        event_id=row.usuario_id,
                        event_metadata={
                            "migrado_de": "usuario_historico",
                            "id_original": row.id,
                            "data_original": row.created_at.isoformat()
                        }
                    )
                    self.migrados["usuarios"] += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao migrar usuário {row.usuario_id}: {e}")
                    self.migrados["erros"] += 1
            
            logger.info(f"Migrados {self.migrados['usuarios']} registros de usuários")
            
        except Exception as e:
            logger.error(f"Erro ao migrar histórico de usuários: {e}")
            raise
    
    async def migrar_logs_sistema(self):
        """Migra dados de sistema_logs"""
        logger.info("Migrando logs do sistema...")
        
        try:
            # Verifica se tabela existe
            if not self._tabela_existe("sistema_logs"):
                logger.warning("Tabela sistema_logs não encontrada")
                return
            
            # Busca dados da tabela antiga
            query = text("""
                SELECT 
                    sl.id,
                    sl.empresa_id,
                    sl.modulo,
                    sl.nivel,
                    sl.mensagem,
                    sl.erro,
                    sl.stack_trace,
                    sl.created_at
                FROM sistema_logs sl
                ORDER BY sl.created_at
            """)
            
            resultados = self.db.execute(query).fetchall()
            
            for row in resultados:
                try:
                    await self.historico_service.registrar_sistema_log(
                        empresa_id=row.empresa_id or "unknown",
                        modulo=row.modulo,
                        nivel=row.nivel,
                        mensagem=row.mensagem,
                        erro=row.erro,
                        stack_trace=row.stack_trace,
                        event_metadata={
                            "migrado_de": "sistema_logs",
                            "id_original": row.id,
                            "data_original": row.created_at.isoformat()
                        }
                    )
                    self.migrados["sistema_logs"] += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao migrar log {row.id}: {e}")
                    self.migrados["erros"] += 1
            
            logger.info(f"Migrados {self.migrados['sistema_logs']} logs do sistema")
            
        except Exception as e:
            logger.error(f"Erro ao migrar logs do sistema: {e}")
            raise
    
    async def migrar_auditoria(self):
        """Migra dados de auditoria"""
        logger.info("Migrando dados de auditoria...")
        
        try:
            # Verifica se tabela existe
            if not self._tabela_existe("auditoria"):
                logger.warning("Tabela auditoria não encontrada")
                return
            
            # Busca dados da tabela antiga
            query = text("""
                SELECT 
                    a.id,
                    a.empresa_id,
                    a.usuario_id,
                    a.acao,
                    a.recurso,
                    a.recurso_id,
                    a.dados_anteriores,
                    a.dados_novos,
                    a.ip_address,
                    a.created_at
                FROM auditoria a
                ORDER BY a.created_at
            """)
            
            resultados = self.db.execute(query).fetchall()
            
            for row in resultados:
                try:
                    await self.historico_service.registrar_auditoria(
                        empresa_id=row.empresa_id or "unknown",
                        usuario_id=row.usuario_id,
                        acao=row.acao,
                        recurso=row.recurso,
                        recurso_id=row.recurso_id,
                        dados_anteriores=row.dados_anteriores,
                        dados_novos=row.dados_novos,
                        ip_address=row.ip_address,
                        event_metadata={
                            "migrado_de": "auditoria",
                            "id_original": row.id,
                            "data_original": row.created_at.isoformat()
                        }
                    )
                    self.migrados["auditoria"] += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao migrar auditoria {row.id}: {e}")
                    self.migrados["erros"] += 1
            
            logger.info(f"Migrados {self.migrados['auditoria']} registros de auditoria")
            
        except Exception as e:
            logger.error(f"Erro ao migrar auditoria: {e}")
            raise
    
    async def verificar_integridade(self):
        """Verifica integridade dos dados migrados"""
        logger.info("Verificando integridade dos dados migrados...")
        
        try:
            # Conta eventos migrados
            eventos_migrados = self.db.execute(text("""
                SELECT COUNT(*) FROM events 
                WHERE event_metadata->>'migrado_de' IS NOT NULL
            """)).scalar()
            
            # Conta notificações relacionadas
            notificacoes_migradas = self.db.execute(text("""
                SELECT COUNT(*) FROM notifications 
                WHERE event_metadata->>'migrado_de' IS NOT NULL
            """)).scalar()
            
            logger.info(f"Verificação de integridade:")
            logger.info(f"- Eventos migrados: {eventos_migrados}")
            logger.info(f"- Notificações migradas: {notificacoes_migradas}")
            logger.info(f"- Total migrado: {sum(self.migrados.values())}")
            
        except Exception as e:
            logger.error(f"Erro na verificação de integridade: {e}")
            raise
    
    def _tabela_existe(self, nome_tabela: str) -> bool:
        """Verifica se uma tabela existe no banco"""
        try:
            query = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = :nome_tabela
                )
            """)
            resultado = self.db.execute(query, {"nome_tabela": nome_tabela}).scalar()
            return resultado
        except Exception:
            return False
    
    async def remover_tabelas_antigas(self, confirmar: bool = False):
        """Remove tabelas antigas após migração (CUIDADO!)"""
        if not confirmar:
            logger.warning("Confirmação necessária para remover tabelas antigas")
            return
        
        logger.info("Removendo tabelas antigas...")
        
        tabelas_para_remover = [
            "pedido_status_historico",
            "pedido_historico", 
            "usuario_historico",
            "sistema_logs",
            "auditoria"
        ]
        
        for tabela in tabelas_para_remover:
            if self._tabela_existe(tabela):
                try:
                    self.db.execute(text(f"DROP TABLE {tabela} CASCADE"))
                    logger.info(f"Tabela {tabela} removida")
                except Exception as e:
                    logger.error(f"Erro ao remover tabela {tabela}: {e}")
            else:
                logger.info(f"Tabela {tabela} não encontrada")

# Função principal para executar migração
async def executar_migracao(db: Session, remover_antigas: bool = False) -> Dict[str, Any]:
    """Executa migração completa"""
    migracao = MigracaoHistoricos(db)
    
    # Executa migração
    resultado = await migracao.migrar_todos_historicos()
    
    # Remove tabelas antigas se solicitado
    if remover_antigas and resultado["sucesso"]:
        await migracao.remover_tabelas_antigas(confirmar=True)
        resultado["tabelas_removidas"] = True
    
    return resultado

# Script para executar via linha de comando
if __name__ == "__main__":
    import sys
    from ....database.db_connection import get_db
    
    async def main():
        db = next(get_db())
        remover_antigas = "--remove" in sys.argv
        
        resultado = await executar_migracao(db, remover_antigas)
        
        print("=== RESULTADO DA MIGRAÇÃO ===")
        print(f"Sucesso: {resultado['sucesso']}")
        print(f"Migrados: {resultado['migrados']}")
        if resultado.get("erro"):
            print(f"Erro: {resultado['erro']}")
        if resultado.get("tabelas_removidas"):
            print("Tabelas antigas removidas")
    
    asyncio.run(main())
