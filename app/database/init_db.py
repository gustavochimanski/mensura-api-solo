import logging
from sqlalchemy import text, quoted_name
from .db_connection import engine, Base

logger = logging.getLogger(__name__)
SCHEMAS = ["mensura", "bi", "pdv", "delivery"]

def criar_schemas():
    try:
        with engine.begin() as conn:
            for schema in SCHEMAS:
                logger.info(f"🛠️ Criando/verificando schema: {schema}")
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {quoted_name(schema, quote=True)}'))
        logger.info("✅ Todos os schemas verificados/criados.")
    except Exception as e:
        logger.error(f"❌ Erro ao criar schemas: {e}")


def importar_models():
    from app.api.mensura.models.empresas_model import EmpresaModel
    from app.api.mensura.models.enderecos_model import EnderecoModel
    from app.api.mensura.models.cadprod_emp_dv_model import ProdutosEmpDeliveryModel
    from app.api.mensura.models.cadprod_dv_model import ProdutoDeliveryModel
    from app.api.mensura.models.user_model import UserModel
    from app.api.mensura.models.categoria_dv_model import CategoriaDeliveryModel
    from app.api.mensura.models.vitrines_dv_model import VitrinesModel
    from app.api.mensura.models.pedido_itens_dv_model import PedidoItemModel
    from app.api.mensura.models.pedidos_dv_model import PedidoDeliveryModel
    from app.api.mensura.models.clientes_dv_model import ClienteDeliveryModel

def criar_tabelas():
    try:
        importar_models()
        # Agora o SQLAlchemy sabe de todas as tabelas
        Base.metadata.create_all(bind=engine)

        logger.info("✅ Tabelas criadas com sucesso.")
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas: {e}")

def inicializar_banco():
    logger.info("🔹 Criando schemas...")
    criar_schemas()
    logger.info("🔹 Criando tabelas...")
    criar_tabelas()
    logger.info("✅ Banco inicializado com sucesso.")

