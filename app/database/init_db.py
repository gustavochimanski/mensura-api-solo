import logging
import time
from sqlalchemy import text, quoted_name
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from .db_connection import engine, Base, SessionLocal
from app.core.security import hash_password
from app.api.cadastros.models.user_model import UserModel

logger = logging.getLogger(__name__)
SCHEMAS = ["notifications", "cadastros", "cardapio", "catalogo", "financeiro", "pedidos"]

#
def verificar_banco_inicializado():
    """Verifica se o banco já foi inicializado consultando se as tabelas principais existem"""
    try:
        with engine.connect() as conn:
            # Verifica se existem tabelas principais dos schemas
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema IN ('cardapio', 'cadastros', 'notifications', 'catalogo', 'financeiro', 'pedidos')
                AND table_name IN (
                    'usuarios', 'empresas', 'produtos', 'produtos_empresa', 'categorias',
                    'clientes', 'pedidos', 'enderecos', 'regioes_entrega',
                    'categoria_dv', 'vitrines_dv', 'entregadores_dv', 'meio_pagamento_dv',
                    'cupons_dv', 'transacoes_pagamento_dv', 'pedidos_itens',
                    'pedidos_historico', 'parceiros_dv', 'banner_parceiros_dv'
                );
            """))
            table_count = result.scalar()
            
            # Se tem pelo menos 15 tabelas principais, considera inicializad
            return table_count >= 15
            
    except Exception as e:
        logger.warning(f"⚠️ Erro ao verificar status de inicialização: {e}")
        return False

def marcar_banco_inicializado():
    """Marca o banco como inicializado (agora baseado na existência das tabelas)"""
    # A verificação agora é baseada na existência das tabelas, não precisa marcar
    logger.info("ℹ️ Status de inicialização baseado na existência das tabelas")

def verificar_estrutura_tabelas():
    """Verifica se as tabelas têm a estrutura correta (colunas necessárias)"""
    try:
        with engine.connect() as conn:
            # Verifica se a tabela regioes_entrega tem as colunas corretas
            result_regioes = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'cadastros' 
                AND table_name = 'regioes_entrega'
                AND column_name IN ('descricao', 'distancia_min_km', 'distancia_max_km', 'taxa_entrega')
            """))
            regioes_columns = [row[0] for row in result_regioes]
            
            # Verifica se a tabela enderecos tem as colunas corretas
            result_enderecos = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'cadastros' 
                AND table_name = 'enderecos'
                AND column_name IN ('logradouro', 'numero', 'bairro', 'cidade', 'estado', 'cep')
            """))
            enderecos_columns = [row[0] for row in result_enderecos]
            
            # Verifica se tem as colunas essenciais
            has_regioes_essential = all(
                col in regioes_columns for col in ['distancia_min_km', 'taxa_entrega']
            )
            has_enderecos_essential = all(col in enderecos_columns for col in ['logradouro', 'numero', 'bairro', 'cidade', 'estado', 'cep'])
            
            # Verifica se não tem as colunas removidas da regioes_entrega
            result_removed = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'cadastros' 
                AND table_name = 'regioes_entrega'
                AND column_name IN ('latitude', 'longitude', 'raio_km', 'bairro', 'cidade', 'uf', 'cep')
            """))
            removed_columns = [row[0] for row in result_removed]
            has_removed = len(removed_columns) > 0
            
            return has_regioes_essential and has_enderecos_essential and not has_removed
            
    except Exception as e:
        logger.warning(f"⚠️ Erro ao verificar estrutura das tabelas: {e}")
        return False

def habilitar_postgis():

    """Habilita a extensão PostGIS necessária para Geography/Geometry e valida sua disponibilidade."""
    logger.info("🗺️ Verificando/Habilitando extensão PostGIS...")
    # 1) Garante schema public
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
    except Exception as e:
        logger.warning(f"⚠️ Erro ao garantir schema public: {e}")

    # 2) Tenta criar a extensão explicitando o schema
    try:
        with engine.begin() as conn:
            # Define search_path para evitar "no schema has been selected to create in"
            conn.execute(text("SET search_path TO public"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public"))
    except Exception as postgis_error:
        logger.warning(f"⚠️ Erro ao criar extensão PostGIS (WITH SCHEMA public): {postgis_error}")

    # 3) Valida em uma nova transação limpa
    try:
        with engine.begin() as conn:
            geography_exists = conn.execute(text(
                """
                SELECT 1
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE n.nspname = 'public' AND t.typname = 'geography'
                """
            )).scalar()

        if geography_exists:
            logger.info("✅ PostGIS disponível (tipo 'geography' encontrado)")
        else:
            logger.error("❌ PostGIS não disponível (tipo 'geography' ausente). Instale/habilite PostGIS no banco.")
            raise RuntimeError("PostGIS ausente: não é possível criar tabelas com colunas Geography")
    except Exception as e:
        # Propaga erro para interromper inicialização e evitar tabelas órfãs
        raise

def configurar_timezone():
    """Configura o timezone do banco de dados para America/Sao_Paulo"""
    try:
        with engine.begin() as conn:
            # Configura timezone da sessão
            conn.execute(text("SET timezone = 'America/Sao_Paulo'"))
            # Verifica se o timezone foi configurado corretamente
            result = conn.execute(text("SHOW timezone"))
            timezone_atual = result.scalar()
            logger.info(f"✅ Timezone do banco configurado: {timezone_atual}")
    except Exception as e:
        logger.warning(f"⚠️ Erro ao configurar timezone do banco: {e}")

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

def criar_enums():
    """Cria os tipos ENUM do PostgreSQL com schema correto antes de criar as tabelas."""
    try:
        with engine.begin() as conn:
            # ENUMs do schema cardapio
            enums_cardapio = [
                ("cardapio", "pedido_status_enum", ["P", "I", "R", "S", "E", "C", "D", "X", "A"]),
                ("cardapio", "tipo_entrega_enum", ["DELIVERY", "RETIRADA"]),
                ("cardapio", "origem_pedido_enum", ["WEB", "APP"]),
                ("cardapio", "pagamento_gateway_enum", ["MERCADOPAGO", "PAGSEGURO", "STRIPE", "PIX_INTERNO", "OUTRO"]),
                ("cardapio", "pagamento_metodo_enum", ["PIX", "PIX_ONLINE", "CREDITO", "DEBITO", "DINHEIRO", "ONLINE", "OUTRO"]),
                ("cardapio", "pagamento_status_enum", ["PENDENTE", "AUTORIZADO", "PAGO", "RECUSADO", "CANCELADO", "ESTORNADO"]),
            ]
            
            # ENUMs do schema cadastros
            enums_cadastros = [
                (
                    "cadastros",
                    "meio_pagamento_tipo_enum",
                    ["CARTAO_ENTREGA", "PIX_ENTREGA", "DINHEIRO", "PIX_ONLINE", "OUTROS"],
                ),
            ]
            
            # ENUMs do schema cadastros (caixa_status está em cadastros pois CaixaModel está em cadastros)
            enums_cadastros_caixas = [
                ("cadastros", "caixa_status_enum", ["ABERTO", "FECHADO"]),
                ("cadastros", "retirada_tipo_enum", ["SANGRIA", "DESPESA"]),
            ]
            
            # ENUMs do schema notifications
            enums_notifications = [
                ("notifications", "notificationstatus", ["pending", "sent", "failed", "retrying", "cancelled"]),
                ("notifications", "notificationchannel", ["email", "whatsapp", "push", "webhook", "in_app", "sms", "telegram"]),
                ("notifications", "notificationpriority", ["low", "normal", "high", "urgent"]),
                ("notifications", "messagetype", ["marketing", "utility", "transactional", "promotional", "alert", "system", "news"]),
            ]
            
            all_enums = enums_cardapio + enums_cadastros + enums_cadastros_caixas + enums_notifications
            
            for schema, enum_name, values in all_enums:
                try:
                    # Verifica se o ENUM já existe
                    exists = conn.execute(text(
                        f"""
                        SELECT 1 FROM pg_type t 
                        JOIN pg_namespace n ON n.oid = t.typnamespace 
                        WHERE n.nspname = '{schema}' AND t.typname = '{enum_name}'
                        """
                    )).scalar()
                    
                    if not exists:
                        # Cria o ENUM com schema especificado
                        values_str = ", ".join([f"'{v}'" for v in values])
                        conn.execute(text(f"CREATE TYPE {schema}.{enum_name} AS ENUM ({values_str})"))
                        logger.info(f"✅ ENUM {schema}.{enum_name} criado com sucesso")
                    else:
                        logger.info(f"ℹ️ ENUM {schema}.{enum_name} já existe")
                except Exception as enum_error:
                    if "already exists" in str(enum_error):
                        logger.info(f"ℹ️ ENUM {schema}.{enum_name} já existe")
                    else:
                        logger.warning(f"⚠️ Erro ao criar ENUM {schema}.{enum_name}: {enum_error}")
        
        logger.info("✅ Todos os ENUMs verificados/criados.")
    except Exception as e:
        logger.error(f"❌ Erro ao criar ENUMs: {e}")

def importar_models():
    # ─── Models Cadastros ────────────────────────────────────────────
    from app.api.empresas.models.empresa_model import EmpresaModel
    from app.api.cadastros.models.user_model import UserModel
    from app.api.cadastros.models.categoria_model import CategoriaModel
    # Importar ProdutoModel DEPOIS de CategoriaModel para resolver relacionamentos
    # ProdutoModel, ProdutoEmpModel, ComboModel e ReceitaModel agora estão no módulo catalogo
    from app.api.catalogo.models.model_produto import ProdutoModel
    from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
    from app.api.catalogo.models.model_combo import ComboModel
    # Receitas (tabela receitas no schema catalogo)
    from app.api.catalogo.models.model_receita import ReceitaModel, ReceitaIngredienteModel, ReceitaAdicionalModel
    from app.api.financeiro.models.model_caixa_conferencia import CaixaConferenciaModel
    from app.api.caixas.models.model_caixa import CaixaModel
    from app.api.caixas.models.model_retirada import RetiradaModel
    # ─── Models Cardápio ───────────────────────────────────────────
    from app.api.cardapio.models.model_transacao_pagamento_dv import TransacaoPagamentoModel
    # Modelos unificados (modelos antigos foram removidos)
    from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel
    from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
    from app.api.pedidos.models.model_pedido_historico_unificado import PedidoHistoricoUnificadoModel
    from app.api.cadastros.models.model_cupom import CupomDescontoModel
    from app.api.cadastros.models.model_cliente_dv import ClienteModel
    from app.api.cadastros.models.model_endereco_dv import EnderecoModel
    from app.api.cardapio.models.model_categoria_dv import CategoriaDeliveryModel
    from app.api.cardapio.models.model_vitrine import VitrinesModel
    # Importar tabelas de associação de vitrines
    from app.api.cadastros.models.association_tables import (
        VitrineComboLink,
        VitrineReceitaLink
    )
    from app.api.cadastros.models.model_entregador_dv import EntregadorDeliveryModel
    from app.api.cadastros.models.model_meio_pagamento import MeioPagamentoModel
    from app.api.cadastros.models.model_parceiros import ParceiroModel, BannerParceiroModel
    from app.api.cadastros.models.model_regiao_entrega import RegiaoEntregaModel
    from app.api.catalogo.models.model_adicional import AdicionalModel
    from app.api.catalogo.models.model_complemento import ComplementoModel
    # ─── Models Notifications ───────────────────────────────────────────
    from app.api.notifications.models.notification import Notification, NotificationLog
    logger.info("📦 Models importados com sucesso.")


def verificar_tabelas_cardapio():
    """Verifica se as tabelas do schema cardapio existem e cria se necessário."""
    try:
        with engine.connect() as conn:
            # Lista de tabelas esperadas no schema cardapio
            # Nota: Tabelas de pedidos foram movidas para o schema pedidos
            tabelas_cardapio = [
                "transacoes_pagamento_dv",
                "categoria_dv",
                "vitrines_dv"
            ]
            
            tabelas_faltando = []
            for tabela in tabelas_cardapio:
                result = conn.execute(text("""
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'cardapio' 
                    AND table_name = :tabela
                """), {"tabela": tabela})
                if not result.scalar():
                    tabelas_faltando.append(tabela)
            
            if tabelas_faltando:
                logger.warning(f"⚠️ Tabelas do schema cardapio faltando: {tabelas_faltando}")
                return False
            return True
    except Exception as e:
        logger.warning(f"⚠️ Erro ao verificar tabelas cardapio: {e}")
        return False

def criar_tabelas_cardapio_antes():
    """Cria as tabelas do cardápio antes das outras para garantir que sejam criadas."""
    try:
        logger.info("🚀 Criando tabelas do schema cardapio primeiro...")
        # Importa os modelos para garantir que estejam registrados no Base
        importar_models()
        
        from app.api.cardapio.models.model_transacao_pagamento_dv import TransacaoPagamentoModel
        # Modelos unificados (modelos antigos foram removidos)
        from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel
        from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
        from app.api.pedidos.models.model_pedido_historico_unificado import PedidoHistoricoUnificadoModel
        
        # Tabelas de pedidos foram movidas para o schema pedidos
        cardapio_tables = [
            TransacaoPagamentoModel.__table__
        ]
        
        # Tabelas do schema pedidos (modelos unificados)
        pedidos_tables = [
            PedidoUnificadoModel.__table__,
            PedidoItemUnificadoModel.__table__,
            PedidoHistoricoUnificadoModel.__table__,
        ]
        
        # Criar tabelas do schema cardapio (modelos antigos)
        for table in cardapio_tables:
            try:
                with engine.begin() as conn:
                    result = conn.execute(text("""
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = :schema 
                        AND table_name = :table_name
                    """), {"schema": table.schema, "table_name": table.name})
                    existe = result.scalar()
                
                if not existe:
                    with engine.begin() as conn:
                        table.create(engine, checkfirst=False)
                    logger.info(f"✅ Tabela {table.schema}.{table.name} criada com sucesso")
                else:
                    logger.info(f"ℹ️ Tabela {table.schema}.{table.name} já existe")
            except Exception as table_err:
                error_msg = str(table_err)
                if "already exists" in error_msg.lower():
                    logger.info(f"ℹ️ Tabela {table.schema}.{table.name} já existe")
                else:
                    logger.error(f"❌ Erro ao criar tabela {table.schema}.{table.name}: {table_err}", exc_info=True)
        
        # Criar tabelas do schema pedidos (modelos unificados)
        for table in pedidos_tables:
            try:
                with engine.begin() as conn:
                    result = conn.execute(text("""
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = :schema 
                        AND table_name = :table_name
                    """), {"schema": table.schema, "table_name": table.name})
                    existe = result.scalar()
                
                if not existe:
                    with engine.begin() as conn:
                        table.create(engine, checkfirst=False)
                    logger.info(f"✅ Tabela {table.schema}.{table.name} criada com sucesso")
                else:
                    logger.info(f"ℹ️ Tabela {table.schema}.{table.name} já existe")
            except Exception as table_err:
                error_msg = str(table_err)
                if "already exists" in error_msg.lower():
                    logger.info(f"ℹ️ Tabela {table.schema}.{table.name} já existe")
                else:
                    logger.error(f"❌ Erro ao criar tabela {table.schema}.{table.name}: {table_err}", exc_info=True)
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas do cardapio antes: {e}", exc_info=True)

def criar_tabelas():
    try:
        importar_models()  # importa só os seus models de mensura e cardapio

        # pega todas as Table objects que o Base conhece
        all_tables = list(Base.metadata.tables.values())
        logger.info(f"📊 Total de tabelas encontradas: {len(all_tables)}")
        
        # Log de debug: mostra todas as tabelas encontradas por schema
        tabelas_por_schema = {}
        for table in all_tables:
            schema = table.schema or "public"
            if schema not in tabelas_por_schema:
                tabelas_por_schema[schema] = []
            tabelas_por_schema[schema].append(table.name)
        
        logger.info("📊 Tabelas encontradas por schema:")
        for schema, tabelas in sorted(tabelas_por_schema.items()):
            logger.info(f"  Schema '{schema}': {len(tabelas)} tabelas - {', '.join(tabelas)}")

        # filtra pelas tabelas que pertencem aos schemas que você gerencia
        tables_para_criar = [
            t
            for t in all_tables
            if t.schema in SCHEMAS
        ]
        
        logger.info(f"📋 Tabelas filtradas para criar nos schemas {SCHEMAS}: {len(tables_para_criar)} tabelas")
        for table in tables_para_criar:
            logger.info(f"  - {table.schema}.{table.name}")

        # Usa a ordenação topológica nativa do SQLAlchemy (respeita FKs)
        ordered_tables = [t for t in Base.metadata.sorted_tables if t.schema in SCHEMAS]

        logger.info("🔧 Criando tabelas na ordem correta:")
        for i, table in enumerate(ordered_tables, 1):
            logger.info(f"  {i:2d}. {table.schema}.{table.name}")

        # Cria as tabelas na ordem correta (delega a checkfirst do SQLAlchemy)
        tabelas_com_erro = []
        for table in ordered_tables:
            try:
                table.create(engine, checkfirst=True)
                logger.info(f"✅/ℹ️ Tabela {table.schema}.{table.name} criada/verificada")
            except Exception as table_error:
                logger.error(f"❌ Erro ao criar tabela {table.schema}.{table.name}: {table_error}", exc_info=True)
                tabelas_com_erro.append((table, table_error))

        # Segunda tentativa para tabelas que falharam
        if tabelas_com_erro:
            logger.info(f"🔄 Segunda tentativa para {len(tabelas_com_erro)} tabelas com erro...")
            for table, error in tabelas_com_erro:
                try:
                    table.create(engine, checkfirst=True)
                    logger.info(f"✅ Tabela {table.schema}.{table.name} criada/verificada (2ª tentativa)")
                except Exception as table_error:
                    logger.error(f"❌ Erro persistente na tabela {table.schema}.{table.name}: {table_error}", exc_info=True)

        # Verifica e força criação das tabelas do cardapio
        logger.info("🔍 Verificando tabelas do schema cardapio...")
        if not verificar_tabelas_cardapio():
            logger.warning("⚠️ Algumas tabelas do schema cardapio não foram criadas. Tentando criar todas as tabelas do cardapio...")
            # Tenta criar todas as tabelas do cardapio usando create_all
            try:
                from app.api.cardapio.models.model_transacao_pagamento_dv import TransacaoPagamentoModel
                # Modelos unificados (modelos antigos foram removidos)
                from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel
                from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
                from app.api.pedidos.models.model_pedido_historico_unificado import PedidoHistoricoUnificadoModel
                
                # Garante que os modelos estão registrados no Base
                # Tabelas de pedidos foram movidas para o schema pedidos
                cardapio_tables = [
                    TransacaoPagamentoModel.__table__
                ]
                
                # Tabelas do schema pedidos (modelos unificados)
                pedidos_tables = [
                    PedidoUnificadoModel.__table__,
                    PedidoItemUnificadoModel.__table__,
                    PedidoHistoricoUnificadoModel.__table__,
                ]
                
                # Cria cada tabela individualmente para melhor controle de erros
                # Criar tabelas do schema cardapio (modelos antigos)
                for table in cardapio_tables:
                    try:
                        with engine.begin() as conn:
                            table.create(engine, checkfirst=True)
                        logger.info(f"✅ Tabela {table.schema}.{table.name} criada/verificada")
                    except Exception as table_err:
                        error_msg = str(table_err)
                        if "already exists" in error_msg.lower():
                            logger.info(f"ℹ️ Tabela {table.schema}.{table.name} já existe")
                        else:
                            logger.error(f"❌ Erro ao criar tabela {table.schema}.{table.name}: {table_err}", exc_info=True)
                
                # Criar tabelas do schema pedidos (modelos unificados)
                for table in pedidos_tables:
                    try:
                        with engine.begin() as conn:
                            table.create(engine, checkfirst=True)
                        logger.info(f"✅ Tabela {table.schema}.{table.name} criada/verificada")
                    except Exception as table_err:
                        error_msg = str(table_err)
                        if "already exists" in error_msg.lower():
                            logger.info(f"ℹ️ Tabela {table.schema}.{table.name} já existe")
                        else:
                            logger.error(f"❌ Erro ao criar tabela {table.schema}.{table.name}: {table_err}", exc_info=True)
                
                # Verifica novamente após tentativa de criação
                if verificar_tabelas_cardapio():
                    logger.info("✅ Todas as tabelas do schema cardapio foram criadas/verificadas com sucesso")
                else:
                    logger.error("❌ Ainda faltam tabelas do schema cardapio após tentativa de criação")
            except Exception as e:
                logger.error(f"❌ Erro ao criar tabelas do cardapio: {e}", exc_info=True)
        else:
            logger.info("✅ Todas as tabelas do schema cardapio já existem")

        # Garante coluna de preço específico por complemento na tabela de associação
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        ALTER TABLE catalogo.complemento_item_link
                        ADD COLUMN IF NOT EXISTS preco_complemento numeric(18,2)
                        """
                    )
                )
            logger.info("✅ Coluna catalogo.complemento_item_link.preco_complemento criada/verificada com sucesso")
        except Exception as e:
            logger.error(
                "❌ Erro ao garantir coluna catalogo.complemento_item_link.preco_complemento: %s",
                e,
                exc_info=True,
            )

        # Garante colunas de mínimo/máximo de itens em complementos
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        ALTER TABLE catalogo.complemento_produto
                        ADD COLUMN IF NOT EXISTS minimo_itens integer,
                        ADD COLUMN IF NOT EXISTS maximo_itens integer
                        """
                    )
                )
            logger.info("✅ Colunas minimo_itens/maximo_itens em catalogo.complemento_produto criadas/verificadas com sucesso")
        except Exception as e:
            logger.error(
                "❌ Erro ao garantir colunas minimo_itens/maximo_itens em catalogo.complemento_produto: %s",
                e,
                exc_info=True,
            )

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


def criar_meios_pagamento_padrao():
    """Cria os meios de pagamento padrão na tabela cadastros.meios_pagamento."""
    try:
        from app.api.cadastros.models.model_meio_pagamento import MeioPagamentoModel

        dados_meios_pagamento = [
            {
                "nome": "Cartão Entrega",
                "tipo": "CARTAO_ENTREGA",
                "ativo": True,
            },
            {
                "nome": "Dinheiro",
                "tipo": "DINHEIRO",
                "ativo": True,
            },
            {
                "nome": "Outros",
                "tipo": "OUTROS",
                "ativo": True,
            },
            {
                "nome": "PIX - Online",
                "tipo": "PIX_ONLINE",
                "ativo": True,
            },
            {
                "nome": "Pix - POS",
                "tipo": "OUTROS",
                "ativo": True,
            },
        ]
#
        with SessionLocal() as session:
            for dados in dados_meios_pagamento:
                stmt = (
                    insert(MeioPagamentoModel)
                    .values(**dados)
                    .on_conflict_do_nothing(index_elements=[MeioPagamentoModel.nome])
                )
                session.execute(stmt)
            session.commit()

        logger.info("✅ Meios de pagamento padrão criados/verificados com sucesso.")
    except Exception as e:
        logger.error(f"❌ Erro ao criar meios de pagamento padrão: {e}", exc_info=True)

def inicializar_banco():
    logger.info("🚀 Iniciando processo de inicialização do banco de dados...")
    
    # Configura timezone primeiro
    logger.info("📦 Passo 1/7: Configurando timezone do banco...")
    configurar_timezone()
    
    # Habilita PostGIS primeiro (necessário para tipos geography)
    logger.info("📦 Passo 2/7: Habilitando extensão PostGIS...")
    habilitar_postgis()
    
    # SEMPRE cria/verifica os schemas primeiro
    logger.info("📦 Passo 3/7: Criando/verificando schemas...")
    criar_schemas()
    
    # Cria os ENUMs antes de criar as tabelas
    logger.info("📦 Passo 4/7: Criando/verificando ENUMs...")
    criar_enums()
    
    # SEMPRE cria as tabelas (criar_tabelas usa checkfirst=True, então não sobrescreve)
    logger.info("📋 Passo 5/7: Criando/verificando todas as tabelas...")
    criar_tabelas()
    
    logger.info("👤 Passo 6/7: Garantindo usuário admin padrão...")
    criar_usuario_admin_padrao()
    
    # Dados iniciais de meios de pagamento
    logger.info("💳 Criando/verificando meios de pagamento padrão...")
    criar_meios_pagamento_padrao()
    
    logger.info("✅ Banco inicializado com sucesso.")
