from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.api.catalogo.models.model_complemento import ComplementoModel
from app.api.catalogo.models.model_produto import ProdutoModel


class ComplementoRepository:
    """Repository para operações CRUD de complementos."""

    def __init__(self, db: Session):
        self.db = db

    def criar_complemento(self, **data) -> ComplementoModel:
        """Cria um novo complemento."""
        obj = ComplementoModel(**data)
        self.db.add(obj)
        self.db.flush()
        return obj

    def buscar_por_id(self, complemento_id: int, carregar_adicionais: bool = False) -> Optional[ComplementoModel]:
        """Busca um complemento por ID."""
        query = self.db.query(ComplementoModel).filter_by(id=complemento_id)
        if carregar_adicionais:
            query = query.options(joinedload(ComplementoModel.adicionais))
        return query.first()

    def listar_por_empresa(self, empresa_id: int, apenas_ativos: bool = True, carregar_adicionais: bool = False) -> List[ComplementoModel]:
        """Lista todos os complementos de uma empresa."""
        query = self.db.query(ComplementoModel).filter_by(empresa_id=empresa_id)
        if apenas_ativos:
            query = query.filter_by(ativo=True)
        if carregar_adicionais:
            query = query.options(joinedload(ComplementoModel.adicionais))
        return query.order_by(ComplementoModel.ordem, ComplementoModel.nome).all()

    def listar_por_produto(self, cod_barras: str, apenas_ativos: bool = True, carregar_adicionais: bool = False) -> List[ComplementoModel]:
        """Lista todos os complementos vinculados a um produto."""
        from app.api.catalogo.models.association_tables import produto_complemento_link
        
        query = (
            self.db.query(ComplementoModel)
            .join(produto_complemento_link, ComplementoModel.id == produto_complemento_link.c.complemento_id)
            .filter(produto_complemento_link.c.produto_cod_barras == cod_barras)
        )
        if apenas_ativos:
            query = query.filter(ComplementoModel.ativo == True)
        if carregar_adicionais:
            query = query.options(joinedload(ComplementoModel.adicionais))
        return query.order_by(produto_complemento_link.c.ordem, ComplementoModel.nome).all()

    def atualizar_complemento(self, complemento: ComplementoModel, **data) -> ComplementoModel:
        """Atualiza um complemento existente."""
        for key, value in data.items():
            if value is not None:
                setattr(complemento, key, value)
        self.db.flush()
        return complemento

    def deletar_complemento(self, complemento: ComplementoModel):
        """Deleta um complemento."""
        self.db.delete(complemento)
        self.db.flush()

    def vincular_complementos_produto(self, cod_barras: str, complemento_ids: List[int]):
        """Vincula múltiplos complementos a um produto."""
        from app.api.catalogo.models.association_tables import produto_complemento_link
        
        produto = self.db.query(ProdutoModel).filter_by(cod_barras=cod_barras).first()
        if not produto:
            raise ValueError(f"Produto {cod_barras} não encontrado")
        
        # Busca os complementos
        complementos = (
            self.db.query(ComplementoModel)
            .filter(ComplementoModel.id.in_(complemento_ids))
            .all()
        )
        
        # Remove vinculações existentes
        self.db.execute(
            produto_complemento_link.delete().where(
                produto_complemento_link.c.produto_cod_barras == cod_barras
            )
        )
        
        # Adiciona novas vinculações
        for i, complemento in enumerate(complementos):
            self.db.execute(
                produto_complemento_link.insert().values(
                    produto_cod_barras=cod_barras,
                    complemento_id=complemento.id,
                    ordem=i
                )
            )
        
        self.db.flush()

    def desvincular_complemento_produto(self, cod_barras: str, complemento_id: int):
        """Remove a vinculação de um complemento com um produto."""
        from app.api.catalogo.models.association_tables import produto_complemento_link
        
        self.db.execute(
            produto_complemento_link.delete().where(
                produto_complemento_link.c.produto_cod_barras == cod_barras,
                produto_complemento_link.c.complemento_id == complemento_id
            )
        )
        self.db.flush()

    def listar_por_receita(self, receita_id: int, apenas_ativos: bool = True, carregar_adicionais: bool = False) -> List[ComplementoModel]:
        """Lista todos os complementos vinculados a uma receita."""
        from app.api.catalogo.models.association_tables import receita_complemento_link
        
        query = (
            self.db.query(ComplementoModel)
            .join(receita_complemento_link, ComplementoModel.id == receita_complemento_link.c.complemento_id)
            .filter(receita_complemento_link.c.receita_id == receita_id)
        )
        if apenas_ativos:
            query = query.filter(ComplementoModel.ativo == True)
        if carregar_adicionais:
            query = query.options(joinedload(ComplementoModel.adicionais))
        return query.order_by(receita_complemento_link.c.ordem, ComplementoModel.nome).all()

    def vincular_complementos_receita(self, receita_id: int, complemento_ids: List[int]):
        """Vincula múltiplos complementos a uma receita."""
        from app.api.catalogo.models.association_tables import receita_complemento_link
        from app.api.catalogo.models.model_receita import ReceitaModel
        
        receita = self.db.query(ReceitaModel).filter_by(id=receita_id).first()
        if not receita:
            raise ValueError(f"Receita {receita_id} não encontrada")
        
        # Busca os complementos
        complementos = (
            self.db.query(ComplementoModel)
            .filter(ComplementoModel.id.in_(complemento_ids))
            .all()
        )
        
        # Remove vinculações existentes
        self.db.execute(
            receita_complemento_link.delete().where(
                receita_complemento_link.c.receita_id == receita_id
            )
        )
        
        # Adiciona novas vinculações
        for i, complemento in enumerate(complementos):
            self.db.execute(
                receita_complemento_link.insert().values(
                    receita_id=receita_id,
                    complemento_id=complemento.id,
                    ordem=i
                )
            )
        
        self.db.flush()

    def desvincular_complemento_receita(self, receita_id: int, complemento_id: int):
        """Remove a vinculação de um complemento com uma receita."""
        from app.api.catalogo.models.association_tables import receita_complemento_link
        
        self.db.execute(
            receita_complemento_link.delete().where(
                receita_complemento_link.c.receita_id == receita_id,
                receita_complemento_link.c.complemento_id == complemento_id
            )
        )
        self.db.flush()

    def listar_por_combo(self, combo_id: int, apenas_ativos: bool = True, carregar_adicionais: bool = False) -> List[ComplementoModel]:
        """Lista todos os complementos vinculados a um combo."""
        from app.api.catalogo.models.association_tables import combo_complemento_link
        
        query = (
            self.db.query(ComplementoModel)
            .join(combo_complemento_link, ComplementoModel.id == combo_complemento_link.c.complemento_id)
            .filter(combo_complemento_link.c.combo_id == combo_id)
        )
        if apenas_ativos:
            query = query.filter(ComplementoModel.ativo == True)
        if carregar_adicionais:
            query = query.options(joinedload(ComplementoModel.adicionais))
        return query.order_by(combo_complemento_link.c.ordem, ComplementoModel.nome).all()

    def vincular_complementos_combo(self, combo_id: int, complemento_ids: List[int]):
        """Vincula múltiplos complementos a um combo."""
        from app.api.catalogo.models.association_tables import combo_complemento_link
        from app.api.catalogo.models.model_combo import ComboModel
        
        combo = self.db.query(ComboModel).filter_by(id=combo_id).first()
        if not combo:
            raise ValueError(f"Combo {combo_id} não encontrado")
        
        # Se lista vazia, apenas remove vinculações existentes
        if not complemento_ids:
            self.db.execute(
                combo_complemento_link.delete().where(
                    combo_complemento_link.c.combo_id == combo_id
                )
            )
            self.db.flush()
            return
        
        # Busca os complementos
        complementos = (
            self.db.query(ComplementoModel)
            .filter(ComplementoModel.id.in_(complemento_ids))
            .all()
        )
        
        if len(complementos) != len(complemento_ids):
            encontrados_ids = {c.id for c in complementos}
            nao_encontrados = [cid for cid in complemento_ids if cid not in encontrados_ids]
            raise ValueError(f"Complementos não encontrados: {nao_encontrados}")
        
        # Remove vinculações existentes
        self.db.execute(
            combo_complemento_link.delete().where(
                combo_complemento_link.c.combo_id == combo_id
            )
        )
        
        # Adiciona novas vinculações
        for i, complemento in enumerate(complementos):
            self.db.execute(
                combo_complemento_link.insert().values(
                    combo_id=combo_id,
                    complemento_id=complemento.id,
                    ordem=i
                )
            )
        
        self.db.flush()

    def desvincular_complemento_combo(self, combo_id: int, complemento_id: int):
        """Remove a vinculação de um complemento com um combo."""
        from app.api.catalogo.models.association_tables import combo_complemento_link
        
        self.db.execute(
            combo_complemento_link.delete().where(
                combo_complemento_link.c.combo_id == combo_id,
                combo_complemento_link.c.complemento_id == complemento_id
            )
        )
        self.db.flush()

