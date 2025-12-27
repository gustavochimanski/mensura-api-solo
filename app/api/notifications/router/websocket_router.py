from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from typing import Dict, Any
import json
import logging
from datetime import datetime

from ..core.websocket_manager import websocket_manager
from ....core.admin_dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/notifications/{user_id}")
async def websocket_notifications(
    websocket: WebSocket, 
    user_id: str, 
    empresa_id: str = Query(..., description="ID da empresa")
):
    """
    WebSocket endpoint para notificações em tempo real
    
    Args:
        user_id: ID do usuário
        empresa_id: ID da empresa
    """
    try:
        # Normaliza IDs para garantir consistência
        user_id = str(user_id)
        empresa_id = str(empresa_id)
        
        logger.info(
            f"[WS_ROUTER] Tentando conectar WebSocket - user_id={user_id}, empresa_id={empresa_id}, "
            f"tipo_user_id={type(user_id)}, tipo_empresa_id={type(empresa_id)}, "
            f"websocket_id={id(websocket)}, client={websocket.client if hasattr(websocket, 'client') else 'N/A'}"
        )
        
        # Conecta o WebSocket
        await websocket_manager.connect(websocket, user_id, empresa_id)
        
        # Verifica se a conexão foi registrada
        stats = websocket_manager.get_connection_stats()
        logger.info(
            f"[WS_ROUTER] WebSocket conectado e registrado - user_id={user_id}, empresa_id={empresa_id}. "
            f"Total de conexões: {stats['total_connections']}, "
            f"Empresas conectadas: {stats['total_empresas_connected']}, "
            f"Empresas: {stats['empresas_with_connections']}, "
            f"Detalhes: {stats.get('empresas_details', {})}"
        )
        
        # Envia mensagem de boas-vindas
        welcome_message = {
            "type": "connection",
            "message": "Conectado com sucesso",
            "user_id": user_id,
            "empresa_id": empresa_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        # Loop para manter a conexão ativa e processar mensagens
        while True:
            try:
                # Aguarda mensagem do cliente (ping/pong, comandos, etc.)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Processa mensagens do cliente
                await _handle_client_message(websocket, user_id, empresa_id, message)
                
            except WebSocketDisconnect:
                logger.info(
                    f"[WS_ROUTER] WebSocket desconectado pelo cliente - user_id={user_id}, empresa_id={empresa_id}, "
                    f"websocket_id={id(websocket)}"
                )
                break
            except json.JSONDecodeError:
                logger.warning(f"Mensagem inválida recebida de {user_id}")
                error_message = {
                    "type": "error",
                    "message": "Formato de mensagem inválido",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(error_message))
            except Exception as e:
                logger.error(f"Erro no WebSocket para usuário {user_id}: {e}")
                break
                
    except Exception as e:
        logger.error(
            f"[WS_ROUTER] Erro ao conectar WebSocket - user_id={user_id}, empresa_id={empresa_id}, "
            f"websocket_id={id(websocket)}, erro={e}", 
            exc_info=True
        )
    finally:
        # Remove a conexão quando desconectar
        logger.info(
            f"[WS_ROUTER] Executando cleanup - user_id={user_id}, empresa_id={empresa_id}, "
            f"websocket_id={id(websocket)}"
        )
        websocket_manager.disconnect(websocket)
        stats_after = websocket_manager.get_connection_stats()
        logger.info(
            f"[WS_ROUTER] WebSocket desconectado e removido - user_id={user_id}, empresa_id={empresa_id}. "
            f"Conexões restantes: {stats_after['total_connections']}, "
            f"Empresas conectadas: {stats_after['total_empresas_connected']}, "
            f"Empresas: {stats_after['empresas_with_connections']}"
        )

async def _handle_client_message(websocket: WebSocket, user_id: str, empresa_id: str, message: Dict[str, Any]):
    """Processa mensagens recebidas do cliente"""
    message_type = message.get("type")
    
    if message_type == "ping":
        # Responde ao ping com pong
        pong_message = {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(pong_message))
        
    elif message_type == "subscribe":
        # Cliente quer se inscrever em tipos específicos de notificação
        event_types = message.get("event_types", [])
        subscription_message = {
            "type": "subscription",
            "message": f"Inscrito em {len(event_types)} tipos de eventos",
            "event_types": event_types,
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(subscription_message))
    
    elif message_type == "set_route":
        # Cliente informa que mudou de rota
        route = message.get("route", "")
        logger.info(
            f"[WS_ROUTER] Recebida mensagem set_route - user_id={user_id}, empresa_id={empresa_id}, "
            f"route={route}, websocket_id={id(websocket)}"
        )
        websocket_manager.set_route(websocket, route)
        route_message = {
            "type": "route_updated",
            "message": f"Rota atualizada para: {route}",
            "route": route,
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(route_message))
        
        # Log do estado após atualizar rota
        stats = websocket_manager.get_connection_stats()
        logger.info(
            f"[WS_ROUTER] Rota atualizada - user_id={user_id}, empresa_id={empresa_id}, route={route}. "
            f"Estado: {stats['total_connections']} conexões, "
            f"Empresas: {stats['empresas_with_connections']}"
        )
        
    elif message_type == "get_stats":
        # Cliente quer estatísticas da conexão
        stats = websocket_manager.get_connection_stats()
        stats_message = {
            "type": "stats",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(stats_message))
        
    else:
        # Tipo de mensagem não reconhecido
        error_message = {
            "type": "error",
            "message": f"Tipo de mensagem '{message_type}' não reconhecido",
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(error_message))

@router.get("/connections/stats")
async def get_connection_stats(current_user = Depends(get_current_user)):
    """Retorna estatísticas das conexões WebSocket"""
    try:
        stats = websocket_manager.get_connection_stats()
        return {
            **stats,
            "message": "Use estas informações para verificar se há conexões WebSocket ativas"
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de conexões: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/connections/check/{empresa_id}")
async def check_empresa_connections(
    empresa_id: str,
    current_user = Depends(get_current_user)
):
    """Verifica se uma empresa específica tem conexões WebSocket ativas"""
    try:
        empresa_id = str(empresa_id)
        is_connected = websocket_manager.is_empresa_connected(empresa_id)
        connection_count = websocket_manager.get_empresa_connections(empresa_id)
        stats = websocket_manager.get_connection_stats()
        
        return {
            "empresa_id": empresa_id,
            "is_connected": is_connected,
            "connection_count": connection_count,
            "all_connected_empresas": stats["empresas_with_connections"],
            "message": "Conecte-se ao WebSocket em /ws/notifications/{user_id}?empresa_id={empresa_id} para receber notificações"
        }
    except Exception as e:
        logger.error(f"Erro ao verificar conexões da empresa {empresa_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/send")
async def send_notification_to_user(
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
    current_user = Depends(get_current_user)
):
    """Envia notificação para um usuário específico via WebSocket"""
    try:
        notification_data = {
            "type": "notification",
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        success = await websocket_manager.send_to_user(user_id, notification_data)
        
        if success:
            return {"message": f"Notificação enviada para usuário {user_id}"}
        else:
            return {"message": f"Usuário {user_id} não está conectado"}
            
    except Exception as e:
        logger.error(f"Erro ao enviar notificação para usuário {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/broadcast")
async def broadcast_notification(
    empresa_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
    current_user = Depends(get_current_user)
):
    """Envia notificação para todos os usuários de uma empresa"""
    try:
        notification_data = {
            "type": "notification",
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "empresa_id": empresa_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        sent_count = await websocket_manager.send_to_empresa(empresa_id, notification_data)
        
        return {
            "message": f"Notificação enviada para {sent_count} usuários da empresa {empresa_id}",
            "sent_count": sent_count
        }
        
    except Exception as e:
        logger.error(f"Erro ao enviar broadcast para empresa {empresa_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
