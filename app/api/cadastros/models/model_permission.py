from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint, Index, func

from app.database.db_connection import Base


class PermissionModel(Base):
    """
    Permissões canônicas do sistema (catálogo).

    - key: string estável usada no código (ex: "route:/dashboard", "route:/configuracoes:usuarios")
    - domain: agrupador para listagem/UX (ex: "routes")
    """

    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("key", name="uq_permissions_key"),
        Index("idx_permissions_domain", "domain"),
        {"schema": "cadastros"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False)
    domain = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

