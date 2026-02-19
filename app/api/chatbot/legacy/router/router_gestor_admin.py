"""
Router administrativo para controle do Gestor
Permite desligar e reiniciar o gestor via endpoints admin
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from app.database.db_connection import get_db
from app.api.cadastros.models.user_model import UserModel
from app.core.admin_dependencies import get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/gestor",
    tags=["Admin - Gestor (Controle)"]
)


class GestorStatusResponse(BaseModel):
    """Resposta com status do gestor"""
    status: str  # "ativo", "inativo", "reiniciando"
    mensagem: str
    timestamp: Optional[str] = None


class GestorControlRequest(BaseModel):
    """Request para controlar o gestor"""
    empresa_id: Optional[int] = None  # Opcional: controlar gestor de uma empresa específica


# Estado global do gestor (pode ser movido para banco de dados se necessário)
_gestor_status = {
    "ativo": True,
    "empresas": {}  # Status por empresa_id
}


@router.get("/status", response_model=GestorStatusResponse, status_code=status.HTTP_200_OK)
def obter_status_gestor(
    empresa_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Obtém o status atual do gestor.
    
    - Se empresa_id for fornecido, retorna status específico da empresa
    - Caso contrário, retorna status global
    """
    try:
        if empresa_id:
            status_empresa = _gestor_status["empresas"].get(empresa_id, "ativo")
            return GestorStatusResponse(
                status=status_empresa,
                mensagem=f"Status do gestor para empresa {empresa_id}: {status_empresa}",
                timestamp=None
            )
        else:
            status_global = "ativo" if _gestor_status["ativo"] else "inativo"
            return GestorStatusResponse(
                status=status_global,
                mensagem=f"Status global do gestor: {status_global}",
                timestamp=None
            )
    except Exception as e:
        logger.error(f"Erro ao obter status do gestor: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter status: {str(e)}"
        )


@router.post("/desligar", response_model=GestorStatusResponse, status_code=status.HTTP_200_OK)
def desligar_gestor(
    request: GestorControlRequest = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin),
):
    """
    Desliga o gestor.
    
    - Se empresa_id for fornecido, desliga apenas para aquela empresa
    - Caso contrário, desliga globalmente
    
    **Atenção**: Desligar o gestor pode afetar funcionalidades do sistema.
    """
    try:
        from datetime import datetime
        
        if request and request.empresa_id:
            # Desliga para empresa específica
            _gestor_status["empresas"][request.empresa_id] = "inativo"
            logger.info(f"[Gestor] Desligado para empresa {request.empresa_id} por usuário {current_user.id}")
            
            # TODO: Implementar lógica específica de desligamento por empresa
            # Exemplo: parar processamento de pedidos, notificações, etc. para aquela empresa
            
            return GestorStatusResponse(
                status="inativo",
                mensagem=f"Gestor desligado para empresa {request.empresa_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            # Desliga globalmente
            _gestor_status["ativo"] = False
            logger.warning(f"[Gestor] Desligado GLOBALMENTE por usuário {current_user.id}")
            
            # TODO: Implementar lógica de desligamento global
            # Exemplo: parar EventBus, notificações, processamento de pedidos, etc.
            # await event_bus.stop()
            # await notification_system.shutdown()
            
            return GestorStatusResponse(
                status="inativo",
                mensagem="Gestor desligado globalmente",
                timestamp=datetime.now().isoformat()
            )
    except Exception as e:
        logger.error(f"Erro ao desligar gestor: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao desligar gestor: {str(e)}"
        )


@router.post("/reiniciar", response_model=GestorStatusResponse, status_code=status.HTTP_200_OK)
def reiniciar_gestor(
    request: GestorControlRequest = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin),
):
    """
    Reinicia o gestor.
    
    - Se empresa_id for fornecido, reinicia apenas para aquela empresa
    - Caso contrário, reinicia globalmente
    
    **Atenção**: Reiniciar o gestor pode interromper operações em andamento.
    """
    try:
        from datetime import datetime
        
        if request and request.empresa_id:
            # Reinicia para empresa específica
            _gestor_status["empresas"][request.empresa_id] = "reiniciando"
            logger.info(f"[Gestor] Reiniciando para empresa {request.empresa_id} por usuário {current_user.id}")
            
            # TODO: Implementar lógica específica de reinício por empresa
            # 1. Parar processamento para a empresa
            # 2. Limpar estado/cache se necessário
            # 3. Reiniciar serviços para a empresa
            
            _gestor_status["empresas"][request.empresa_id] = "ativo"
            
            return GestorStatusResponse(
                status="ativo",
                mensagem=f"Gestor reiniciado para empresa {request.empresa_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            # Reinicia globalmente
            _gestor_status["ativo"] = False
            logger.warning(f"[Gestor] Reiniciando GLOBALMENTE por usuário {current_user.id}")
            
            # TODO: Implementar lógica de reinício global
            # 1. Parar serviços
            # await event_bus.stop()
            # await notification_system.shutdown()
            
            # 2. Limpar estado/cache se necessário
            # _gestor_status["empresas"].clear()
            
            # 3. Reiniciar serviços
            # await event_bus.start()
            # await notification_system.initialize()
            
            _gestor_status["ativo"] = True
            
            return GestorStatusResponse(
                status="ativo",
                mensagem="Gestor reiniciado globalmente",
                timestamp=datetime.now().isoformat()
            )
    except Exception as e:
        logger.error(f"Erro ao reiniciar gestor: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao reiniciar gestor: {str(e)}"
        )


@router.post("/ligar", response_model=GestorStatusResponse, status_code=status.HTTP_200_OK)
def ligar_gestor(
    request: GestorControlRequest = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin),
):
    """
    Liga o gestor (se estiver desligado).
    
    - Se empresa_id for fornecido, liga apenas para aquela empresa
    - Caso contrário, liga globalmente
    """
    try:
        from datetime import datetime
        
        if request and request.empresa_id:
            # Liga para empresa específica
            _gestor_status["empresas"][request.empresa_id] = "ativo"
            logger.info(f"[Gestor] Ligado para empresa {request.empresa_id} por usuário {current_user.id}")
            
            # TODO: Implementar lógica específica de ligamento por empresa
            
            return GestorStatusResponse(
                status="ativo",
                mensagem=f"Gestor ligado para empresa {request.empresa_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            # Liga globalmente
            _gestor_status["ativo"] = True
            logger.info(f"[Gestor] Ligado GLOBALMENTE por usuário {current_user.id}")
            
            # TODO: Implementar lógica de ligamento global
            # await event_bus.start()
            # await notification_system.initialize()
            
            return GestorStatusResponse(
                status="ativo",
                mensagem="Gestor ligado globalmente",
                timestamp=datetime.now().isoformat()
            )
    except Exception as e:
        logger.error(f"Erro ao ligar gestor: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao ligar gestor: {str(e)}"
        )
