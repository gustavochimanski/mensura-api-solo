"""Adaptadores para provedores de destinatários"""

from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session

from ..contracts.recipient_provider_contract import IRecipientProvider
from app.api.cadastros.repositories.repo_cliente import ClienteRepository
from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.api.cadastros.models.user_model import UserModel
from app.api.auth.auth_repo import AuthRepository

logger = logging.getLogger(__name__)

class ClienteRecipientAdapter(IRecipientProvider):
    """Adaptador para buscar destinatários do modelo ClienteModel"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cliente_repo = ClienteRepository(db)
    
    def get_recipient_by_id(self, recipient_id: str) -> Optional[Dict[str, Any]]:
        """Busca cliente por ID e retorna informações de destinatário"""
        try:
            cliente_id = int(recipient_id) if recipient_id.isdigit() else None
            if not cliente_id:
                return None
            
            cliente = self.cliente_repo.get_by_id(cliente_id)
            if not cliente or not cliente.ativo:
                return None
            
            recipient_data = {
                "user_id": str(cliente.id),
                "cliente_id": str(cliente.id)
            }
            
            if cliente.email:
                recipient_data["email"] = cliente.email
            if cliente.telefone:
                recipient_data["phone"] = cliente.telefone
            
            return recipient_data if (recipient_data.get("email") or recipient_data.get("phone")) else None
            
        except Exception as e:
            logger.error(f"Erro ao buscar cliente {recipient_id}: {e}")
            return None
    
    def get_recipients_by_ids(self, recipient_ids: List[str]) -> List[Dict[str, Any]]:
        """Busca múltiplos clientes por IDs"""
        recipients = []
        for recipient_id in recipient_ids:
            recipient = self.get_recipient_by_id(recipient_id)
            if recipient:
                recipients.append(recipient)
        return recipients
    
    def get_recipients_by_filters(
        self,
        empresa_id: str,
        filter_by_empresa: bool = True,
        filter_by_user_type: Optional[str] = None,
        filter_by_tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Busca clientes baseado em filtros"""
        recipients = []
        
        try:
            # Busca clientes ativos
            query = self.db.query(ClienteModel).filter(ClienteModel.ativo == True)
            
            # TODO: Implementar filtro por empresa_id através de pedidos ou outra relação
            # Por enquanto, busca todos os clientes ativos se filter_by_empresa=True
            
            clientes = query.all()
            
            for cliente in clientes:
                recipient_data = {
                    "user_id": str(cliente.id),
                    "cliente_id": str(cliente.id)
                }
                
                if cliente.email:
                    recipient_data["email"] = cliente.email
                if cliente.telefone:
                    recipient_data["phone"] = cliente.telefone
                
                if recipient_data.get("email") or recipient_data.get("phone"):
                    recipients.append(recipient_data)
            
            logger.info(f"Encontrados {len(recipients)} clientes com os filtros especificados")
            
        except Exception as e:
            logger.error(f"Erro ao buscar clientes por filtros: {e}")
            raise
        
        return recipients

class UserRecipientAdapter(IRecipientProvider):
    """Adaptador para buscar destinatários do modelo UserModel"""
    
    def __init__(self, db: Session):
        self.db = db
        self.auth_repo = AuthRepository(db)
    
    def get_recipient_by_id(self, recipient_id: str) -> Optional[Dict[str, Any]]:
        """Busca usuário por ID"""
        try:
            user_id = int(recipient_id) if recipient_id.isdigit() else None
            if not user_id:
                return None
            
            user = self.auth_repo.get_user_by_id(user_id)
            if not user:
                return None
            
            # UserModel não tem email/telefone diretamente
            # Retorna apenas o user_id para notificações in-app
            return {
                "user_id": str(user.id),
                "username": user.username
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar usuário {recipient_id}: {e}")
            return None
    
    def get_recipients_by_ids(self, recipient_ids: List[str]) -> List[Dict[str, Any]]:
        """Busca múltiplos usuários por IDs"""
        recipients = []
        for recipient_id in recipient_ids:
            recipient = self.get_recipient_by_id(recipient_id)
            if recipient:
                recipients.append(recipient)
        return recipients
    
    def get_recipients_by_filters(
        self,
        empresa_id: str,
        filter_by_empresa: bool = True,
        filter_by_user_type: Optional[str] = None,
        filter_by_tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Busca usuários baseado em filtros"""
        recipients = []
        
        try:
            # Busca usuários relacionados à empresa
            query = self.db.query(UserModel)
            
            # Filtro por tipo de usuário
            if filter_by_user_type:
                query = query.filter(UserModel.type_user == filter_by_user_type)
            
            # Filtro por empresa (através da tabela de associação)
            if filter_by_empresa:
                from app.api.cadastros.models.association_tables import usuario_empresa
                query = query.join(usuario_empresa).filter(
                    usuario_empresa.c.empresa_id == int(empresa_id) if empresa_id.isdigit() else None
                )
            
            users = query.all()
            
            for user in users:
                recipients.append({
                    "user_id": str(user.id),
                    "username": user.username
                })
            
            logger.info(f"Encontrados {len(recipients)} usuários com os filtros especificados")
            
        except Exception as e:
            logger.error(f"Erro ao buscar usuários por filtros: {e}")
            raise
        
        return recipients

class CompositeRecipientAdapter(IRecipientProvider):
    """Adaptador composto que combina múltiplos adaptadores"""
    
    def __init__(self, adapters: List[IRecipientProvider]):
        self.adapters = adapters
    
    def get_recipient_by_id(self, recipient_id: str) -> Optional[Dict[str, Any]]:
        """Tenta buscar em todos os adaptadores até encontrar"""
        for adapter in self.adapters:
            recipient = adapter.get_recipient_by_id(recipient_id)
            if recipient:
                return recipient
        return None
    
    def get_recipients_by_ids(self, recipient_ids: List[str]) -> List[Dict[str, Any]]:
        """Busca em todos os adaptadores e combina resultados"""
        all_recipients = []
        seen_ids = set()
        
        for adapter in self.adapters:
            recipients = adapter.get_recipients_by_ids(recipient_ids)
            for recipient in recipients:
                recipient_id = recipient.get("user_id") or recipient.get("cliente_id")
                if recipient_id and recipient_id not in seen_ids:
                    all_recipients.append(recipient)
                    seen_ids.add(recipient_id)
        
        return all_recipients
    
    def get_recipients_by_filters(
        self,
        empresa_id: str,
        filter_by_empresa: bool = True,
        filter_by_user_type: Optional[str] = None,
        filter_by_tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Busca em todos os adaptadores e combina resultados"""
        all_recipients = []
        seen_ids = set()
        
        for adapter in self.adapters:
            recipients = adapter.get_recipients_by_filters(
                empresa_id,
                filter_by_empresa,
                filter_by_user_type,
                filter_by_tags
            )
            for recipient in recipients:
                recipient_id = recipient.get("user_id") or recipient.get("cliente_id")
                if recipient_id and recipient_id not in seen_ids:
                    all_recipients.append(recipient)
                    seen_ids.add(recipient_id)
        
        return all_recipients

