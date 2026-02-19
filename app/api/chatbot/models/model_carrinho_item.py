# app/api/chatbot/models/model_carrinho_item.py
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Numeric, Index, CheckConstraint
)
from sqlalchemy.orm import relationship, validates

from app.database.db_connection import Base


class CarrinhoItemModel(Base):
    """
    Modelo de item do carrinho temporário no schema chatbot.
    
    Suporta três tipos de itens através de colunas nullable:
    - Produto: produto_cod_barras preenchido, combo_id e receita_id NULL
    - Combo: combo_id preenchido, produto_cod_barras e receita_id NULL
    - Receita: receita_id preenchido, produto_cod_barras e combo_id NULL
    
    Validação: Apenas um dos três campos deve estar preenchido.
    """
    __tablename__ = "carrinho_itens"
    __table_args__ = (
        Index("idx_carrinho_itens_carrinho", "carrinho_id"),
        # Índices de item-produto (novo: produto_id; legado: produto_cod_barras)
        Index("idx_carrinho_itens_produto_id", "produto_id"),
        Index("idx_carrinho_itens_produto_cod_barras", "produto_cod_barras"),
        Index("idx_carrinho_itens_combo", "combo_id"),
        Index("idx_carrinho_itens_receita", "receita_id"),
        # Constraint CHECK para garantir que apenas um tipo está preenchido
        CheckConstraint(
            """
            ((produto_id IS NOT NULL OR produto_cod_barras IS NOT NULL) AND combo_id IS NULL AND receita_id IS NULL) OR
            ((produto_id IS NULL AND produto_cod_barras IS NULL) AND combo_id IS NOT NULL AND receita_id IS NULL) OR
            ((produto_id IS NULL AND produto_cod_barras IS NULL) AND combo_id IS NULL AND receita_id IS NOT NULL)
            """,
            name="chk_carrinho_item_tipo_unico"
        ),
        {"schema": "chatbot"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Relacionamento com carrinho
    carrinho_id = Column(
        Integer,
        ForeignKey("chatbot.carrinho_temporario.id", ondelete="CASCADE"),
        nullable=False
    )
    carrinho = relationship("CarrinhoTemporarioModel", back_populates="itens")
    
    # Identificação do item (apenas um deve estar preenchido)
    # Novo: FK técnica para produto
    produto_id = Column(
        Integer,
        ForeignKey("catalogo.produtos.id", ondelete="RESTRICT"),
        nullable=True,
    )
    # Legado/compatibilidade: código de barras armazenado como atributo (sem FK)
    produto_cod_barras = Column(String, nullable=True)
    produto = relationship("ProdutoModel", lazy="select", foreign_keys=[produto_id])
    
    combo_id = Column(
        Integer,
        ForeignKey("catalogo.combos.id", ondelete="RESTRICT"),
        nullable=True
    )
    combo = relationship("ComboModel", lazy="select")
    
    receita_id = Column(
        Integer,
        ForeignKey("catalogo.receitas.id", ondelete="RESTRICT"),
        nullable=True
    )
    receita = relationship("ReceitaModel", lazy="select")
    
    # Dados do item
    quantidade = Column(Integer, nullable=False, default=1)
    preco_unitario = Column(Numeric(18, 2), nullable=False)
    preco_total = Column(Numeric(18, 2), nullable=False)
    
    # Observação específica do item
    observacao = Column(String(500), nullable=True)
    
    # Snapshots para não "mudar o passado" se o produto/combo/receita for atualizado
    produto_descricao_snapshot = Column(String(255), nullable=True)
    produto_imagem_snapshot = Column(String(255), nullable=True)

    # Normalização: complementos/adicionais em tabelas relacionais
    complementos = relationship(
        "CarrinhoItemComplementoModel",
        back_populates="carrinho_item",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    @validates('produto_cod_barras', 'combo_id', 'receita_id')
    def validate_item_tipo(self, key, value):
        """
        Validação no nível do modelo para garantir que apenas um tipo está preenchido.
        Esta validação é complementar ao constraint CHECK do banco de dados.
        """
        if value is None:
            return value
        
        # Verifica se algum outro campo já está preenchido
        outros_campos = {
            'produto_cod_barras': self.produto_cod_barras,
            'combo_id': self.combo_id,
            'receita_id': self.receita_id,
        }
        outros_campos.pop(key)  # Remove o campo que está sendo validado
        
        # Se algum outro campo está preenchido, não permite
        if any(v is not None for v in outros_campos.values()):
            raise ValueError(
                f"Apenas um dos campos (produto_cod_barras, combo_id, receita_id) "
                f"pode estar preenchido por vez. Campo '{key}' não pode ser definido "
                f"quando outro campo já está preenchido."
            )
        
        return value
    
    def calcular_preco_total(self) -> Decimal:
        """Calcula o preço total baseado no preço unitário e quantidade."""
        if self.preco_unitario is None or self.quantidade is None:
            return Decimal("0")
        return Decimal(str(self.preco_unitario)) * Decimal(str(self.quantidade))
    
    def get_tipo_item(self) -> str:
        """Retorna o tipo do item: 'produto', 'combo' ou 'receita'."""
        if self.produto_cod_barras is not None:
            return "produto"
        elif self.combo_id is not None:
            return "combo"
        elif self.receita_id is not None:
            return "receita"
        else:
            return "desconhecido"
    
    def get_descricao_item(self) -> str:
        """Retorna a descrição do item baseado no snapshot ou relacionamento."""
        if self.produto_descricao_snapshot:
            return self.produto_descricao_snapshot
        elif self.produto:
            return self.produto.descricao or self.produto.nome or "Produto"
        elif self.combo:
            return self.combo.descricao or self.combo.titulo or "Combo"
        elif self.receita:
            return self.receita.descricao or self.receita.nome or "Receita"
        else:
            return "Item sem descrição"
