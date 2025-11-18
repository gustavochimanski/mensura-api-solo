from typing import List, Optional
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session, joinedload

from app.api.cadastros.models.categoria_model import CategoriaModel


class CategoriaRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_por_id(self, categoria_id: int) -> Optional[CategoriaModel]:
        """Busca uma categoria por ID"""
        return self.db.query(CategoriaModel).filter_by(id=categoria_id).first()

    def buscar_por_descricao(self, descricao: str) -> Optional[CategoriaModel]:
        """Busca uma categoria por descrição exata"""
        return self.db.query(CategoriaModel).filter_by(descricao=descricao).first()

    def criar_categoria(self, **data) -> CategoriaModel:
        """Cria uma nova categoria"""
        obj = CategoriaModel(**data)
        self.db.add(obj)
        self.db.flush()
        return obj

    def atualizar_categoria(self, categoria_id: int, **data) -> Optional[CategoriaModel]:
        """Atualiza uma categoria existente"""
        categoria = self.buscar_por_id(categoria_id)
        if not categoria:
            return None
        
        for key, value in data.items():
            if hasattr(categoria, key) and value is not None:
                setattr(categoria, key, value)
        
        self.db.flush()
        return categoria

    def deletar_categoria(self, categoria_id: int) -> bool:
        """Deleta uma categoria (soft delete - marca como inativo)"""
        categoria = self.buscar_por_id(categoria_id)
        if not categoria:
            return False
        
        # Verifica se tem filhos ativos
        filhos_ativos = self.db.query(CategoriaModel).filter(
            and_(
                CategoriaModel.parent_id == categoria_id,
                CategoriaModel.ativo == 1
            )
        ).count()
        
        if filhos_ativos > 0:
            return False  # Não pode deletar se tem filhos ativos
        
        categoria.ativo = 0
        self.db.flush()
        return True

    def listar_categorias_paginado(
        self, 
        offset: int, 
        limit: int, 
        apenas_ativas: bool = True,
        parent_id: Optional[int] = None
    ) -> List[CategoriaModel]:
        """Lista categorias com paginação"""
        q = self.db.query(CategoriaModel)
        
        if apenas_ativas:
            q = q.filter(CategoriaModel.ativo == 1)
        
        if parent_id is not None:
            q = q.filter(CategoriaModel.parent_id == parent_id)
        
        return q.order_by(CategoriaModel.descricao).offset(offset).limit(limit).all()

    def contar_total(
        self, 
        apenas_ativas: bool = True,
        parent_id: Optional[int] = None
    ) -> int:
        """Conta total de categorias"""
        q = self.db.query(func.count(CategoriaModel.id))
        
        if apenas_ativas:
            q = q.filter(CategoriaModel.ativo == 1)
        
        if parent_id is not None:
            q = q.filter(CategoriaModel.parent_id == parent_id)
        
        return int(q.scalar() or 0)

    def buscar_categorias_por_termo(
        self, 
        termo: str, 
        offset: int, 
        limit: int,
        apenas_ativas: bool = True
    ) -> List[CategoriaModel]:
        """Busca categorias por termo de pesquisa"""
        q = self.db.query(CategoriaModel).filter(
            CategoriaModel.descricao.ilike(f"%{termo}%")
        )
        
        if apenas_ativas:
            q = q.filter(CategoriaModel.ativo == 1)
        
        return q.order_by(CategoriaModel.descricao).offset(offset).limit(limit).all()

    def contar_busca_total(self, termo: str, apenas_ativas: bool = True) -> int:
        """Conta total de categorias encontradas na busca"""
        q = self.db.query(func.count(CategoriaModel.id)).filter(
            CategoriaModel.descricao.ilike(f"%{termo}%")
        )
        
        if apenas_ativas:
            q = q.filter(CategoriaModel.ativo == 1)
        
        return int(q.scalar() or 0)

    def buscar_categorias_raiz(self, apenas_ativas: bool = True) -> List[CategoriaModel]:
        """Busca categorias raiz (sem pai)"""
        q = self.db.query(CategoriaModel).filter(CategoriaModel.parent_id.is_(None))
        
        if apenas_ativas:
            q = q.filter(CategoriaModel.ativo == 1)
        
        return q.order_by(CategoriaModel.descricao).all()

    def buscar_filhos_da_categoria(
        self, 
        parent_id: int, 
        apenas_ativas: bool = True
    ) -> List[CategoriaModel]:
        """Busca filhos de uma categoria"""
        q = self.db.query(CategoriaModel).filter(CategoriaModel.parent_id == parent_id)
        
        if apenas_ativas:
            q = q.filter(CategoriaModel.ativo == 1)
        
        return q.order_by(CategoriaModel.descricao).all()

    def buscar_arvore_categorias(self, apenas_ativas: bool = True) -> List[CategoriaModel]:
        """Busca todas as categorias organizadas em árvore"""
        q = self.db.query(CategoriaModel).options(
            joinedload(CategoriaModel.children)
        )
        
        if apenas_ativas:
            q = q.filter(CategoriaModel.ativo == 1)
        
        # Busca apenas as raízes, os filhos serão carregados via joinedload
        return q.filter(CategoriaModel.parent_id.is_(None)).order_by(CategoriaModel.descricao).all()

    def verificar_se_pode_deletar(self, categoria_id: int) -> bool:
        """Verifica se uma categoria pode ser deletada (não tem filhos ativos)"""
        filhos_ativos = self.db.query(CategoriaModel).filter(
            and_(
                CategoriaModel.parent_id == categoria_id,
                CategoriaModel.ativo == 1
            )
        ).count()
        
        return filhos_ativos == 0

    def buscar_categorias_com_contadores(self, offset: int, limit: int) -> List[dict]:
        """Busca categorias com contadores de filhos"""
        # Subquery para contar filhos ativos
        subquery = self.db.query(
            CategoriaModel.parent_id,
            func.count(CategoriaModel.id).label('total_filhos')
        ).filter(CategoriaModel.ativo == 1).group_by(CategoriaModel.parent_id).subquery()
        
        # Query principal com join para pegar contadores
        q = self.db.query(
            CategoriaModel,
            func.coalesce(subquery.c.total_filhos, 0).label('total_filhos')
        ).outerjoin(
            subquery, CategoriaModel.id == subquery.c.parent_id
        ).filter(CategoriaModel.ativo == 1)
        
        results = q.order_by(CategoriaModel.descricao).offset(offset).limit(limit).all()
        
        return [
            {
                'categoria': result[0],
                'total_filhos': result[1]
            }
            for result in results
        ]
