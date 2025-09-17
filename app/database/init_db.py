import logging
import time
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

def verificar_banco_inicializado():
    """Verifica se o banco já foi inicializado consultando uma tabela de controle"""
    try:
        with engine.connect() as conn:
            # Verifica se existe a tabela de controle
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'db_initialization_status'
                );
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                return False
                
            # Verifica se está marcado como inicializado
            result = conn.execute(text("""
                SELECT initialized FROM public.db_initialization_status 
                WHERE id = 1;
            """))
            status = result.scalar()
            return status is True
            
    except Exception as e:
        logger.warning(f"⚠️ Erro ao verificar status de inicialização: {e}")
        return False

def marcar_banco_inicializado():
    """Marca o banco como inicializado"""
    try:
        with engine.begin() as conn:
            # Cria a tabela de controle se não existir
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.db_initialization_status (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    initialized BOOLEAN NOT NULL DEFAULT FALSE,
                    initialized_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """))
            
            # Marca como inicializado
            conn.execute(text("""
                INSERT INTO public.db_initialization_status (id, initialized) 
                VALUES (1, TRUE) 
                ON CONFLICT (id) 
                DO UPDATE SET 
                    initialized = TRUE, 
                    initialized_at = NOW();
            """))
            
    except Exception as e:
        logger.error(f"❌ Erro ao marcar banco como inicializado: {e}")

def criar_schemas():
    try:
        with engine.begin() as conn:
            for schema in SCHEMAS:
                logger.info(f"🛠️ Criando/verificando schema: {schema}")
                try:
                    conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {quoted_name(schema, quote=True)}'))
                except Exception as schema_error:
                    # Se for erro de schema já existente, apenas avisa (não é crítico)
                    if "already exists" in str(schema_error) or "duplicate key value violates unique constraint" in str(schema_error):
                        logger.info(f"ℹ️ Schema {schema} já existe (pulando)")
                    else:
                        logger.error(f"❌ Erro ao criar schema {schema}: {schema_error}")
                        raise schema_error
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
                # Verifica se a tabela referenciada está nos schemas gerenciados
                if fk.column.table.schema in SCHEMAS:
                    dependencies.add(fk.column.table)
            return dependencies

        # Ordenação topológica das tabelas com retry para dependências circulares
        ordered_tables = []
        remaining_tables = set(tables_para_criar)
        max_attempts = len(tables_para_criar) * 2  # Evita loop infinito
        attempts = 0
        
        while remaining_tables and attempts < max_attempts:
            attempts += 1
            # Encontra tabelas sem dependências pendentes
            ready_tables = []
            for table in remaining_tables:
                deps = get_table_dependencies(table)
                # Verifica se todas as dependências já foram criadas
                if deps.issubset(set(ordered_tables)):
                    ready_tables.append(table)
            
            if not ready_tables:
                # Se não há tabelas prontas, tenta criar as restantes (pode haver dependências circulares)
                logger.warning(f"⚠️ Nenhuma tabela pronta na tentativa {attempts}. Tentando criar as restantes...")
                ready_tables = list(remaining_tables)
            
            for table in ready_tables:
                ordered_tables.append(table)
                remaining_tables.remove(table)

        if remaining_tables:
            logger.warning(f"⚠️ Algumas tabelas não puderam ser ordenadas: {[f'{t.schema}.{t.name}' for t in remaining_tables]}")
            # Adiciona as tabelas restantes no final
            ordered_tables.extend(remaining_tables)

        logger.info("🔧 Criando tabelas na ordem correta:")
        for i, table in enumerate(ordered_tables, 1):
            logger.info(f"  {i:2d}. {table.schema}.{table.name}")

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
                    # Para tabelas com erro de dependência, tenta novamente no final
                    if "does not exist" in str(table_error):
                        logger.warning(f"🔄 Tabela {table.schema}.{table.name} será tentada novamente no final")
                # Continua com as próximas tabelas mesmo se uma falhar

        # Segunda tentativa para tabelas que falharam por dependência
        logger.info("🔄 Segunda tentativa para tabelas com dependências...")
        for table in ordered_tables:
            try:
                table.create(engine, checkfirst=True)
                logger.info(f"✅ Tabela {table.schema}.{table.name} criada com sucesso (2ª tentativa)")
            except Exception as table_error:
                if "already exists" in str(table_error):
                    logger.info(f"ℹ️ Tabela {table.schema}.{table.name} já existe (2ª tentativa)")
                elif "does not exist" not in str(table_error):  # Só loga erros que não são de dependência
                    logger.error(f"❌ Erro persistente na tabela {table.schema}.{table.name}: {table_error}")

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
    # Verifica se já foi inicializado
    if verificar_banco_inicializado():
        logger.info("ℹ️ Banco já foi inicializado (pulando)")
        return
    
    # Tenta adquirir um lock usando uma tabela temporária
    lock_acquired = False
    max_retries = 10
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            with engine.begin() as conn:
                # Tenta criar uma tabela de lock (será removida automaticamente)
                conn.execute(text("""
                    CREATE TEMPORARY TABLE IF NOT EXISTS db_init_lock (
                        id INTEGER PRIMARY KEY DEFAULT 1,
                        process_id TEXT NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                """))
                
                # Tenta inserir o lock
                conn.execute(text("""
                    INSERT INTO db_init_lock (id, process_id) 
                    VALUES (1, :process_id);
                """), {"process_id": str(time.time())})
                
                lock_acquired = True
                logger.info(f"🔒 Lock adquirido (tentativa {attempt + 1})")
                break
                
        except Exception as e:
            if "duplicate key value violates unique constraint" in str(e):
                logger.info(f"⏳ Aguardando lock ser liberado (tentativa {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 1.5  # Backoff exponencial
            else:
                logger.warning(f"⚠️ Erro ao adquirir lock: {e}")
                time.sleep(retry_delay)
    
    if not lock_acquired:
        logger.warning("⚠️ Não foi possível adquirir lock, tentando inicialização mesmo assim...")
    
    try:
        # Verifica novamente se foi inicializado por outro processo
        if verificar_banco_inicializado():
            logger.info("ℹ️ Banco foi inicializado por outro processo (pulando)")
            return
        
        logger.info("🔹 Instalando extensões...")
        ensure_unaccent()
        ensure_postgis()
        logger.info("🔹 Criando schemas...")
        criar_schemas()
        logger.info("🔹 Criando tabelas...")
        criar_tabelas()
        logger.info("🔹 Garantindo usuário admin padrão...")
        criar_usuario_admin_padrao()
        logger.info("🔹 Marcando banco como inicializado...")
        marcar_banco_inicializado()
        logger.info("✅ Banco inicializado com sucesso.")
        
    except Exception as e:
        logger.error(f"❌ Erro durante inicialização do banco: {e}")
        raise
    finally:
        # Remove o lock
        if lock_acquired:
            try:
                with engine.connect() as conn:
                    conn.execute(text("DROP TABLE IF EXISTS db_init_lock;"))
                    conn.commit()
                    logger.info("🔓 Lock liberado")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao liberar lock: {e}")

