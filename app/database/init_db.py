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

def criar_tabelas_criticas():
    """Cria tabelas críticas que são dependências de outras tabelas"""
    try:
        # Cria mensura.enderecos primeiro (dependência de empresas)
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS mensura.enderecos (
                    id SERIAL PRIMARY KEY,
                    logradouro VARCHAR(255) NOT NULL,
                    numero VARCHAR(20),
                    complemento VARCHAR(100),
                    bairro VARCHAR(100) NOT NULL,
                    cidade VARCHAR(100) NOT NULL,
                    uf VARCHAR(2) NOT NULL,
                    cep VARCHAR(9),
                    latitude NUMERIC(10, 6),
                    longitude NUMERIC(10, 6),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
                );
            """))
            conn.commit()
            logger.info("✅ Tabela mensura.enderecos criada/verificada com sucesso")
            
        # Cria mensura.cadprod (dependência de cadprod_emp)
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS mensura.cadprod (
                    cod_barras VARCHAR PRIMARY KEY,
                    descricao VARCHAR(255) NOT NULL,
                    imagem VARCHAR(255),
                    data_cadastro DATE,
                    cod_categoria INTEGER,
                    ativo BOOLEAN NOT NULL DEFAULT TRUE,
                    unidade_medida VARCHAR(10),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
                );
            """))
            conn.commit()
            logger.info("✅ Tabela mensura.cadprod criada/verificada com sucesso")
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas críticas: {e}")

def criar_tabelas():
    try:
        # Primeiro cria tabelas críticas
        logger.info("🔧 Criando tabelas críticas...")
        criar_tabelas_criticas()
        
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

        # Ordenação simples: cria tabelas na ordem que aparecem nos models
        # O SQLAlchemy já resolve as dependências automaticamente
        ordered_tables = tables_para_criar

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
                elif "does not exist" in str(table_error):
                    # Se a tabela referenciada não existe, tenta criar novamente no final
                    logger.warning(f"⚠️ Tabela {table.schema}.{table.name} falhou por dependência. Tentando novamente...")
                    try:
                        table.create(engine, checkfirst=True)
                        logger.info(f"✅ Tabela {table.schema}.{table.name} criada com sucesso na segunda tentativa")
                    except Exception as retry_error:
                        logger.error(f"❌ Erro persistente ao criar tabela {table.schema}.{table.name}: {retry_error}")
                else:
                    logger.error(f"❌ Erro ao criar tabela {table.schema}.{table.name}: {table_error}")
                # Continua com as próximas tabelas mesmo se uma falhar

        # Segunda passada para tabelas que falharam por dependências
        logger.info("🔄 Segunda passada para tabelas com dependências...")
        for table in ordered_tables:
            try:
                # Verifica se a tabela já existe
                with engine.connect() as conn:
                    result = conn.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = '{table.schema}' 
                            AND table_name = '{table.name}'
                        );
                    """))
                    exists = result.scalar()
                    
                if not exists:
                    table.create(engine, checkfirst=True)
                    logger.info(f"✅ Tabela {table.schema}.{table.name} criada na segunda passada")
            except Exception as second_pass_error:
                if "already exists" not in str(second_pass_error):
                    logger.error(f"❌ Erro na segunda passada para {table.schema}.{table.name}: {second_pass_error}")

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

