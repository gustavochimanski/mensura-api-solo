from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status
from decimal import Decimal

from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.catalogo.models.model_adicional import AdicionalModel
from app.api.catalogo.models.model_ingrediente import IngredienteModel
from app.api.catalogo.models.model_receita import ReceitaIngredienteModel, ReceitaAdicionalModel, ReceitaModel
from app.api.catalogo.schemas.schema_receitas import (
    ReceitaIngredienteIn,
    AdicionalIn,
    ReceitaIn,
    ReceitaUpdate,
)


class ReceitasRepository:
    def __init__(self, db: Session):
        self.db = db

    def _buscar_preco_adicional(self, adicional_id: int) -> Decimal:
        """
        Busca o preço do adicional do cadastro atual (AdicionalModel).
        Retorna 0.00 se não encontrar.
        """
        adicional = (
            self.db.query(AdicionalModel)
            .filter_by(id=adicional_id)
            .first()
        )
        
        if adicional and adicional.preco is not None:
            return adicional.preco
        return Decimal('0.00')

    # Receitas - CRUD completo
    def create_receita(self, data: ReceitaIn) -> ReceitaModel:
        receita = ReceitaModel(
            empresa_id=data.empresa_id,
            nome=data.nome,
            descricao=data.descricao,
            preco_venda=data.preco_venda,
            imagem=data.imagem,
            ativo=data.ativo,
            disponivel=data.disponivel,
        )
        self.db.add(receita)
        self.db.commit()
        self.db.refresh(receita)
        return receita

    def get_receita_by_id(self, receita_id: int) -> Optional[ReceitaModel]:
        return self.db.query(ReceitaModel).filter_by(id=receita_id).first()

    def list_receitas(self, empresa_id: Optional[int] = None, ativo: Optional[bool] = None) -> List[ReceitaModel]:
        query = self.db.query(ReceitaModel)
        
        if empresa_id is not None:
            query = query.filter_by(empresa_id=empresa_id)
        
        if ativo is not None:
            query = query.filter_by(ativo=ativo)
        
        return query.order_by(ReceitaModel.nome).all()
    
    def list_receitas_com_ingredientes(self, empresa_id: Optional[int] = None, ativo: Optional[bool] = None) -> List[ReceitaModel]:
        """Lista receitas com seus ingredientes carregados"""
        query = (
            self.db.query(ReceitaModel)
            .options(joinedload(ReceitaModel.ingredientes).joinedload(ReceitaIngredienteModel.ingrediente))
        )
        
        if empresa_id is not None:
            query = query.filter_by(empresa_id=empresa_id)
        
        if ativo is not None:
            query = query.filter_by(ativo=ativo)
        
        return query.order_by(ReceitaModel.nome).all()

    def update_receita(self, receita_id: int, data: ReceitaUpdate) -> ReceitaModel:
        receita = self.get_receita_by_id(receita_id)
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")

        if data.nome is not None:
            receita.nome = data.nome
        if data.descricao is not None:
            receita.descricao = data.descricao
        if data.preco_venda is not None:
            receita.preco_venda = data.preco_venda
        if data.imagem is not None:
            receita.imagem = data.imagem
        if data.ativo is not None:
            receita.ativo = data.ativo
        if data.disponivel is not None:
            receita.disponivel = data.disponivel

        self.db.add(receita)
        self.db.commit()
        self.db.refresh(receita)
        return receita

    def delete_receita(self, receita_id: int) -> None:
        receita = self.get_receita_by_id(receita_id)
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
        
        self.db.delete(receita)
        self.db.commit()

    # Ingredientes - Usa ReceitaIngredienteModel (receita_ingrediente)
    # Relacionamento N:N (um ingrediente pode estar em várias receitas, uma receita pode ter vários ingredientes)
    def add_ingrediente(self, data: ReceitaIngredienteIn) -> ReceitaIngredienteModel:
        # Verifica se a receita existe
        receita = self.get_receita_by_id(data.receita_id)
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
        
        # Verifica se o ingrediente existe
        ingrediente = self.db.query(IngredienteModel).filter_by(id=data.ingrediente_id).first()
        if not ingrediente:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingrediente não encontrado")

        # Verifica se já existe na mesma receita (evita duplicatas)
        exists_mesma_receita = (
            self.db.query(ReceitaIngredienteModel)
            .filter_by(receita_id=data.receita_id, ingrediente_id=data.ingrediente_id)
            .first()
        )
        if exists_mesma_receita:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ingrediente já cadastrado nesta receita")

        obj = ReceitaIngredienteModel(
            receita_id=data.receita_id,
            ingrediente_id=data.ingrediente_id,
            quantidade=data.quantidade,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def list_ingredientes(self, receita_id: int) -> List[ReceitaIngredienteModel]:
        # Verifica se a receita existe
        receita = self.get_receita_by_id(receita_id)
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
        
        return (
            self.db.query(ReceitaIngredienteModel)
            .options(joinedload(ReceitaIngredienteModel.ingrediente))
            .filter(ReceitaIngredienteModel.receita_id == receita_id)
            .all()
        )

    def update_ingrediente(self, receita_ingrediente_id: int, quantidade: float | None) -> ReceitaIngredienteModel:
        obj = self.db.query(ReceitaIngredienteModel).filter_by(id=receita_ingrediente_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingrediente não encontrado na receita")
        if quantidade is not None:
            obj.quantidade = quantidade
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
    def add_adicional(self, data: AdicionalIn) -> ReceitaAdicionalModel:
        # Verifica se a receita existe
        receita = self.get_receita_by_id(data.receita_id)
        if not receita:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, 
                f"Receita não encontrada com ID: {data.receita_id}. "
                f"Verifique se o receita_id está correto e se a receita existe no banco de dados."
            )
        
        # Verifica se o adicional existe na tabela de adicionais
        adicional = self.db.query(AdicionalModel).filter_by(id=data.adicional_id).first()
        if not adicional:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, 
                f"Adicional não encontrado com ID: {data.adicional_id}. "
                f"O adicional deve estar cadastrado na tabela de adicionais (catalogo.adicionais) antes de ser vinculado à receita."
            )
        
        # Verifica se o adicional pertence à mesma empresa da receita
        if adicional.empresa_id != receita.empresa_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"O adicional pertence a uma empresa diferente da receita. "
                f"Adicional empresa_id: {adicional.empresa_id}, Receita empresa_id: {receita.empresa_id}"
            )

        # Verifica se já existe
        exists = (
            self.db.query(ReceitaAdicionalModel)
            .filter_by(receita_id=data.receita_id, adicional_id=data.adicional_id)
            .first()
        )
        if exists:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Adicional já cadastrado nesta receita")

        # Cria o adicional (preço não é mais armazenado, sempre busca do cadastro)
        obj = ReceitaAdicionalModel(
            receita_id=data.receita_id,
            adicional_id=data.adicional_id,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def list_adicionais(self, receita_id: int) -> List[ReceitaAdicionalModel]:
        # Verifica se a receita existe
        receita = self.get_receita_by_id(receita_id)
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
        
        return (
            self.db.query(ReceitaAdicionalModel)
            .filter(ReceitaAdicionalModel.receita_id == receita_id)
            .all()
        )

    def update_adicional(self, adicional_id: int) -> ReceitaAdicionalModel:
        """
        Atualiza um adicional de uma receita.
        Nota: O preço não é mais armazenado, sempre busca do cadastro em tempo de execução.
        Este método existe apenas para compatibilidade com a API.
        """
        obj = self.db.query(ReceitaAdicionalModel).filter_by(id=adicional_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Adicional não encontrado")
        
        # Não precisa fazer nada, o preço sempre é buscado dinamicamente
        self.db.refresh(obj)
        return obj

    def remove_adicional(self, adicional_id: int) -> None:
        obj = self.db.query(ReceitaAdicionalModel).filter_by(id=adicional_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Adicional não encontrado")
        self.db.delete(obj)
        self.db.commit()

    def receita_tem_ingredientes(self, receita_id: int) -> bool:
        """Verifica se uma receita possui ingredientes cadastrados"""
        receita = self.get_receita_by_id(receita_id)
        if not receita:
            return False
        
        count = (
            self.db.query(func.count(ReceitaIngredienteModel.id))
            .filter(ReceitaIngredienteModel.receita_id == receita_id)
            .scalar()
        )
        return count > 0 if count else False

    def produto_tem_receita(self, produto_cod_barras: str) -> bool:
        """
        Verifica se um produto está associado a alguma receita.
        Nota: Este método verifica produtos, não adicionais. Adicionais agora usam adicional_id.
        """
        # Este método não é mais relevante para adicionais, pois adicionais usam ID, não cod_barras
        # Mantido para compatibilidade, mas sempre retorna False para adicionais
        return False

    def calcular_custo_receita(self, receita_id: int) -> Decimal:
        """
        Calcula o custo total de uma receita baseado nos custos dos ingredientes vinculados.
        O cálculo é: soma de (quantidade * custo) para cada ingrediente vinculado.
        """
        receita = self.get_receita_by_id(receita_id)
        if not receita:
            return Decimal('0.00')
        
        # Busca todos os ingredientes vinculados à receita com seus dados
        ingredientes = (
            self.db.query(ReceitaIngredienteModel)
            .options(joinedload(ReceitaIngredienteModel.ingrediente))
            .filter(ReceitaIngredienteModel.receita_id == receita_id)
            .all()
        )
        
        custo_total = Decimal('0.00')
        for receita_ingrediente in ingredientes:
            if receita_ingrediente.ingrediente:
                quantidade = receita_ingrediente.quantidade if receita_ingrediente.quantidade else Decimal('0.00')
                custo_ingrediente = receita_ingrediente.ingrediente.custo if receita_ingrediente.ingrediente.custo else Decimal('0.00')
                custo_total += quantidade * custo_ingrediente
        
        return custo_total

