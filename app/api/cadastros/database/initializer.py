"""
Inicializador do domínio Cadastros.
Responsável por criar tabelas e dados iniciais do domínio.
"""
import logging
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.database.domain.base import DomainInitializer
from app.database.domain.registry import register_domain
from app.database.db_connection import SessionLocal
from app.core.security import hash_password

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
from app.api.catalogo.models.model_adicional import AdicionalModel
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
        self._criar_usuario_admin_padrao()
    
    def _criar_usuario_admin_padrao(self) -> None:
        """Cria o usuário 'admin' com senha padrão caso não exista."""
        try:
            with SessionLocal() as session:
                stmt = (
                    insert(UserModel)
                    .values(
                        username="super",
                        hashed_password=hash_password("171717"),
                        type_user="admin",
                    )
                    .on_conflict_do_nothing(index_elements=[UserModel.username])
                )
                result = session.execute(stmt)
                session.commit()
                if hasattr(result, "rowcount") and result.rowcount == 0:
                    logger.info("  ℹ️ Usuário admin já existe. Pulando criação.")
                else:
                    logger.info("  ✅ Usuário admin criado com sucesso (senha padrão: 171717).")
        except IntegrityError:
            # Em caso de corrida entre múltiplos processos
            try:
                session.rollback()
            except Exception:
                pass
            logger.info("  ℹ️ Usuário admin já existe (detectado por integridade).")
        except Exception as e:
            logger.error(f"  ❌ Erro ao criar usuário admin: {e}", exc_info=True)


# Cria e registra a instância do inicializador
_cadastros_initializer = CadastrosInitializer()
register_domain(_cadastros_initializer)

