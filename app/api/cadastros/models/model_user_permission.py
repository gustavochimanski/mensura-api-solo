from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    func,
)

from app.database.db_connection import Base


class UserPermissionModel(Base):
    """
    Grants diretos de permissão por usuário e por empresa (tenant).

    Composite PK evita duplicidade e facilita revogação.
    """

    __tablename__ = "user_permissions"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "empresa_id", "permission_id", name="pk_user_permissions"),
        Index("idx_user_permissions_user_empresa", "user_id", "empresa_id"),
        Index("idx_user_permissions_empresa", "empresa_id"),
        {"schema": "cadastros"},
    )

    user_id = Column(Integer, ForeignKey("cadastros.usuarios.id", ondelete="CASCADE"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("cadastros.empresas.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Integer, ForeignKey("cadastros.permissions.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

