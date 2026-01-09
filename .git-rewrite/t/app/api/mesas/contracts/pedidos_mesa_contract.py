from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel


class ClienteMinDTO(BaseModel):
    id: Optional[int] = None
    nome: Optional[str] = None


class MesaPedidoDTO(BaseModel):
    id: int
    empresa_id: int
    cliente: Optional[ClienteMinDTO] = None
    valor_total: Decimal | float
    created_at: datetime
    updated_at: Optional[datetime] = None
    status: str
    observacoes: Optional[str] = None
    mesa_numero: Optional[str] = None


class IMesaPedidosContract(ABC):
    @abstractmethod
    def listar_abertos(self, *, empresa_id: int) -> List[MesaPedidoDTO]:
        raise NotImplementedError

    @abstractmethod
    def listar_finalizados(self, *, empresa_id: int, date_filter: date) -> List[MesaPedidoDTO]:
        raise NotImplementedError

    @abstractmethod
    def listar_pendentes_impressao(self, *, empresa_id: int) -> List[MesaPedidoDTO]:
        """Retorna pedidos com status 'I' (Impressão)"""
        raise NotImplementedError


