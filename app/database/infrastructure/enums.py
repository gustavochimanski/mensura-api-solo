"""Criação de tipos ENUM do PostgreSQL."""
import logging
from sqlalchemy import text
from ..db_connection import engine

logger = logging.getLogger(__name__)


def criar_enums():
    """
    Cria os tipos ENUM do PostgreSQL com schema correto antes de criar as tabelas.
    
    Raises:
        Exception: Se houver erro ao criar algum ENUM.
    """
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
            
            # ENUMs do schema cadastros (caixa_status está aqui pois CaixaModel está em cadastros)
            # O enum já está em enums_cadastros acima via modelo CaixaModel
            
            all_enums = enums_cardapio + enums_cadastros
            
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
        raise

