import logging
from sqlalchemy import text
from .db_connection import engine, Base

logger = logging.getLogger(__name__)
SCHEMAS = ["mensura", "bi", "pdv"]

def criar_schemas():
    try:
        with engine.begin() as conn:
            for schema in SCHEMAS:
                logger.info(f"🛠️ Criando/verificando schema: {schema}")
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        logger.info("✅ Todos os schemas verificados/criados.")
    except Exception as e:
        logger.error(f"❌ Erro ao criar schemas: {e}")

def criar_tabelas():
    try:
        # ✅ IMPORTAÇÃO EXPLÍCITA DOS MODELS
        from app.api.mensura.models.empresas_model import EmpresaModel
        from app.api.mensura.models.user_model import UserModel
        from app.api.mensura.models.endereco_model import EnderecoModel
        from app.api.mensura.models.cad_categoria_delivery_model import CategoriaDeliveryModel
        from app.api.mensura.models.vitrines_model import VitrinesModel
        from app.api.mensura.models.cad_prod_delivery_model import ProdutoDeliveryModel
        from app.api.mensura.models.cad_prod_emp_delivery_model import ProdutosEmpDeliveryModel

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

