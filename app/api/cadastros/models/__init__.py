"""
Models de Cadastros
Centraliza todos os models relacionados a entidades de cadastro
"""

# Importar todos os models para garantir registro no SQLAlchemy
# ProdutoModel, ProdutoEmpModel, ComboModel, ComboItemModel e AdicionalModel agora estão no módulo catalogo
from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.catalogo.models.model_combo import ComboModel, ComboItemModel
from app.api.catalogo.models.model_adicional import AdicionalModel
from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.api.cardapio.models.model_categoria_dv import CategoriaDeliveryModel
from app.api.cadastros.models.model_meio_pagamento import MeioPagamentoModel
from app.api.cadastros.models.model_parceiros import ParceiroModel, BannerParceiroModel
from app.api.cardapio.models.model_vitrine import VitrinesModel
from app.api.cadastros.models.association_tables import (
    VitrineCategoriaLink,
    VitrineProdutoLink,
)
# Importa produto_adicional_link do módulo catalogo (definido lá)
from app.api.catalogo.models.association_tables import produto_adicional_link
