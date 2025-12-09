from typing import List, Optional
from sqlalchemy.orm import Session
from app.api.catalogo.models.model_adicional import AdicionalModel
from app.api.catalogo.models.association_tables import complemento_item_link


class ComplementoItemRepository:
    """Repository para operações CRUD de itens de complemento (independentes)."""

    def __init__(self, db: Session):
        self.db = db

    def criar_item(self, **data) -> AdicionalModel:
        """Cria um novo item de complemento (independente)."""
        obj = AdicionalModel(**data)
        self.db.add(obj)
        self.db.flush()
        return obj

    def buscar_por_id(self, item_id: int, carregar_complementos: bool = False) -> Optional[AdicionalModel]:
        """Busca um item por ID."""
        query = self.db.query(AdicionalModel).filter_by(id=item_id)
        if carregar_complementos:
            query = query.options(
                # Carrega os complementos via tabela de associação
            )
        return query.first()

    def listar_por_empresa(self, empresa_id: int, apenas_ativos: bool = True) -> List[AdicionalModel]:
        """Lista todos os itens de uma empresa."""
        query = self.db.query(AdicionalModel).filter_by(empresa_id=empresa_id)
        if apenas_ativos:
            query = query.filter_by(ativo=True)
        return query.order_by(AdicionalModel.nome).all()

    def buscar_por_termo(self, empresa_id: int, termo: str, apenas_ativos: bool = True) -> List[AdicionalModel]:
        """Busca itens por termo (nome ou descrição)."""
        from sqlalchemy import or_
        
        termo_lower = f"%{termo.lower()}%"
        query = self.db.query(AdicionalModel).filter_by(empresa_id=empresa_id)
        
        if apenas_ativos:
            query = query.filter_by(ativo=True)
        
        query = query.filter(
            or_(
                AdicionalModel.nome.ilike(termo_lower),
                AdicionalModel.descricao.ilike(termo_lower)
            )
        )
        
        return query.order_by(AdicionalModel.nome).all()

    def atualizar_item(self, item: AdicionalModel, **data) -> AdicionalModel:
        """Atualiza um item existente."""
        for key, value in data.items():
            if value is not None:
                setattr(item, key, value)
        self.db.flush()
        return item

    def deletar_item(self, item: AdicionalModel):
        """Deleta um item (remove automaticamente os vínculos com complementos via CASCADE)."""
        self.db.delete(item)
        self.db.flush()

    def vincular_itens_complemento(self, complemento_id: int, item_ids: List[int], ordens: Optional[List[int]] = None):
        """Vincula múltiplos itens a um complemento."""
        # Remove vinculações existentes do complemento
        self.db.execute(
            complemento_item_link.delete().where(
                complemento_item_link.c.complemento_id == complemento_id
            )
        )
        
        # Adiciona novas vinculações
        for i, item_id in enumerate(item_ids):
            ordem = ordens[i] if ordens and i < len(ordens) else i
            self.db.execute(
                complemento_item_link.insert().values(
                    complemento_id=complemento_id,
                    item_id=item_id,
                    ordem=ordem
                )
            )
        
        self.db.flush()

    def desvincular_item_complemento(self, complemento_id: int, item_id: int):
        """Remove a vinculação de um item com um complemento."""
        self.db.execute(
            complemento_item_link.delete().where(
                complemento_item_link.c.complemento_id == complemento_id,
                complemento_item_link.c.item_id == item_id
            )
        )
        self.db.flush()

    def listar_itens_complemento(self, complemento_id: int, apenas_ativos: bool = True) -> List[tuple]:
        """Lista todos os itens vinculados a um complemento.
        
        Returns:
            Lista de tuplas (item, ordem) ordenadas por ordem
        """
        from sqlalchemy import select
        
        query = (
            select(AdicionalModel, complemento_item_link.c.ordem)
            .join(complemento_item_link, AdicionalModel.id == complemento_item_link.c.item_id)
            .where(complemento_item_link.c.complemento_id == complemento_id)
        )
        if apenas_ativos:
            query = query.where(AdicionalModel.ativo == True)
        query = query.order_by(complemento_item_link.c.ordem, AdicionalModel.nome)
        
        results = self.db.execute(query).all()
        return [(item, ordem) for item, ordem in results]

    def atualizar_ordem_itens(self, complemento_id: int, item_ordens: List[dict]):
        """Atualiza a ordem dos itens em um complemento.
        
        Args:
            complemento_id: ID do complemento
            item_ordens: Lista de dicts com {'item_id': int, 'ordem': int}
        """
        for item_ordem in item_ordens:
            item_id = item_ordem.get('item_id')
            ordem = item_ordem.get('ordem')
            if item_id and ordem is not None:
                self.db.execute(
                    complemento_item_link.update()
                    .where(
                        complemento_item_link.c.complemento_id == complemento_id,
                        complemento_item_link.c.item_id == item_id
                    )
                    .values(ordem=ordem)
                )
        self.db.flush()

