"""
Compat layer para manter imports antigos.

Historicamente `CategoriaDeliveryRepository` ficava neste pacote, mas
foi movido para `app.api.cardapio.repositories.repo_categoria`. Para não
quebrar imports existentes (`app.api.cadastros.repositories.repo_categoria`)
reexportamos a classe daqui.
"""

from app.api.cardapio.repositories.repo_categoria import CategoriaDeliveryRepository  # noqa: F401

__all__ = ["CategoriaDeliveryRepository"]

