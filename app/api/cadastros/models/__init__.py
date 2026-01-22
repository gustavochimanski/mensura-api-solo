"""
Models de Cadastros
Centraliza todos os models relacionados a entidades de cadastro
"""

# Importar todos os models para garantir registro no SQLAlchemy
# ProdutoModel, ProdutoEmpModel, ComboModel, ComboItemModel agora estão no módulo catalogo
# AdicionalModel removido - tabela adicionais não é mais usada
# Adicionais agora são vínculos de produtos/receitas/combos em complementos (complemento_vinculo_item)
from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.catalogo.models.model_combo import ComboModel, ComboItemModel
from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.api.cardapio.models.model_categoria_dv import CategoriaDeliveryModel
from app.api.cadastros.models.model_meio_pagamento import MeioPagamentoModel
from app.api.cadastros.models.model_parceiros import ParceiroModel, BannerParceiroModel
from app.api.cardapio.models.model_vitrine import VitrinesModel
from app.api.cadastros.models.association_tables import (
    VitrineCategoriaLink,
    VitrineProdutoLink,
)
# Nota: produto_adicional_link foi removido - adicionais agora são vínculos de produtos/receitas/combos em complementos
