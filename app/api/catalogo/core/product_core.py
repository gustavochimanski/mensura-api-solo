"""
ProductCore - Sistema unificado para lidar com produtos, combos, receitas, complementos e adicionais.

Este módulo fornece uma interface unificada para trabalhar com diferentes tipos de produtos
(produtos simples, combos, receitas) de forma consistente, abstraindo as diferenças entre eles.
"""

from __future__ import annotations

from enum import Enum
from decimal import Decimal
from typing import Optional, List, Dict, Any, Sequence
from dataclasses import dataclass
from abc import ABC, abstractmethod

from app.api.catalogo.contracts.produto_contract import IProdutoContract, ProdutoEmpDTO
from app.api.catalogo.contracts.combo_contract import IComboContract, ComboMiniDTO
from app.api.catalogo.contracts.receitas_contract import IReceitasContract
from app.api.catalogo.contracts.complemento_contract import IComplementoContract, ComplementoDTO
from app.api.pedidos.utils.complementos import resolve_produto_complementos, resolve_complementos_diretos


class ProductType(str, Enum):
    """Enum para identificar o tipo de produto."""
    PRODUTO = "produto"
    COMBO = "combo"
    RECEITA = "receita"


@dataclass
class ProductBase:
    """
    Classe base unificada para representar qualquer tipo de produto.
    Abstrai as diferenças entre produtos, combos e receitas.
    """
    product_type: ProductType
    identifier: str | int  # cod_barras para produtos, id para combos/receitas
    empresa_id: int
    nome: str
    descricao: Optional[str] = None
    preco_base: Decimal = Decimal("0")
    ativo: bool = True
    disponivel: bool = True
    imagem: Optional[str] = None
    
    def get_preco_venda(self) -> Decimal:
        """Retorna o preço de venda do produto."""
        return self.preco_base
    
    def is_available(self) -> bool:
        """Verifica se o produto está disponível para venda."""
        return self.ativo and self.disponivel


class ProductCore:
    """
    Core unificado para lidar com produtos, combos, receitas, complementos e adicionais.
    
    Fornece métodos unificados para:
    - Buscar produtos de qualquer tipo
    - Validar disponibilidade
    - Calcular preços com complementos
    - Resolver complementos e adicionais
    - Obter informações unificadas
    """
    
    def __init__(
        self,
        produto_contract: Optional[IProdutoContract] = None,
        combo_contract: Optional[IComboContract] = None,
        receita_contract: Optional[IReceitasContract] = None,
        complemento_contract: Optional[IComplementoContract] = None,
    ):
        self.produto_contract = produto_contract
        self.combo_contract = combo_contract
        self.receita_contract = receita_contract
        self.complemento_contract = complemento_contract
    
    # ========== Métodos de Busca ==========
    
    def buscar_produto(
        self,
        empresa_id: int,
        cod_barras: Optional[str] = None,
        produto_id: Optional[int] = None,
    ) -> Optional[ProductBase]:
        """
        Busca um produto por código de barras.
        
        Args:
            empresa_id: ID da empresa
            cod_barras: Código de barras do produto
            
        Returns:
            ProductBase ou None se não encontrado
        """
        if not self.produto_contract or not cod_barras:
            return None
        
        produto_emp = self.produto_contract.obter_produto_emp_por_cod(empresa_id, cod_barras)
        if not produto_emp or not produto_emp.produto:
            return None
        
        produto = produto_emp.produto
        
        return ProductBase(
            product_type=ProductType.PRODUTO,
            identifier=cod_barras,
            empresa_id=empresa_id,
            nome=produto.descricao,
            descricao=produto.descricao,
            preco_base=produto_emp.preco_venda,
            ativo=produto.ativo,
            disponivel=produto_emp.disponivel,
            imagem=produto.imagem,
        )
    
    def buscar_combo(
        self,
        combo_id: int,
    ) -> Optional[ProductBase]:
        """
        Busca um combo por ID.
        
        Args:
            combo_id: ID do combo
            
        Returns:
            ProductBase ou None se não encontrado
        """
        if not self.combo_contract:
            return None
        
        combo = self.combo_contract.buscar_por_id(combo_id)
        if not combo:
            return None
        
        return ProductBase(
            product_type=ProductType.COMBO,
            identifier=combo_id,
            empresa_id=combo.empresa_id,
            nome=combo.titulo or "Combo",
            descricao=combo.titulo,
            preco_base=combo.preco_total,
            ativo=combo.ativo,
            disponivel=combo.ativo,  # Combos não têm campo disponivel separado
            imagem=None,  # Combos podem ter imagem, mas não está no DTO
        )
    
    def buscar_receita(
        self,
        receita_id: int,
        empresa_id: Optional[int] = None,
        receita_model: Optional[Any] = None,
    ) -> Optional[ProductBase]:
        """
        Busca uma receita por ID.
        
        Args:
            receita_id: ID da receita
            empresa_id: ID da empresa (opcional, para validação)
            receita_model: Modelo de receita do SQLAlchemy (opcional, para evitar busca extra)
            
        Returns:
            ProductBase ou None se não encontrado
        """
        # Se receita_model foi fornecido, usa diretamente
        if receita_model:
            return ProductBase(
                product_type=ProductType.RECEITA,
                identifier=receita_id,
                empresa_id=receita_model.empresa_id,
                nome=receita_model.nome,
                descricao=receita_model.descricao,
                preco_base=receita_model.preco_venda,
                ativo=receita_model.ativo,
                disponivel=receita_model.disponivel,
                imagem=receita_model.imagem,
            )
        
        # Nota: IReceitasContract atual não tem método buscar_por_id
        # Para usar este método sem receita_model, é necessário ter acesso ao repositório
        # ou implementar o método no contract
        return None
    
    def buscar_qualquer(
        self,
        empresa_id: int,
        cod_barras: Optional[str] = None,
        combo_id: Optional[int] = None,
        receita_id: Optional[int] = None,
        receita_model: Optional[Any] = None,
    ) -> Optional[ProductBase]:
        """
        Busca qualquer tipo de produto (produto, combo ou receita).
        
        Args:
            empresa_id: ID da empresa
            cod_barras: Código de barras (para produtos)
            combo_id: ID do combo
            receita_id: ID da receita
            receita_model: Modelo de receita do SQLAlchemy (opcional, para evitar busca extra)
            
        Returns:
            ProductBase ou None se não encontrado
        """
        if cod_barras:
            return self.buscar_produto(empresa_id, cod_barras)
        elif combo_id:
            return self.buscar_combo(combo_id)
        elif receita_id:
            return self.buscar_receita(receita_id, empresa_id, receita_model)
        
        return None
    
    def criar_de_modelo(
        self,
        model: Any,
    ) -> Optional[ProductBase]:
        """
        Cria um ProductBase a partir de um modelo do SQLAlchemy.
        
        Args:
            model: Modelo do SQLAlchemy (ProdutoModel, ComboModel, ReceitaModel)
            
        Returns:
            ProductBase ou None se o modelo não for reconhecido
        """
        from app.api.catalogo.models.model_produto import ProdutoModel
        from app.api.catalogo.models.model_combo import ComboModel
        from app.api.catalogo.models.model_receita import ReceitaModel
        
        if isinstance(model, ProdutoModel):
            # Para produtos, precisa buscar ProdutoEmpModel para obter preço
            # Por enquanto, retorna None - precisa de mais contexto
            return None
        elif isinstance(model, ComboModel):
            return ProductBase(
                product_type=ProductType.COMBO,
                identifier=model.id,
                empresa_id=model.empresa_id,
                nome=model.titulo or model.descricao,
                descricao=model.descricao,
                preco_base=model.preco_total,
                ativo=model.ativo,
                disponivel=model.ativo,
                imagem=model.imagem,
            )
        elif isinstance(model, ReceitaModel):
            return ProductBase(
                product_type=ProductType.RECEITA,
                identifier=model.id,
                empresa_id=model.empresa_id,
                nome=model.nome,
                descricao=model.descricao,
                preco_base=model.preco_venda,
                ativo=model.ativo,
                disponivel=model.disponivel,
                imagem=model.imagem,
            )
        
        return None
    
    # ========== Métodos de Validação ==========
    
    def validar_disponivel(
        self,
        product: ProductBase,
        quantidade: int = 1,
    ) -> bool:
        """
        Valida se um produto está disponível para venda.
        
        Args:
            product: ProductBase a ser validado
            quantidade: Quantidade desejada
            
        Returns:
            True se disponível, False caso contrário
        """
        if not product.is_available():
            return False
        
        # Validação específica por tipo
        if product.product_type == ProductType.PRODUTO:
            if not self.produto_contract:
                return False
            return self.produto_contract.validar_produto_disponivel(
                product.empresa_id,
                str(product.identifier),
                quantidade,
            )
        elif product.product_type == ProductType.COMBO:
            # Combos não têm validação de estoque adicional
            return product.ativo
        elif product.product_type == ProductType.RECEITA:
            # Receitas não têm validação de estoque adicional
            return product.ativo and product.disponivel
        
        return False
    
    def validar_empresa(
        self,
        product: ProductBase,
        empresa_id: int,
    ) -> bool:
        """
        Valida se o produto pertence à empresa especificada.
        
        Args:
            product: ProductBase a ser validado
            empresa_id: ID da empresa
            
        Returns:
            True se pertence à empresa, False caso contrário
        """
        return product.empresa_id == empresa_id
    
    # ========== Métodos de Complementos ==========
    
    def listar_complementos(
        self,
        product: ProductBase,
        apenas_ativos: bool = True,
        db: Optional[Any] = None,
    ) -> List[ComplementoDTO]:
        """
        Lista todos os complementos vinculados a um produto.
        
        Args:
            product: ProductBase
            apenas_ativos: Se True, retorna apenas complementos ativos
            db: Session do SQLAlchemy (opcional, necessário para receitas e combos)
            
        Returns:
            Lista de ComplementoDTO
        """
        if not self.complemento_contract:
            return []
        
        if product.product_type == ProductType.PRODUTO:
            return self.complemento_contract.listar_por_produto(
                str(product.identifier),
                apenas_ativos=apenas_ativos,
            )
        elif product.product_type == ProductType.COMBO:
            # Para combos, usa método do adapter
            return self.complemento_contract.listar_por_combo(
                int(product.identifier),
                apenas_ativos=apenas_ativos,
            )
        elif product.product_type == ProductType.RECEITA:
            # Para receitas, usa método do adapter
            return self.complemento_contract.listar_por_receita(
                int(product.identifier),
                apenas_ativos=apenas_ativos,
            )
        #
        return []
    
    def calcular_preco_com_complementos(
        self,
        product: ProductBase,
        quantidade: int,
        complementos_request: Optional[Sequence] = None,
    ) -> tuple[Decimal, List[Dict[str, Any]]]:
        """
        Calcula o preço total de um produto incluindo complementos e adicionais.
        
        Args:
            product: ProductBase
            quantidade: Quantidade do produto
            complementos_request: Lista de complementos com adicionais selecionados
            
        Returns:
            Tupla com (preco_total, snapshot_complementos)
        """
        quantidade = max(1, int(quantidade or 1))
        preco_base = product.get_preco_venda() * quantidade
        
        if not complementos_request:
            return preco_base, []
        
        # Calcula complementos baseado no tipo de produto
        if product.product_type == ProductType.PRODUTO:
            total_complementos, snapshot = resolve_produto_complementos(
                complemento_contract=self.complemento_contract,
                produto_cod_barras=str(product.identifier),
                complementos_request=complementos_request,
                quantidade_item=quantidade,
            )
        else:
            # Combos e receitas usam busca direta por IDs
            combo_id = None
            receita_id = None
            if product.product_type == ProductType.COMBO:
                combo_id = product.identifier
            elif product.product_type == ProductType.RECEITA:
                receita_id = product.identifier
            
            total_complementos, snapshot = resolve_complementos_diretos(
                complemento_contract=self.complemento_contract,
                empresa_id=product.empresa_id,
                complementos_request=complementos_request,
                quantidade_item=quantidade,
                combo_id=combo_id,
                receita_id=receita_id,
            )
        
        preco_total = preco_base + total_complementos
        return preco_total, snapshot
    
    # ========== Métodos Utilitários ==========
    
    def obter_descricao_completa(
        self,
        product: ProductBase,
    ) -> str:
        """
        Obtém uma descrição completa do produto.
        
        Args:
            product: ProductBase
            
        Returns:
            String com descrição completa
        """
        tipo_nome = {
            ProductType.PRODUTO: "Produto",
            ProductType.COMBO: "Combo",
            ProductType.RECEITA: "Receita",
        }.get(product.product_type, "Produto")
        
        return f"{tipo_nome}: {product.nome}"
    
    def obter_identificador_formatado(
        self,
        product: ProductBase,
    ) -> str:
        """
        Obtém o identificador formatado do produto.
        
        Args:
            product: ProductBase
            
        Returns:
            String formatada com o identificador
        """
        if product.product_type == ProductType.PRODUTO:
            return f"COD: {product.identifier}"
        else:
            return f"ID: {product.identifier}"
    
    # ========== Métodos Helper para Processamento de Pedidos ==========
    
    def processar_item_pedido(
        self,
        product: ProductBase,
        quantidade: int,
        complementos_request: Optional[Sequence] = None,
        observacao: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Processa um item completo de pedido (produto, receita ou combo).
        
        Este método unifica todo o processamento necessário para adicionar um item ao pedido:
        - Valida disponibilidade
        - Calcula preço com complementos
        - Prepara dados formatados
        
        Args:
            product: ProductBase do produto
            quantidade: Quantidade do item
            complementos_request: Lista de complementos selecionados
            observacao: Observação adicional do item
            
        Returns:
            Dicionário com todos os dados processados:
            {
                'product': ProductBase,
                'preco_total': Decimal,
                'preco_unitario': Decimal,
                'complementos_snapshot': List[Dict],
                'descricao': str,
                'observacao_formatada': str,
                'tipo': str,
            }
        """
        quantidade = max(1, int(quantidade or 1))
        
        # Calcula preço com complementos
        preco_total, complementos_snapshot = self.calcular_preco_com_complementos(
            product=product,
            quantidade=quantidade,
            complementos_request=complementos_request,
        )
        
        preco_unitario = preco_total / quantidade
        descricao = product.nome or product.descricao or ""
        
        # Formata observação baseado no tipo
        observacao_formatada = observacao or ""
        if product.product_type == ProductType.COMBO:
            observacao_formatada = f"Combo #{product.identifier} - {descricao}"
            if observacao:
                observacao_formatada += f" | {observacao}"
        elif product.product_type == ProductType.RECEITA:
            observacao_formatada = f"Receita #{product.identifier} - {descricao}"
            if observacao:
                observacao_formatada += f" | {observacao}"
        
        return {
            'product': product,
            'preco_total': preco_total,
            'preco_unitario': preco_unitario,
            'complementos_snapshot': complementos_snapshot,
            'descricao': descricao,
            'observacao_formatada': observacao_formatada,
            'tipo': product.product_type.value,
        }
    
    def validar_e_processar_item(
        self,
        empresa_id: int,
        cod_barras: Optional[str] = None,
        combo_id: Optional[int] = None,
        receita_id: Optional[int] = None,
        receita_model: Optional[Any] = None,
        quantidade: int = 1,
        complementos_request: Optional[Sequence] = None,
        observacao: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Método completo que busca, valida e processa um item de pedido.
        
        Combina buscar_qualquer, validações e processar_item_pedido em um único método.
        
        Args:
            empresa_id: ID da empresa
            cod_barras: Código de barras do produto (opcional)
            combo_id: ID do combo (opcional)
            receita_id: ID da receita (opcional)
            receita_model: Modelo de receita do SQLAlchemy (opcional, para evitar busca extra)
            quantidade: Quantidade do item
            complementos_request: Lista de complementos selecionados
            observacao: Observação adicional
            
        Returns:
            Dicionário com todos os dados processados (mesmo formato de processar_item_pedido)
            
        Raises:
            ValueError: Se produto não encontrado ou inválido
        """
        # Busca produto
        product = self.buscar_qualquer(
            empresa_id=empresa_id,
            cod_barras=cod_barras,
            combo_id=combo_id,
            receita_id=receita_id,
            receita_model=receita_model,
        )
        
        if not product:
            raise ValueError("Produto não encontrado")
        
        # Validações
        if not self.validar_disponivel(product, quantidade):
            tipo_nome = product.product_type.value
            raise ValueError(f"{tipo_nome.capitalize()} não disponível")
        
        if not self.validar_empresa(product, empresa_id):
            raise ValueError(f"Produto não pertence à empresa {empresa_id}")
        
        # Processa item
        return self.processar_item_pedido(
            product=product,
            quantidade=quantidade,
            complementos_request=complementos_request,
            observacao=observacao,
        )

