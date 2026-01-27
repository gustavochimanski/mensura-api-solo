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


def garantir_colunas_whatsapp_configs():
    """Garante colunas necessárias para configuração do WhatsApp/360dialog."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    ALTER TABLE notifications.whatsapp_configs
                    ALTER COLUMN access_token DROP NOT NULL,
                    ADD COLUMN IF NOT EXISTS webhook_url varchar,
                    ADD COLUMN IF NOT EXISTS webhook_verify_token varchar,
                    ADD COLUMN IF NOT EXISTS webhook_header_key varchar,
                    ADD COLUMN IF NOT EXISTS webhook_header_value text,
                    ADD COLUMN IF NOT EXISTS webhook_is_active boolean DEFAULT false,
                    ADD COLUMN IF NOT EXISTS webhook_status varchar DEFAULT 'pending',
                    ADD COLUMN IF NOT EXISTS webhook_last_sync timestamp without time zone
                    """
                )
            )
        logger.info("✅ Colunas de webhook em notifications.whatsapp_configs criadas/verificadas")
    except Exception as e:
        logger.error("❌ Erro ao garantir colunas de webhook em notifications.whatsapp_configs: %s", e)

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
        from app.api.pedidos.models.model_pedido_item_complemento import PedidoItemComplementoModel
        from app.api.pedidos.models.model_pedido_item_complemento_adicional import PedidoItemComplementoAdicionalModel
        
        # Tabelas de pedidos foram movidas para o schema pedidos
        cardapio_tables = [
            TransacaoPagamentoModel.__table__
        ]
        
        # Tabelas do schema pedidos (modelos unificados)
        pedidos_tables = [
            PedidoUnificadoModel.__table__,
            PedidoItemUnificadoModel.__table__,
            PedidoHistoricoUnificadoModel.__table__,
            PedidoItemComplementoModel.__table__,
            PedidoItemComplementoAdicionalModel.__table__,
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

def criar_tabela_pedidos_sem_postgis():
    """
    Tenta criar a tabela pedidos.pedidos sem a coluna Geography quando PostGIS não está disponível.
    Esta é uma solução de fallback para permitir que a aplicação funcione sem PostGIS.
    """
    try:
        logger.info("⚠️ Tentando criar tabela pedidos.pedidos sem coluna Geography...")
        with engine.begin() as conn:
            # Verifica se a tabela já existe
            result = conn.execute(text("""
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'pedidos' 
                AND table_name = 'pedidos'
            """))
            if result.scalar():
                logger.info("ℹ️ Tabela pedidos.pedidos já existe")
                return True
            
            # Tenta criar a tabela sem a coluna Geography
            # Nota: Esta é uma versão simplificada - pode precisar de ajustes baseado no modelo completo
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pedidos.pedidos (
                    id SERIAL PRIMARY KEY,
                    tipo_entrega pedidos.tipo_entrega_enum NOT NULL,
                    empresa_id INTEGER NOT NULL REFERENCES cadastros.empresas(id) ON DELETE RESTRICT,
                    numero_pedido VARCHAR(20) NOT NULL,
                    status pedidos.pedido_status_enum NOT NULL DEFAULT 'P',
                    mesa_id INTEGER REFERENCES cadastros.mesas(id) ON DELETE SET NULL,
                    cliente_id INTEGER REFERENCES cadastros.clientes(id) ON DELETE SET NULL,
                    endereco_id INTEGER REFERENCES cadastros.enderecos(id) ON DELETE SET NULL,
                    entregador_id INTEGER REFERENCES cadastros.entregadores_dv(id) ON DELETE SET NULL,
                    meio_pagamento_id INTEGER REFERENCES cadastros.meios_pagamento(id) ON DELETE SET NULL,
                    cupom_id INTEGER REFERENCES cadastros.cupons_dv(id) ON DELETE SET NULL,
                    canal pedidos.canal_pedido_enum,
                    observacoes VARCHAR(500),
                    observacao_geral VARCHAR(255),
                    num_pessoas INTEGER,
                    subtotal NUMERIC(18, 2) NOT NULL DEFAULT 0,
                    desconto NUMERIC(18, 2) NOT NULL DEFAULT 0,
                    taxa_entrega NUMERIC(18, 2) NOT NULL DEFAULT 0,
                    taxa_servico NUMERIC(18, 2) NOT NULL DEFAULT 0,
                    valor_total NUMERIC(18, 2) NOT NULL DEFAULT 0,
                    troco_para NUMERIC(18, 2),
                    previsao_entrega TIMESTAMP WITH TIME ZONE,
                    distancia_km NUMERIC(10, 3),
                    endereco_snapshot JSONB,
                    -- endereco_geo omitido (requer PostGIS)
                    acertado_entregador BOOLEAN NOT NULL DEFAULT false,
                    acertado_entregador_em TIMESTAMP WITH TIME ZONE,
                    pago BOOLEAN NOT NULL DEFAULT false,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    CONSTRAINT uq_pedidos_empresa_numero UNIQUE (empresa_id, numero_pedido)
                );
                
                CREATE INDEX IF NOT EXISTS idx_pedidos_empresa ON pedidos.pedidos(empresa_id);
                CREATE INDEX IF NOT EXISTS idx_pedidos_empresa_tipo_status ON pedidos.pedidos(empresa_id, tipo_entrega, status);
                CREATE INDEX IF NOT EXISTS idx_pedidos_tipo_status ON pedidos.pedidos(tipo_entrega, status);
                CREATE INDEX IF NOT EXISTS idx_pedidos_numero ON pedidos.pedidos(empresa_id, numero_pedido);
                CREATE INDEX IF NOT EXISTS idx_pedidos_endereco_snapshot_gin ON pedidos.pedidos USING gin(endereco_snapshot);
                -- Índice endereco_geo omitido (requer PostGIS)
            """))
        logger.info("✅ Tabela pedidos.pedidos criada sem coluna Geography")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabela pedidos.pedidos sem PostGIS: {e}", exc_info=True)
        return False

def criar_tabelas(postgis_disponivel: bool = True):
    try:
        importar_models()  # importa só os seus models de mensura e cardapio

        # Nota: Se PostGIS não estiver disponível, tabelas com colunas Geography falharão na criação
        # mas o erro será tratado especificamente abaixo

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
        
        # Exclui a tabela adicionais que não é mais usada
        # Adicionais agora são vínculos de produtos/receitas/combos em complementos (complemento_vinculo_item)
        # Filtra a tabela da lista de tabelas a criar (não pode deletar do metadata pois é imutável)
        tabelas_antes = len(ordered_tables)
        ordered_tables = [t for t in ordered_tables if not (t.schema == "catalogo" and t.name == "adicionais")]
        if len(ordered_tables) < tabelas_antes:
            logger.info("⚠️ Tabela catalogo.adicionais filtrada da criação (não é mais usada)")

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
                error_msg = str(table_error)
                # Verifica se o erro é relacionado ao tipo Geography e PostGIS não está disponível
                is_geography_error = ("geography" in error_msg.lower() or 
                                     ("type" in error_msg.lower() and "does not exist" in error_msg.lower()) or
                                     "postgis" in error_msg.lower())
                
                if not postgis_disponivel and is_geography_error and table.name == "pedidos" and table.schema == "pedidos":
                    logger.warning(f"⚠️ Tabela {table.schema}.{table.name} requer PostGIS mas PostGIS não está disponível.")
                    logger.warning(f"⚠️ Tentando criar versão simplificada sem coluna Geography...")
                    # Tenta criar a tabela sem a coluna Geography
                    if criar_tabela_pedidos_sem_postgis():
                        logger.info(f"✅ Tabela {table.schema}.{table.name} criada sem PostGIS (funcionalidades geográficas desabilitadas)")
                    else:
                        logger.error(f"❌ Não foi possível criar tabela {table.schema}.{table.name} mesmo sem PostGIS")
                        tabelas_com_erro.append((table, table_error))
                elif not postgis_disponivel and is_geography_error:
                    logger.warning(f"⚠️ Tabela {table.schema}.{table.name} requer PostGIS mas PostGIS não está disponível.")
                    logger.warning(f"⚠️ Pulando criação desta tabela. Funcionalidades geográficas estarão desabilitadas.")
                    # Verifica se a tabela já existe
                    try:
                        with engine.connect() as conn:
                            result = conn.execute(text("""
                                SELECT 1 FROM information_schema.tables 
                                WHERE table_schema = :schema 
                                AND table_name = :table_name
                            """), {"schema": table.schema, "table_name": table.name})
                            existe = result.scalar()
                            if existe:
                                logger.info(f"ℹ️ Tabela {table.schema}.{table.name} já existe")
                            else:
                                logger.warning(f"⚠️ Tabela {table.schema}.{table.name} não pode ser criada sem PostGIS")
                    except Exception as check_error:
                        logger.warning(f"⚠️ Erro ao verificar existência da tabela: {check_error}")
                else:
                    logger.error(f"❌ Erro ao criar tabela {table.schema}.{table.name}: {table_error}", exc_info=True)
                    tabelas_com_erro.append((table, table_error))

        # Segunda tentativa para tabelas que falharam (apenas se não for erro de PostGIS)
        if tabelas_com_erro:
            logger.info(f"🔄 Segunda tentativa para {len(tabelas_com_erro)} tabelas com erro...")
            for table, error in tabelas_com_erro:
                try:
                    table.create(engine, checkfirst=True)
                    logger.info(f"✅ Tabela {table.schema}.{table.name} criada/verificada (2ª tentativa)")
                except Exception as table_error:
                    logger.error(f"❌ Erro persistente na tabela {table.schema}.{table.name}: {table_error}", exc_info=True)

        # Garante colunas específicas do 360dialog (webhook) na tabela whatsapp_configs
        garantir_colunas_whatsapp_configs()

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
                from app.api.pedidos.models.model_pedido_item_complemento import PedidoItemComplementoModel
                from app.api.pedidos.models.model_pedido_item_complemento_adicional import PedidoItemComplementoAdicionalModel
                
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
                    PedidoItemComplementoModel.__table__,
                    PedidoItemComplementoAdicionalModel.__table__,
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

        # Garante criação de vitrines_landingpage_store e link tables (podem falhar no loop geral)
        try:
            from app.api.cardapio.models.model_vitrine import VitrinesLandingpageStoreModel
            from app.api.cadastros.models.association_tables import (
                VitrineLandingProdutoLink,
                VitrineLandingComboLink,
                VitrineLandingReceitaLink,
            )
            VitrinesLandingpageStoreModel.__table__.create(engine, checkfirst=True)
            VitrineLandingProdutoLink.__table__.create(engine, checkfirst=True)
            VitrineLandingComboLink.__table__.create(engine, checkfirst=True)
            VitrineLandingReceitaLink.__table__.create(engine, checkfirst=True)
            logger.info("✅ Tabelas vitrines_landingpage_store e vitrine_landing_* criadas/verificadas")
        except Exception as e:
            logger.warning("⚠️ Erro ao garantir tabelas vitrines_landingpage_store / link: %s", e)

        # Garante multi-tenant (empresa_id) em categorias/vitrines do cardápio
        try:
            with engine.begin() as conn:
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

        # Garante colunas de redirecionamento de home em cadastros.empresas
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        ALTER TABLE cadastros.empresas
                        ADD COLUMN IF NOT EXISTS redireciona_home boolean NOT NULL DEFAULT false,
                        ADD COLUMN IF NOT EXISTS redireciona_home_para varchar(255)
                        """
                    )
                )
            logger.info("✅ Colunas redireciona_home/redireciona_home_para em cadastros.empresas criadas/verificadas com sucesso")
        except Exception as e:
            logger.error(
                "❌ Erro ao garantir colunas redireciona_home/redireciona_home_para em cadastros.empresas: %s",
                e,
                exc_info=True,
            )

        # Garante landingpage_store e remove redireciona_categoria em cadastros.parceiros_banner
        # Ordem: 1) DROP coluna antiga; 2) ADD coluna nova (cada um em execute separado)
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE cadastros.parceiros_banner DROP COLUMN IF EXISTS redireciona_categoria"))
                conn.execute(text("ALTER TABLE cadastros.parceiros_banner ADD COLUMN IF NOT EXISTS landingpage_store boolean NOT NULL DEFAULT false"))
            logger.info("✅ Coluna landingpage_store em cadastros.parceiros_banner criada/verificada e redireciona_categoria removida (se existia)")
        except Exception as e:
            logger.error(
                "❌ Erro ao garantir coluna landingpage_store / remover redireciona_categoria em cadastros.parceiros_banner: %s",
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

        # Garante que a tabela existe antes de inserir dados
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'cadastros' 
                    AND table_name = 'meios_pagamento'
                """))
                existe = result.scalar()
                
                if not existe:
                    logger.info("📋 Criando tabela cadastros.meios_pagamento...")
                    MeioPagamentoModel.__table__.create(engine, checkfirst=True)
                    logger.info("✅ Tabela cadastros.meios_pagamento criada com sucesso")
                else:
                    logger.info("ℹ️ Tabela cadastros.meios_pagamento já existe")
        except Exception as table_err:
            logger.error(f"❌ Erro ao verificar/criar tabela cadastros.meios_pagamento: {table_err}", exc_info=True)
            # Tenta criar mesmo assim
            try:
                MeioPagamentoModel.__table__.create(engine, checkfirst=True)
                logger.info("✅ Tabela cadastros.meios_pagamento criada (2ª tentativa)")
            except Exception as e2:
                logger.error(f"❌ Erro persistente ao criar tabela: {e2}", exc_info=True)
                raise

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
    
    # Cria tabelas do chatbot (que não usam modelos SQLAlchemy)
    logger.info("🤖 Passo 6/8: Criando/verificando tabelas do chatbot...")
    criar_tabelas_chatbot()
    
    logger.info("👤 Passo 7/8: Garantindo usuário admin padrão...")
    criar_usuario_admin_padrao()
    
    # Dados iniciais de meios de pagamento
    logger.info("💳 Passo 8/8: Criando/verificando meios de pagamento padrão...")
    criar_meios_pagamento_padrao()
    
    logger.info("✅ Banco inicializado com sucesso.")
