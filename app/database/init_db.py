import logging
from sqlalchemy import text, quoted_name
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from .db_connection import engine, Base, SessionLocal
from app.core.security import hash_password
from app.api.mensura.models.user_model import UserModel

logger = logging.getLogger(__name__)
SCHEMAS = ["mensura", "bi", "delivery", "pdv"]

def ensure_unaccent():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent;"))
        conn.commit()
        logger.info("unaccent instalado com sucesso")

def ensure_postgis():
    try:
        with engine.connect() as conn:
            # Verifica se a extensão PostGIS está disponível
            result = conn.execute(text("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_available_extensions 
                    WHERE name = 'postgis'
                );
            """))
            is_available = result.scalar()
            
            if is_available:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                conn.commit()
                logger.info("PostGIS instalado com sucesso")
            else:
                logger.warning("PostGIS não está disponível no servidor PostgreSQL. Pulando instalação.")
    except Exception as e:
        logger.warning(f"Erro ao instalar PostGIS: {e}. Continuando sem PostGIS.")

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
    # ─── Models Mensura ────────────────────────────────────────────
    from app.api.mensura.models.empresa_model import EmpresaModel
    from app.api.mensura.models.user_model import UserModel
    from app.api.mensura.models.endereco_model import EnderecoModel
    from app.api.mensura.models.cadprod_emp_model import ProdutoEmpModel
    from app.api.mensura.models.cadprod_model import ProdutoModel
    # ─── Models Delivery ───────────────────────────────────────────
    from app.api.delivery.models.model_transacao_pagamento_dv import TransacaoPagamentoModel
    from app.api.delivery.models.model_pedido_dv import PedidoDeliveryModel
    from app.api.delivery.models.model_pedido_item_dv import PedidoItemModel
    from app.api.delivery.models.model_pedido_status_historico_dv import PedidoStatusHistoricoModel
    from app.api.delivery.models.model_cupom_dv import CupomDescontoModel
    from app.api.delivery.models.model_cliente_dv import ClienteDeliveryModel
    from app.api.delivery.models.model_endereco_dv import EnderecoDeliveryModel
    from app.api.delivery.models.model_categoria_dv import CategoriaDeliveryModel
    from app.api.delivery.models.model_vitrine_dv import VitrinesModel
    from app.api.delivery.models.model_entregador_dv import EntregadorDeliveryModel
    from app.api.delivery.models.model_meio_pagamento_dv import MeioPagamentoModel
    from app.api.delivery.models.model_cliente_codigo_validacao import ClienteOtpModel
    from app.api.delivery.models.model_parceiros_dv import BannerParceiroModel, ParceiroModel
    from app.api.delivery.models.model_regiao_entrega import RegiaoEntregaModel

    logger.info("📦 Models importados com sucesso.")

def criar_tabelas():
    try:
        importar_models()  # importa só os seus models de mensura e delivery

        # pega todas as Table objects que o Base conhece
        all_tables = list(Base.metadata.tables.values())
        logger.info(f"📊 Total de tabelas encontradas: {len(all_tables)}")

        # filtra pelas tabelas que pertencem aos schemas que você gerencia
        tables_para_criar = [
            t
            for t in all_tables
            if t.schema in SCHEMAS
        ]
        
        logger.info(f"📋 Tabelas para criar nos schemas {SCHEMAS}:")
        for table in tables_para_criar:
            logger.info(f"  - {table.schema}.{table.name}")

        # Ordena as tabelas por dependências (tabelas sem FK primeiro)
        def get_table_dependencies(table):
            dependencies = set()
            for fk in table.foreign_keys:
                if fk.column.table.schema in SCHEMAS:
                    dependencies.add(fk.column.table)
            return dependencies

        # Ordenação topológica das tabelas
        ordered_tables = []
        remaining_tables = set(tables_para_criar)
        
        while remaining_tables:
            # Encontra tabelas sem dependências pendentes
            ready_tables = []
            for table in remaining_tables:
                deps = get_table_dependencies(table)
                if deps.issubset(set(ordered_tables)):
                    ready_tables.append(table)
            
            if not ready_tables:
                # Se não há tabelas prontas, adiciona as restantes (pode haver dependências circulares)
                ready_tables = list(remaining_tables)
            
            for table in ready_tables:
                ordered_tables.append(table)
                remaining_tables.remove(table)

        logger.info("🔧 Criando tabelas na ordem correta:")
        for table in ordered_tables:
            logger.info(f"  - {table.schema}.{table.name}")

        # Cria as tabelas na ordem correta
        for table in ordered_tables:
            try:
                table.create(engine, checkfirst=True)
                logger.info(f"✅ Tabela {table.schema}.{table.name} criada com sucesso")
            except Exception as table_error:
                # Se for erro de duplicação, apenas avisa (não é crítico)
                if "duplicate key value violates unique constraint" in str(table_error) or "already exists" in str(table_error):
                    logger.info(f"ℹ️ Tabela {table.schema}.{table.name} já existe (pulando)")
                else:
                    logger.error(f"❌ Erro ao criar tabela {table.schema}.{table.name}: {table_error}")
                # Continua com as próximas tabelas mesmo se uma falhar

        logger.info("✅ Processo de criação de tabelas concluído.")
    except Exception as e:
        logger.error(f"❌ Erro geral ao criar tabelas: {e}", exc_info=True)

def criar_usuario_admin_padrao():
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
                logger.info("🔹 Usuário admin já existe. Pulando criação.")
            else:
                logger.info("✅ Usuário admin criado com sucesso (senha padrão: 123456).")
    except IntegrityError:
        # Em caso de corrida entre múltiplos processos
        try:
            session.rollback()
        except Exception:
            pass
        logger.info("🔹 Usuário admin já existe (detectado por integridade).")
    except Exception as e:
        logger.error(f"❌ Erro ao criar usuário admin: {e}", exc_info=True)

def inicializar_banco():
    logger.info("🔹 Instalando extensões...")
    ensure_unaccent()
    ensure_postgis()
    logger.info("🔹 Criando schemas...")
    criar_schemas()
    logger.info("🔹 Criando tabelas...")
    criar_tabelas()
    logger.info("🔹 Garantindo usuário admin padrão...")
    criar_usuario_admin_padrao()
    logger.info("✅ Banco inicializado com sucesso.")

