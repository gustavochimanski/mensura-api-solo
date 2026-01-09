"""Compatibilidade para CategoriasService (cardápio).

Este módulo existe apenas para manter os imports antigos de
`app.api.cadastros.services.service_categoria`. A implementação real
permanece em `app.api.cardapio.services.service_categoria_dv`.
"""

from app.api.cardapio.services.service_categoria_dv import CategoriasService  # noqa: F401

__all__ = ["CategoriasService"]
