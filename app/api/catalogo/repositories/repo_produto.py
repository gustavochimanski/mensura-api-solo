from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.cardapio.models.model_vitrine import VitrinesModel
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.catalogo.models.model_produto import ProdutoModel


# -------- Listagem paginada --------
class ProdutoMensuraRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_por_cod_barras(self, cod_barras: str) -> Optional[ProdutoModel]:
        return self.db.query(ProdutoModel).filter_by(cod_barras=cod_barras).first()

    def criar_produto(self, **data) -> ProdutoModel:
        obj = ProdutoModel(**data)
        self.db.add(obj)
        self.db.flush()
        return obj

    def buscar_produtos_da_empresa(
            self, empresa_id: int, offset: int, limit: int,
            apenas_disponiveis: bool = False,
            apenas_delivery: bool = True
    ) -> List[ProdutoModel]:
        q = (
            self.db.query(ProdutoModel)
            .join(ProdutoEmpModel, ProdutoModel.cod_barras == ProdutoEmpModel.cod_barras)
            .filter(ProdutoEmpModel.empresa_id == empresa_id)
            .options(
                joinedload(ProdutoModel.produtos_empresa),
            )
            .order_by(ProdutoModel.created_at.desc())
        )
        if apenas_disponiveis:
            q = q.filter(ProdutoModel.ativo.is_(True), ProdutoEmpModel.disponivel.is_(True), ProdutoEmpModel.preco_venda > 0)
        if apenas_delivery:
            q = q.filter(ProdutoEmpModel.exibir_delivery.is_(True))
        return q.offset(offset).limit(limit).all()

    def contar_total(self, empresa_id: int, apenas_disponiveis: bool = False, apenas_delivery: bool = True) -> int:
        q = (
            self.db.query(func.count(ProdutoModel.cod_barras))
            .join(ProdutoEmpModel, ProdutoModel.cod_barras == ProdutoEmpModel.cod_barras)
            .filter(ProdutoEmpModel.empresa_id == empresa_id)
        )
        if apenas_disponiveis:
            q = q.filter(ProdutoModel.ativo.is_(True), ProdutoEmpModel.disponivel.is_(True), ProdutoEmpModel.preco_venda > 0)
        if apenas_delivery:
            q = q.filter(ProdutoEmpModel.exibir_delivery.is_(True))
        return int(q.scalar() or 0)

    # -------- Produto x Empresa --------
    def get_produto_emp(self, empresa_id: int, cod_barras: str) -> Optional[ProdutoEmpModel]:
        return (
            self.db.query(ProdutoEmpModel)
            .filter_by(empresa_id=empresa_id, cod_barras=cod_barras)
            .first()
        )

    def upsert_produto_emp(
        self,
        *,
        empresa_id: int,
        cod_barras: str,
        preco_venda: Decimal,
        custo: Optional[Decimal] = None,
        sku_empresa: Optional[str] = None,
        disponivel: Optional[bool] = None,
        exibir_delivery: Optional[bool] = None,
    ) -> ProdutoEmpModel:
        pe = self.get_produto_emp(empresa_id, cod_barras)
        if pe:
            pe.preco_venda = preco_venda
            pe.custo = custo
            if sku_empresa is not None:
                pe.sku_empresa = sku_empresa
            if disponivel is not None:
                pe.disponivel = disponivel
            if exibir_delivery is not None:
                pe.exibir_delivery = exibir_delivery
        else:
            pe = ProdutoEmpModel(
                empresa_id=empresa_id,
                cod_barras=cod_barras,
                preco_venda=preco_venda,
                custo=custo,
                sku_empresa=sku_empresa,
                disponivel=True if disponivel is None else disponivel,
                exibir_delivery=True if exibir_delivery is None else exibir_delivery,
            )
            self.db.add(pe)

        self.db.flush()
        return pe

    def atualizar_produto(self, cod_barras: str, **data) -> Optional[ProdutoModel]:
        """Atualiza um produto existente"""
        produto = self.buscar_por_cod_barras(cod_barras)
        if not produto:
            return None
        
        for key, value in data.items():
            if hasattr(produto, key) and value is not None:
                setattr(produto, key, value)
        
        self.db.flush()
        return produto

    def atualizar_produto_emp(self, empresa_id: int, cod_barras: str, **data) -> Optional[ProdutoEmpModel]:
        """Atualiza dados do produto na empresa"""
        produto_emp = self.get_produto_emp(empresa_id, cod_barras)
        if not produto_emp:
            return None
        
        for key, value in data.items():
            if hasattr(produto_emp, key) and value is not None:
                setattr(produto_emp, key, value)
        
        self.db.flush()
        return produto_emp

    def buscar_produtos_por_termo(
            self, empresa_id: int, termo: str, offset: int, limit: int,
            apenas_disponiveis: bool = False,
            apenas_delivery: bool = True
    ) -> List[ProdutoModel]:
        """Busca produtos por termo (código de barras, descrição ou SKU)"""
        q = (
            self.db.query(ProdutoModel)
            .join(ProdutoEmpModel, ProdutoModel.cod_barras == ProdutoEmpModel.cod_barras)
            .filter(ProdutoEmpModel.empresa_id == empresa_id)
            .options(
                joinedload(ProdutoModel.produtos_empresa),
            )
            .filter(
                (ProdutoModel.cod_barras.ilike(f"%{termo}%")) |
                (ProdutoModel.descricao.ilike(f"%{termo}%")) |
                (ProdutoEmpModel.sku_empresa.ilike(f"%{termo}%"))
            )
            .order_by(ProdutoModel.created_at.desc())
        )
        if apenas_disponiveis:
            q = q.filter(ProdutoModel.ativo.is_(True), ProdutoEmpModel.disponivel.is_(True), ProdutoEmpModel.preco_venda > 0)
        if apenas_delivery:
            q = q.filter(ProdutoEmpModel.exibir_delivery.is_(True))
        return q.offset(offset).limit(limit).all()

    def contar_busca_total(self, empresa_id: int, termo: str, apenas_disponiveis: bool = False, apenas_delivery: bool = True) -> int:
        """Conta total de produtos encontrados na busca"""
        q = (
            self.db.query(func.count(ProdutoModel.cod_barras))
            .join(ProdutoEmpModel, ProdutoModel.cod_barras == ProdutoEmpModel.cod_barras)
            .filter(ProdutoEmpModel.empresa_id == empresa_id)
            .filter(
                (ProdutoModel.cod_barras.ilike(f"%{termo}%")) |
                (ProdutoModel.descricao.ilike(f"%{termo}%")) |
                (ProdutoEmpModel.sku_empresa.ilike(f"%{termo}%"))
            )
        )
        if apenas_disponiveis:
            q = q.filter(ProdutoModel.ativo.is_(True), ProdutoEmpModel.disponivel.is_(True), ProdutoEmpModel.preco_venda > 0)
        if apenas_delivery:
            q = q.filter(ProdutoEmpModel.exibir_delivery.is_(True))
        return int(q.scalar() or 0)

    def gerar_proximo_cod_barras(self) -> str:
        """
        Gera o próximo código de barras disponível.
        Busca o maior código numérico e incrementa, ou gera um código baseado em timestamp.
        """
        # Busca todos os códigos de barras numéricos
        try:
            produtos = self.db.query(ProdutoModel.cod_barras).all()
            codigos_numericos = []
            
            for produto in produtos:
                cod = produto.cod_barras
                # Verifica se é numérico
                if cod and cod.isdigit():
                    try:
                        codigos_numericos.append(int(cod))
                    except ValueError:
                        continue
            
            if codigos_numericos:
                # Encontra o maior e incrementa
                max_cod = max(codigos_numericos)
                novo_cod = str(max_cod + 1)
                
                # Verifica se já existe (caso raro de colisão)
                if not self.buscar_por_cod_barras(novo_cod):
                    return novo_cod
        except Exception as e:
            # Se falhar, continua com a lógica alternativa
            pass
        
        # Se não encontrou códigos numéricos ou falhou, gera baseado em timestamp
        import time
        timestamp = int(time.time() * 1000)  # Usa milissegundos para mais precisão
        # Usa os últimos 13 dígitos do timestamp (formato similar a código de barras EAN-13)
        cod_barras = str(timestamp)[-13:] if len(str(timestamp)) >= 13 else str(timestamp).zfill(13)
        
        # Verifica se já existe, se sim, incrementa
        contador = 0
        while self.buscar_por_cod_barras(cod_barras) and contador < 100:
            timestamp += 1
            cod_barras = str(timestamp)[-13:] if len(str(timestamp)) >= 13 else str(timestamp).zfill(13)
            contador += 1
        
        return cod_barras

