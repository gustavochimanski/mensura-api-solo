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
# ENDPOINTS PARA CONSULTAR HISTÓRICO (ADMIN)
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
