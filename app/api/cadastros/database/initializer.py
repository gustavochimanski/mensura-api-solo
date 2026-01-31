"""
Inicializador do domínio Cadastros.
Responsável por criar tabelas e dados iniciais do domínio.
"""
import logging

from app.database.domain.base import DomainInitializer
from app.database.domain.registry import register_domain

# Importar models do domínio
from app.api.empresas.models.empresa_model import EmpresaModel
from app.api.cadastros.models.user_model import UserModel
from app.api.cadastros.models.categoria_model import CategoriaModel
from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.catalogo.models.model_combo import ComboModel
from app.api.cadastros.models.model_cupom import CupomDescontoModel
from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.api.cadastros.models.model_endereco_dv import EnderecoModel
from app.api.cadastros.models.model_entregador_dv import EntregadorDeliveryModel
from app.api.cadastros.models.model_meio_pagamento import MeioPagamentoModel
from app.api.cadastros.models.model_parceiros import ParceiroModel, BannerParceiroModel
from app.api.cadastros.models.model_regiao_entrega import RegiaoEntregaModel
# AdicionalModel removido - tabela adicionais não é mais usada
# Adicionais agora são vínculos de produtos/receitas/combos em complementos (complemento_vinculo_item)
from app.api.cadastros.models.association_tables import (
    VitrineComboLink,
    VitrineReceitaLink
)

logger = logging.getLogger(__name__)


class CadastrosInitializer(DomainInitializer):
    """Inicializador do domínio Cadastros."""
    
    def get_domain_name(self) -> str:
        return "cadastros"
    
    def get_schema_name(self) -> str:
        return "cadastros"
    
    def initialize_data(self) -> None:
        """Popula dados iniciais do domínio Cadastros."""
        # Não cria mais usuário `super`/`admin` automaticamente.
        return


# Cria e registra a instância do inicializador
_cadastros_initializer = CadastrosInitializer()
register_domain(_cadastros_initializer)

