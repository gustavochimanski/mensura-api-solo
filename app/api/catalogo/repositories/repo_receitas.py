from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from fastapi import HTTPException, status
from decimal import Decimal

from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
# AdicionalModel removido - não é mais usado
# Adicionais agora são vínculos de produtos/receitas/combos em complementos (complemento_vinculo_item)
from app.api.catalogo.models.model_receita import ReceitaIngredienteModel, ReceitaModel
# Nota: ReceitaAdicionalModel foi removido - adicionais agora são vínculos de produtos/receitas/combos em complementos
from app.api.catalogo.models.model_combo import ComboModel
from app.api.catalogo.schemas.schema_receitas import (
    ReceitaIngredienteIn,
    ReceitaIn,
    ReceitaUpdate,
)


class ReceitasRepository:
    def __init__(self, db: Session):
        self.db = db

    def _buscar_preco_adicional(self, adicional_id: int) -> Decimal:
        """
        DEPRECADO: AdicionalModel foi removido.
        Adicionais agora são vínculos de produtos/receitas/combos em complementos (complemento_vinculo_item).
        Retorna 0.00 sempre, pois o preço deve vir do vínculo do complemento.
        """
        # AdicionalModel foi removido - preço agora vem de complemento_vinculo_item
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
        query = self.db.query(ReceitaModel).options(
            joinedload(ReceitaModel.ingredientes).joinedload(ReceitaIngredienteModel.receita_ingrediente),
            joinedload(ReceitaModel.ingredientes).joinedload(ReceitaIngredienteModel.produto),
            joinedload(ReceitaModel.ingredientes).joinedload(ReceitaIngredienteModel.combo),
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

    # Itens - Usa ReceitaIngredienteModel (receita_ingrediente)
    # Relacionamento N:N (uma receita pode ter vários itens)
    # Suporta: sub-receitas, produtos e combos
    def add_ingrediente(self, data: ReceitaIngredienteIn) -> ReceitaIngredienteModel:
        # Verifica se a receita existe
        receita = self.get_receita_by_id(data.receita_id)
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
        
        # Determina qual tipo de item está sendo adicionado
        if data.receita_ingrediente_id is not None:
            # Sub-receita
            receita_ingrediente = self.get_receita_by_id(data.receita_ingrediente_id)
            if not receita_ingrediente:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita ingrediente não encontrada")
            
            if data.receita_id == data.receita_ingrediente_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uma receita não pode ser ingrediente de si mesma")
            
            exists = (
                self.db.query(ReceitaIngredienteModel)
                .filter_by(receita_id=data.receita_id, receita_ingrediente_id=data.receita_ingrediente_id)
                .filter(ReceitaIngredienteModel.produto_cod_barras.is_(None))
                .filter(ReceitaIngredienteModel.combo_id.is_(None))
                .first()
            )
            if exists:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sub-receita já cadastrada nesta receita")
            
            obj = ReceitaIngredienteModel(
                receita_id=data.receita_id,
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
                .filter(ReceitaIngredienteModel.receita_ingrediente_id.is_(None))
                .filter(ReceitaIngredienteModel.combo_id.is_(None))
                .first()
            )
            if exists:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Produto já cadastrado nesta receita")
            
            obj = ReceitaIngredienteModel(
                receita_id=data.receita_id,
                receita_ingrediente_id=None,
                produto_id=produto.id,
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
                .filter(ReceitaIngredienteModel.receita_ingrediente_id.is_(None))
                .filter(ReceitaIngredienteModel.produto_cod_barras.is_(None))
                .first()
            )
            if exists:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Combo já cadastrado nesta receita")
            
            obj = ReceitaIngredienteModel(
                receita_id=data.receita_id,
                receita_ingrediente_id=None,
                produto_cod_barras=None,
                combo_id=data.combo_id,
                quantidade=data.quantidade,
            )
        
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Deve fornecer receita_ingrediente_id, produto_cod_barras ou combo_id")
        
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def list_ingredientes(self, receita_id: int, tipo: Optional[str] = None) -> List[ReceitaIngredienteModel]:
        """
        Lista todos os itens de uma receita, opcionalmente filtrados por tipo.
        
        Args:
            receita_id: ID da receita
            tipo: Tipo de item a filtrar ('sub-receita', 'produto' ou 'combo')
        """
        # Verifica se a receita existe
        receita = self.get_receita_by_id(receita_id)
        if not receita:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Receita não encontrada")
        
        query = (
            self.db.query(ReceitaIngredienteModel)
            .options(
                joinedload(ReceitaIngredienteModel.receita_ingrediente),
                joinedload(ReceitaIngredienteModel.produto),
                joinedload(ReceitaIngredienteModel.combo)
            )
            .filter(ReceitaIngredienteModel.receita_id == receita_id)
        )
        
        # Aplica filtro por tipo se fornecido
        if tipo:
            if tipo == "sub-receita":
                query = query.filter(ReceitaIngredienteModel.receita_ingrediente_id.isnot(None))
            elif tipo == "produto":
                query = query.filter(ReceitaIngredienteModel.produto_cod_barras.isnot(None))
            elif tipo == "combo":
                query = query.filter(ReceitaIngredienteModel.combo_id.isnot(None))
            else:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Tipo inválido: {tipo}. Tipos válidos: sub-receita, produto, combo"
                )
        
        return query.all()

    def update_ingrediente(self, receita_ingrediente_id: int, quantidade: float | None) -> ReceitaIngredienteModel:
        """
        Atualiza a quantidade de um item (ingrediente, receita, produto ou combo) em uma receita.
        
        Args:
            receita_ingrediente_id: ID do vínculo na tabela receita_ingrediente
            quantidade: Nova quantidade do item
        """
        obj = self.db.query(ReceitaIngredienteModel).filter_by(id=receita_ingrediente_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Item não encontrado na receita")
        if quantidade is not None:
            obj.quantidade = quantidade
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def remove_ingrediente(self, ingrediente_id: int) -> None:
        """
        Remove um item (ingrediente, receita, produto ou combo) de uma receita.
        
        Args:
            ingrediente_id: ID do vínculo na tabela receita_ingrediente (não é o ID do ingrediente em si)
        """
        obj = self.db.query(ReceitaIngredienteModel).filter_by(id=ingrediente_id).first()
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Item não encontrado na receita")
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
                joinedload(ReceitaIngredienteModel.receita_ingrediente),
                joinedload(ReceitaIngredienteModel.produto),
                joinedload(ReceitaIngredienteModel.combo),
            )
            .filter(ReceitaIngredienteModel.receita_id == receita_id)
            .all()
        )
        
        custo_total = Decimal('0.00')
        for receita_ingrediente in ingredientes:
            quantidade = receita_ingrediente.quantidade if receita_ingrediente.quantidade else Decimal('0.00')
            
            # Se for uma sub-receita
            if receita_ingrediente.receita_ingrediente_id is not None:
                # Calcula o custo da sub-receita recursivamente
                custo_sub_receita = self.calcular_custo_receita(
                    receita_ingrediente.receita_ingrediente_id,
                    receitas_visitadas.copy()  # Passa uma cópia para evitar modificar o set original
                )
                custo_total += quantidade * custo_sub_receita
            
            # Se for um produto
            elif receita_ingrediente.produto_cod_barras is not None:
                produto_emp = (
                    self.db.query(ProdutoEmpModel)
                    .filter_by(empresa_id=receita.empresa_id, cod_barras=receita_ingrediente.produto_cod_barras)
                    .first()
                )
                custo_produto = produto_emp.custo if produto_emp and produto_emp.custo is not None else Decimal('0.00')
                custo_total += quantidade * custo_produto
            
            # Se for um combo, usa o preço total como referência de custo
            elif receita_ingrediente.combo_id is not None and receita_ingrediente.combo:
                custo_combo = receita_ingrediente.combo.preco_total if receita_ingrediente.combo.preco_total is not None else Decimal('0.00')
                custo_total += quantidade * custo_combo
        
        return custo_total

    def clonar_ingredientes(self, receita_origem_id: int, receita_destino_id: int) -> int:
        """
        Clona todos os ingredientes de uma receita para outra.
        
        Args:
            receita_origem_id: ID da receita de origem (de onde serão copiados os ingredientes)
            receita_destino_id: ID da receita de destino (para onde serão copiados os ingredientes)
        
        Returns:
            Número de ingredientes clonados
        """
        # Verifica se as receitas existem
        receita_origem = self.get_receita_by_id(receita_origem_id)
        if not receita_origem:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Receita origem (ID: {receita_origem_id}) não encontrada")
        
        receita_destino = self.get_receita_by_id(receita_destino_id)
        if not receita_destino:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Receita destino (ID: {receita_destino_id}) não encontrada")
        
        # Verifica se as receitas são diferentes
        if receita_origem_id == receita_destino_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Não é possível clonar ingredientes para a mesma receita")
        
        # Busca todos os ingredientes da receita origem
        ingredientes_origem = (
            self.db.query(ReceitaIngredienteModel)
            .filter(ReceitaIngredienteModel.receita_id == receita_origem_id)
            .all()
        )
        
        if not ingredientes_origem:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"A receita origem (ID: {receita_origem_id}) não possui ingredientes para clonar"
            )
        
        # Contador de ingredientes clonados
        ingredientes_clonados = 0
        
        # Clona cada ingrediente para a receita destino
        for ingrediente_origem in ingredientes_origem:
            # Verifica se o ingrediente já existe na receita destino
            # (para evitar duplicatas)
            if ingrediente_origem.receita_ingrediente_id is not None:
                # Sub-receita
                exists = (
                    self.db.query(ReceitaIngredienteModel)
                    .filter_by(receita_id=receita_destino_id, receita_ingrediente_id=ingrediente_origem.receita_ingrediente_id)
                    .filter(ReceitaIngredienteModel.produto_cod_barras.is_(None))
                    .filter(ReceitaIngredienteModel.combo_id.is_(None))
                    .first()
                )
            elif ingrediente_origem.produto_cod_barras is not None:
                # Produto
                exists = (
                    self.db.query(ReceitaIngredienteModel)
                    .filter_by(receita_id=receita_destino_id, produto_cod_barras=ingrediente_origem.produto_cod_barras)
                    .filter(ReceitaIngredienteModel.receita_ingrediente_id.is_(None))
                    .filter(ReceitaIngredienteModel.combo_id.is_(None))
                    .first()
                )
            elif ingrediente_origem.combo_id is not None:
                # Combo
                exists = (
                    self.db.query(ReceitaIngredienteModel)
                    .filter_by(receita_id=receita_destino_id, combo_id=ingrediente_origem.combo_id)
                    .filter(ReceitaIngredienteModel.receita_ingrediente_id.is_(None))
                    .filter(ReceitaIngredienteModel.produto_cod_barras.is_(None))
                    .first()
                )
            else:
                # Item inválido (não deveria acontecer)
                continue
            
            # Se o ingrediente já existe, pula
            if exists:
                continue
            
            # Cria novo ingrediente na receita destino
            novo_ingrediente = ReceitaIngredienteModel(
                receita_id=receita_destino_id,
                receita_ingrediente_id=ingrediente_origem.receita_ingrediente_id,
                produto_id=getattr(ingrediente_origem, "produto_id", None),
                produto_cod_barras=ingrediente_origem.produto_cod_barras,
                combo_id=ingrediente_origem.combo_id,
                quantidade=ingrediente_origem.quantidade,
            )
            
            self.db.add(novo_ingrediente)
            ingredientes_clonados += 1
        
        # Commit de todas as alterações
        self.db.commit()
        
        return ingredientes_clonados

