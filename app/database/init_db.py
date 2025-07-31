import logging
from sqlalchemy import text, quoted_name
from .db_connection import engine, Base

logger = logging.getLogger(__name__)
SCHEMAS = ["mensura", "bi", "delivery"]

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
    # ─── Models de Mensura ────────────────────────────────────────────
    import app.api.mensura.models.user_model
    import app.api.mensura.models.endereco_model
    import app.api.mensura.models.empresa_model
    import app.api.mensura.models.association_tables

    # ─── Models de Delivery ───────────────────────────────────────────
    import app.api.delivery.models.cadprod_dv_model
    import app.api.delivery.models.cadprod_emp_dv_model
    import app.api.delivery.models.categoria_dv_model
    import app.api.delivery.models.cliente_dv_model
    import app.api.delivery.models.endereco_dv_model
    import app.api.delivery.models.entregador_dv_model
    import app.api.delivery.models.pedido_item_dv_model
    import app.api.delivery.models.pedido_dv_model
    import app.api.delivery.models.vitrine_dv_model

def criar_tabelas():
    try:
        importar_models()  # importa só os seus models de mensura e delivery

        # pega todas as Table objects que o Base conhece
        all_tables = list(Base.metadata.tables.values())

        # filtra pelas tabelas que pertencem aos schemas que você gerencia
        tables_para_criar = [
            t
            for t in all_tables
            if t.schema in SCHEMAS
        ]

        # cria apenas essas tabelas
        Base.metadata.create_all(
            bind=engine,
            tables=tables_para_criar
        )

        logger.info("✅ Tabelas criadas com sucesso (somente nos schemas da aplicação).")
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas: {e}", exc_info=True)

def inicializar_banco():
    logger.info("🔹 Criando schemas...")
    criar_schemas()
    logger.info("🔹 Criando tabelas...")
    criar_tabelas()
    logger.info("✅ Banco inicializado com sucesso.")

