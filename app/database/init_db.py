import logging
import time
from sqlalchemy import text, quoted_name
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from .db_connection import engine, Base, SessionLocal
from app.core.security import hash_password
from app.api.cadastros.models.user_model import UserModel

logger = logging.getLogger(__name__)
SCHEMAS = ["notifications", "cadastros", "cardapio", "catalogo", "financeiro", "pedidos", "chatbot"]

#
def verificar_banco_inicializado():
    """Verifica se o banco já foi inicializado consultando se as tabelas principais existem"""
    try:
        with engine.connect() as conn:
            # Verifica se existem tabelas principais dos schemas
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema IN ('cardapio', 'cadastros', 'notifications', 'catalogo', 'financeiro', 'pedidos', 'chatbot')
                AND table_name IN (
                    'usuarios', 'empresas', 'produtos', 'produtos_empresa', 'categorias',
                    'clientes', 'pedidos', 'enderecos', 'regioes_entrega',
                    'categoria_dv', 'vitrines_dv', 'entregadores_dv', 'meio_pagamento_dv',
                    'cupons_dv', 'transacoes_pagamento_dv', 'pedidos_itens',
                    'pedidos_historico', 'parceiros_dv', 'banner_parceiros_dv',
                    'notifications', 'notification_logs', 'events', 'notification_subscriptions', 'whatsapp_configs',
                    'prompts', 'conversations', 'messages', 'bot_status'
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
    """
    Habilita a extensão PostGIS necessária para Geography/Geometry e valida sua disponibilidade.
    
    Returns:
        bool: True se PostGIS está disponível, False caso contrário
    """
    logger.info("🗺️ Verificando/Habilitando extensão PostGIS...")
    # 1) Garante schema public
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
    except Exception as e:
        logger.warning(f"⚠️ Erro ao garantir schema public: {e}")

    # 2) Tenta criar a extensão explicitando o schema
    # NOTA: Esta função apenas TENTA HABILITAR a extensão PostGIS.
    # Se o PostGIS não estiver INSTALADO no sistema, essa tentativa falhará.
    # A instalação do PostGIS deve ser feita no sistema operacional (não pode ser feita via SQL).
    try:
        with engine.begin() as conn:
            # Define search_path para evitar "no schema has been selected to create in"
            conn.execute(text("SET search_path TO public"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public"))
            logger.info("ℹ️ Tentativa de habilitar extensão PostGIS executada")
    except Exception as postgis_error:
        error_msg = str(postgis_error)
        # Verifica se é erro de extensão não instalada no sistema
        if "is not available" in error_msg or "extension control file" in error_msg or "No such file" in error_msg:
            logger.warning("⚠️ PostGIS não está INSTALADO no sistema PostgreSQL")
            logger.warning("⚠️ O init_db não pode instalar PostGIS - apenas habilita se já estiver instalado")
            logger.warning("⚠️ A instalação deve ser feita ANTES de criar o cliente (via scripts/api/criar_cliente.sh)")
            logger.warning("⚠️ Para instalar PostGIS, execute no servidor PostgreSQL (exemplo Ubuntu/Debian):")
            logger.warning("⚠️   sudo apt-get update")
            logger.warning("⚠️   sudo apt-get install postgresql-15-postgis-3")
            logger.warning("⚠️   (ajuste '15' para a versão do seu PostgreSQL: 14, 15, 16, etc.)")
            logger.warning("⚠️ Depois, o init_db habilitará automaticamente na próxima inicialização")
            logger.warning("⚠️ Funcionalidades geográficas estarão desabilitadas até PostGIS ser instalado")
        else:
            logger.warning(f"⚠️ Erro ao habilitar extensão PostGIS: {postgis_error}")
            logger.warning("⚠️ Funcionalidades geográficas estarão desabilitadas")

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
            # Remove esquemas desnecessários do PostGIS (topology, tiger, tiger_data)
            remover_esquemas_postgis_desnecessarios()
            return True
        else:
            logger.warning("⚠️ PostGIS não disponível (tipo 'geography' ausente).")
            logger.warning("⚠️ Funcionalidades geográficas estarão desabilitadas.")
            logger.warning("⚠️ Para habilitar: instale PostGIS no PostgreSQL e execute:")
            logger.warning("⚠️   CREATE EXTENSION postgis;")
            return False
    except Exception as e:
        logger.warning(f"⚠️ Erro ao verificar PostGIS: {e}")
        logger.warning("⚠️ Funcionalidades geográficas estarão desabilitadas.")
        return False

def remover_esquemas_postgis_desnecessarios():
    """Remove esquemas do PostGIS que não são necessários (topology, tiger, tiger_data)"""
    esquemas_para_remover = ["topology", "tiger", "tiger_data"]
    
    try:
        with engine.begin() as conn:
            for schema in esquemas_para_remover:
                try:
                    # Verifica se o schema existe antes de tentar remover
                    result = conn.execute(text("""
                        SELECT 1 FROM information_schema.schemata 
                        WHERE schema_name = :schema_name
                    """), {"schema_name": schema})
                    
                    if result.scalar():
                        conn.execute(text(f"DROP SCHEMA IF EXISTS {quoted_name(schema, quote=True)} CASCADE"))
                        logger.info(f"✅ Schema {schema} removido com sucesso")
                    else:
                        logger.info(f"ℹ️ Schema {schema} não existe (pulando)")
                except Exception as schema_error:
                    # Não é crítico se falhar, apenas loga o aviso
                    logger.warning(f"⚠️ Erro ao remover schema {schema}: {schema_error}")
    except Exception as e:
        logger.warning(f"⚠️ Erro ao remover esquemas PostGIS desnecessários: {e}")

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
            
            # ENUMs do schema chatbot
            enums_chatbot = [
                ("chatbot", "tipo_entrega_carrinho_enum", ["DELIVERY", "RETIRADA", "BALCAO", "MESA"]),
            ]
            
            all_enums = enums_cardapio + enums_cadastros + enums_cadastros_caixas + enums_notifications + enums_chatbot
            
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
    # Permissões (RBAC/grants por domínio)
    from app.api.cadastros.models.model_permission import PermissionModel
    from app.api.cadastros.models.model_user_permission import UserPermissionModel
    from app.api.cadastros.models.categoria_model import CategoriaModel
    # Importar ProdutoModel DEPOIS de CategoriaModel para resolver relacionamentos
    # ProdutoModel, ProdutoEmpModel, ComboModel e ReceitaModel agora estão no módulo catalogo
    from app.api.catalogo.models.model_produto import ProdutoModel
    from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
    from app.api.catalogo.models.model_combo import ComboModel
    # Receitas (tabela receitas no schema catalogo)
    from app.api.catalogo.models.model_receita import ReceitaModel, ReceitaIngredienteModel
    from app.api.financeiro.models.model_caixa_conferencia import CaixaConferenciaModel
    from app.api.caixas.models.model_caixa import CaixaModel
    from app.api.caixas.models.model_caixa_abertura import CaixaAberturaModel
    from app.api.caixas.models.model_retirada import RetiradaModel
    # ─── Models Cardápio ───────────────────────────────────────────
    from app.api.cardapio.models.model_transacao_pagamento_dv import TransacaoPagamentoModel
    # Modelos unificados (modelos antigos foram removidos)
    from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel
    from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
    from app.api.pedidos.models.model_pedido_historico_unificado import PedidoHistoricoUnificadoModel
    from app.api.pedidos.models.model_pedido_item_complemento import PedidoItemComplementoModel
    from app.api.pedidos.models.model_pedido_item_complemento_adicional import PedidoItemComplementoAdicionalModel
    from app.api.cadastros.models.model_cupom import CupomDescontoModel
    from app.api.cadastros.models.model_cliente_dv import ClienteModel
    from app.api.cadastros.models.model_endereco_dv import EnderecoModel
    from app.api.cardapio.models.model_categoria_dv import CategoriaDeliveryModel
    from app.api.cardapio.models.model_vitrine import VitrinesModel, VitrinesLandingpageStoreModel
    # Importar tabelas de associação de vitrines
    from app.api.cadastros.models.association_tables import (
        VitrineComboLink,
        VitrineReceitaLink,
        VitrineLandingProdutoLink,
        VitrineLandingComboLink,
        VitrineLandingReceitaLink,
    )
    from app.api.cadastros.models.model_entregador_dv import EntregadorDeliveryModel
    from app.api.cadastros.models.model_meio_pagamento import MeioPagamentoModel
    from app.api.cadastros.models.model_parceiros import ParceiroModel, BannerParceiroModel
    from app.api.cadastros.models.model_regiao_entrega import RegiaoEntregaModel
    from app.api.catalogo.models.model_complemento import ComplementoModel
    from app.api.catalogo.models.model_complemento_vinculo_item import ComplementoVinculoItemModel
    # ─── Models Notifications ───────────────────────────────────────────
    from app.api.notifications.models.notification import Notification, NotificationLog
    from app.api.notifications.models.event import Event
    from app.api.notifications.models.subscription import NotificationSubscription
    from app.api.notifications.models.whatsapp_config_model import WhatsAppConfigModel
    # ─── Models Chatbot ───────────────────────────────────────────
    from app.api.chatbot.models.model_chatbot_config import ChatbotConfigModel
    from app.api.chatbot.models.model_carrinho import CarrinhoTemporarioModel, TipoEntregaCarrinhoEnum
    from app.api.chatbot.models.model_carrinho_item import CarrinhoItemModel
    from app.api.chatbot.models.model_carrinho_item_complemento import CarrinhoItemComplementoModel
    from app.api.chatbot.models.model_carrinho_item_complemento_adicional import CarrinhoItemComplementoAdicionalModel
    logger.info("📦 Models importados com sucesso.")


def criar_permissoes_padrao():
    """Cria/verifica permissões padrão (catálogo)."""
    try:
        from app.core.permissions_catalog import get_default_permissions
        from app.api.cadastros.models.model_permission import PermissionModel

        with engine.connect() as conn:
            exists = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'cadastros' AND table_name = 'permissions'
                    """
                )
            ).scalar()
            if not exists:
                logger.warning("⚠️ Tabela cadastros.permissions não existe; pulando seed de permissões.")
                return

        defaults = get_default_permissions()
        rows = [{"key": p.key, "domain": p.domain, "description": p.description} for p in defaults]

        with SessionLocal() as session:
            for row in rows:
                stmt = (
                    insert(PermissionModel)
                    .values(**row)
                    .on_conflict_do_nothing(index_elements=[PermissionModel.key])
                )
                session.execute(stmt)
            session.commit()

        logger.info("✅ Permissões padrão criadas/verificadas com sucesso (%s).", len(rows))
    except Exception as e:
        logger.error(f"❌ Erro ao criar permissões padrão: {e}", exc_info=True)


def verificar_tabelas_cardapio():
    """Verifica se as tabelas do schema cardapio existem e cria se necessário."""
    try:
        with engine.connect() as conn:
            # Lista de tabelas esperadas no schema cardapio
            # Nota: Tabelas de pedidos foram movidas para o schema pedidos
            tabelas_cardapio = [
                "transacoes_pagamento_dv",
                "categoria_dv",
                "vitrines_dv",
                "vitrines_landingpage_store",
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
    """Importa os modelos do cardápio para garantir que estejam registrados no Base."""
    try:
        logger.info("🚀 Importando modelos do schema cardapio...")
        # Importa os modelos para garantir que estejam registrados no Base
        importar_models()
        
        from app.api.cardapio.models.model_transacao_pagamento_dv import TransacaoPagamentoModel
        # Modelos unificados (modelos antigos foram removidos)
        from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel
        from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
        from app.api.pedidos.models.model_pedido_historico_unificado import PedidoHistoricoUnificadoModel
        from app.api.pedidos.models.model_pedido_item_complemento import PedidoItemComplementoModel
        from app.api.pedidos.models.model_pedido_item_complemento_adicional import PedidoItemComplementoAdicionalModel
        
        logger.info("✅ Modelos do cardapio importados com sucesso")
    except Exception as e:
        logger.error(f"❌ Erro ao importar modelos do cardapio: {e}", exc_info=True)

def criar_tabela_pedidos_sem_postgis():
    """
    Função removida - tabelas são criadas automaticamente pelos imports dos modelos.
    """
    logger.info("ℹ️ Criação de tabelas delegada aos imports dos modelos")
    return True

def criar_tabelas(postgis_disponivel: bool = True):
    """
    Importa os modelos para garantir que estejam registrados no Base.
    As tabelas serão criadas automaticamente pelos imports dos modelos.
    """
    try:
        logger.info("📦 Importando modelos para registro no Base...")
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
            if t.schema is not None and str(t.schema) in SCHEMAS
        ]
        
        logger.info(f"📋 Tabelas registradas nos schemas {SCHEMAS}: {len(tables_para_criar)} tabelas")
        for table in tables_para_criar:
            logger.info(f"  - {table.schema}.{table.name}")

        # ── (1) Cria/garante as tabelas via SQLAlchemy ────────────────────────
        # Importante: antes de qualquer ALTER/seed, precisamos garantir que as
        # tabelas realmente existam no banco.
        def _has_geo_columns(table) -> bool:
            try:
                for col in table.columns:
                    t = getattr(col, "type", None)
                    if t is None:
                        continue
                    # GeoAlchemy2 normalmente expõe tipos Geography/Geometry
                    if t.__class__.__name__ in ("Geography", "Geometry"):
                        return True
                    if (t.__class__.__module__ or "").startswith("geoalchemy2"):
                        return True
                return False
            except Exception:
                # em dúvida, não assume que é geo
                return False

        def _table_exists(conn, schema: str, table_name: str) -> bool:
            return (
                conn.execute(
                    text(
                        """
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = :schema
                          AND table_name = :table
                        """
                    ),
                    {"schema": schema, "table": table_name},
                ).scalar()
                is not None
            )

        try:
            if postgis_disponivel:
                tables_to_create = tables_para_criar
            else:
                # Se PostGIS não está disponível, evita criar tabelas que dependem
                # de Geography/Geometry para não quebrar a inicialização inteira.
                tables_to_create = [t for t in tables_para_criar if not _has_geo_columns(t)]
                skipped = [t for t in tables_para_criar if t not in tables_to_create]
                if skipped:
                    logger.warning(
                        "⚠️ PostGIS indisponível; pulando criação de %s tabelas com tipos geo: %s",
                        len(skipped),
                        ", ".join([f"{t.schema}.{t.name}" for t in skipped]),
                    )

            Base.metadata.create_all(bind=engine, tables=tables_to_create, checkfirst=True)
            logger.info("✅ create_all concluído (%s tabelas garantidas).", len(tables_to_create))
        except Exception as e:
            # Falha crítica: sem tabelas, qualquer ALTER/seed vai quebrar.
            logger.error("❌ Erro ao criar tabelas via SQLAlchemy (create_all): %s", e, exc_info=True)
            raise

        # Garante multi-tenant (empresa_id) em categorias/vitrines do cardápio
        try:
            with engine.begin() as conn:
                # Se as tabelas não existirem por algum motivo, não tenta ALTER.
                if not _table_exists(conn, "cardapio", "categoria_dv") or not _table_exists(conn, "cardapio", "vitrines_dv"):
                    logger.warning("⚠️ Tabelas cardapio.categoria_dv/vitrines_dv não existem; pulando ajustes multi-tenant.")
                else:
                    # Colunas (um ALTER por execute; vários statements em um execute podem falhar)
                    conn.execute(text("ALTER TABLE cardapio.categoria_dv ADD COLUMN IF NOT EXISTS empresa_id integer"))
                    conn.execute(text("ALTER TABLE cardapio.vitrines_dv ADD COLUMN IF NOT EXISTS empresa_id integer"))
                    # vitrines_landingpage_store: só altera se a tabela existir
                    r = conn.execute(text("""
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'cardapio' AND table_name = 'vitrines_landingpage_store'
                    """))
                    vitrines_landing_exists = r.scalar()
                    if vitrines_landing_exists:
                        conn.execute(text("ALTER TABLE cardapio.vitrines_landingpage_store ADD COLUMN IF NOT EXISTS empresa_id integer"))

                    # Índices (performance)
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_categoria_dv_empresa_id ON cardapio.categoria_dv (empresa_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vitrines_dv_empresa_id ON cardapio.vitrines_dv (empresa_id)"))
                    if vitrines_landing_exists:
                        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vitrines_landingpage_store_empresa_id ON cardapio.vitrines_landingpage_store (empresa_id)"))

                    # FKs (idempotentes via DO)
                    conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                              IF NOT EXISTS (
                                SELECT 1
                                FROM pg_constraint c
                                JOIN pg_class t ON t.oid = c.conrelid
                                JOIN pg_namespace n ON n.oid = t.relnamespace
                                WHERE n.nspname = 'cardapio'
                                  AND t.relname = 'categoria_dv'
                                  AND c.conname = 'fk_categoria_dv_empresa_id'
                              ) THEN
                                ALTER TABLE cardapio.categoria_dv
                                  ADD CONSTRAINT fk_categoria_dv_empresa_id
                                  FOREIGN KEY (empresa_id)
                                  REFERENCES cadastros.empresas(id)
                                  ON DELETE CASCADE;
                              END IF;
                            END$$;
                            """
                        )
                    )
                    conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                              IF NOT EXISTS (
                                SELECT 1
                                FROM pg_constraint c
                                JOIN pg_class t ON t.oid = c.conrelid
                                JOIN pg_namespace n ON n.oid = t.relnamespace
                                WHERE n.nspname = 'cardapio'
                                  AND t.relname = 'vitrines_dv'
                                  AND c.conname = 'fk_vitrines_dv_empresa_id'
                              ) THEN
                                ALTER TABLE cardapio.vitrines_dv
                                  ADD CONSTRAINT fk_vitrines_dv_empresa_id
                                  FOREIGN KEY (empresa_id)
                                  REFERENCES cadastros.empresas(id)
                                  ON DELETE CASCADE;
                              END IF;
                            END$$;
                            """
                        )
                    )
                    if vitrines_landing_exists:
                        conn.execute(
                            text(
                                """
                                DO $$
                                BEGIN
                                  IF NOT EXISTS (
                                    SELECT 1
                                    FROM pg_constraint c
                                    JOIN pg_class t ON t.oid = c.conrelid
                                    JOIN pg_namespace n ON n.oid = t.relnamespace
                                    WHERE n.nspname = 'cardapio'
                                      AND t.relname = 'vitrines_landingpage_store'
                                      AND c.conname = 'fk_vitrines_landingpage_store_empresa_id'
                                  ) THEN
                                    ALTER TABLE cardapio.vitrines_landingpage_store
                                      ADD CONSTRAINT fk_vitrines_landingpage_store_empresa_id
                                      FOREIGN KEY (empresa_id)
                                      REFERENCES cadastros.empresas(id)
                                      ON DELETE CASCADE;
                                  END IF;
                                END$$;
                                """
                            )
                        )

                    # Unicidade de slug por empresa (remove unicidade global se existir)
                    conn.execute(text("ALTER TABLE cardapio.vitrines_dv DROP CONSTRAINT IF EXISTS uq_vitrine_slug_global"))
                    conn.execute(text("ALTER TABLE cardapio.categoria_dv DROP CONSTRAINT IF EXISTS categoria_dv_slug_key"))
                    conn.execute(text("ALTER TABLE cardapio.categoria_dv DROP CONSTRAINT IF EXISTS uq_categoria_slug_global"))

                    conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                              IF NOT EXISTS (
                                SELECT 1
                                FROM pg_constraint c
                                JOIN pg_class t ON t.oid = c.conrelid
                                JOIN pg_namespace n ON n.oid = t.relnamespace
                                WHERE n.nspname = 'cardapio'
                                  AND t.relname = 'vitrines_dv'
                                  AND c.conname = 'uq_vitrine_slug_empresa'
                              ) THEN
                                ALTER TABLE cardapio.vitrines_dv
                                  ADD CONSTRAINT uq_vitrine_slug_empresa UNIQUE (empresa_id, slug);
                              END IF;
                            END$$;
                            """
                        )
                    )
                    conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                              IF NOT EXISTS (
                                SELECT 1
                                FROM pg_constraint c
                                JOIN pg_class t ON t.oid = c.conrelid
                                JOIN pg_namespace n ON n.oid = t.relnamespace
                                WHERE n.nspname = 'cardapio'
                                  AND t.relname = 'categoria_dv'
                                  AND c.conname = 'uq_categoria_slug_empresa'
                              ) THEN
                                ALTER TABLE cardapio.categoria_dv
                                  ADD CONSTRAINT uq_categoria_slug_empresa UNIQUE (empresa_id, slug);
                              END IF;
                            END$$;
                            """
                        )
                    )
                    if vitrines_landing_exists:
                        conn.execute(
                            text(
                                """
                                DO $$
                                BEGIN
                                  IF NOT EXISTS (
                                    SELECT 1
                                    FROM pg_constraint c
                                    JOIN pg_class t ON t.oid = c.conrelid
                                    JOIN pg_namespace n ON n.oid = t.relnamespace
                                    WHERE n.nspname = 'cardapio'
                                      AND t.relname = 'vitrines_landingpage_store'
                                      AND c.conname = 'uq_vitrine_landing_slug_empresa'
                                  ) THEN
                                    ALTER TABLE cardapio.vitrines_landingpage_store
                                      ADD CONSTRAINT uq_vitrine_landing_slug_empresa UNIQUE (empresa_id, slug);
                                  END IF;
                                END$$;
                                """
                            )
                        )
                    logger.info("✅ Coluna/constraints empresa_id em cardapio.categoria_dv, cardapio.vitrines_dv e cardapio.vitrines_landingpage_store (se existir) criadas/verificadas com sucesso")
        except Exception as e:
            logger.error(
                "❌ Erro ao garantir empresa_id em categorias/vitrines do cardápio: %s",
                e,
                exc_info=True,
            )

        # Garante colunas de mínimo/máximo de itens em complementos
        try:
            with engine.begin() as conn:
                if not _table_exists(conn, "catalogo", "complemento_produto"):
                    logger.warning("⚠️ Tabela catalogo.complemento_produto não existe; pulando criação de colunas minimo_itens/maximo_itens.")
                else:
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

        # Garante colunas de horário de funcionamento em cadastros.empresas
        try:
            with engine.begin() as conn:
                if not _table_exists(conn, "cadastros", "empresas"):
                    logger.warning("⚠️ Tabela cadastros.empresas não existe; pulando ajustes de timezone/horarios_funcionamento.")
                else:
                    conn.execute(
                        text(
                            """
                            ALTER TABLE cadastros.empresas
                            ADD COLUMN IF NOT EXISTS timezone varchar(64) DEFAULT 'America/Sao_Paulo',
                            ADD COLUMN IF NOT EXISTS horarios_funcionamento jsonb
                            """
                        )
                    )
            logger.info("✅ Colunas timezone/horarios_funcionamento em cadastros.empresas criadas/verificadas com sucesso")
        except Exception as e:
            logger.error(
                "❌ Erro ao garantir colunas timezone/horarios_funcionamento em cadastros.empresas: %s",
                e,
                exc_info=True,
            )

        # Remove colunas antigas redireciona_home / redireciona_home_para de cadastros.empresas (não existem mais)
        try:
            with engine.begin() as conn:
                if not _table_exists(conn, "cadastros", "empresas"):
                    logger.warning("⚠️ Tabela cadastros.empresas não existe; pulando remoção de colunas antigas.")
                else:
                    conn.execute(text("ALTER TABLE cadastros.empresas DROP COLUMN IF EXISTS redireciona_home"))
                    conn.execute(text("ALTER TABLE cadastros.empresas DROP COLUMN IF EXISTS redireciona_home_para"))
            logger.info("✅ Colunas redireciona_home/redireciona_home_para removidas de cadastros.empresas (se existiam)")
        except Exception as e:
            logger.error(
                "❌ Erro ao remover redireciona_home/redireciona_home_para de cadastros.empresas: %s",
                e,
                exc_info=True,
            )

        # Garante landingpage_store em cadastros.empresas
        try:
            with engine.begin() as conn:
                if not _table_exists(conn, "cadastros", "empresas"):
                    logger.warning("⚠️ Tabela cadastros.empresas não existe; pulando criação da coluna landingpage_store.")
                else:
                    conn.execute(text("ALTER TABLE cadastros.empresas ADD COLUMN IF NOT EXISTS landingpage_store boolean NOT NULL DEFAULT false"))
            logger.info("✅ Coluna landingpage_store em cadastros.empresas criada/verificada com sucesso")
        except Exception as e:
            logger.error(
                "❌ Erro ao garantir coluna landingpage_store em cadastros.empresas: %s",
                e,
                exc_info=True,
            )

        logger.info("✅ Processo de criação de tabelas concluído.")
    except Exception as e:
        logger.error(f"❌ Erro geral ao criar tabelas: {e}", exc_info=True)

def criar_tabelas_chatbot():
    """Cria as tabelas do chatbot usando a função de inicialização do módulo chatbot"""
    try:
        logger.info("🤖 Inicializando tabelas do schema chatbot...")
        from app.api.chatbot.core.database import init_database, seed_default_prompts
        
        with SessionLocal() as session:
            success = init_database(session)
            if success:
                # Semeia prompts padrão
                seed_default_prompts(session)
                logger.info("✅ Tabelas do chatbot criadas/verificadas com sucesso")
            else:
                logger.error("❌ Erro ao criar tabelas do chatbot")
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas do chatbot: {e}", exc_info=True)

def criar_usuario_admin_padrao():
    """Cria o usuário 'admin' com senha padrão caso não exista."""
    try:
        with engine.connect() as conn:
            exists = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'cadastros' AND table_name = 'usuarios'
                    """
                )
            ).scalar()
            if not exists:
                logger.warning("⚠️ Tabela cadastros.usuarios não existe; pulando criação do usuário admin padrão.")
                return

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
                logger.info("✅ Usuário admin criado com sucesso.")
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

        # Importa o modelo para garantir que esteja registrado no Base
        # A tabela será criada automaticamente pelos imports

        dados_meios_pagamento = [
            {
                "nome": "Cartão Débito",
                "tipo": "CARTAO_ENTREGA",
                "ativo": True,
            },
            {
                "nome": "Cartão Crédito",
                "tipo": "CARTAO_ENTREGA",
                "ativo": True,
            },
            {
                "nome": "Pix Entrega",
                "tipo": "PIX_ENTREGA",
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
            }
        ]
#
        with engine.connect() as conn:
            exists = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'cadastros' AND table_name = 'meios_pagamento'
                    """
                )
            ).scalar()
            if not exists:
                logger.warning("⚠️ Tabela cadastros.meios_pagamento não existe; pulando seed de meios de pagamento.")
                return

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
    logger.info("📦 Passo 1/8: Configurando timezone do banco...")
    configurar_timezone()
    
    # Habilita PostGIS primeiro (necessário para tipos geography)
    logger.info("📦 Passo 2/8: Habilitando extensão PostGIS...")
    postgis_disponivel = habilitar_postgis()
    
    # SEMPRE cria/verifica os schemas primeiro
    logger.info("📦 Passo 3/8: Criando/verificando schemas...")
    criar_schemas()
    
    # Cria os ENUMs antes de criar as tabelas
    logger.info("📦 Passo 4/8: Criando/verificando ENUMs...")
    criar_enums()
    
    # SEMPRE cria as tabelas (criar_tabelas usa checkfirst=True, então não sobrescreve)
    logger.info("📋 Passo 5/8: Criando/verificando todas as tabelas...")
    criar_tabelas(postgis_disponivel=postgis_disponivel)

    # Se as tabelas essenciais não existirem, não adianta seguir com seed.
    if not verificar_banco_inicializado():
        logger.error("❌ Banco não está inicializado (tabelas principais ausentes). Abortando passos 6-8.")
        return
    
    # Cria tabelas do chatbot (que não usam modelos SQLAlchemy)
    logger.info("🤖 Passo 6/8: Criando/verificando tabelas do chatbot...")
    criar_tabelas_chatbot()
    
    logger.info("👤 Passo 7/8: Garantindo usuário admin padrão...")
    criar_usuario_admin_padrao()
    
    # Dados iniciais de meios de pagamento
    logger.info("💳 Passo 8/8: Criando/verificando meios de pagamento padrão...")
    criar_meios_pagamento_padrao()

    # Catálogo de permissões (idempotente)
    logger.info("🔐 Seed: Criando/verificando permissões padrão...")
    criar_permissoes_padrao()
    
    logger.info("✅ Banco inicializado com sucesso.")
