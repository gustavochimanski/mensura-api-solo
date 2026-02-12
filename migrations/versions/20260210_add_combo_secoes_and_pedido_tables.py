"""Add combo_secoes/catalogo and pedido_item_combo_secoes/pedidos tables

Revision ID: 20260210_add_combo_secoes_and_pedido_tables
Revises: 
Create Date: 2026-02-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260210_add_combo_secoes_and_pedido_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure schemas exist
    op.execute("CREATE SCHEMA IF NOT EXISTS catalogo")
    op.execute("CREATE SCHEMA IF NOT EXISTS pedidos")

    # catalogo.combo_secoes
    op.create_table(
        "combo_secoes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("combo_id", sa.Integer, sa.ForeignKey("catalogo.combos.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("titulo", sa.String(120), nullable=False),
        sa.Column("descricao", sa.String(255), nullable=True),
        sa.Column("obrigatorio", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("quantitativo", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("minimo_itens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("maximo_itens", sa.Integer, nullable=False, server_default="1"),
        sa.Column("ordem", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="catalogo",
    )

    # catalogo.combo_secoes_itens
    op.create_table(
        "combo_secoes_itens",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("secao_id", sa.Integer, sa.ForeignKey("catalogo.combo_secoes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("produto_id", sa.Integer, sa.ForeignKey("catalogo.produtos.id", ondelete="RESTRICT"), nullable=True, index=True),
        sa.Column("produto_cod_barras", sa.String(), nullable=True, index=True),
        sa.Column("receita_id", sa.Integer, sa.ForeignKey("catalogo.receitas.id", ondelete="RESTRICT"), nullable=True, index=True),
        sa.Column("ordem", sa.Integer, nullable=False, server_default="0"),
        sa.Column("preco_incremental", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("permite_quantidade", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("quantidade_min", sa.Integer, nullable=False, server_default="1"),
        sa.Column("quantidade_max", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(CASE WHEN (produto_id IS NOT NULL OR produto_cod_barras IS NOT NULL) THEN 1 ELSE 0 END + "
            "CASE WHEN receita_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_combo_secao_item_exatamente_um_tipo",
        ),
        schema="catalogo",
    )

    # pedidos.pedido_item_combo_secoes — vincula pedido_item -> secao selecionada
    op.create_table(
        "pedido_item_combo_secoes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("pedido_item_id", sa.Integer, sa.ForeignKey("pedidos.pedidos_itens.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("secao_id", sa.Integer, sa.ForeignKey("catalogo.combo_secoes.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("secao_titulo_snapshot", sa.String(120), nullable=True),
        sa.Column("ordem", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="pedidos",
    )

    # pedidos.pedido_item_combo_secoes_itens — itens selecionados dentro da seção para um pedido_item
    op.create_table(
        "pedido_item_combo_secoes_itens",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("pedido_item_secao_id", sa.Integer, sa.ForeignKey("pedidos.pedido_item_combo_secoes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("combo_secoes_item_id", sa.Integer, sa.ForeignKey("catalogo.combo_secoes_itens.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("produto_cod_barras_snapshot", sa.String(), nullable=True),
        sa.Column("receita_id_snapshot", sa.Integer, nullable=True),
        sa.Column("preco_incremental_snapshot", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("quantidade", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="pedidos",
    )

    # Indexes for faster queries
    op.create_index("ix_combo_secoes_combo_id", "combo_secoes", ["combo_id"], schema="catalogo")
    op.create_index("ix_combo_secoes_itens_secao_id", "combo_secoes_itens", ["secao_id"], schema="catalogo")
    op.create_index("ix_pedido_item_combo_secoes_pedido_item_id", "pedido_item_combo_secoes", ["pedido_item_id"], schema="pedidos")
    op.create_index("ix_pedido_item_combo_secoes_itens_pedido_item_secao_id", "pedido_item_combo_secoes_itens", ["pedido_item_secao_id"], schema="pedidos")


def downgrade() -> None:
    op.drop_index("ix_pedido_item_combo_secoes_itens_pedido_item_secao_id", table_name="pedido_item_combo_secoes_itens", schema="pedidos")
    op.drop_index("ix_pedido_item_combo_secoes_pedido_item_id", table_name="pedido_item_combo_secoes", schema="pedidos")
    op.drop_index("ix_combo_secoes_itens_secao_id", table_name="combo_secoes_itens", schema="catalogo")
    op.drop_index("ix_combo_secoes_combo_id", table_name="combo_secoes", schema="catalogo")

    op.drop_table("pedido_item_combo_secoes_itens", schema="pedidos")
    op.drop_table("pedido_item_combo_secoes", schema="pedidos")
    op.drop_table("combo_secoes_itens", schema="catalogo")
    op.drop_table("combo_secoes", schema="catalogo")

