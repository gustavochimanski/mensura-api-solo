from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from fastapi import HTTPException, status
from decimal import Decimal

from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.catalogo.models.model_adicional import AdicionalModel
from app.api.catalogo.models.model_ingrediente import IngredienteModel
from app.api.catalogo.models.model_receita import ReceitaIngredienteModel, ReceitaAdicionalModel, ReceitaModel
from app.api.catalogo.models.model_combo import ComboModel
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

    def list_receitas(
        self,
        empresa_id: Optional[int] = None,
        ativo: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[ReceitaModel]:
        """
        Lista receitas com filtros opcionais e suporte a busca textual em nome/descrição.
        """
        query = self.db.query(ReceitaModel)
        
        if empresa_id is not None:
            query = query.filter_by(empresa_id=empresa_id)
        
        if ativo is not None:
            query = query.filter_by(ativo=ativo)

        if search and search.strip():
            termo = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    ReceitaModel.nome.ilike(termo),
                    ReceitaModel.descricao.ilike(termo),
                )
            )
        
        return query.order_by(ReceitaModel.nome).all()
    
    def list_receitas_com_ingredientes(
        self,
        empresa_id: Optional[int] = None,
        ativo: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[ReceitaModel]:
        """Lista receitas com seus ingredientes carregados e suporte a busca textual."""
        query = (
            self.db.query(ReceitaModel)
            .options(joinedload(ReceitaModel.ingredientes).joinedload(ReceitaIngredienteModel.ingrediente))
        )
        
        if empresa_id is not None:
            query = query.filter_by(empresa_id=empresa_id)
        
        if ativo is not None:
            query = query.filter_by(ativo=ativo)

        if search and search.strip():
            termo = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    ReceitaModel.nome.ilike(termo),
                    ReceitaModel.descricao.ilike(termo),
                )
            )
        
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
        
        # Verifica se a receita está sendo usada como sub-receita em outras receitas
        receitas_que_usam = (
            self.db.query(ReceitaIngredienteModel)
            .filter(ReceitaIngredienteModel.receita_ingrediente_id == receita_id)
            .count()
        )
        
        if receitas_que_usam > 0:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Não é possível deletar a receita. Ela está sendo usada como ingrediente em {receitas_que_usam} receita(s). "
                f"Remova a receita das receitas que a utilizam antes de deletá-la."
            )
        
        # Verifica se a receita está sendo usada em combos
        from app.api.catalogo.models.model_combo import ComboItemModel
        combos_que_usam = (
            self.db.query(ComboItemModel)
            .filter(ComboItemModel.receita_id == receita_id)
            .count()
        )
        
        if combos_que_usam > 0:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Não é possível deletar a receita. Ela está sendo usada como item em {combos_que_usam} combo(s). "
                f"Remova a receita dos combos que a utilizam antes de deletá-la."
            )
        
        # Verifica se a receita está sendo usada em pedidos
        from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
        pedidos_que_usam = (
            self.db.query(PedidoItemUnificadoModel)
            .filter(PedidoItemUnificadoModel.receita_id == receita_id)
            .count()
        )
        
        if pedidos_que_usam > 0:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Não é possível deletar a receita. Ela está sendo usada em {pedidos_que_usam} item(ns) de pedido(s). "
                f"Não é possível deletar receitas que já foram utilizadas em pedidos."
            )
        
        self.db.delete(receita)
        self.db.commit()

    # Ingredientes - Usa ReceitaIngredienteModel (receita_ingrediente)
    # Relacionamento N:N (um ingrediente pode estar em várias receitas, uma receita pode ter vários ingredientes)
    # Agora suporta: ingredientes, receitas, produtos e combos
    def add_ingrediente(self, data: ReceitaIngredienteIn) -> ReceitaIngredienteModel:
        # Verifica se a receita existe
        receita = self.get_receita_by_id(data.receita_id)
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
        
        # Determina qual tipo de item está sendo adicionado
        if data.ingrediente_id is not None:
            # Ingrediente básico
            ingrediente = self.db.query(IngredienteModel).filter_by(id=data.ingrediente_id).first()
            if not ingrediente:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingrediente não encontrado")
            
            exists = (
                self.db.query(ReceitaIngredienteModel)
                .filter_by(receita_id=data.receita_id, ingrediente_id=data.ingrediente_id)
                .filter(ReceitaIngredienteModel.receita_ingrediente_id.is_(None))
                .filter(ReceitaIngredienteModel.produto_cod_barras.is_(None))
                .filter(ReceitaIngredienteModel.combo_id.is_(None))
                .first()
            )
            if exists:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ingrediente já cadastrado nesta receita")
            
            obj = ReceitaIngredienteModel(
                receita_id=data.receita_id,
                ingrediente_id=data.ingrediente_id,
                receita_ingrediente_id=None,
                produto_cod_barras=None,
                combo_id=None,
                quantidade=data.quantidade,
            )
        
        elif data.receita_ingrediente_id is not None:
            # Sub-receita
            receita_ingrediente = self.get_receita_by_id(data.receita_ingrediente_id)
            if not receita_ingrediente:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita ingrediente não encontrada")
            
            if data.receita_id == data.receita_ingrediente_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uma receita não pode ser ingrediente de si mesma")
            
            exists = (
                self.db.query(ReceitaIngredienteModel)
                .filter_by(receita_id=data.receita_id, receita_ingrediente_id=data.receita_ingrediente_id)
                .filter(ReceitaIngredienteModel.ingrediente_id.is_(None))
                .filter(ReceitaIngredienteModel.produto_cod_barras.is_(None))
                .filter(ReceitaIngredienteModel.combo_id.is_(None))
                .first()
            )
            if exists:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sub-receita já cadastrada nesta receita")
            
            obj = ReceitaIngredienteModel(
                receita_id=data.receita_id,
                ingrediente_id=None,
                receita_ingrediente_id=data.receita_ingrediente_id,
                produto_cod_barras=None,
                combo_id=None,
                quantidade=data.quantidade,
            )
        
        elif data.produto_cod_barras is not None:
            # Produto normal
            produto = self.db.query(ProdutoModel).filter_by(cod_barras=data.produto_cod_barras).first()
            if not produto:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")
            
            exists = (
                self.db.query(ReceitaIngredienteModel)
                .filter_by(receita_id=data.receita_id, produto_cod_barras=data.produto_cod_barras)
                .filter(ReceitaIngredienteModel.ingrediente_id.is_(None))
                .filter(ReceitaIngredienteModel.receita_ingrediente_id.is_(None))
                .filter(ReceitaIngredienteModel.combo_id.is_(None))
                .first()
            )
            if exists:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Produto já cadastrado nesta receita")
            
            obj = ReceitaIngredienteModel(
                receita_id=data.receita_id,
                ingrediente_id=None,
                receita_ingrediente_id=None,
                produto_cod_barras=data.produto_cod_barras,
                combo_id=None,
                quantidade=data.quantidade,
            )
        
        elif data.combo_id is not None:
            # Combo
            combo = self.db.query(ComboModel).filter_by(id=data.combo_id).first()
            if not combo:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Combo não encontrado")
            
            exists = (
                self.db.query(ReceitaIngredienteModel)
                .filter_by(receita_id=data.receita_id, combo_id=data.combo_id)
                .filter(ReceitaIngredienteModel.ingrediente_id.is_(None))
                .filter(ReceitaIngredienteModel.receita_ingrediente_id.is_(None))
                .filter(ReceitaIngredienteModel.produto_cod_barras.is_(None))
                .first()
            )
            if exists:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Combo já cadastrado nesta receita")
            
            obj = ReceitaIngredienteModel(
                receita_id=data.receita_id,
                ingrediente_id=None,
                receita_ingrediente_id=None,
                produto_cod_barras=None,
                combo_id=data.combo_id,
                quantidade=data.quantidade,
            )
        
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Deve fornecer ingrediente_id, receita_ingrediente_id, produto_cod_barras ou combo_id")
        
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
            .options(
                joinedload(ReceitaIngredienteModel.ingrediente),
                joinedload(ReceitaIngredienteModel.receita_ingrediente),
                joinedload(ReceitaIngredienteModel.produto),
                joinedload(ReceitaIngredienteModel.combo)
            )
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

    def calcular_custo_receita(self, receita_id: int, receitas_visitadas: Optional[set] = None) -> Decimal:
        """
        Calcula o custo total de uma receita baseado nos custos dos ingredientes vinculados.
        O cálculo é: soma de (quantidade * custo) para cada ingrediente vinculado.
        
        Agora também suporta sub-receitas: quando uma receita é usada como ingrediente,
        calcula o custo da sub-receita recursivamente.
        
        Args:
            receita_id: ID da receita
            receitas_visitadas: Set de IDs de receitas já visitadas (para evitar loops infinitos)
        
        Returns:
            Custo total da receita
        """
        receita = self.get_receita_by_id(receita_id)
        if not receita:
            return Decimal('0.00')
        
        # Inicializa o set de receitas visitadas se não foi fornecido
        if receitas_visitadas is None:
            receitas_visitadas = set()
        
        # Proteção contra loops infinitos (referências circulares)
        if receita_id in receitas_visitadas:
            # Se já visitamos esta receita, retorna 0 para evitar loop infinito
            # Isso pode acontecer se houver referências circulares (ex: receita A usa receita B, receita B usa receita A)
            return Decimal('0.00')
        
        # Marca esta receita como visitada
        receitas_visitadas.add(receita_id)
        
        # Busca todos os ingredientes vinculados à receita com seus dados
        ingredientes = (
            self.db.query(ReceitaIngredienteModel)
            .options(
                joinedload(ReceitaIngredienteModel.ingrediente),
                joinedload(ReceitaIngredienteModel.receita_ingrediente)
            )
            .filter(ReceitaIngredienteModel.receita_id == receita_id)
            .all()
        )
        
        custo_total = Decimal('0.00')
        for receita_ingrediente in ingredientes:
            quantidade = receita_ingrediente.quantidade if receita_ingrediente.quantidade else Decimal('0.00')
            
            # Se for um ingrediente básico
            if receita_ingrediente.ingrediente_id is not None and receita_ingrediente.ingrediente:
                custo_ingrediente = receita_ingrediente.ingrediente.custo if receita_ingrediente.ingrediente.custo else Decimal('0.00')
                custo_total += quantidade * custo_ingrediente
            
            # Se for uma sub-receita
            elif receita_ingrediente.receita_ingrediente_id is not None:
                # Calcula o custo da sub-receita recursivamente
                custo_sub_receita = self.calcular_custo_receita(
                    receita_ingrediente.receita_ingrediente_id,
                    receitas_visitadas.copy()  # Passa uma cópia para evitar modificar o set original
                )
                custo_total += quantidade * custo_sub_receita
        
        return custo_total

