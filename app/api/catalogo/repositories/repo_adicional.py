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
        """
        DEPRECADO: Este método foi desabilitado.
        produto_adicional_link foi removido - adicionais agora são vínculos de produtos/receitas/combos em complementos.
        Retorna lista vazia para não quebrar código que ainda chama este método.
        """
        # TODO: Refatorar código que chama este método para usar complementos/vínculos
        return []

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
        """
        DEPRECADO: Este método foi desabilitado.
        produto_adicional_link foi removido - adicionais agora são vínculos de produtos/receitas/combos em complementos.
        Use os endpoints de complementos para vincular itens a produtos.
        """
        raise ValueError(
            "Este método foi removido. produto_adicional_link não existe mais. "
            "Adicionais agora são vínculos de produtos/receitas/combos em complementos. "
            "Use os endpoints de complementos para vincular itens a produtos."
        )

    def desvincular_adicional_produto(self, cod_barras: str, adicional_id: int):
        """
        DEPRECADO: Este método foi desabilitado.
        produto_adicional_link foi removido - adicionais agora são vínculos de produtos/receitas/combos em complementos.
        Use os endpoints de complementos para desvincular itens de produtos.
        """
        raise ValueError(
            "Este método foi removido. produto_adicional_link não existe mais. "
            "Adicionais agora são vínculos de produtos/receitas/combos em complementos. "
            "Use os endpoints de complementos para desvincular itens de produtos."
        )

