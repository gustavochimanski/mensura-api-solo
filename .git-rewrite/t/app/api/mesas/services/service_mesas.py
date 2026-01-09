from __future__ import annotations
from typing import Optional, List
from sqlalchemy.orm import Session

from app.api.mesas.repositories.repo_mesas import MesaRepository
from app.api.mesas.schemas.schema_mesa import MesaIn, MesaUpdate, StatusMesaEnum
from app.api.mesas.models.model_mesa import StatusMesa
from app.utils.logger import logger


class MesaService:
    def __init__(self, db: Session):
        self.repo = MesaRepository(db)

    def create(self, data: MesaIn):
        """Cria uma nova mesa"""
        logger.info(f"[MesaService] Criando mesa - codigo={data.codigo}, capacidade={data.capacidade}")
        return self.repo.create(data)

    def get_by_id(self, mesa_id: int, *, empresa_id: Optional[int] = None):
        """Busca mesa por ID"""
        logger.info(f"[MesaService] Buscando mesa por ID - id={mesa_id}")
        return self.repo.get_by_id(mesa_id, empresa_id=empresa_id)

    def get_by_numero(self, numero: str, *, empresa_id: Optional[int] = None):
        """Busca mesa por número"""
        logger.info(f"[MesaService] Buscando mesa por número - numero={numero}")
        return self.repo.get_by_numero(numero, empresa_id=empresa_id)

    def list_all(self, ativa: Optional[bool] = None, *, empresa_id: Optional[int] = None):
        """Lista todas as mesas"""
        logger.info(f"[MesaService] Listando mesas - ativa={ativa}")
        return self.repo.list_all(empresa_id=empresa_id, ativa=ativa)

    def list_by_status(self, status: StatusMesa, *, empresa_id: Optional[int] = None):
        """Lista mesas por status"""
        logger.info(f"[MesaService] Listando mesas por status - status={status}")
        return self.repo.list_by_status(status, empresa_id=empresa_id)

    def update(self, mesa_id: int, data: MesaUpdate, *, empresa_id: Optional[int] = None):
        """Atualiza uma mesa"""
        logger.info(f"[MesaService] Atualizando mesa - id={mesa_id}")
        
        # Converte dados para dict, removendo campos None
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        
        return self.repo.update(mesa_id, update_data, empresa_id=empresa_id)

    def update_status(self, mesa_id: int, status: StatusMesaEnum, *, empresa_id: Optional[int] = None):
        """Atualiza apenas o status da mesa"""
        logger.info(f"[MesaService] Atualizando status da mesa - id={mesa_id}, status={status}")
        
        # Converte StatusMesaEnum para StatusMesa
        status_mesa = StatusMesa(status.value)
        return self.repo.update_status(mesa_id, status_mesa, empresa_id=empresa_id)

    def delete(self, mesa_id: int, *, empresa_id: Optional[int] = None):
        """Deleta uma mesa"""
        logger.info(f"[MesaService] Deletando mesa - id={mesa_id}")
        return self.repo.delete(mesa_id, empresa_id=empresa_id)

    def search(
        self, 
        q: Optional[str] = None, 
        ativa: Optional[bool] = None,
        limit: int = 30, 
        offset: int = 0,
        *,
        empresa_id: Optional[int] = None,
    ):
        """Busca mesas com filtros"""
        logger.info(f"[MesaService] Buscando mesas - q={q}, ativa={ativa}")
        return self.repo.search(q, None, ativa, limit, offset, empresa_id=empresa_id)

    def get_stats(self, *, empresa_id: Optional[int] = None):
        """Retorna estatísticas das mesas"""
        logger.info(f"[MesaService] Obtendo estatísticas das mesas")
        return self.repo.get_stats(empresa_id=empresa_id)

    # -------- OPERAÇÕES DE STATUS --------
    def liberar_mesa(self, mesa_id: int, *, empresa_id: Optional[int] = None):
        """Libera uma mesa"""
        logger.info(f"[MesaService] Liberando mesa - id={mesa_id}")
        return self.repo.liberar_mesa(mesa_id, empresa_id=empresa_id)

    def ocupar_mesa(self, mesa_id: int, *, empresa_id: Optional[int] = None):
        """Ocupa uma mesa"""
        logger.info(f"[MesaService] Ocupando mesa - id={mesa_id}")
        return self.repo.ocupar_mesa(mesa_id, empresa_id=empresa_id)

    def reservar_mesa(self, mesa_id: int, *, empresa_id: Optional[int] = None):
        """Reserva uma mesa"""
        logger.info(f"[MesaService] Reservando mesa - id={mesa_id}")
        return self.repo.reservar_mesa(mesa_id, empresa_id=empresa_id)


    # -------- VALIDAÇÕES --------
    def validar_mesa_disponivel(self, mesa_id: int, *, empresa_id: Optional[int] = None) -> bool:
        """Valida se a mesa está disponível para ocupação"""
        mesa = self.get_by_id(mesa_id, empresa_id=empresa_id)
        return mesa.is_disponivel and mesa.ativa == "S"

    def validar_mesa_ocupavel(self, mesa_id: int, *, empresa_id: Optional[int] = None) -> bool:
        """Valida se a mesa pode ser ocupada (disponível)"""
        mesa = self.get_by_id(mesa_id, empresa_id=empresa_id)
        return mesa.is_disponivel and mesa.ativa == "S"

    def validar_mesa_reservavel(self, mesa_id: int, *, empresa_id: Optional[int] = None) -> bool:
        """Valida se a mesa pode ser reservada (disponível)"""
        mesa = self.get_by_id(mesa_id, empresa_id=empresa_id)
        return mesa.is_disponivel and mesa.ativa == "S"

    # -------- OPERAÇÕES COM VALIDAÇÃO --------
    def ocupar_mesa_se_disponivel(self, mesa_id: int, *, empresa_id: Optional[int] = None):
        """Ocupa mesa apenas se estiver disponível"""
        if not self.validar_mesa_ocupavel(mesa_id, empresa_id=empresa_id):
            raise ValueError("Mesa não está disponível para ocupação")
        return self.ocupar_mesa(mesa_id, empresa_id=empresa_id)

    def reservar_mesa_se_disponivel(self, mesa_id: int, *, empresa_id: Optional[int] = None):
        """Reserva mesa apenas se estiver disponível"""
        if not self.validar_mesa_reservavel(mesa_id, empresa_id=empresa_id):
            raise ValueError("Mesa não está disponível para reserva")
        return self.reservar_mesa(mesa_id, empresa_id=empresa_id)

    def liberar_mesa_se_ocupada(self, mesa_id: int, *, empresa_id: Optional[int] = None):
        """Libera mesa apenas se estiver ocupada"""
        mesa = self.get_by_id(mesa_id, empresa_id=empresa_id)
        if not mesa.is_ocupada:
            raise ValueError("Mesa não está ocupada")
        return self.liberar_mesa(mesa_id, empresa_id=empresa_id)
    
    def get_historico(self, mesa_id: int, limit: int = 50, *, empresa_id: Optional[int] = None):
        """Retorna o histórico de uma mesa"""
        logger.info(f"[MesaService] Obtendo histórico da mesa - id={mesa_id}, limit={limit}")
        return self.repo.get_historico(mesa_id, limit, empresa_id=empresa_id)
    
    def associar_cliente(self, mesa_id: int, cliente_id: int, *, empresa_id: Optional[int] = None):
        """Associa um cliente à mesa"""
        logger.info(f"[MesaService] Associando cliente à mesa - mesa_id={mesa_id}, cliente_id={cliente_id}")
        return self.repo.associar_cliente(mesa_id, cliente_id, empresa_id=empresa_id)
    
    def desassociar_cliente(self, mesa_id: int, *, empresa_id: Optional[int] = None):
        """Desassocia o cliente da mesa"""
        logger.info(f"[MesaService] Desassociando cliente da mesa - mesa_id={mesa_id}")
        return self.repo.desassociar_cliente(mesa_id, empresa_id=empresa_id)
