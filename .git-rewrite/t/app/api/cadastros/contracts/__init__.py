"""Contratos (interfaces + DTOs) expostos pelo contexto de Cadastros."""

# Nota: Produto, Combo e Adicional contracts estão no módulo catalogo
# Importe diretamente de app.api.catalogo.contracts se necessário

from .cliente_contract import (
    IClienteContract,
    ClienteDTO,
    EnderecoDTO,
)
from .entregador_contract import (
    IEntregadorContract,
    EntregadorDTO,
)
from .regiao_entrega_contract import (
    IRegiaoEntregaContract,
    RegiaoEntregaDTO,
)

__all__ = [
    # Cliente
    "IClienteContract",
    "ClienteDTO",
    "EnderecoDTO",
    # Entregador
    "IEntregadorContract",
    "EntregadorDTO",
    # Região de entrega
    "IRegiaoEntregaContract",
    "RegiaoEntregaDTO",
]


