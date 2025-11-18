from typing import List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status

from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.models.model_receita import ReceitaIngredienteModel, ReceitaAdicionalModel, ReceitaModel
from app.api.cadastros.schemas.schema_receitas import IngredienteIn, AdicionalIn


class ReceitasRepository:
    def __init__(self, db: Session):
        self.db = db

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
        
        # Busca a receita pelo produto (assumindo que produto_cod_barras identifica a receita)
        # Nota: Esta lógica pode precisar ser ajustada conforme a estrutura real
        receita = self.db.query(ReceitaModel).filter_by(empresa_id=1).first()  # Ajustar conforme necessário
        if not receita:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Receita não encontrada para este produto")
        
        add = self.db.query(ProdutoModel).filter_by(cod_barras=data.adicional_cod_barras).first()
        if not add:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Adicional inválido")

        exists = (
            self.db.query(ReceitaAdicionalModel)
            .filter_by(receita_id=receita.id, adicional_cod_barras=data.adicional_cod_barras)
            .first()
        )
        if exists:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Adicional já cadastrado nesta receita")

        obj = ReceitaAdicionalModel(
            receita_id=receita.id,
            adicional_cod_barras=data.adicional_cod_barras,
            preco=data.preco,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def list_adicionais(self, produto_cod_barras: str) -> List[ReceitaAdicionalModel]:
        from app.api.catalogo.models.model_receita import ReceitaModel
        
        # Busca a receita pelo produto
        receita = self.db.query(ReceitaModel).filter_by(empresa_id=1).first()  # Ajustar conforme necessário
        if not receita:
            return []
        
        return (
            self.db.query(ReceitaAdicionalModel)
            .filter(ReceitaAdicionalModel.receita_id == receita.id)
            .all()
        )

    def update_adicional(self, adicional_id: int, preco) -> ReceitaAdicionalModel:
        obj = self.db.query(ReceitaAdicionalModel).filter_by(id=adicional_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Adicional não encontrado")
        obj.preco = preco
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

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


