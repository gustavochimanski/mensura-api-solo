from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.api.catalogo.models.model_adicional import AdicionalModel
from app.api.catalogo.models.model_produto import ProdutoModel


class AdicionalRepository:
    """Repository para operações CRUD de adicionais."""

    def __init__(self, db: Session):
        self.db = db

    def criar_adicional(self, **data) -> AdicionalModel:
        """Cria um novo adicional."""
        obj = AdicionalModel(**data)
        self.db.add(obj)
        self.db.flush()
        return obj

    def buscar_por_id(self, adicional_id: int) -> Optional[AdicionalModel]:
        """Busca um adicional por ID."""
        return self.db.query(AdicionalModel).filter_by(id=adicional_id).first()

    def listar_por_empresa(self, empresa_id: int, apenas_ativos: bool = True) -> List[AdicionalModel]:
        """Lista todos os adicionais de uma empresa."""
        query = self.db.query(AdicionalModel).filter_by(empresa_id=empresa_id)
        if apenas_ativos:
            query = query.filter_by(ativo=True)
        return query.order_by(AdicionalModel.ordem, AdicionalModel.nome).all()

    def listar_por_produto(self, cod_barras: str, apenas_ativos: bool = True) -> List[AdicionalModel]:
        """Lista todos os adicionais vinculados a um produto."""
        from app.api.catalogo.models.association_tables import produto_adicional_link
        
        query = (
            self.db.query(AdicionalModel)
            .join(produto_adicional_link, AdicionalModel.id == produto_adicional_link.c.adicional_id)
            .filter(produto_adicional_link.c.produto_cod_barras == cod_barras)
        )
        if apenas_ativos:
            query = query.filter(AdicionalModel.ativo == True)
        return query.order_by(produto_adicional_link.c.ordem, AdicionalModel.nome).all()

    def atualizar_adicional(self, adicional: AdicionalModel, **data) -> AdicionalModel:
        """Atualiza um adicional existente."""
        for key, value in data.items():
            if value is not None:
                setattr(adicional, key, value)
        self.db.flush()
        return adicional

    def deletar_adicional(self, adicional: AdicionalModel):
        """Deleta um adicional."""
        self.db.delete(adicional)
        self.db.flush()

    def vincular_adicionais_produto(self, cod_barras: str, adicional_ids: List[int]):
        """Vincula múltiplos adicionais a um produto."""
        from app.api.catalogo.models.association_tables import produto_adicional_link
        
        produto = self.db.query(ProdutoModel).filter_by(cod_barras=cod_barras).first()
        if not produto:
            raise ValueError(f"Produto {cod_barras} não encontrado")
        
        # Busca os adicionais
        adicionais = (
            self.db.query(AdicionalModel)
            .filter(AdicionalModel.id.in_(adicional_ids))
            .all()
        )
        
        # Remove vinculações existentes
        self.db.execute(
            produto_adicional_link.delete().where(
                produto_adicional_link.c.produto_cod_barras == cod_barras
            )
        )
        
        # Adiciona novas vinculações
        for i, adicional in enumerate(adicionais):
            self.db.execute(
                produto_adicional_link.insert().values(
                    produto_cod_barras=cod_barras,
                    adicional_id=adicional.id,
                    ordem=i
                )
            )
        
        self.db.flush()

    def desvincular_adicional_produto(self, cod_barras: str, adicional_id: int):
        """Remove a vinculação de um adicional com um produto."""
        from app.api.catalogo.models.association_tables import produto_adicional_link
        
        self.db.execute(
            produto_adicional_link.delete().where(
                produto_adicional_link.c.produto_cod_barras == cod_barras,
                produto_adicional_link.c.adicional_id == adicional_id
            )
        )
        self.db.flush()

