from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from typing import Dict, Any
import json
import logging
from datetime import datetime

# Tenta importar ClientDisconnected, se não estiver disponível, usa verificação dinâmica
try:
    from uvicorn.protocols.utils import ClientDisconnected
except ImportError:
    ClientDisconnected = None

def _is_disconnect_exception(e: Exception) -> bool:
    """Verifica se a exceção é relacionada a desconexão do cliente"""
    if isinstance(e, WebSocketDisconnect):
        return True
    if ClientDisconnected and isinstance(e, ClientDisconnected):
        return True
    # Verifica pelo nome da classe (para casos onde o import falhou)
    exception_type = type(e).__name__
    if "Disconnect" in exception_type or "ConnectionClosed" in exception_type:
        return True
    return False

from ..core.websocket_manager import websocket_manager
from ....core.admin_dependencies import get_current_user, decode_access_token
from ....database.db_connection import get_db
from sqlalchemy.orm import Session
from app.api.auth.auth_repo import AuthRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

async def _close_ws_policy(websocket: WebSocket, reason: str) -> None:
    # 1008: Policy Violation (apropriado para auth inválida)
    # IMPORTANTE: Precisamos aceitar o WebSocket antes de fechar para responder ao Sec-WebSocket-Protocol
    try:
        # Verifica se já foi aceito
        client_state = getattr(websocket, 'client_state', None)
        is_connected = client_state and hasattr(client_state, 'name') and client_state.name == "CONNECTED"
        
        if not is_connected:
            # Aceita primeiro para responder ao Sec-WebSocket-Protocol
            # Se o cliente enviou um subprotocolo, precisamos responder com ele
            proto = websocket.headers.get("sec-websocket-protocol") or websocket.headers.get("Sec-WebSocket-Protocol")
            if proto:
                parts = [p.strip() for p in proto.split(",") if p.strip()]
                if parts and parts[0].lower() in ("mensura-bearer", "bearer"):
                    subprotocol = parts[0]
                    await websocket.accept(subprotocol=subprotocol)
                else:
                    await websocket.accept()
            else:
                await websocket.accept()
            
            # Envia mensagem de erro antes de fechar
            error_msg = {
                "type": "error",
                "message": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            try:
                await websocket.send_text(json.dumps(error_msg))
            except:
                pass  # Ignora se não conseguir enviar
        
        # Fecha a conexão
        await websocket.close(code=1008, reason=reason.encode('utf-8')[:123])  # Limite de 123 bytes
    except Exception as e:
        logger.error(f"[WS_ROUTER] Erro ao fechar WebSocket: {e}")
        return

def _get_bearer_token_from_ws(websocket: WebSocket) -> str | None:
    # Starlette normaliza headers; tentamos ambos por segurança.
    auth_header = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
    
    # Log para debug - usando INFO para garantir que apareça
    all_headers = dict(websocket.headers) if hasattr(websocket, 'headers') else {}
    logger.info(f"[WS_AUTH] Headers recebidos: {list(all_headers.keys())}")
    logger.info(f"[WS_AUTH] Authorization header presente: {auth_header is not None}")
    if auth_header:
        logger.info(f"[WS_AUTH] Authorization header (primeiros 20 chars): {auth_header[:20]}...")
    
    if not auth_header:
        # Browser não permite setar Authorization no WebSocket nativo.
        # Alternativa suportada: enviar o token via Sec-WebSocket-Protocol:
        #   new WebSocket(url, ['mensura-bearer', token])
        # Header chega como: "mensura-bearer, <token>"
        proto = websocket.headers.get("sec-websocket-protocol") or websocket.headers.get("Sec-WebSocket-Protocol")
        logger.info(f"[WS_AUTH] Sec-WebSocket-Protocol presente: {proto is not None}")
        if proto:
            logger.info(f"[WS_AUTH] Sec-WebSocket-Protocol (primeiros 50 chars): {proto[:50]}...")
        if not proto:
            logger.warning("[WS_AUTH] Token não encontrado nem em Authorization nem em Sec-WebSocket-Protocol")
            return None

        parts = [p.strip() for p in proto.split(",") if p.strip()]
        logger.info(f"[WS_AUTH] Protocol parts: {len(parts)} partes")
        if not parts:
            logger.warning("[WS_AUTH] Protocol parts vazio após split")
            return None

        # Formato 1: ['mensura-bearer', '<token>'] ou ['bearer', '<token>']
        if len(parts) >= 2 and parts[0].lower() in ("mensura-bearer", "bearer"):
            token = parts[1]
            logger.info(f"[WS_AUTH] Token extraído do formato 1 (primeiros 30 chars): {token[:30]}...")
            return token

        # Formato 2: 'mensura-bearer.<token>' ou 'bearer.<token>'
        for p in parts:
            lower = p.lower()
            if lower.startswith("mensura-bearer.") or lower.startswith("bearer."):
                token = p.split(".", 1)[1].strip()
                logger.info(f"[WS_AUTH] Token extraído do formato 2 (primeiros 30 chars): {token[:30]}...")
                return token

        logger.warning(f"[WS_AUTH] Nenhum formato de token reconhecido. Parts: {parts}")
        return None
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None

@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket, 
    empresa_id: str | None = Query(None, description="ID da empresa (será validado contra as empresas do usuário)"),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint para notificações em tempo real
    
    Identidade é derivada do JWT (Authorization: Bearer <token>).
    `empresa_id` pode ser usado para selecionar o escopo, mas é validado no banco.
    
    Nota: O frontend precisa se conectar a este endpoint. Funciona tanto localmente quanto na nuvem.
    - Local: ws://localhost:8000/api/notifications/ws/notifications?empresa_id={empresa_id}
    - Nuvem: wss://api.seudominio.com/api/notifications/ws/notifications?empresa_id={empresa_id}
    """
    user_id = "unknown"
    try:
        # 1) Autentica via header Authorization (Bearer) ANTES do accept()
        logger.info(f"[WS_ROUTER] Tentando autenticar WebSocket - empresa_id={empresa_id}")
        token = _get_bearer_token_from_ws(websocket)
        if not token:
            logger.warning(f"[WS_ROUTER] Token não encontrado - empresa_id={empresa_id}")
            await _close_ws_policy(websocket, "Authorization Bearer ausente ou malformado")
            return
        
        logger.info(f"[WS_ROUTER] Token encontrado, decodificando... (token length: {len(token)})")

        try:
            payload = decode_access_token(token)
            logger.info(f"[WS_ROUTER] Token decodificado com sucesso. Payload keys: {list(payload.keys())}")
        except Exception as e:
            logger.error(f"[WS_ROUTER] Erro ao decodificar token: {e}", exc_info=True)
            await _close_ws_policy(websocket, "Token inválido ou expirado")
            return
            
        raw_sub = payload.get("sub")
        logger.info(f"[WS_ROUTER] JWT sub extraído: {raw_sub}")
        if raw_sub is None:
            logger.warning(f"[WS_ROUTER] JWT sem sub - payload: {payload.keys()}")
            await _close_ws_policy(websocket, "JWT sem sub")
            return

        try:
            user_id_int = int(raw_sub)
            logger.info(f"[WS_ROUTER] User ID convertido: {user_id_int}")
        except ValueError as e:
            logger.error(f"[WS_ROUTER] JWT sub inválido: {raw_sub} - erro: {e}")
            await _close_ws_policy(websocket, "JWT sub inválido")
            return

        logger.info(f"[WS_ROUTER] Buscando usuário no banco: {user_id_int}")
        user = AuthRepository(db).get_user_by_id(user_id_int)
        if not user:
            logger.warning(f"[WS_ROUTER] Usuário não encontrado: {user_id_int}")
            await _close_ws_policy(websocket, "Usuário não encontrado")
            return
        
        logger.info(f"[WS_ROUTER] Usuário encontrado: {user_id_int}")

        # 2) Resolve/valida empresa_id (não confiamos cegamente na URL)
        logger.info(f"[WS_ROUTER] Obtendo empresas do usuário...")
        # Força o carregamento do relacionamento se ainda não foi carregado
        try:
            user_empresas = list(user.empresas) if hasattr(user, 'empresas') else []
        except Exception as e:
            logger.error(f"[WS_ROUTER] Erro ao acessar empresas do usuário: {e}")
            user_empresas = []
        
        logger.info(f"[WS_ROUTER] Usuário tem {len(user_empresas)} empresa(s)")
        if user_empresas:
            empresa_ids = [str(emp.id) for emp in user_empresas]
            logger.info(f"[WS_ROUTER] IDs das empresas do usuário: {empresa_ids}")
        
        if not user_empresas:
            logger.warning(f"[WS_ROUTER] Usuário sem empresas vinculadas. Verifique a tabela cadastros.usuario_empresa")
            await _close_ws_policy(websocket, "Usuário sem empresas vinculadas")
            return

        resolved_empresa_id: str | None = None
        if empresa_id is not None:
            empresa_id = str(empresa_id)
            logger.info(f"[WS_ROUTER] Validando empresa_id={empresa_id} contra empresas do usuário")
            empresa_ids_usuario = [str(emp.id) for emp in user_empresas]
            logger.info(f"[WS_ROUTER] Empresas do usuário: {empresa_ids_usuario}")
            if any(str(emp.id) == empresa_id for emp in user_empresas):
                resolved_empresa_id = empresa_id
                logger.info(f"[WS_ROUTER] Empresa {empresa_id} validada com sucesso")
            else:
                logger.warning(f"[WS_ROUTER] Empresa {empresa_id} não pertence ao usuário. Empresas válidas: {empresa_ids_usuario}")
                await _close_ws_policy(websocket, "empresa_id não pertence ao usuário")
                return
        else:
            # Se não vier empresa_id e o usuário só tem 1, assume automaticamente.
            logger.info(f"[WS_ROUTER] empresa_id não fornecido, verificando se usuário tem apenas 1 empresa")
            if len(user_empresas) == 1:
                resolved_empresa_id = str(user_empresas[0].id)
                logger.info(f"[WS_ROUTER] Usuário tem apenas 1 empresa, usando: {resolved_empresa_id}")
            else:
                logger.warning(f"[WS_ROUTER] Usuário tem {len(user_empresas)} empresas, empresa_id é obrigatório")
                await _close_ws_policy(websocket, "empresa_id é obrigatório para usuários multi-empresa")
                return

        # 3) Agora sim aceita a conexão
        # IMPORTANTE: Se o cliente enviou um subprotocolo, precisamos responder com ele
        logger.info(f"[WS_ROUTER] Todas as validações passaram, aceitando conexão WebSocket...")
        
        # Verifica se o cliente enviou Sec-WebSocket-Protocol
        proto = websocket.headers.get("sec-websocket-protocol") or websocket.headers.get("Sec-WebSocket-Protocol")
        if proto:
            # Extrai o primeiro subprotocolo (mensura-bearer ou bearer)
            parts = [p.strip() for p in proto.split(",") if p.strip()]
            if parts and parts[0].lower() in ("mensura-bearer", "bearer"):
                # Responde com o subprotocolo que o cliente enviou
                subprotocol = parts[0]
                logger.info(f"[WS_ROUTER] Aceitando conexão com subprotocolo: {subprotocol}")
                await websocket.accept(subprotocol=subprotocol)
            else:
                await websocket.accept()
        else:
            await websocket.accept()
        
        logger.info(f"[WS_ROUTER] Conexão WebSocket aceita com sucesso!")

        # Normaliza IDs para garantir consistência
        user_id = str(user_id_int)
        empresa_id = str(resolved_empresa_id)
        
        # Obtém informações do cliente (IP, host, etc)
        client_host = websocket.client.host if websocket.client else "unknown"
        client_port = websocket.client.port if websocket.client else "unknown"
        headers = dict(websocket.headers) if hasattr(websocket, 'headers') else {}
        origin = headers.get('origin', 'unknown')
        
        logger.info(
            f"[WS_ROUTER] Tentando conectar WebSocket - user_id={user_id}, empresa_id={empresa_id}, "
            f"tipo_user_id={type(user_id)}, tipo_empresa_id={type(empresa_id)}, "
            f"websocket_id={id(websocket)}, client={client_host}:{client_port}, origin={origin}"
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
        try:
            await websocket.send_text(json.dumps(welcome_message))
        except Exception as e:
            if _is_disconnect_exception(e):
                logger.info(
                    f"[WS_ROUTER] Cliente desconectou antes de receber mensagem de boas-vindas - "
                    f"user_id={user_id}, empresa_id={empresa_id}, websocket_id={id(websocket)}"
                )
                # Cliente desconectou imediatamente, não há problema - apenas retorna
                return
            else:
                logger.warning(
                    f"[WS_ROUTER] Erro ao enviar mensagem de boas-vindas - "
                    f"user_id={user_id}, empresa_id={empresa_id}, erro={e}"
                )
                # Se houver erro ao enviar, continua mesmo assim - o cliente pode ter desconectado
        
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
                # Se falhar ao enviar, o cliente provavelmente desconectou
                if not await _safe_send_text(websocket, error_message, user_id, empresa_id):
                    break
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
        await websocket_manager.disconnect(websocket)


async def _safe_send_text(websocket: WebSocket, message: Dict[str, Any], user_id: str = "unknown", empresa_id: str = "unknown") -> bool:
    """Envia mensagem de forma segura, tratando desconexões"""
    try:
        await websocket.send_text(json.dumps(message))
        return True
    except Exception as e:
        if _is_disconnect_exception(e):
            logger.debug(
                f"[WS_ROUTER] Cliente desconectado ao enviar mensagem - "
                f"user_id={user_id}, empresa_id={empresa_id}, tipo={message.get('type', 'unknown')}"
            )
        else:
            logger.warning(
                f"[WS_ROUTER] Erro ao enviar mensagem - "
                f"user_id={user_id}, empresa_id={empresa_id}, tipo={message.get('type', 'unknown')}, erro={e}"
            )
        return False

async def _handle_client_message(websocket: WebSocket, user_id: str, empresa_id: str, message: Dict[str, Any]):
    """Processa mensagens recebidas do cliente"""
    message_type = message.get("type")
    
    if message_type == "ping":
        # Responde ao ping com pong
        pong_message = {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }
        await _safe_send_text(websocket, pong_message, user_id, empresa_id)
        
    elif message_type == "subscribe":
        # Cliente quer se inscrever em tipos específicos de notificação
        event_types = message.get("event_types", [])
        subscription_message = {
            "type": "subscription",
            "message": f"Inscrito em {len(event_types)} tipos de eventos",
            "event_types": event_types,
            "timestamp": datetime.utcnow().isoformat()
        }
        await _safe_send_text(websocket, subscription_message, user_id, empresa_id)
    
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
        await _safe_send_text(websocket, route_message, user_id, empresa_id)
        
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
        await _safe_send_text(websocket, stats_message, user_id, empresa_id)
        
    else:
        # Tipo de mensagem não reconhecido
        error_message = {
            "type": "error",
            "message": f"Tipo de mensagem '{message_type}' não reconhecido",
            "timestamp": datetime.utcnow().isoformat()
        }
        await _safe_send_text(websocket, error_message, user_id, empresa_id)

@router.get("/connections/stats")
async def get_connection_stats(current_user = Depends(get_current_user)):
    """Retorna estatísticas das conexões WebSocket"""
    try:
        stats = websocket_manager.get_connection_stats()
        
        # Log detalhado do estado atual
        logger.info(
            f"[STATS] Estatísticas de conexões solicitadas. "
            f"Total: {stats['total_connections']}, "
            f"Empresas: {stats['total_empresas_connected']}, "
            f"Lista: {stats['empresas_with_connections']}, "
            f"Detalhes: {stats.get('empresas_details', {})}"
        )
        
        return {
            **stats,
            "message": "Use estas informações para verificar se há conexões WebSocket ativas",
            "how_to_connect": {
                "endpoint": "/api/notifications/ws/notifications?empresa_id={empresa_id}",
                "example": f"/api/notifications/ws/notifications?empresa_id=1",
                "protocol": "WebSocket (ws:// ou wss://)",
                "note": "A conexão exige Authorization: Bearer <token>. user_id é derivado do JWT."
            }
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
        
        logger.info(
            f"[CHECK_ENDPOINT] Verificando conexões para empresa_id={empresa_id} "
            f"(tipo: {type(empresa_id)})"
        )
        
        is_connected = websocket_manager.is_empresa_connected(empresa_id)
        connection_count = websocket_manager.get_empresa_connections(empresa_id)
        stats = websocket_manager.get_connection_stats()
        
        logger.info(
            f"[CHECK_ENDPOINT] Resultado - empresa_id={empresa_id}, "
            f"is_connected={is_connected}, connection_count={connection_count}, "
            f"todas_empresas={stats['empresas_with_connections']}"
        )
        
        return {
            "empresa_id": empresa_id,
            "is_connected": is_connected,
            "connection_count": connection_count,
            "all_connected_empresas": stats["empresas_with_connections"],
            "total_connections": stats["total_connections"],
            "empresas_details": stats.get("empresas_details", {}),
            "message": "Conecte-se ao WebSocket em /api/notifications/ws/notifications?empresa_id={empresa_id} para receber notificações (Authorization Bearer obrigatório)",
            "how_to_connect": {
                "endpoint": f"/api/notifications/ws/notifications?empresa_id={empresa_id}",
                "protocol": "WebSocket (ws:// ou wss://)",
                "example_url": f"ws://localhost:8000/api/notifications/ws/notifications?empresa_id={empresa_id}",
                "note": "Envie Authorization: Bearer <token>. user_id é derivado do JWT."
            }
        }
    except Exception as e:
        logger.error(f"Erro ao verificar conexões da empresa {empresa_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

