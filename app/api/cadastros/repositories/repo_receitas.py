from typing import List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status
from decimal import Decimal

from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.models.model_receita import ReceitaIngredienteModel, ReceitaAdicionalModel, ReceitaModel
from app.api.cadastros.schemas.schema_receitas import IngredienteIn, AdicionalIn


class ReceitasRepository:
    def __init__(self, db: Session):
        self.db = db

    def _buscar_preco_adicional(self, empresa_id: int, cod_barras: str) -> Decimal:
        """
        Busca o preço do adicional do cadastro atual (ProdutoEmpModel).
        Retorna 0.00 se não encontrar.
        """
        from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
        
        produto_emp = (
            self.db.query(ProdutoEmpModel)
            .filter_by(empresa_id=empresa_id, cod_barras=cod_barras)
            .first()
        )
        
        if produto_emp and produto_emp.preco_venda is not None:
            return produto_emp.preco_venda
        return Decimal('0.00')

    # Diretiva
    def set_diretiva(self, cod_barras: str, diretiva: str | None) -> ProdutoModel:
        prod = self.db.query(ProdutoModel).filter_by(cod_barras=cod_barras).first()
        if not prod:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")
        prod.diretiva = diretiva
        self.db.add(prod)
        self.db.commit()
        self.db.refresh(prod)
        return prod

    # Ingredientes - Usa ReceitaIngredienteModel (receita_ingrediente)
    # Nota: Ingredientes agora são vinculados a receitas, não diretamente a produtos
    def add_ingrediente(self, data: IngredienteIn) -> ReceitaIngredienteModel:
        # Busca a receita pelo produto (assumindo que produto_cod_barras identifica a receita)
        # Nota: Esta lógica pode precisar ser ajustada conforme a estrutura real
        receita = self.db.query(ReceitaModel).filter_by(empresa_id=1).first()  # Ajustar conforme necessário
        if not receita:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Receita não encontrada para este produto")
        
        ing = self.db.query(ProdutoModel).filter_by(cod_barras=data.ingrediente_cod_barras).first()
        if not ing:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ingrediente inválido")

        exists = (
            self.db.query(ReceitaIngredienteModel)
            .filter_by(receita_id=receita.id, ingrediente_cod_barras=data.ingrediente_cod_barras)
            .first()
        )
        if exists:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ingrediente já cadastrado nesta receita")

        obj = ReceitaIngredienteModel(
            receita_id=receita.id,
            ingrediente_cod_barras=data.ingrediente_cod_barras,
            quantidade=data.quantidade,
            unidade=data.unidade,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def list_ingredientes(self, produto_cod_barras: str) -> List[ReceitaIngredienteModel]:
        # Tenta converter cod_barras para receita_id (assumindo que cod_barras é o ID da receita)
        # Se não for numérico, retorna vazio
        try:
            receita_id = int(produto_cod_barras)
        except ValueError:
            # Se não for numérico, retorna vazio
            return []
        
        # Verifica se a receita existe
        receita = self.db.query(ReceitaModel).filter_by(id=receita_id).first()
        if not receita:
            return []
        
        # Busca os ingredientes da receita com eager loading do ingrediente
        return (
            self.db.query(ReceitaIngredienteModel)
            .options(joinedload(ReceitaIngredienteModel.ingrediente))
            .filter(ReceitaIngredienteModel.receita_id == receita_id)
            .all()
        )

    def update_ingrediente(self, ingrediente_id: int, quantidade: float | None, unidade: str | None) -> ReceitaIngredienteModel:
        obj = self.db.query(ReceitaIngredienteModel).filter_by(id=ingrediente_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingrediente não encontrado")
        obj.quantidade = quantidade
        obj.unidade = unidade
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def remove_ingrediente(self, ingrediente_id: int) -> None:
        obj = self.db.query(ReceitaIngredienteModel).filter_by(id=ingrediente_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingrediente não encontrado")
        self.db.delete(obj)
        self.db.commit()

    # Adicionais - Usa ReceitaAdicionalModel (receita_adicional)
    # Nota: Adicionais agora são vinculados a receitas, não diretamente a produtos
    def add_adicional(self, data: AdicionalIn) -> ReceitaAdicionalModel:
        from app.api.catalogo.models.model_receita import ReceitaModel
        from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
        
        # Tenta converter produto_cod_barras para receita_id (assumindo que cod_barras é o ID da receita)
        try:
            receita_id = int(data.produto_cod_barras)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código de barras do produto inválido (deve ser o ID da receita)")
        
        # Verifica se a receita existe
        receita = self.db.query(ReceitaModel).filter_by(id=receita_id).first()
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
        
        # Verifica se o adicional (produto) existe na tabela de produtos
        add = self.db.query(ProdutoModel).filter_by(cod_barras=data.adicional_cod_barras).first()
        if not add:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, 
                f"Produto adicional não encontrado com código de barras: {data.adicional_cod_barras}. "
                f"O produto deve estar cadastrado na tabela de produtos (catalogo.produtos) antes de ser vinculado à receita."
            )

        # Verifica se já existe
        exists = (
            self.db.query(ReceitaAdicionalModel)
            .filter_by(receita_id=receita_id, adicional_cod_barras=data.adicional_cod_barras)
            .first()
        )
        if exists:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Adicional já cadastrado nesta receita")

        # Cria o adicional (preço não é mais armazenado, sempre busca do cadastro)
        obj = ReceitaAdicionalModel(
            receita_id=receita_id,
            adicional_cod_barras=data.adicional_cod_barras,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def list_adicionais(self, produto_cod_barras: str) -> List[ReceitaAdicionalModel]:
        from app.api.catalogo.models.model_receita import ReceitaModel
        
        # Tenta converter cod_barras para receita_id (assumindo que cod_barras é o ID da receita)
        # Se não for numérico, retorna vazio
        try:
            receita_id = int(produto_cod_barras)
        except ValueError:
            # Se não for numérico, retorna vazio
            return []
        
        # Verifica se a receita existe
        receita = self.db.query(ReceitaModel).filter_by(id=receita_id).first()
        if not receita:
            return []
        
        # Busca os adicionais da receita
        return (
            self.db.query(ReceitaAdicionalModel)
            .filter(ReceitaAdicionalModel.receita_id == receita_id)
            .all()
        )

    def remove_adicional(self, adicional_id: int) -> None:
        obj = self.db.query(ReceitaAdicionalModel).filter_by(id=adicional_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Adicional não encontrado")
        self.db.delete(obj)
        self.db.commit()

    def produto_tem_receita(self, produto_cod_barras: str) -> bool:
        """Verifica se um produto possui receita (tem pelo menos um ingrediente cadastrado)"""
        # Busca a receita pelo produto
        receita = self.db.query(ReceitaModel).filter_by(empresa_id=1).first()  # Ajustar conforme necessário
        if not receita:
            return False
        
        count = (
            self.db.query(func.count(ReceitaIngredienteModel.id))
            .filter(ReceitaIngredienteModel.receita_id == receita.id)
            .scalar()
        )
        return count > 0 if count else False


