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
def _table_exists(conn, schema: str, table_name: str) -> bool:
    """
    Helper global para checar existência de tabela.

    Importante: várias rotinas de seed/migração são chamadas fora do escopo de `criar_tabelas()`,
    então este helper precisa existir no módulo (não apenas como função interna).
    """
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
            # A partir de agora, o catálogo deve conter APENAS permissões por rota (route:/...).
            # Remove permissões antigas por domínio (<dominio>:*) e legados (ex: relatorios:read).
            # Observação: isso pode remover grants antigos (CASCADE via FK em user_permissions).
            session.query(PermissionModel).filter(~PermissionModel.key.like("route:%")).delete(
                synchronize_session=False
            )

            # Preferimos UPSERT (atualiza domain/description) quando o banco tiver constraint/índice adequado.
            # Para bancos legados que ainda não têm UNIQUE em `permissions.key`, caímos num fallback sem ON CONFLICT.
            try:
                for row in rows:
                    stmt = insert(PermissionModel).values(**row)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=[PermissionModel.key],
                        set_={
                            "domain": stmt.excluded.domain,
                            "description": stmt.excluded.description,
                        },
                    )
                    session.execute(stmt)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.warning(
                    "⚠️ Seed de permissões: UPSERT falhou; aplicando fallback sem ON CONFLICT. Motivo: %s",
                    e,
                )
                if rows:
                    values_sql = []
                    params: dict = {}
                    for i, r in enumerate(rows):
                        values_sql.append(f"(:key{i}, :domain{i}, :description{i})")
                        params[f"key{i}"] = r["key"]
                        params[f"domain{i}"] = r["domain"]
                        params[f"description{i}"] = r.get("description")

                    session.execute(
                        text(
                            f"""
                            WITH data(key, domain, description) AS (
                              VALUES {", ".join(values_sql)}
                            )
                            INSERT INTO cadastros.permissions (key, domain, description)
                            SELECT d.key, d.domain, d.description
                            FROM data d
                            LEFT JOIN cadastros.permissions p ON p.key = d.key
                            WHERE p.key IS NULL
                            """
                        ),
                        params,
                    )
                    session.commit()

        logger.info("✅ Permissões padrão criadas/verificadas com sucesso (%s).", len(rows))
    except Exception as e:
        logger.error(f"❌ Erro ao criar permissões padrão: {e}", exc_info=True)


def criar_usuario_secreto_com_todas_permissoes():
    """
    Cria/garante um usuário de bootstrap:

    - username: secreto
    - senha: 171717
    - type_user: funcionario
    - vínculo: todas as empresas existentes (cadastros.usuario_empresa)
    - permissões: todas as permissões do catálogo `route:*` para cada empresa (cadastros.user_permissions)

    Observação: este seed é idempotente e pode ser executado múltiplas vezes.
    """
    try:
        # Pré-checagem de tabelas (evita stacktrace em bancos parciais)
        with engine.connect() as conn:
            required = [
                ("cadastros", "usuarios"),
                ("cadastros", "empresas"),
                ("cadastros", "permissions"),
                ("cadastros", "usuario_empresa"),
                ("cadastros", "user_permissions"),
            ]
            for schema, table in required:
                exists = conn.execute(
                    text(
                        """
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = :schema AND table_name = :table
                        """
                    ),
                    {"schema": schema, "table": table},
                ).scalar()
                if not exists:
                    logger.warning(
                        "⚠️ Tabela %s.%s não existe; pulando seed do usuário 'secreto'.",
                        schema,
                        table,
                    )
                    return

        with SessionLocal() as session:
            # 1) Cria/atualiza usuário
            user = session.query(UserModel).filter(UserModel.username == "secreto").first()
            if not user:
                user = UserModel(
                    username="secreto",
                    hashed_password=hash_password("171717"),
                    type_user="funcionario",
                )
                session.add(user)
                session.flush()
                logger.info("✅ Seed: usuário 'secreto' criado (id=%s).", getattr(user, "id", None))
            else:
                user.type_user = "funcionario"
                # Mantém a senha do seed sempre consistente (idempotente e previsível)
                user.hashed_password = hash_password("171717")
                session.flush()
                logger.info("✅ Seed: usuário 'secreto' atualizado (id=%s).", getattr(user, "id", None))

            user_id = int(getattr(user, "id", 0) or 0)
            if user_id <= 0:
                raise RuntimeError("Falha ao obter user_id do usuário 'secreto'.")

            # 2) Vincula usuário a todas as empresas (idempotente)
            session.execute(
                text(
                    """
                    INSERT INTO cadastros.usuario_empresa (usuario_id, empresa_id)
                    SELECT :user_id, e.id
                    FROM cadastros.empresas e
                    WHERE NOT EXISTS (
                      SELECT 1
                      FROM cadastros.usuario_empresa ue
                      WHERE ue.usuario_id = :user_id AND ue.empresa_id = e.id
                    )
                    """
                ),
                {"user_id": user_id},
            )

            # 3) Concede todas as permissões do catálogo `route:*` para cada empresa (idempotente)
            session.execute(
                text(
                    """
                    INSERT INTO cadastros.user_permissions (user_id, empresa_id, permission_id)
                    SELECT :user_id, e.id, p.id
                    FROM cadastros.empresas e
                    CROSS JOIN cadastros.permissions p
                    WHERE p.key LIKE 'route:%'
                    AND NOT EXISTS (
                      SELECT 1
                      FROM cadastros.user_permissions up
                      WHERE up.user_id = :user_id
                        AND up.empresa_id = e.id
                        AND up.permission_id = p.id
                    )
                    """
                ),
                {"user_id": user_id},
            )

            session.commit()
            logger.info("✅ Seed: usuário 'secreto' com todas as permissões aplicado com sucesso.")
    except Exception as e:
        logger.error("❌ Erro ao criar usuário 'secreto' e permissões: %s", e, exc_info=True)


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

        # ------------------------------------------------------------------
        # Migração: Produto PK técnica (id) + FKs por produto_id
        # ------------------------------------------------------------------
        try:
            with engine.begin() as conn:
                if _table_exists(conn, "catalogo", "produtos"):
                    # 1) catalogo.produtos: adiciona id + troca PK
                    conn.execute(text("ALTER TABLE catalogo.produtos ADD COLUMN IF NOT EXISTS id integer"))

                    # sequence + default + backfill + not null (idempotente)
                    conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                              IF NOT EXISTS (
                                SELECT 1
                                FROM pg_class c
                                JOIN pg_namespace n ON n.oid = c.relnamespace
                                WHERE n.nspname = 'catalogo'
                                  AND c.relkind = 'S'
                                  AND c.relname = 'produtos_id_seq'
                              ) THEN
                                CREATE SEQUENCE catalogo.produtos_id_seq;
                              END IF;

                              -- default para novos registros
                              BEGIN
                                ALTER TABLE catalogo.produtos
                                  ALTER COLUMN id SET DEFAULT nextval('catalogo.produtos_id_seq');
                              EXCEPTION WHEN others THEN
                                -- ignora se não conseguir (ex.: permissões)
                                NULL;
                              END;

                              -- backfill para registros antigos
                              UPDATE catalogo.produtos
                              SET id = nextval('catalogo.produtos_id_seq')
                              WHERE id IS NULL;

                              -- ajusta sequência para MAX(id)
                              -- IMPORTANTE: `setval(..., 0, true)` quebra (sequence não aceita 0).
                              -- Se a tabela estiver vazia, posiciona em 1 com is_called=false.
                              DECLARE max_id bigint;
                              BEGIN
                                SELECT MAX(id) INTO max_id FROM catalogo.produtos;
                                IF max_id IS NULL OR max_id < 1 THEN
                                  PERFORM setval('catalogo.produtos_id_seq', 1, false);
                                ELSE
                                  PERFORM setval('catalogo.produtos_id_seq', max_id, true);
                                END IF;
                              END;

                              -- garante NOT NULL
                              BEGIN
                                ALTER TABLE catalogo.produtos ALTER COLUMN id SET NOT NULL;
                              EXCEPTION WHEN others THEN
                                NULL;
                              END;
                            END$$;
                            """
                        )
                    )

                    # IMPORTANTE:
                    # - Neste ponto ainda podem existir FKs legadas apontando para produtos(cod_barras),
                    #   que dependem do índice/constraint da PK atual (geralmente em cod_barras).
                    # - Para conseguir criar as FKs novas (produto_id -> produtos.id) sem derrubar
                    #   a PK antiga ainda, garantimos UMA UNIQUE em (id).
                    # - A troca efetiva da PK para (id) é feita no final da migração, após remover
                    #   as FKs legadas em cod_barras.
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
                                WHERE n.nspname = 'catalogo'
                                  AND t.relname = 'produtos'
                                  AND c.conname = 'uq_produtos_id'
                              ) THEN
                                ALTER TABLE catalogo.produtos
                                  ADD CONSTRAINT uq_produtos_id UNIQUE (id);
                              END IF;
                            END$$;
                            """
                        )
                    )

                # 2) catalogo.produtos_empresa: adiciona produto_id + troca PK + FK nova
                if _table_exists(conn, "catalogo", "produtos_empresa") and _table_exists(conn, "catalogo", "produtos"):
                    conn.execute(text("ALTER TABLE catalogo.produtos_empresa ADD COLUMN IF NOT EXISTS produto_id integer"))

                    conn.execute(
                        text(
                            """
                            UPDATE catalogo.produtos_empresa pe
                            SET produto_id = p.id
                            FROM catalogo.produtos p
                            WHERE pe.produto_id IS NULL
                              AND pe.cod_barras = p.cod_barras;
                            """
                        )
                    )

                    # garante NOT NULL (quando possível)
                    conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                              IF EXISTS (
                                SELECT 1
                                FROM information_schema.columns
                                WHERE table_schema='catalogo' AND table_name='produtos_empresa' AND column_name='produto_id'
                              ) THEN
                                -- só tenta se não houver NULLs restantes
                                IF NOT EXISTS (SELECT 1 FROM catalogo.produtos_empresa WHERE produto_id IS NULL LIMIT 1) THEN
                                  ALTER TABLE catalogo.produtos_empresa ALTER COLUMN produto_id SET NOT NULL;
                                END IF;
                              END IF;
                            END$$;
                            """
                        )
                    )

                    # remove FK antiga (cod_barras -> produtos.cod_barras), se existir
                    conn.execute(
                        text(
                            """
                            DO $$
                            DECLARE fk_name text;
                            BEGIN
                              SELECT c.conname INTO fk_name
                              FROM pg_constraint c
                              JOIN pg_class t ON t.oid = c.conrelid
                              JOIN pg_namespace n ON n.oid = t.relnamespace
                              WHERE n.nspname = 'catalogo'
                                AND t.relname = 'produtos_empresa'
                                AND c.contype = 'f'
                                AND pg_get_constraintdef(c.oid) LIKE '%REFERENCES catalogo.produtos(cod_barras)%'
                              LIMIT 1;
                              IF fk_name IS NOT NULL THEN
                                EXECUTE format('ALTER TABLE catalogo.produtos_empresa DROP CONSTRAINT IF EXISTS %I', fk_name);
                              END IF;
                            END$$;
                            """
                        )
                    )

                    # FK nova (produto_id -> produtos.id)
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
                                WHERE n.nspname = 'catalogo'
                                  AND t.relname = 'produtos_empresa'
                                  AND c.conname = 'fk_produtos_empresa_produto_id'
                              ) THEN
                                ALTER TABLE catalogo.produtos_empresa
                                  ADD CONSTRAINT fk_produtos_empresa_produto_id
                                  FOREIGN KEY (produto_id)
                                  REFERENCES catalogo.produtos(id)
                                  ON DELETE CASCADE;
                              END IF;
                            END$$;
                            """
                        )
                    )

                    # Troca PK para (empresa_id, produto_id)
                    conn.execute(
                        text(
                            """
                            DO $$
                            DECLARE pk_name text;
                            DECLARE pk_def text;
                            BEGIN
                              SELECT c.conname, pg_get_constraintdef(c.oid)
                              INTO pk_name, pk_def
                              FROM pg_constraint c
                              JOIN pg_class t ON t.oid = c.conrelid
                              JOIN pg_namespace n ON n.oid = t.relnamespace
                              WHERE n.nspname = 'catalogo'
                                AND t.relname = 'produtos_empresa'
                                AND c.contype = 'p'
                              LIMIT 1;
                              -- Só derruba PK se ela NÃO for a esperada (empresa_id, produto_id)
                              IF pk_name IS NOT NULL AND (pk_def IS NULL OR pk_def NOT ILIKE '%(empresa_id, produto_id)%') THEN
                                EXECUTE format('ALTER TABLE catalogo.produtos_empresa DROP CONSTRAINT IF EXISTS %I', pk_name);
                              END IF;
                              IF NOT EXISTS (
                                SELECT 1
                                FROM pg_constraint c
                                JOIN pg_class t ON t.oid = c.conrelid
                                JOIN pg_namespace n ON n.oid = t.relnamespace
                                WHERE n.nspname = 'catalogo'
                                  AND t.relname = 'produtos_empresa'
                                  AND c.contype = 'p'
                              ) THEN
                                ALTER TABLE catalogo.produtos_empresa
                                  ADD CONSTRAINT produtos_empresa_pkey PRIMARY KEY (empresa_id, produto_id);
                              END IF;
                            END$$;
                            """
                        )
                    )

                    # Unicidade por (empresa_id, cod_barras) para compatibilidade de busca
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
                                WHERE n.nspname='catalogo'
                                  AND t.relname='produtos_empresa'
                                  AND c.conname='uq_produtos_empresa_empresa_cod_barras'
                              ) THEN
                                ALTER TABLE catalogo.produtos_empresa
                                  ADD CONSTRAINT uq_produtos_empresa_empresa_cod_barras
                                  UNIQUE (empresa_id, cod_barras);
                              END IF;
                            END$$;
                            """
                        )
                    )

                # 3) catalogo.produto_complemento_link: adiciona produto_id + troca PK + FK nova
                if _table_exists(conn, "catalogo", "produto_complemento_link") and _table_exists(conn, "catalogo", "produtos"):
                    conn.execute(text("ALTER TABLE catalogo.produto_complemento_link ADD COLUMN IF NOT EXISTS produto_id integer"))
                    # backfill (quando vier do esquema antigo com `produto_cod_barras`)
                    conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                              IF EXISTS (
                                SELECT 1
                                FROM information_schema.columns
                                WHERE table_schema='catalogo'
                                  AND table_name='produto_complemento_link'
                                  AND column_name='produto_cod_barras'
                              ) THEN
                                UPDATE catalogo.produto_complemento_link l
                                SET produto_id = p.id
                                FROM catalogo.produtos p
                                WHERE l.produto_id IS NULL
                                  AND l.produto_cod_barras = p.cod_barras;
                              END IF;
                            END$$;
                            """
                        )
                    )
                    # FK antiga (produto_cod_barras -> produtos.cod_barras), se existir
                    conn.execute(
                        text(
                            """
                            DO $$
                            DECLARE fk_name text;
                            BEGIN
                              SELECT c.conname INTO fk_name
                              FROM pg_constraint c
                              JOIN pg_class t ON t.oid = c.conrelid
                              JOIN pg_namespace n ON n.oid = t.relnamespace
                              WHERE n.nspname = 'catalogo'
                                AND t.relname = 'produto_complemento_link'
                                AND c.contype = 'f'
                                AND pg_get_constraintdef(c.oid) LIKE '%REFERENCES catalogo.produtos(cod_barras)%'
                              LIMIT 1;
                              IF fk_name IS NOT NULL THEN
                                EXECUTE format('ALTER TABLE catalogo.produto_complemento_link DROP CONSTRAINT IF EXISTS %I', fk_name);
                              END IF;
                            END$$;
                            """
                        )
                    )
                    # FK nova
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
                                WHERE n.nspname='catalogo'
                                  AND t.relname='produto_complemento_link'
                                  AND c.conname='fk_produto_complemento_link_produto_id'
                              ) THEN
                                ALTER TABLE catalogo.produto_complemento_link
                                  ADD CONSTRAINT fk_produto_complemento_link_produto_id
                                  FOREIGN KEY (produto_id)
                                  REFERENCES catalogo.produtos(id)
                                  ON DELETE CASCADE;
                              END IF;
                            END$$;
                            """
                        )
                    )
                    # PK -> (produto_id, complemento_id)
                    conn.execute(
                        text(
                            """
                            DO $$
                            DECLARE pk_name text;
                            DECLARE pk_def text;
                            BEGIN
                              SELECT c.conname, pg_get_constraintdef(c.oid)
                              INTO pk_name, pk_def
                              FROM pg_constraint c
                              JOIN pg_class t ON t.oid = c.conrelid
                              JOIN pg_namespace n ON n.oid = t.relnamespace
                              WHERE n.nspname='catalogo'
                                AND t.relname='produto_complemento_link'
                                AND c.contype='p'
                              LIMIT 1;
                              -- Só derruba PK se ela NÃO for a esperada (produto_id, complemento_id)
                              IF pk_name IS NOT NULL AND (pk_def IS NULL OR pk_def NOT ILIKE '%(produto_id, complemento_id)%') THEN
                                EXECUTE format('ALTER TABLE catalogo.produto_complemento_link DROP CONSTRAINT IF EXISTS %I', pk_name);
                              END IF;
                              IF NOT EXISTS (
                                SELECT 1
                                FROM pg_constraint c
                                JOIN pg_class t ON t.oid=c.conrelid
                                JOIN pg_namespace n ON n.oid=t.relnamespace
                                WHERE n.nspname='catalogo'
                                  AND t.relname='produto_complemento_link'
                                  AND c.contype='p'
                              ) THEN
                                ALTER TABLE catalogo.produto_complemento_link
                                  ADD CONSTRAINT produto_complemento_link_pkey PRIMARY KEY (produto_id, complemento_id);
                              END IF;
                            END$$;
                            """
                        )
                    )
                    # Remove coluna legado (evita inserts quebrarem por NOT NULL/PK antigo)
                    conn.execute(text("ALTER TABLE catalogo.produto_complemento_link DROP COLUMN IF EXISTS produto_cod_barras"))

                # 4) cardapio.vitrine_produto + cardapio.vitrine_landing_produto: migra para produto_id
                for table_name, pk_name, fk_name in (
                    ("vitrine_produto", "pk_vitrine_produto", "fk_vitrine_produto_produto_id"),
                    ("vitrine_landing_produto", "pk_vitrine_landing_produto", "fk_vitrine_landing_produto_produto_id"),
                ):
                    if _table_exists(conn, "cardapio", table_name) and _table_exists(conn, "catalogo", "produtos"):
                        conn.execute(text(f"ALTER TABLE cardapio.{table_name} ADD COLUMN IF NOT EXISTS produto_id integer"))

                        has_cod_barras = (
                            conn.execute(
                                text(
                                    """
                                    SELECT 1
                                    FROM information_schema.columns
                                    WHERE table_schema='cardapio'
                                      AND table_name=:t
                                      AND column_name='cod_barras'
                                    LIMIT 1
                                    """
                                ),
                                {"t": table_name},
                            ).scalar()
                            is not None
                        )

                        if has_cod_barras:
                            # backfill baseado em cod_barras (esquema legado)
                            conn.execute(
                                text(
                                    f"""
                                    UPDATE cardapio.{table_name} vp
                                    SET produto_id = p.id
                                    FROM catalogo.produtos p
                                    WHERE vp.produto_id IS NULL
                                      AND vp.cod_barras = p.cod_barras;
                                    """
                                )
                            )

                            # remove FK antiga em cod_barras, se existir
                            conn.execute(
                                text(
                                    f"""
                                    DO $$
                                    DECLARE fk_old text;
                                    BEGIN
                                      SELECT c.conname INTO fk_old
                                      FROM pg_constraint c
                                      JOIN pg_class t ON t.oid=c.conrelid
                                      JOIN pg_namespace n ON n.oid=t.relnamespace
                                      WHERE n.nspname='cardapio'
                                        AND t.relname='{table_name}'
                                        AND c.contype='f'
                                        AND pg_get_constraintdef(c.oid) LIKE '%REFERENCES catalogo.produtos(cod_barras)%'
                                      LIMIT 1;
                                      IF fk_old IS NOT NULL THEN
                                        EXECUTE format('ALTER TABLE cardapio.{table_name} DROP CONSTRAINT IF EXISTS %I', fk_old);
                                      END IF;
                                    END$$;
                                    """
                                )
                            )

                        # FK nova em produto_id
                        conn.execute(
                            text(
                                f"""
                                DO $$
                                BEGIN
                                  IF NOT EXISTS (
                                    SELECT 1
                                    FROM pg_constraint c
                                    JOIN pg_class t ON t.oid=c.conrelid
                                    JOIN pg_namespace n ON n.oid=t.relnamespace
                                    WHERE n.nspname='cardapio'
                                      AND t.relname='{table_name}'
                                      AND c.conname='{fk_name}'
                                  ) THEN
                                    ALTER TABLE cardapio.{table_name}
                                      ADD CONSTRAINT {fk_name}
                                      FOREIGN KEY (produto_id)
                                      REFERENCES catalogo.produtos(id)
                                      ON DELETE CASCADE;
                                  END IF;
                                END$$;
                                """
                            )
                        )

                        # PK -> (vitrine_id, produto_id) (só precisa mexer se veio do esquema legado)
                        if has_cod_barras:
                            conn.execute(text(f"ALTER TABLE cardapio.{table_name} DROP CONSTRAINT IF EXISTS {pk_name}"))
                            conn.execute(
                                text(
                                    f"""
                                    DO $$
                                    BEGIN
                                      IF NOT EXISTS (
                                        SELECT 1
                                        FROM pg_constraint c
                                        JOIN pg_class t ON t.oid=c.conrelid
                                        JOIN pg_namespace n ON n.oid=t.relnamespace
                                        WHERE n.nspname='cardapio'
                                          AND t.relname='{table_name}'
                                          AND c.contype='p'
                                      ) THEN
                                        ALTER TABLE cardapio.{table_name}
                                          ADD CONSTRAINT {pk_name} PRIMARY KEY (vitrine_id, produto_id);
                                      END IF;
                                    END$$;
                                    """
                                )
                            )

                            # remove coluna legado (evita conflitos de NOT NULL/uso futuro)
                            conn.execute(text(f"ALTER TABLE cardapio.{table_name} DROP COLUMN IF EXISTS cod_barras"))

                        # índice para produto_id
                        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_produto_id ON cardapio.{table_name} (produto_id)"))

                # 5) Tabelas que guardam produto_cod_barras: adiciona produto_id + FK nova (mantém coluna legado como snapshot)
                # pedidos.pedidos_itens
                if _table_exists(conn, "pedidos", "pedidos_itens") and _table_exists(conn, "catalogo", "produtos"):
                    conn.execute(text("ALTER TABLE pedidos.pedidos_itens ADD COLUMN IF NOT EXISTS produto_id integer"))
                    conn.execute(
                        text(
                            """
                            UPDATE pedidos.pedidos_itens pi
                            SET produto_id = p.id
                            FROM catalogo.produtos p
                            WHERE pi.produto_id IS NULL
                              AND pi.produto_cod_barras = p.cod_barras;
                            """
                        )
                    )
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pedidos_itens_produto_id ON pedidos.pedidos_itens (produto_id)"))
                    conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                              IF NOT EXISTS (
                                SELECT 1
                                FROM pg_constraint c
                                JOIN pg_class t ON t.oid=c.conrelid
                                JOIN pg_namespace n ON n.oid=t.relnamespace
                                WHERE n.nspname='pedidos'
                                  AND t.relname='pedidos_itens'
                                  AND c.conname='fk_pedidos_itens_produto_id'
                              ) THEN
                                ALTER TABLE pedidos.pedidos_itens
                                  ADD CONSTRAINT fk_pedidos_itens_produto_id
                                  FOREIGN KEY (produto_id)
                                  REFERENCES catalogo.produtos(id)
                                  ON DELETE RESTRICT;
                              END IF;
                            END$$;
                            """
                        )
                    )
                    # Remove FK antiga (produto_cod_barras -> produtos.cod_barras), se existir
                    conn.execute(
                        text(
                            """
                            DO $$
                            DECLARE fk_old text;
                            BEGIN
                              SELECT c.conname INTO fk_old
                              FROM pg_constraint c
                              JOIN pg_class t ON t.oid=c.conrelid
                              JOIN pg_namespace n ON n.oid=t.relnamespace
                              WHERE n.nspname='pedidos'
                                AND t.relname='pedidos_itens'
                                AND c.contype='f'
                                AND pg_get_constraintdef(c.oid) LIKE '%REFERENCES catalogo.produtos(cod_barras)%'
                              LIMIT 1;
                              IF fk_old IS NOT NULL THEN
                                EXECUTE format('ALTER TABLE pedidos.pedidos_itens DROP CONSTRAINT IF EXISTS %I', fk_old);
                              END IF;
                            END$$;
                            """
                        )
                    )
                # chatbot.carrinho_itens
                if _table_exists(conn, "chatbot", "carrinho_itens") and _table_exists(conn, "catalogo", "produtos"):
                    conn.execute(text("ALTER TABLE chatbot.carrinho_itens ADD COLUMN IF NOT EXISTS produto_id integer"))
                    conn.execute(
                        text(
                            """
                            UPDATE chatbot.carrinho_itens ci
                            SET produto_id = p.id
                            FROM catalogo.produtos p
                            WHERE ci.produto_id IS NULL
                              AND ci.produto_cod_barras = p.cod_barras;
                            """
                        )
                    )
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_carrinho_itens_produto_id ON chatbot.carrinho_itens (produto_id)"))
                    conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                              IF NOT EXISTS (
                                SELECT 1
                                FROM pg_constraint c
                                JOIN pg_class t ON t.oid=c.conrelid
                                JOIN pg_namespace n ON n.oid=t.relnamespace
                                WHERE n.nspname='chatbot'
                                  AND t.relname='carrinho_itens'
                                  AND c.conname='fk_carrinho_itens_produto_id'
                              ) THEN
                                ALTER TABLE chatbot.carrinho_itens
                                  ADD CONSTRAINT fk_carrinho_itens_produto_id
                                  FOREIGN KEY (produto_id)
                                  REFERENCES catalogo.produtos(id)
                                  ON DELETE RESTRICT;
                              END IF;
                            END$$;
                            """
                        )
                    )
                    # Remove FK antiga (produto_cod_barras -> produtos.cod_barras), se existir
                    conn.execute(
                        text(
                            """
                            DO $$
                            DECLARE fk_old text;
                            BEGIN
                              SELECT c.conname INTO fk_old
                              FROM pg_constraint c
                              JOIN pg_class t ON t.oid=c.conrelid
                              JOIN pg_namespace n ON n.oid=t.relnamespace
                              WHERE n.nspname='chatbot'
                                AND t.relname='carrinho_itens'
                                AND c.contype='f'
                                AND pg_get_constraintdef(c.oid) LIKE '%REFERENCES catalogo.produtos(cod_barras)%'
                              LIMIT 1;
                              IF fk_old IS NOT NULL THEN
                                EXECUTE format('ALTER TABLE chatbot.carrinho_itens DROP CONSTRAINT IF EXISTS %I', fk_old);
                              END IF;
                            END$$;
                            """
                        )
                    )
                # catalogo.combos_itens
                if _table_exists(conn, "catalogo", "combos_itens") and _table_exists(conn, "catalogo", "produtos"):
                    conn.execute(text("ALTER TABLE catalogo.combos_itens ADD COLUMN IF NOT EXISTS produto_id integer"))
                    conn.execute(
                        text(
                            """
                            UPDATE catalogo.combos_itens ci
                            SET produto_id = p.id
                            FROM catalogo.produtos p
                            WHERE ci.produto_id IS NULL
                              AND ci.produto_cod_barras = p.cod_barras;
                            """
                        )
                    )
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_combos_itens_produto_id ON catalogo.combos_itens (produto_id)"))
                    conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                              IF NOT EXISTS (
                                SELECT 1
                                FROM pg_constraint c
                                JOIN pg_class t ON t.oid=c.conrelid
                                JOIN pg_namespace n ON n.oid=t.relnamespace
                                WHERE n.nspname='catalogo'
                                  AND t.relname='combos_itens'
                                  AND c.conname='fk_combos_itens_produto_id'
                              ) THEN
                                ALTER TABLE catalogo.combos_itens
                                  ADD CONSTRAINT fk_combos_itens_produto_id
                                  FOREIGN KEY (produto_id)
                                  REFERENCES catalogo.produtos(id)
                                  ON DELETE RESTRICT;
                              END IF;
                            END$$;
                            """
                        )
                    )
                    # Remove FK antiga (produto_cod_barras -> produtos.cod_barras), se existir
                    conn.execute(
                        text(
                            """
                            DO $$
                            DECLARE fk_old text;
                            BEGIN
                              SELECT c.conname INTO fk_old
                              FROM pg_constraint c
                              JOIN pg_class t ON t.oid=c.conrelid
                              JOIN pg_namespace n ON n.oid=t.relnamespace
                              WHERE n.nspname='catalogo'
                                AND t.relname='combos_itens'
                                AND c.contype='f'
                                AND pg_get_constraintdef(c.oid) LIKE '%REFERENCES catalogo.produtos(cod_barras)%'
                              LIMIT 1;
                              IF fk_old IS NOT NULL THEN
                                EXECUTE format('ALTER TABLE catalogo.combos_itens DROP CONSTRAINT IF EXISTS %I', fk_old);
                              END IF;
                            END$$;
                            """
                        )
                    )
                # catalogo.receita_ingrediente
                if _table_exists(conn, "catalogo", "receita_ingrediente") and _table_exists(conn, "catalogo", "produtos"):
                    conn.execute(text("ALTER TABLE catalogo.receita_ingrediente ADD COLUMN IF NOT EXISTS produto_id integer"))
                    conn.execute(
                        text(
                            """
                            UPDATE catalogo.receita_ingrediente ri
                            SET produto_id = p.id
                            FROM catalogo.produtos p
                            WHERE ri.produto_id IS NULL
                              AND ri.produto_cod_barras = p.cod_barras;
                            """
                        )
                    )
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_receita_ingrediente_produto_id ON catalogo.receita_ingrediente (produto_id)"))
                    conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                              IF NOT EXISTS (
                                SELECT 1
                                FROM pg_constraint c
                                JOIN pg_class t ON t.oid=c.conrelid
                                JOIN pg_namespace n ON n.oid=t.relnamespace
                                WHERE n.nspname='catalogo'
                                  AND t.relname='receita_ingrediente'
                                  AND c.conname='fk_receita_ingrediente_produto_id'
                              ) THEN
                                ALTER TABLE catalogo.receita_ingrediente
                                  ADD CONSTRAINT fk_receita_ingrediente_produto_id
                                  FOREIGN KEY (produto_id)
                                  REFERENCES catalogo.produtos(id)
                                  ON DELETE RESTRICT;
                              END IF;
                            END$$;
                            """
                        )
                    )
                    # Remove FK antiga (produto_cod_barras -> produtos.cod_barras), se existir
                    conn.execute(
                        text(
                            """
                            DO $$
                            DECLARE fk_old text;
                            BEGIN
                              SELECT c.conname INTO fk_old
                              FROM pg_constraint c
                              JOIN pg_class t ON t.oid=c.conrelid
                              JOIN pg_namespace n ON n.oid=t.relnamespace
                              WHERE n.nspname='catalogo'
                                AND t.relname='receita_ingrediente'
                                AND c.contype='f'
                                AND pg_get_constraintdef(c.oid) LIKE '%REFERENCES catalogo.produtos(cod_barras)%'
                              LIMIT 1;
                              IF fk_old IS NOT NULL THEN
                                EXECUTE format('ALTER TABLE catalogo.receita_ingrediente DROP CONSTRAINT IF EXISTS %I', fk_old);
                              END IF;
                            END$$;
                            """
                        )
                    )
                # catalogo.complemento_vinculo_item
                if _table_exists(conn, "catalogo", "complemento_vinculo_item") and _table_exists(conn, "catalogo", "produtos"):
                    conn.execute(text("ALTER TABLE catalogo.complemento_vinculo_item ADD COLUMN IF NOT EXISTS produto_id integer"))
                    conn.execute(
                        text(
                            """
                            UPDATE catalogo.complemento_vinculo_item cvi
                            SET produto_id = p.id
                            FROM catalogo.produtos p
                            WHERE cvi.produto_id IS NULL
                              AND cvi.produto_cod_barras = p.cod_barras;
                            """
                        )
                    )
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_complemento_vinculo_item_produto_id ON catalogo.complemento_vinculo_item (produto_id)"))
                    conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                              IF NOT EXISTS (
                                SELECT 1
                                FROM pg_constraint c
                                JOIN pg_class t ON t.oid=c.conrelid
                                JOIN pg_namespace n ON n.oid=t.relnamespace
                                WHERE n.nspname='catalogo'
                                  AND t.relname='complemento_vinculo_item'
                                  AND c.conname='fk_complemento_vinculo_item_produto_id'
                              ) THEN
                                ALTER TABLE catalogo.complemento_vinculo_item
                                  ADD CONSTRAINT fk_complemento_vinculo_item_produto_id
                                  FOREIGN KEY (produto_id)
                                  REFERENCES catalogo.produtos(id)
                                  ON DELETE RESTRICT;
                              END IF;
                            END$$;
                            """
                        )
                    )
                    # índice único novo (complemento_id, produto_id) quando produto_id existe
                    conn.execute(
                        text(
                            """
                            CREATE UNIQUE INDEX IF NOT EXISTS uq_comp_vinc_produto_id
                              ON catalogo.complemento_vinculo_item (complemento_id, produto_id)
                              WHERE produto_id IS NOT NULL;
                            """
                        )
                    )
                    # Remove FK antiga (produto_cod_barras -> produtos.cod_barras), se existir
                    conn.execute(
                        text(
                            """
                            DO $$
                            DECLARE fk_old text;
                            BEGIN
                              SELECT c.conname INTO fk_old
                              FROM pg_constraint c
                              JOIN pg_class t ON t.oid=c.conrelid
                              JOIN pg_namespace n ON n.oid=t.relnamespace
                              WHERE n.nspname='catalogo'
                                AND t.relname='complemento_vinculo_item'
                                AND c.contype='f'
                                AND pg_get_constraintdef(c.oid) LIKE '%REFERENCES catalogo.produtos(cod_barras)%'
                              LIMIT 1;
                              IF fk_old IS NOT NULL THEN
                                EXECUTE format('ALTER TABLE catalogo.complemento_vinculo_item DROP CONSTRAINT IF EXISTS %I', fk_old);
                              END IF;
                            END$$;
                            """
                        )
                    )

                # 6) Finaliza: troca PK de produtos para (id) e garante unicidade de cod_barras
                # Somente agora é seguro mexer na PK antiga, pois as FKs legadas em cod_barras
                # já foram removidas/atualizadas nas tabelas dependentes.
                if _table_exists(conn, "catalogo", "produtos"):
                    # Drop PK antigo (em cod_barras) e cria PK em id
                    conn.execute(
                        text(
                            """
                            DO $$
                            DECLARE pk_name text;
                            DECLARE pk_def text;
                            BEGIN
                              SELECT c.conname, pg_get_constraintdef(c.oid)
                              INTO pk_name, pk_def
                              FROM pg_constraint c
                              JOIN pg_class t ON t.oid = c.conrelid
                              JOIN pg_namespace n ON n.oid = t.relnamespace
                              WHERE n.nspname = 'catalogo'
                                AND t.relname = 'produtos'
                                AND c.contype = 'p'
                              LIMIT 1;

                              -- Só derruba PK se ela NÃO for a esperada (id)
                              IF pk_name IS NOT NULL AND (pk_def IS NULL OR pk_def NOT ILIKE '%(id)%') THEN
                                EXECUTE format('ALTER TABLE catalogo.produtos DROP CONSTRAINT IF EXISTS %I', pk_name);
                              END IF;

                              IF NOT EXISTS (
                                SELECT 1
                                FROM pg_constraint c
                                JOIN pg_class t ON t.oid = c.conrelid
                                JOIN pg_namespace n ON n.oid = t.relnamespace
                                WHERE n.nspname = 'catalogo'
                                  AND t.relname = 'produtos'
                                  AND c.contype = 'p'
                              ) THEN
                                ALTER TABLE catalogo.produtos
                                  ADD CONSTRAINT produtos_pkey PRIMARY KEY (id);
                              END IF;
                            END$$;
                            """
                        )
                    )

                    # Unicidade do código de barras (substitui o papel de PK)
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
                                WHERE n.nspname = 'catalogo'
                                  AND t.relname = 'produtos'
                                  AND c.conname = 'uq_produtos_cod_barras'
                              ) THEN
                                ALTER TABLE catalogo.produtos
                                  ADD CONSTRAINT uq_produtos_cod_barras UNIQUE (cod_barras);
                              END IF;
                            END$$;
                            """
                        )
                    )

            logger.info("✅ Migração produtos: PK id + FKs por produto_id aplicada/verificada.")
        except Exception as e:
            logger.error("❌ Erro na migração produtos (id/produto_id): %s", e, exc_info=True)

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

def criar_usuario_super_padrao():
    """
    DEPRECATED: o projeto não usa mais usuário `super`/bypass por `type_user`.
    Mantido apenas para compatibilidade (não faz nada).
    """
    return


def vincular_todas_permissoes_ao_usuario_super():
    """
    DEPRECATED: o projeto não usa mais usuário `super`/bypass por `type_user`.
    Mantido apenas para compatibilidade (não faz nada).
    """
    return


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


def normalizar_tipos_usuario():
    """
    Normaliza usuários legados que ainda tenham `type_user` antigo.

    - admin/super -> funcionario
    """
    try:
        with engine.begin() as conn:
            if not _table_exists(conn, "cadastros", "usuarios"):
                logger.warning("⚠️ Tabela cadastros.usuarios não existe; pulando normalização de type_user.")
                return
            result = conn.execute(
                text(
                    """
                    UPDATE cadastros.usuarios
                    SET type_user = 'funcionario'
                    WHERE type_user IN ('admin', 'super')
                    """
                )
            )
            # rowcount pode ser -1 dependendo do driver, então apenas loga quando disponível
            if getattr(result, "rowcount", None) not in (None, -1):
                logger.info("✅ Normalização de type_user aplicada (linhas=%s).", result.rowcount)
            else:
                logger.info("✅ Normalização de type_user aplicada.")
    except Exception as e:
        logger.error("❌ Erro ao normalizar type_user em cadastros.usuarios: %s", e, exc_info=True)


def inicializar_banco():
    logger.info("🚀 Iniciando processo de inicialização do banco de dados...")
    
    # Configura timezone primeiro
    logger.info("📦 Passo 1/7: Configurando timezone do banco...")
    configurar_timezone()
    
    # Habilita PostGIS primeiro (necessário para tipos geography)
    logger.info("📦 Passo 2/7: Habilitando extensão PostGIS...")
    postgis_disponivel = habilitar_postgis()
    
    # SEMPRE cria/verifica os schemas primeiro
    logger.info("📦 Passo 3/7: Criando/verificando schemas...")
    criar_schemas()
    
    # Cria os ENUMs antes de criar as tabelas
    logger.info("📦 Passo 4/7: Criando/verificando ENUMs...")
    criar_enums()
    
    # SEMPRE cria as tabelas (criar_tabelas usa checkfirst=True, então não sobrescreve)
    logger.info("📋 Passo 5/7: Criando/verificando todas as tabelas...")
    criar_tabelas(postgis_disponivel=postgis_disponivel)

    # Se as tabelas essenciais não existirem, não adianta seguir com seed.
    if not verificar_banco_inicializado():
        logger.error("❌ Banco não está inicializado (tabelas principais ausentes). Abortando passos 6-8.")
        return
    
    # Normaliza types legados (admin/super -> funcionario)
    logger.info("👥 Passo 6/7: Normalizando type_user (legado)...")
    normalizar_tipos_usuario()

    # Cria tabelas do chatbot (que não usam modelos SQLAlchemy)
    logger.info("🤖 (extra) Criando/verificando tabelas do chatbot...")
    criar_tabelas_chatbot()
    
    # Dados iniciais de meios de pagamento
    logger.info("💳 Passo 7/7: Criando/verificando meios de pagamento padrão...")
    criar_meios_pagamento_padrao()

    # Catálogo de permissões (idempotente)
    logger.info("🔐 Seed: Criando/verificando permissões padrão...")
    criar_permissoes_padrao()

    # Usuário bootstrap (funcionário) com acesso total por permissões
    logger.info("🧑‍💼 Seed: Criando/verificando usuário 'secreto' com todas as permissões...")
    criar_usuario_secreto_com_todas_permissoes()

    logger.info("✅ Banco inicializado com sucesso.")
