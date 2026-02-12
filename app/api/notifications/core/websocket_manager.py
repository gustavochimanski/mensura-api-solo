from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set, Optional, Any, Literal
import json
import logging
import asyncio
import os
from urllib.parse import urlparse
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Gerenciador de conexões WebSocket para notificações em tempo real"""
    
    def __init__(self):
        # Armazena conexões por user_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Armazena conexões por empresa_id
        self.empresa_connections: Dict[str, Set[WebSocket]] = {}
        # Mapeia WebSocket para user_id
        self.websocket_to_user: Dict[WebSocket, str] = {}
        # Mapeia WebSocket para empresa_id
        self.websocket_to_empresa: Dict[WebSocket, str] = {}
        # Mapeia WebSocket para rota atual do cliente
        self.websocket_to_route: Dict[WebSocket, str] = {}
        # Mapeia WebSocket para timestamp de conexão (usado para expulsar conexões antigas)
        self.websocket_to_connected_at: Dict[WebSocket, datetime] = {}

        # Lock para evitar race conditions em connect/disconnect concorrentes
        self._lock = asyncio.Lock()

        # Limite de conexões simultâneas por (user_id, empresa_id)
        # Default: 1 (evita explosão de conexões quando o frontend entra em loop de reconnect)
        self.max_connections_per_user_empresa: int = int(
            os.getenv("WS_MAX_CONNECTIONS_PER_USER_EMPRESA", "1")
        )

    @staticmethod
    def _normalize_route(route: str | None) -> str:
        """
        Normaliza rota para comparações consistentes.

        Aceita:
        - "/pedidos", "/pedidos/"
        - "pedidos" (sem barra)
        - URL completa ("https://host/app/pedidos?x=1#y")
        - strings com query/hash
        """
        if not route:
            return ""

        r = str(route).strip()
        if not r:
            return ""

        # URL completa → extrai apenas path
        if "://" in r:
            try:
                r = urlparse(r).path or ""
            except Exception:
                # Fallback: remove query/hash manualmente
                r = r.split("?", 1)[0].split("#", 1)[0]
        else:
            # Remove query/hash se vierem por engano
            r = r.split("?", 1)[0].split("#", 1)[0]

        r = r.strip()
        if not r:
            return ""

        if not r.startswith("/"):
            r = "/" + r

        r = r.lower()

        # Remove trailing slash (exceto root)
        if r != "/" and r.endswith("/"):
            r = r.rstrip("/")
            if not r:
                r = "/"

        return r

    def _remove_connection_no_lock(self, websocket: WebSocket) -> None:
        """Remove um websocket das estruturas internas (NÃO faz await e pressupõe lock)."""
        try:
            ws_id = id(websocket)
            client = getattr(websocket, 'client', None)
            client_repr = f"{getattr(client, 'host', 'unknown')}:{getattr(client, 'port', 'unknown')}" if client else "unknown"
            logger.debug(f"[STATE] Removendo websocket id={ws_id}, client={client_repr}")
        except Exception:
            logger.debug("[STATE] Removendo websocket - falha ao obter informações do cliente", exc_info=True)
        user_id = self.websocket_to_user.get(websocket)
        empresa_id = self.websocket_to_empresa.get(websocket)

        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        if empresa_id and empresa_id in self.empresa_connections:
            self.empresa_connections[empresa_id].discard(websocket)
            if not self.empresa_connections[empresa_id]:
                del self.empresa_connections[empresa_id]

        self.websocket_to_user.pop(websocket, None)
        self.websocket_to_empresa.pop(websocket, None)
        self.websocket_to_route.pop(websocket, None)
        self.websocket_to_connected_at.pop(websocket, None)

    def _is_websocket_active(self, websocket: WebSocket) -> bool:
        """Verifica se um WebSocket ainda está ativo/aberto"""
        try:
            # Verifica o estado do cliente
            client_state = getattr(websocket, 'client_state', None)
            if client_state:
                state_name = getattr(client_state, 'name', None)
                # CONNECTED significa que está aberto e ativo
                if state_name == "CONNECTED":
                    return True
                # DISCONNECTED ou outros estados significam que está fechado
                return False
            # Se não tem client_state, assume que pode estar ativo (fallback)
            return True
        except Exception as e:
            logger.debug(f"[CONNECT] Erro ao verificar estado do WebSocket: {e}")
            # Em caso de erro, assume que não está ativo para evitar problemas
            return False
    
    async def _best_effort_close(self, websocket: WebSocket, code: int, reason: str) -> None:
        """Tenta fechar um websocket sem deixar exceção vazar."""
        try:
            # Verifica se ainda está ativo antes de tentar fechar
            if not self._is_websocket_active(websocket):
                logger.debug(f"[CONNECT] WebSocket já está fechado, pulando close()")
                return
            try:
                ws_id = id(websocket)
                client = getattr(websocket, 'client', None)
                client_repr = f"{getattr(client, 'host', 'unknown')}:{getattr(client, 'port', 'unknown')}" if client else "unknown"
                logger.debug(f"[CONNECT] Fechando websocket id={ws_id}, client={client_repr}, code={code}, reason={reason}")
            except Exception:
                logger.debug("[CONNECT] Fechando websocket - falha ao obter informações do cliente", exc_info=True)
            await websocket.close(code=code, reason=reason)
        except Exception:
            # Pode falhar se já estiver fechado / estado inválido; é ok.
            return
    
    async def connect(self, websocket: WebSocket, user_id: str, empresa_id: str):
        """
        Registra uma nova conexão WebSocket.

        IMPORTANTE: o `accept()` deve ser feito ANTES (após autenticação/validação) no endpoint WS.
        """
        
        # Normaliza IDs para string para evitar inconsistências
        user_id = str(user_id)
        empresa_id = str(empresa_id)
        
        logger.info(
            f"[CONNECT] Iniciando conexão - user_id={user_id}, empresa_id={empresa_id}, "
            f"websocket={id(websocket)}, client={websocket.client if hasattr(websocket, 'client') else 'N/A'}"
        )

        # Evita explosão de conexões por (user_id, empresa_id) fechando conexões antigas
        websockets_to_evict: List[WebSocket] = []
        async with self._lock:
            if self.max_connections_per_user_empresa > 0:
                existing_for_user = list(self.active_connections.get(user_id, set()))
                existing_same_empresa = [
                    ws for ws in existing_for_user
                    if self.websocket_to_empresa.get(ws) == empresa_id
                ]
                # Inicializa listas para evitar UnboundLocalError caso não sejam criadas abaixo
                active_existing: List[WebSocket] = []
                inactive_existing: List[WebSocket] = []

                if existing_same_empresa:
                    # Filtra apenas conexões que ainda estão ativas
                    active_existing = [ws for ws in existing_same_empresa if self._is_websocket_active(ws)]
                    
                    # Remove conexões inativas do estado (cleanup)
                    inactive_existing = [ws for ws in existing_same_empresa if not self._is_websocket_active(ws)]
                    for ws in inactive_existing:
                        logger.debug(f"[CONNECT] Removendo conexão inativa do estado - websocket_id={id(ws)}")
                        self._remove_connection_no_lock(ws)
                    
                    # Se ainda há conexões ativas após o cleanup, verifica o limite
                if active_existing:
                    # Ordena por tempo de conexão (mais antigas primeiro)
                    active_existing.sort(
                        key=lambda ws: self.websocket_to_connected_at.get(ws, datetime.min)
                    )

                    allowed_existing = max(0, self.max_connections_per_user_empresa - 1)
                    evict_count = max(0, len(active_existing) - allowed_existing)
                    if evict_count > 0:
                        websockets_to_evict = active_existing[:evict_count]

                        # DEBUG: registra ids e timestamps das conexões que serão expulsas
                        evict_info = []
                        for ws in websockets_to_evict:
                            ts = self.websocket_to_connected_at.get(ws)
                            evict_info.append({"ws_id": id(ws), "connected_at": ts.isoformat() if ts else None})
                        logger.debug(f"[CONNECT] Conexões selecionadas para expulsão: {evict_info}")

                        # Remove do estado imediatamente (mesmo que o close falhe)
                        for ws in websockets_to_evict:
                            # Proteção extra: não remover acidentalmente a nova conexão (defensivo)
                            if ws is websocket:
                                logger.warning(f"[CONNECT] Tentativa de expulsar a própria conexão nova (id={id(ws)}); pulando.")
                                continue
                            self._remove_connection_no_lock(ws)

                        logger.warning(
                            f"[CONNECT] Limite atingido para user_id={user_id}, empresa_id={empresa_id}. "
                            f"Fechando {len(websockets_to_evict)} conexão(ões) antiga(s) ativa(s) para aceitar a nova. "
                            f"Total encontradas: {len(existing_same_empresa)}, Ativas: {len(active_existing)}, "
                            f"Inativas removidas: {len(inactive_existing)}, max_connections_per_user_empresa={self.max_connections_per_user_empresa}"
                        )
                else:
                    logger.debug(
                        f"[CONNECT] Todas as conexões existentes para user_id={user_id}, empresa_id={empresa_id} "
                        f"já estão inativas. Total encontradas: {len(existing_same_empresa)}, "
                        f"Inativas removidas: {len(inactive_existing)}"
                    )

            # Adiciona a nova conexão ao estado
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
                logger.debug(f"[CONNECT] Criando novo conjunto de conexões para user_id={user_id}")
            self.active_connections[user_id].add(websocket)
            logger.debug(f"[CONNECT] Adicionado ao active_connections[{user_id}]. Total: {len(self.active_connections[user_id])}")

            if empresa_id not in self.empresa_connections:
                self.empresa_connections[empresa_id] = set()
                logger.debug(f"[CONNECT] Criando novo conjunto de conexões para empresa_id={empresa_id}")
            self.empresa_connections[empresa_id].add(websocket)
            logger.debug(f"[CONNECT] Adicionado ao empresa_connections[{empresa_id}]. Total: {len(self.empresa_connections[empresa_id])}")

            self.websocket_to_user[websocket] = user_id
            self.websocket_to_empresa[websocket] = empresa_id
            self.websocket_to_route[websocket] = ""
            self.websocket_to_connected_at[websocket] = datetime.utcnow()
            # Log extra: headers/origin do websocket recém-adicionado para correlação
            try:
                headers = getattr(websocket, 'headers', {}) or {}
                origin = headers.get('origin', headers.get('Origin', 'unknown'))
                sec_proto = headers.get("sec-websocket-protocol") or headers.get("Sec-WebSocket-Protocol")
                logger.debug(
                    f"[CONNECT] Registrado websocket id={id(websocket)}, user_id={user_id}, empresa_id={empresa_id}, "
                    f"origin={origin}, sec_protocol={sec_proto[:200] if sec_proto else None}"
                )
            except Exception:
                logger.debug("[CONNECT] Falha ao logar headers do websocket recém-adicionado", exc_info=True)
        
        # Fecha as conexões expulsas (fora do lock, best-effort)
        for ws in websockets_to_evict:
            # Tenta notificar o cliente que será desconectado e deve deslogar/fechar sessão no front
            try:
                if self._is_websocket_active(ws):
                    logout_msg = {
                        "type": "event",
                        "event": "force_logout",
                        "scope": "usuario",
                        "payload": {
                            "reason": "conexao_substituida",
                            "message": "Sua sessão foi encerrada porque houve nova conexão para sua conta."
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await ws.send_text(json.dumps(logout_msg))
            except Exception as e:
                logger.debug(f"[CONNECT] Falha ao notificar websocket expulsado (id={id(ws)}): {e}")

            await self._best_effort_close(
                ws,
                code=4001,
                reason="Conexão substituída por outra mais recente para o mesmo usuário/empresa"
            )
        
        # Log do estado completo após conexão
        stats = self.get_connection_stats()
        logger.info(
            f"[CONNECT] WebSocket conectado com sucesso - user_id={user_id}, empresa_id={empresa_id}. "
            f"Estado atual: {stats['total_connections']} conexões totais, "
            f"{stats['total_empresas_connected']} empresas conectadas, "
            f"Empresas: {stats['empresas_with_connections']}"
        )

    async def emit_event(
        self,
        *,
        event: str,
        scope: Literal["empresa", "usuario"],
        payload: Dict[str, Any],
        empresa_id: str | None = None,
        user_id: str | None = None,
        required_route: str | None = None,
    ) -> int | bool:
        """
        Envia um evento padronizado via WebSocket.

        Envelope:
        {
          "type": "event",
          "event": "<nome>",
          "scope": "empresa" | "usuario",
          "payload": {...},
          "timestamp": "..."
        }
        """
        message = {
            "type": "event",
            "event": event,
            "scope": scope,
            "payload": payload or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        if scope == "usuario":
            if not user_id:
                raise ValueError("user_id é obrigatório quando scope='usuario'")
            return await self.send_to_user(str(user_id), message)

        # scope == "empresa"
        if not empresa_id:
            raise ValueError("empresa_id é obrigatório quando scope='empresa'")

        if required_route:
            return await self.send_to_empresa_on_route(str(empresa_id), message, required_route=required_route)

        return await self.send_to_empresa(str(empresa_id), message)
    
    async def disconnect(self, websocket: WebSocket):
        """Remove uma conexão WebSocket (async para ser consistente com o lock)."""
        user_id = self.websocket_to_user.get(websocket)
        empresa_id = self.websocket_to_empresa.get(websocket)
        route = self.websocket_to_route.get(websocket, "")

        logger.info(
            f"[DISCONNECT] Iniciando desconexão - user_id={user_id}, empresa_id={empresa_id}, "
            f"route={route}, websocket={id(websocket)}"
        )

        async with self._lock:
            self._remove_connection_no_lock(websocket)
        
        # Log do estado completo após desconexão
        stats = self.get_connection_stats()
        logger.info(
            f"[DISCONNECT] WebSocket desconectado - user_id={user_id}, empresa_id={empresa_id}. "
            f"Estado atual: {stats['total_connections']} conexões totais, "
            f"{stats['total_empresas_connected']} empresas conectadas, "
            f"Empresas: {stats['empresas_with_connections']}"
        )
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Envia mensagem para um usuário específico"""
        if user_id not in self.active_connections:
            logger.warning(f"Usuário {user_id} não está conectado")
            return False
        
        connections = self.active_connections[user_id].copy()
        if not connections:
            return False
        
        success_count = 0
        for websocket in connections:
            try:
                await websocket.send_text(json.dumps(message))
                success_count += 1
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem para usuário {user_id}: {e}")
                # Remove conexão inválida
                await self.disconnect(websocket)
        
        logger.info(f"Mensagem enviada para {success_count}/{len(connections)} conexões do usuário {user_id}")
        return success_count > 0
    
    async def send_to_empresa(self, empresa_id: str, message: Dict[str, Any]) -> int:
        """Envia mensagem para todos os usuários de uma empresa"""
        # Normaliza empresa_id para string para evitar inconsistências
        empresa_id = str(empresa_id)
        
        # Verifica se a empresa tem conexões (tenta também como int caso esteja armazenado assim)
        if empresa_id not in self.empresa_connections:
            # Tenta também verificar se há conexões com empresa_id como int
            empresa_id_int = None
            try:
                empresa_id_int = str(int(empresa_id))
            except (ValueError, TypeError):
                pass
            
            if empresa_id_int and empresa_id_int in self.empresa_connections:
                # Se encontrou com int, usa esse
                empresa_id = empresa_id_int
            else:
                logger.warning(
                    f"Empresa {empresa_id} não tem conexões ativas. "
                    f"Empresas conectadas: {list(self.empresa_connections.keys())}"
                )
                return 0
        
        connections = self.empresa_connections[empresa_id].copy()
        if not connections:
            logger.warning(f"Empresa {empresa_id} não tem conexões ativas (conjunto vazio)")
            return 0
        
        success_count = 0
        for websocket in connections:
            try:
                await websocket.send_text(json.dumps(message))
                success_count += 1
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem para empresa {empresa_id}: {e}")
                # Remove conexão inválida
                await self.disconnect(websocket)
        
        logger.info(f"Mensagem enviada para {success_count}/{len(connections)} conexões da empresa {empresa_id}")
        return success_count
    
    async def broadcast(self, message: Dict[str, Any]) -> int:
        """Envia mensagem para todos os usuários conectados"""
        all_connections = set()
        for connections in self.active_connections.values():
            all_connections.update(connections)
        
        if not all_connections:
            return 0
        
        success_count = 0
        for websocket in all_connections:
            try:
                await websocket.send_text(json.dumps(message))
                success_count += 1
            except Exception as e:
                logger.error(f"Erro no broadcast: {e}")
                # Remove conexão inválida
                await self.disconnect(websocket)
        
        logger.info(f"Broadcast enviado para {success_count}/{len(all_connections)} conexões")
        return success_count
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas das conexões"""
        total_users = len(self.active_connections)
        total_empresas = len(self.empresa_connections)
        total_connections = sum(len(connections) for connections in self.active_connections.values())
        
        # Detalhes das empresas conectadas
        empresas_details = {}
        for emp_id, connections in self.empresa_connections.items():
            empresas_details[emp_id] = {
                "connection_count": len(connections),
                "routes": [self.websocket_to_route.get(ws, "") for ws in connections]
            }
        
        return {
            "total_users_connected": total_users,
            "total_empresas_connected": total_empresas,
            "total_connections": total_connections,
            "users_with_connections": list(self.active_connections.keys()),
            "empresas_with_connections": list(self.empresa_connections.keys()),
            "empresas_details": empresas_details
        }
    
    def is_user_connected(self, user_id: str) -> bool:
        """Verifica se um usuário está conectado"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
    
    def get_user_connections(self, user_id: str) -> int:
        """Retorna número de conexões de um usuário"""
        return len(self.active_connections.get(user_id, set()))
    
    def is_empresa_connected(self, empresa_id: str) -> bool:
        """Verifica se uma empresa tem conexões ativas"""
        # Normaliza empresa_id para string
        original_empresa_id = empresa_id
        empresa_id = str(empresa_id)
        
        logger.debug(
            f"[CHECK] Verificando conexões para empresa_id={empresa_id} (original={original_empresa_id}). "
            f"Empresas no dicionário: {list(self.empresa_connections.keys())}"
        )
        
        # Verifica se a empresa tem conexões (tenta também como int caso esteja armazenado assim)
        if empresa_id not in self.empresa_connections:
            # Tenta também verificar se há conexões com empresa_id como int
            empresa_id_int = None
            try:
                empresa_id_int = str(int(empresa_id))
                logger.debug(f"[CHECK] Tentando empresa_id como int: {empresa_id_int}")
            except (ValueError, TypeError):
                logger.debug(f"[CHECK] Não foi possível converter empresa_id para int")
                pass
            
            if empresa_id_int and empresa_id_int in self.empresa_connections:
                # Se encontrou com int, usa esse
                logger.debug(f"[CHECK] Encontrado com empresa_id_int={empresa_id_int}")
                empresa_id = empresa_id_int
            else:
                logger.warning(
                    f"[CHECK] Empresa {empresa_id} (original: {original_empresa_id}) não tem conexões ativas. "
                    f"Empresas conectadas: {list(self.empresa_connections.keys())}, "
                    f"Tipo original: {type(original_empresa_id)}, "
                    f"Tentou int: {empresa_id_int}"
                )
                return False
        
        # Verifica se há conexões válidas
        connections = self.empresa_connections.get(empresa_id, set())
        connection_count = len(connections)
        logger.debug(
            f"[CHECK] Empresa {empresa_id} tem {connection_count} conexões ativas. "
            f"Rotas: {[self.websocket_to_route.get(ws, '') for ws in connections]}"
        )
        return connection_count > 0
    
    def get_empresa_connections(self, empresa_id: str) -> int:
        """Retorna número de conexões de uma empresa"""
        # Normaliza empresa_id para string
        empresa_id = str(empresa_id)
        
        # Verifica se a empresa tem conexões (tenta também como int caso esteja armazenado assim)
        if empresa_id not in self.empresa_connections:
            # Tenta também verificar se há conexões com empresa_id como int
            empresa_id_int = None
            try:
                empresa_id_int = str(int(empresa_id))
            except (ValueError, TypeError):
                pass
            
            if empresa_id_int and empresa_id_int in self.empresa_connections:
                # Se encontrou com int, usa esse
                empresa_id = empresa_id_int
        
        return len(self.empresa_connections.get(empresa_id, set()))
    
    def set_route(self, websocket: WebSocket, route: str):
        """Define a rota atual de um cliente conectado"""
        if websocket in self.websocket_to_user:
            normalized = self._normalize_route(route)
            self.websocket_to_route[websocket] = normalized
            user_id = self.websocket_to_user.get(websocket)
            logger.debug(f"Rota atualizada para usuário {user_id}: {normalized} (raw={route})")
    
    def get_route(self, websocket: WebSocket) -> Optional[str]:
        """Retorna a rota atual de um cliente"""
        return self.websocket_to_route.get(websocket, "")
    
    async def send_to_empresa_on_route(
        self, 
        empresa_id: str, 
        message: Dict[str, Any], 
        required_route: str = "/pedidos"
    ) -> int:
        """
        Envia mensagem apenas para usuários de uma empresa que estão em uma rota específica
        
        Args:
            empresa_id: ID da empresa
            message: Mensagem a ser enviada
            required_route: Rota que o cliente deve estar para receber a mensagem (padrão: /pedidos)
        
        Returns:
            Número de conexões que receberam a mensagem
        """
        # Normaliza empresa_id para string
        empresa_id = str(empresa_id)
        required_route = self._normalize_route(required_route)

        # Se não há rota requerida válida, envia para toda a empresa (fallback seguro)
        if not required_route:
            return await self.send_to_empresa(empresa_id, message)
        
        # Verifica se a empresa tem conexões
        if empresa_id not in self.empresa_connections:
            # Tenta também verificar se há conexões com empresa_id como int
            empresa_id_int = None
            try:
                empresa_id_int = str(int(empresa_id))
            except (ValueError, TypeError):
                pass
            
            if empresa_id_int and empresa_id_int in self.empresa_connections:
                empresa_id = empresa_id_int
            else:
                logger.warning(
                    f"Empresa {empresa_id} não tem conexões ativas para rota {required_route}. "
                    f"Empresas conectadas: {list(self.empresa_connections.keys())}"
                )
                return 0
        
        connections = self.empresa_connections[empresa_id].copy()
        if not connections:
            logger.warning(f"Empresa {empresa_id} não tem conexões ativas (conjunto vazio)")
            return 0
        
        # Filtra conexões que estão na rota requerida
        # Regra:
        # - aceita rota exatamente igual ("/chatbot")
        # - aceita prefixo ("/chatbot/..." ) para rotas aninhadas
        # - mantém compatibilidade com comportamento antigo (endswith) para casos como "/admin/pedidos"
        filtered_connections = []
        required_route_norm = required_route.rstrip("/")
        for websocket in connections:
            current_route = self._normalize_route(self.websocket_to_route.get(websocket, ""))
            if not current_route:
                continue
            if current_route == required_route:
                filtered_connections.append(websocket)
                continue
            # Prefix match (ex: /chatbot/conversations/123)
            if required_route_norm and current_route.startswith(required_route_norm + "/"):
                filtered_connections.append(websocket)
                continue
            # Compat: rota pode ser uma URL completa ou rota com prefixo (ex: /admin/pedidos)
            if current_route.endswith(required_route):
                filtered_connections.append(websocket)
        
        if not filtered_connections:
            logger.info(
                f"Nenhum cliente da empresa {empresa_id} está na rota {required_route}. "
                f"Total de conexões: {len(connections)}, "
                f"Rotas ativas: {[self.websocket_to_route.get(ws, '') for ws in connections]}"
            )
            return 0
        
        success_count = 0
        for websocket in filtered_connections:
            try:
                await websocket.send_text(json.dumps(message))
                success_count += 1
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem para empresa {empresa_id} na rota {required_route}: {e}")
                # Remove conexão inválida
                await self.disconnect(websocket)
        
        logger.info(
            f"Mensagem enviada para {success_count}/{len(filtered_connections)} conexões "
            f"da empresa {empresa_id} na rota {required_route} "
            f"(total de conexões da empresa: {len(connections)})"
        )
        return success_count

    async def broadcast_on_route(self, message: Dict[str, Any], required_route: str) -> int:
        """
        Broadcast apenas para conexões que estão em uma rota específica.

        Útil para eventos que só fazem sentido quando o usuário está na tela (ex: /chatbot).
        """
        required_route = self._normalize_route(required_route)
        required_route_norm = required_route.rstrip("/")

        all_connections = set()
        for connections in self.active_connections.values():
            all_connections.update(connections)

        if not all_connections:
            return 0

        filtered_connections = []
        for websocket in all_connections:
            current_route = self._normalize_route(self.websocket_to_route.get(websocket, ""))
            if not current_route:
                continue
            if current_route == required_route:
                filtered_connections.append(websocket)
                continue
            if required_route_norm and current_route.startswith(required_route_norm + "/"):
                filtered_connections.append(websocket)
                continue
            if current_route.endswith(required_route):
                filtered_connections.append(websocket)

        if not filtered_connections:
            return 0

        success_count = 0
        for websocket in filtered_connections:
            try:
                await websocket.send_text(json.dumps(message))
                success_count += 1
            except Exception as e:
                logger.error(f"Erro no broadcast_on_route ({required_route}): {e}")
                await self.disconnect(websocket)

        logger.info(
            f"Broadcast_on_route enviado para {success_count}/{len(filtered_connections)} conexões "
            f"(route={required_route})"
        )
        return success_count

# Instância global do gerenciador de conexões
websocket_manager = ConnectionManager()
