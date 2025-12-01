"""
Repositories de Cadastros
Centraliza todos os repositories relacionados a entidades de cadastro
"""

from app.api.cadastros.repositories.repo_cliente import ClienteRepository
# CategoriaDeliveryRepository está em cardapio, mas mantemos compat layer em repo_categoria.py
from app.api.cadastros.repositories.repo_meio_pagamento import MeioPagamentoRepository
from app.api.cadastros.repositories.repo_parceiros import ParceirosRepository
