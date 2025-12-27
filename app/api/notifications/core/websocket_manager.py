from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set, Optional, Any
import json
import logging
import asyncio
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
    
    async def connect(self, websocket: WebSocket, user_id: str, empresa_id: str):
        """Aceita uma nova conexão WebSocket"""
        await websocket.accept()
        
        # Normaliza IDs para string para evitar inconsistências
        user_id = str(user_id)
        empresa_id = str(empresa_id)
        
        # Adiciona à lista de conexões do usuário
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        # Adiciona à lista de conexões da empresa
        if empresa_id not in self.empresa_connections:
            self.empresa_connections[empresa_id] = set()
        self.empresa_connections[empresa_id].add(websocket)
        
        # Mapeia WebSocket para identificadores
        self.websocket_to_user[websocket] = user_id
        self.websocket_to_empresa[websocket] = empresa_id
        
        logger.info(f"WebSocket conectado: usuário {user_id}, empresa {empresa_id}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove uma conexão WebSocket"""
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
        
        # Remove mapeamentos
        self.websocket_to_user.pop(websocket, None)
        self.websocket_to_empresa.pop(websocket, None)
        
        logger.info(f"WebSocket desconectado: usuário {user_id}, empresa {empresa_id}")
    
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
                self.disconnect(websocket)
        
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
                self.disconnect(websocket)
        
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
                self.disconnect(websocket)
        
        logger.info(f"Broadcast enviado para {success_count}/{len(all_connections)} conexões")
        return success_count
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas das conexões"""
        total_users = len(self.active_connections)
        total_empresas = len(self.empresa_connections)
        total_connections = sum(len(connections) for connections in self.active_connections.values())
        
        return {
            "total_users_connected": total_users,
            "total_empresas_connected": total_empresas,
            "total_connections": total_connections,
            "users_with_connections": list(self.active_connections.keys()),
            "empresas_with_connections": list(self.empresa_connections.keys())
        }
    
    def is_user_connected(self, user_id: str) -> bool:
        """Verifica se um usuário está conectado"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
    
    def get_user_connections(self, user_id: str) -> int:
        """Retorna número de conexões de um usuário"""
        return len(self.active_connections.get(user_id, set()))
    
    def is_empresa_connected(self, empresa_id: str) -> bool:
        """Verifica se uma empresa tem conexões ativas"""
        empresa_id = str(empresa_id)
        return empresa_id in self.empresa_connections and len(self.empresa_connections[empresa_id]) > 0
    
    def get_empresa_connections(self, empresa_id: str) -> int:
        """Retorna número de conexões de uma empresa"""
        empresa_id = str(empresa_id)
        return len(self.empresa_connections.get(empresa_id, set()))

# Instância global do gerenciador de conexões
websocket_manager = ConnectionManager()
