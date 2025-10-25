from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, Any
import json
import logging
from datetime import datetime

from ...core.websocket_manager import websocket_manager
from ...core.admin_dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/notifications/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: str, empresa_id: str):
    """
    WebSocket endpoint para notificações em tempo real
    
    Args:
        user_id: ID do usuário
        empresa_id: ID da empresa
    """
    try:
        # Conecta o WebSocket
        await websocket_manager.connect(websocket, user_id, empresa_id)
        logger.info(f"WebSocket conectado: usuário {user_id}, empresa {empresa_id}")
        
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
                logger.info(f"WebSocket desconectado: usuário {user_id}")
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
        logger.error(f"Erro ao conectar WebSocket para usuário {user_id}: {e}")
    finally:
        # Remove a conexão quando desconectar
        websocket_manager.disconnect(websocket)

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
        return stats
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de conexões: {e}")
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
