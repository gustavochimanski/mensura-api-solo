from typing import List, Optional
from sqlalchemy.orm import Session
from app.api.catalogo.models.model_complemento import ComplementoModel
from app.api.catalogo.models.model_produto import ProdutoModel


class ComplementoRepository:
    """Repository para operações CRUD de complementos."""

    def __init__(self, db: Session):
        self.db = db
        from app.utils.logger import logger
        self.logger = logger

    def criar_complemento(self, **data) -> ComplementoModel:
        """Cria um novo complemento."""
        obj = ComplementoModel(**data)
        self.db.add(obj)
        self.db.flush()
        return obj

    def buscar_por_id(self, complemento_id: int, carregar_adicionais: bool = False) -> Optional[ComplementoModel]:
        """Busca um complemento por ID. carregar_adicionais ignorado (itens vêm de complemento_vinculo_item)."""
        return self.db.query(ComplementoModel).filter_by(id=complemento_id).first()

    def listar_por_empresa(self, empresa_id: int, apenas_ativos: bool = True, carregar_adicionais: bool = False) -> List[ComplementoModel]:
        """Lista todos os complementos de uma empresa."""
        query = self.db.query(ComplementoModel).filter_by(empresa_id=empresa_id)
        if apenas_ativos:
            query = query.filter_by(ativo=True)
        return query.order_by(ComplementoModel.ordem, ComplementoModel.nome).all()

    def listar_por_produto(self, cod_barras: str, apenas_ativos: bool = True, carregar_adicionais: bool = False) -> List[tuple]:
        """Lista todos os complementos vinculados a um produto.
        
        Returns:
            Lista de tuplas (complemento, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens) ordenadas por ordem.
        """
        from app.api.catalogo.models.association_tables import produto_complemento_link
        from sqlalchemy import select

        produto = self.db.query(ProdutoModel).filter_by(cod_barras=cod_barras).first()
        if not produto:
            return []
        
        query = (
            select(
                ComplementoModel, 
                produto_complemento_link.c.ordem,
                produto_complemento_link.c.obrigatorio,
                produto_complemento_link.c.quantitativo,
                produto_complemento_link.c.minimo_itens,
                produto_complemento_link.c.maximo_itens
            )
            .join(produto_complemento_link, ComplementoModel.id == produto_complemento_link.c.complemento_id)
            .where(produto_complemento_link.c.produto_id == produto.id)
        )
        if apenas_ativos:
            query = query.where(ComplementoModel.ativo == True)
        query = query.order_by(produto_complemento_link.c.ordem, ComplementoModel.nome)
        result = self.db.execute(query)
        results = result.all()
        return [(complemento, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens) 
                for complemento, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens in results]

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

    def vincular_complementos_produto(
        self, 
        cod_barras: str, 
        complemento_ids: List[int], 
        ordens: Optional[List[int]] = None,
        obrigatorios: Optional[List[bool]] = None,
        quantitativos: Optional[List[bool]] = None,
        minimos_itens: Optional[List[Optional[int]]] = None,
        maximos_itens: Optional[List[Optional[int]]] = None
    ):
        """Vincula múltiplos complementos a um produto.
        
        Args:
            cod_barras: Código de barras do produto
            complemento_ids: Lista de IDs dos complementos a vincular
            ordens: Lista opcional de ordens. Se não informado, usa o índice como ordem.
            obrigatorios: Lista de obrigatoriedade (obrigatório, sem valores padrão).
            quantitativos: Lista de quantitativo (obrigatório, sem valores padrão).
            minimos_itens: Lista opcional de mínimos.
            maximos_itens: Lista opcional de máximos.
        """
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
        
        # Valida que todos os complementos foram encontrados
        if len(complementos) != len(complemento_ids):
            encontrados_ids = {c.id for c in complementos}
            nao_encontrados = [cid for cid in complemento_ids if cid not in encontrados_ids]
            raise ValueError(f"Complementos não encontrados: {nao_encontrados}")
        
        # Remove vinculações existentes
        # Log e remove vinculações existentes
        self.logger.info(f"[ComplementoRepository] Removendo vinculações existentes para produto_id={produto.id} (cod_barras={cod_barras})")
        self.db.execute(
            produto_complemento_link.delete().where(
                produto_complemento_link.c.produto_id == produto.id
            )
        )
        
        # Adiciona novas vinculações com ordens e configurações
        if ordens is None:
            ordens = list(range(len(complemento_ids)))
        
        # Garante que ordens tenha o mesmo tamanho de complemento_ids
        if len(ordens) != len(complemento_ids):
            ordens = list(range(len(complemento_ids)))
        
        # Garante que as listas de configuração tenham o mesmo tamanho
        if obrigatorios is None:
            obrigatorios = [False] * len(complemento_ids)
        if quantitativos is None:
            quantitativos = [False] * len(complemento_ids)
        if minimos_itens is None:
            minimos_itens = [None] * len(complemento_ids)
        if maximos_itens is None:
            maximos_itens = [None] * len(complemento_ids)
        
        for idx, complemento_id in enumerate(complemento_ids):
            # Encontra o complemento correspondente
            complemento = next((c for c in complementos if c.id == complemento_id), None)
            if complemento:
                self.logger.info(f"[ComplementoRepository] Inserindo vinculo produto_id={produto.id} complemento_id={complemento.id} ordem={ordens[idx]} obrigatorio={obrigatorios[idx] if obrigatorios is not None else None}")
                self.db.execute(
                    produto_complemento_link.insert().values(
                        produto_id=produto.id,
                        complemento_id=complemento.id,
                        ordem=ordens[idx],
                        obrigatorio=obrigatorios[idx],
                        quantitativo=quantitativos[idx],
                        minimo_itens=minimos_itens[idx],
                        maximo_itens=maximos_itens[idx]
                    )
                )
        
        self.db.flush()

    def desvincular_complemento_produto(self, cod_barras: str, complemento_id: int):
        """Remove a vinculação de um complemento com um produto."""
        from app.api.catalogo.models.association_tables import produto_complemento_link

        produto = self.db.query(ProdutoModel).filter_by(cod_barras=cod_barras).first()
        if not produto:
            return
        
        self.db.execute(
            produto_complemento_link.delete().where(
                produto_complemento_link.c.produto_id == produto.id,
                produto_complemento_link.c.complemento_id == complemento_id
            )
        )
        self.db.flush()

    def listar_por_receita(self, receita_id: int, apenas_ativos: bool = True, carregar_adicionais: bool = False) -> List[tuple]:
        """Lista todos os complementos vinculados a uma receita.
        
        Returns:
            Lista de tuplas (complemento, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens) ordenadas por ordem.
        """
        from app.api.catalogo.models.association_tables import receita_complemento_link
        from sqlalchemy import select
        
        query = (
            select(
                ComplementoModel, 
                receita_complemento_link.c.ordem,
                receita_complemento_link.c.obrigatorio,
                receita_complemento_link.c.quantitativo,
                receita_complemento_link.c.minimo_itens,
                receita_complemento_link.c.maximo_itens
            )
            .join(receita_complemento_link, ComplementoModel.id == receita_complemento_link.c.complemento_id)
            .where(receita_complemento_link.c.receita_id == receita_id)
        )
        if apenas_ativos:
            query = query.where(ComplementoModel.ativo == True)
        query = query.order_by(receita_complemento_link.c.ordem, ComplementoModel.nome)
        result = self.db.execute(query)
        results = result.all()
        return [(complemento, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens) 
                for complemento, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens in results]

    def vincular_complementos_receita(
        self, 
        receita_id: int, 
        complemento_ids: List[int], 
        ordens: Optional[List[int]] = None,
        obrigatorios: Optional[List[bool]] = None,
        quantitativos: Optional[List[bool]] = None,
        minimos_itens: Optional[List[Optional[int]]] = None,
        maximos_itens: Optional[List[Optional[int]]] = None
    ):
        """Vincula múltiplos complementos a uma receita.
        
        Args:
            receita_id: ID da receita
            complemento_ids: Lista de IDs dos complementos a vincular
            ordens: Lista opcional de ordens. Se não informado, usa o índice como ordem.
            obrigatorios: Lista de obrigatoriedade (obrigatório, sem valores padrão).
            quantitativos: Lista de quantitativo (obrigatório, sem valores padrão).
            minimos_itens: Lista opcional de mínimos.
            maximos_itens: Lista opcional de máximos.
        """
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
        
        # Valida que todos os complementos foram encontrados
        if len(complementos) != len(complemento_ids):
            encontrados_ids = {c.id for c in complementos}
            nao_encontrados = [cid for cid in complemento_ids if cid not in encontrados_ids]
            raise ValueError(f"Complementos não encontrados: {nao_encontrados}")
        
        # Remove vinculações existentes
        self.db.execute(
            receita_complemento_link.delete().where(
                receita_complemento_link.c.receita_id == receita_id
            )
        )
        
        # Adiciona novas vinculações com ordens e configurações
        if ordens is None:
            ordens = list(range(len(complemento_ids)))
        
        # Garante que ordens tenha o mesmo tamanho de complemento_ids
        if len(ordens) != len(complemento_ids):
            ordens = list(range(len(complemento_ids)))
        
        # Garante que as listas de configuração tenham o mesmo tamanho
        if obrigatorios is None:
            obrigatorios = [False] * len(complemento_ids)
        if quantitativos is None:
            quantitativos = [False] * len(complemento_ids)
        if minimos_itens is None:
            minimos_itens = [None] * len(complemento_ids)
        if maximos_itens is None:
            maximos_itens = [None] * len(complemento_ids)
        
        for idx, complemento_id in enumerate(complemento_ids):
            # Encontra o complemento correspondente
            complemento = next((c for c in complementos if c.id == complemento_id), None)
            if complemento:
                self.db.execute(
                    receita_complemento_link.insert().values(
                        receita_id=receita_id,
                        complemento_id=complemento.id,
                        ordem=ordens[idx],
                        obrigatorio=obrigatorios[idx],
                        quantitativo=quantitativos[idx],
                        minimo_itens=minimos_itens[idx],
                        maximo_itens=maximos_itens[idx]
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

    def listar_por_combo(self, combo_id: int, apenas_ativos: bool = True, carregar_adicionais: bool = False) -> List[tuple]:
        """Lista todos os complementos vinculados a um combo.
        
        Returns:
            Lista de tuplas (complemento, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens) ordenadas por ordem.
        """
        from app.api.catalogo.models.association_tables import combo_complemento_link
        from sqlalchemy import select
        
        query = (
            select(
                ComplementoModel, 
                combo_complemento_link.c.ordem,
                combo_complemento_link.c.obrigatorio,
                combo_complemento_link.c.quantitativo,
                combo_complemento_link.c.minimo_itens,
                combo_complemento_link.c.maximo_itens
            )
            .join(combo_complemento_link, ComplementoModel.id == combo_complemento_link.c.complemento_id)
            .where(combo_complemento_link.c.combo_id == combo_id)
        )
        if apenas_ativos:
            query = query.where(ComplementoModel.ativo == True)
        query = query.order_by(combo_complemento_link.c.ordem, ComplementoModel.nome)
        result = self.db.execute(query)
        results = result.all()
        return [(complemento, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens) 
                for complemento, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens in results]

    def vincular_complementos_combo(
        self, 
        combo_id: int, 
        complemento_ids: List[int], 
        ordens: Optional[List[int]] = None,
        obrigatorios: Optional[List[bool]] = None,
        quantitativos: Optional[List[bool]] = None,
        minimos_itens: Optional[List[Optional[int]]] = None,
        maximos_itens: Optional[List[Optional[int]]] = None
    ):
        """Vincula múltiplos complementos a um combo.
        
        Args:
            combo_id: ID do combo
            complemento_ids: Lista de IDs dos complementos a vincular
            ordens: Lista opcional de ordens. Se não informado, usa o índice como ordem.
            obrigatorios: Lista de obrigatoriedade (obrigatório, sem valores padrão).
            quantitativos: Lista de quantitativo (obrigatório, sem valores padrão).
            minimos_itens: Lista opcional de mínimos.
            maximos_itens: Lista opcional de máximos.
        """
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
        
        # Adiciona novas vinculações com ordens e configurações
        if ordens is None:
            ordens = list(range(len(complemento_ids)))
        
        # Garante que ordens tenha o mesmo tamanho de complemento_ids
        if len(ordens) != len(complemento_ids):
            ordens = list(range(len(complemento_ids)))
        
        # Garante que as listas de configuração tenham o mesmo tamanho
        if obrigatorios is None:
            obrigatorios = [False] * len(complemento_ids)
        if quantitativos is None:
            quantitativos = [False] * len(complemento_ids)
        if minimos_itens is None:
            minimos_itens = [None] * len(complemento_ids)
        if maximos_itens is None:
            maximos_itens = [None] * len(complemento_ids)
        
        for idx, complemento_id in enumerate(complemento_ids):
            # Encontra o complemento correspondente
            complemento = next((c for c in complementos if c.id == complemento_id), None)
            if complemento:
                self.db.execute(
                    combo_complemento_link.insert().values(
                        combo_id=combo_id,
                        complemento_id=complemento.id,
                        ordem=ordens[idx],
                        obrigatorio=obrigatorios[idx],
                        quantitativo=quantitativos[idx],
                        minimo_itens=minimos_itens[idx],
                        maximo_itens=maximos_itens[idx]
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

