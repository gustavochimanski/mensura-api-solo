from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class EventType(str, Enum):
    # Eventos de Pedidos (Histórico Completo)
    PEDIDO_CRIADO = "pedido_criado"
    PEDIDO_APROVADO = "pedido_aprovado"
    PEDIDO_REJEITADO = "pedido_rejeitado"
    PEDIDO_CANCELADO = "pedido_cancelado"
    PEDIDO_ENTREGUE = "pedido_entregue"
    PEDIDO_STATUS_CHANGED = "pedido_status_changed"
    PEDIDO_ATUALIZADO = "pedido_atualizado"
    PEDIDO_ITEM_ADICIONADO = "pedido_item_adicionado"
    PEDIDO_ITEM_REMOVIDO = "pedido_item_removido"
    PEDIDO_VALOR_ALTERADO = "pedido_valor_alterado"
    
    # Eventos de Estoque
    ESTOQUE_BAIXO = "estoque_baixo"
    ESTOQUE_ESGOTADO = "estoque_esgotado"
    PRODUTO_INDISPONIVEL = "produto_indisponivel"
    ESTOQUE_ATUALIZADO = "estoque_atualizado"
    PRODUTO_CADASTRADO = "produto_cadastrado"
    PRODUTO_ATUALIZADO = "produto_atualizado"
    
    # Eventos de Pagamento
    PAGAMENTO_APROVADO = "pagamento_aprovado"
    PAGAMENTO_REJEITADO = "pagamento_rejeitado"
    PAGAMENTO_PENDENTE = "pagamento_pendente"
    PAGAMENTO_CANCELADO = "pagamento_cancelado"
    PAGAMENTO_REEMBOLSADO = "pagamento_reembolsado"
    PAGAMENTO_PROCESSANDO = "pagamento_processando"
    
    # Eventos de Usuário (Histórico Completo)
    USUARIO_CADASTRO = "usuario_cadastro"
    USUARIO_LOGIN = "usuario_login"
    USUARIO_LOGOUT = "usuario_logout"
    USUARIO_PERFIL_ATUALIZADO = "usuario_perfil_atualizado"
    USUARIO_SENHA_ALTERADA = "usuario_senha_alterada"
    USUARIO_EMAIL_ALTERADO = "usuario_email_alterado"
    USUARIO_TELEFONE_ALTERADO = "usuario_telefone_alterado"
    USUARIO_ENDERECO_ALTERADO = "usuario_endereco_alterado"
    USUARIO_ATIVADO = "usuario_ativado"
    USUARIO_DESATIVADO = "usuario_desativado"
    USUARIO_BLOQUEADO = "usuario_bloqueado"
    USUARIO_DESBLOQUEADO = "usuario_desbloqueado"
    
    # Eventos de Cliente
    CLIENTE_CADASTRADO = "cliente_cadastrado"
    CLIENTE_ATUALIZADO = "cliente_atualizado"
    CLIENTE_ENDERECO_ALTERADO = "cliente_endereco_alterado"
    CLIENTE_TELEFONE_ALTERADO = "cliente_telefone_alterado"
    CLIENTE_EMAIL_ALTERADO = "cliente_email_alterado"
    
    # Eventos de Sistema (Logs Completos)
    SISTEMA_ERRO = "sistema_erro"
    SISTEMA_WARNING = "sistema_warning"
    SISTEMA_INFO = "sistema_info"
    SISTEMA_DEBUG = "sistema_debug"
    SISTEMA_MANUTENCAO = "sistema_manutencao"
    SISTEMA_BACKUP = "sistema_backup"
    SISTEMA_RESTORE = "sistema_restore"
    SISTEMA_UPDATE = "sistema_update"
    SISTEMA_CONFIG_ALTERADA = "sistema_config_alterada"
    
    # Eventos de API
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    API_ERROR = "api_error"
    API_RATE_LIMIT = "api_rate_limit"
    
    # Eventos de Integração
    INTEGRACAO_WEBHOOK = "integracao_webhook"
    INTEGRACAO_EMAIL = "integracao_email"
    INTEGRACAO_SMS = "integracao_sms"
    INTEGRACAO_PAGAMENTO = "integracao_pagamento"
    INTEGRACAO_ESTOQUE = "integracao_estoque"
    
    # Eventos de Auditoria
    AUDITORIA_ACESSO = "auditoria_acesso"
    AUDITORIA_ALTERACAO = "auditoria_alteracao"
    AUDITORIA_EXCLUSAO = "auditoria_exclusao"
    AUDITORIA_EXPORTACAO = "auditoria_exportacao"
    AUDITORIA_IMPORTACAO = "auditoria_importacao"

@dataclass
class Event:
    id: str
    empresa_id: str
    event_type: EventType
    event_id: Optional[str]
    data: Dict[str, Any]
    event_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    processed: bool = False

class EventHandler(ABC):
    """Interface para handlers de eventos"""
    
    @abstractmethod
    async def handle(self, event: Event) -> None:
        """Processa um evento"""
        pass
    
    @abstractmethod
    def can_handle(self, event_type: EventType) -> bool:
        """Verifica se pode processar o tipo de evento"""
        pass

class EventBus:
    """Sistema de eventos local para processamento de notificações"""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._running = False
    
    async def initialize(self):
        """Inicializa o EventBus"""
        logger.info("EventBus inicializado")
    
    def subscribe(self, event_type: EventType, handler: EventHandler):
        """Registra um handler para um tipo de evento"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info(f"Handler registrado para evento: {event_type}")
    
    def unsubscribe(self, event_type: EventType, handler: EventHandler):
        """Remove um handler de um tipo de evento"""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.info(f"Handler removido para evento: {event_type}")
            except ValueError:
                logger.warning(f"Handler não encontrado para evento: {event_type}")
    
    async def publish(self, event: Event):
        """Publica um evento e processa localmente através dos handlers registrados"""
        try:
            logger.info(f"Publicando evento: {event.event_type} - {event.id}")
            # Processa o evento localmente através dos handlers
            await self._process_event(event)
            logger.info(f"Evento processado: {event.event_type} - {event.id}")
        except Exception as e:
            logger.error(f"Erro ao publicar evento {event.id}: {e}")
            # Não propaga o erro para não quebrar o fluxo principal
    
    async def start(self):
        """Inicia o processamento de eventos"""
        if self._running:
            return
        
        await self.initialize()
        self._running = True
        logger.info("EventBus iniciado")
    
    async def stop(self):
        """Para o processamento de eventos"""
        self._running = False
        logger.info("EventBus parado")
    
    async def _process_event(self, event: Event):
        """Processa um evento individual"""
        event_type = event.event_type
        
        if event_type not in self._handlers:
            logger.warning(f"Nenhum handler registrado para evento: {event_type}")
            return
        
        handlers = self._handlers[event_type]
        logger.info(f"Processando evento {event.id} com {len(handlers)} handlers")
        
        # Executa todos os handlers em paralelo
        tasks = []
        for handler in handlers:
            if handler.can_handle(event_type):
                task = asyncio.create_task(self._execute_handler(handler, event))
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_handler(self, handler: EventHandler, event: Event):
        """Executa um handler de forma segura"""
        try:
            await handler.handle(event)
            logger.info(f"Handler executado com sucesso para evento {event.id}")
        except Exception as e:
            logger.error(f"Erro no handler para evento {event.id}: {e}")

# Instância global do EventBus
event_bus = EventBus()
