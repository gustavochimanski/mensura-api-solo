# app/api/mensura/models/association_tables.py
from sqlalchemy import Table, Column, Integer, ForeignKey
from app.database.db_connection import Base

entregador_empresa = Table(
    "entregador_empresa",
    Base.metadata,
    Column("entregador_id", Integer, ForeignKey("delivery.entregadores_dv.id", ondelete="CASCADE")),
    Column("empresa_id", Integer, ForeignKey("mensura.empresas.id", ondelete="CASCADE")),
    schema="delivery",
)

usuario_empresa = Table(
    "usuario_empresa",
    Base.metadata,
    Column("usuario_id", Integer, ForeignKey("mensura.usuarios.id", ondelete="CASCADE")),
    Column("empresa_id", Integer, ForeignKey("mensura.empresas.id", ondelete="CASCADE")),
    schema="mensura",
)
