from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ....database.db_connection import get_db
from ....core.admin_dependencies import get_current_user
from ..services.historico_service import HistoricoService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/historico", tags=["historico"])

def get_historico_service(db: Session = Depends(get_db)) -> HistoricoService:
    """Dependency para obter o serviço de histórico"""
    return HistoricoService(db)

# ========================================
# ENDPOINTS PARA REGISTRAR HISTÓRICO
# ========================================

@router.post("/pedido/status-change")
async def registrar_mudanca_status_pedido(
    empresa_id: str,
    pedido_id: str,
    status_anterior: str,
    status_novo: str,
    usuario_id: str,
    motivo: Optional[str] = None,
    service: HistoricoService = Depends(get_historico_service),
    current_user = Depends(get_current_user)
):
    """Registra mudança de status de pedido no histórico"""
    try:
        event_id = await service.registrar_pedido_status_change(
            empresa_id=empresa_id,
            pedido_id=pedido_id,
            status_anterior=status_anterior,
            status_novo=status_novo,
            usuario_id=usuario_id,
            motivo=motivo
        )
        
        return {
            "success": True,
            "message": "Mudança de status registrada no histórico",
            "event_id": event_id,
            "pedido_id": pedido_id
        }
        
    except Exception as e:
        logger.error(f"Erro ao registrar mudança de status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/usuario/login")
async def registrar_login_usuario(
    empresa_id: str,
    user_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    service: HistoricoService = Depends(get_historico_service),
    current_user = Depends(get_current_user)
):
    """Registra login de usuário no histórico"""
    try:
        event_id = await service.registrar_usuario_login(
            empresa_id=empresa_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return {
            "success": True,
            "message": "Login registrado no histórico",
            "event_id": event_id,
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Erro ao registrar login: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/usuario/logout")
async def registrar_logout_usuario(
    empresa_id: str,
    user_id: str,
    session_duration: Optional[int] = None,
    service: HistoricoService = Depends(get_historico_service),
    current_user = Depends(get_current_user)
):
    """Registra logout de usuário no histórico"""
    try:
        event_id = await service.registrar_usuario_logout(
            empresa_id=empresa_id,
            user_id=user_id,
            session_duration=session_duration
        )
        
        return {
            "success": True,
            "message": "Logout registrado no histórico",
            "event_id": event_id,
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Erro ao registrar logout: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sistema/log")
async def registrar_log_sistema(
    empresa_id: str,
    modulo: str,
    nivel: str,
    mensagem: str,
    erro: Optional[str] = None,
    stack_trace: Optional[str] = None,
    service: HistoricoService = Depends(get_historico_service),
    current_user = Depends(get_current_user)
):
    """Registra log do sistema no histórico"""
    try:
        event_id = await service.registrar_sistema_log(
            empresa_id=empresa_id,
            modulo=modulo,
            nivel=nivel,
            mensagem=mensagem,
            erro=erro,
            stack_trace=stack_trace
        )
        
        return {
            "success": True,
            "message": "Log do sistema registrado no histórico",
            "event_id": event_id,
            "modulo": modulo,
            "nivel": nivel
        }
        
    except Exception as e:
        logger.error(f"Erro ao registrar log do sistema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auditoria")
async def registrar_auditoria(
    empresa_id: str,
    usuario_id: str,
    acao: str,
    recurso: str,
    recurso_id: str,
    dados_anteriores: Optional[Dict[str, Any]] = None,
    dados_novos: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    service: HistoricoService = Depends(get_historico_service),
    current_user = Depends(get_current_user)
):
    """Registra evento de auditoria no histórico"""
    try:
        event_id = await service.registrar_auditoria(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            acao=acao,
            recurso=recurso,
            recurso_id=recurso_id,
            dados_anteriores=dados_anteriores,
            dados_novos=dados_novos,
            ip_address=ip_address
        )
        
        return {
            "success": True,
            "message": "Auditoria registrada no histórico",
            "event_id": event_id,
            "acao": acao,
            "recurso": recurso
        }
        
    except Exception as e:
        logger.error(f"Erro ao registrar auditoria: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========================================
# ENDPOINTS PARA CONSULTAR HISTÓRICO
# ========================================

@router.get("/empresa/{empresa_id}")
async def get_historico_empresa(
    empresa_id: str,
    data_inicio: Optional[datetime] = Query(None, description="Data de início (ISO format)"),
    data_fim: Optional[datetime] = Query(None, description="Data de fim (ISO format)"),
    tipos_evento: Optional[List[str]] = Query(None, description="Tipos de evento para filtrar"),
    limit: int = Query(100, ge=1, le=1000, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    service: HistoricoService = Depends(get_historico_service),
    current_user = Depends(get_current_user)
):
    """Busca histórico completo da empresa"""
    try:
        historico = await service.get_historico_empresa(
            empresa_id=empresa_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipos_evento=tipos_evento,
            limit=limit,
            offset=offset
        )
        
        return {
            "empresa_id": empresa_id,
            "periodo": {
                "inicio": data_inicio.isoformat() if data_inicio else None,
                "fim": data_fim.isoformat() if data_fim else None
            },
            "filtros": {
                "tipos_evento": tipos_evento,
                "limit": limit,
                "offset": offset
            },
            "dados": historico
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar histórico da empresa {empresa_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pedido/{pedido_id}")
async def get_historico_pedido(
    pedido_id: str,
    empresa_id: str,
    service: HistoricoService = Depends(get_historico_service),
    current_user = Depends(get_current_user)
):
    """Busca histórico completo de um pedido"""
    try:
        historico = await service.get_historico_pedido(
            empresa_id=empresa_id,
            pedido_id=pedido_id
        )
        
        return {
            "pedido_id": pedido_id,
            "empresa_id": empresa_id,
            "historico": historico
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar histórico do pedido {pedido_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/usuario/{user_id}")
async def get_historico_usuario(
    user_id: str,
    empresa_id: str,
    data_inicio: Optional[datetime] = Query(None, description="Data de início (ISO format)"),
    data_fim: Optional[datetime] = Query(None, description="Data de fim (ISO format)"),
    service: HistoricoService = Depends(get_historico_service),
    current_user = Depends(get_current_user)
):
    """Busca histórico completo de um usuário"""
    try:
        historico = await service.get_historico_usuario(
            empresa_id=empresa_id,
            user_id=user_id,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        return {
            "user_id": user_id,
            "empresa_id": empresa_id,
            "periodo": {
                "inicio": data_inicio.isoformat() if data_inicio else None,
                "fim": data_fim.isoformat() if data_fim else None
            },
            "historico": historico
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar histórico do usuário {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/estatisticas/{empresa_id}")
async def get_estatisticas_empresa(
    empresa_id: str,
    data_inicio: Optional[datetime] = Query(None, description="Data de início (ISO format)"),
    data_fim: Optional[datetime] = Query(None, description="Data de fim (ISO format)"),
    service: HistoricoService = Depends(get_historico_service),
    current_user = Depends(get_current_user)
):
    """Busca estatísticas da empresa"""
    try:
        estatisticas = await service.get_estatisticas_empresa(
            empresa_id=empresa_id,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        return {
            "empresa_id": empresa_id,
            "periodo": {
                "inicio": data_inicio.isoformat() if data_inicio else None,
                "fim": data_fim.isoformat() if data_fim else None
            },
            "estatisticas": estatisticas
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas da empresa {empresa_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/{empresa_id}")
async def get_dashboard_empresa(
    empresa_id: str,
    periodo_dias: int = Query(30, ge=1, le=365, description="Período em dias"),
    service: HistoricoService = Depends(get_historico_service),
    current_user = Depends(get_current_user)
):
    """Busca dados para dashboard da empresa"""
    try:
        dashboard = await service.get_dashboard_empresa(
            empresa_id=empresa_id,
            periodo_dias=periodo_dias
        )
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Erro ao buscar dashboard da empresa {empresa_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========================================
# ENDPOINTS PARA MIGRAÇÃO
# ========================================

@router.post("/migrar")
async def executar_migracao_historicos(
    remover_antigas: bool = Query(False, description="Remove tabelas antigas após migração"),
    service: HistoricoService = Depends(get_historico_service),
    current_user = Depends(get_current_user)
):
    """Executa migração de dados antigos para o sistema unificado"""
    try:
        from ..scripts.migrate_historicos import executar_migracao
        
        resultado = await executar_migracao(service.db, remover_antigas)
        
        return {
            "message": "Migração executada",
            "resultado": resultado
        }
        
    except Exception as e:
        logger.error(f"Erro na migração: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/migracao/status")
async def status_migracao(
    service: HistoricoService = Depends(get_historico_service),
    current_user = Depends(get_current_user)
):
    """Verifica status da migração"""
    try:
        # Conta eventos migrados
        eventos_migrados = service.db.execute(
            "SELECT COUNT(*) FROM events WHERE event_metadata->>'migrado_de' IS NOT NULL"
        ).scalar()
        
        # Conta notificações migradas
        notificacoes_migradas = service.db.execute(
            "SELECT COUNT(*) FROM notifications WHERE channel_metadata->>'migrado_de' IS NOT NULL"
        ).scalar()
        
        # Verifica tabelas antigas
        tabelas_antigas = []
        tabelas_para_verificar = [
            "pedido_status_historico",
            "pedido_historico",
            "usuario_historico", 
            "sistema_logs",
            "auditoria"
        ]
        
        for tabela in tabelas_para_verificar:
            if service._tabela_existe(tabela):
                tabelas_antigas.append(tabela)
        
        return {
            "migracao_concluida": len(tabelas_antigas) == 0,
            "eventos_migrados": eventos_migrados,
            "notificacoes_migradas": notificacoes_migradas,
            "tabelas_antigas_restantes": tabelas_antigas,
            "total_migrado": eventos_migrados + notificacoes_migradas
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar status da migração: {e}")
        raise HTTPException(status_code=500, detail=str(e))
