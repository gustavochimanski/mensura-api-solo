from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.cadastros.repositories.repo_categorias import CategoriaRepository
from app.api.cadastros.schemas.schema_categorias import (
    CriarCategoriaRequest,
    AtualizarCategoriaRequest,
    CategoriaBaseDTO,
    CategoriaComFilhosDTO,
    CategoriaListItem,
    CategoriasPaginadasResponse,
    CategoriaResponse,
    CategoriaArvoreResponse
)


class CategoriaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CategoriaRepository(db)

    def _categoria_or_404(self, categoria_id: int):
        """Busca categoria ou retorna 404"""
        categoria = self.repo.buscar_por_id(categoria_id)
        if not categoria:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoria não encontrada."
            )
        return categoria

    def criar_categoria(self, req: CriarCategoriaRequest) -> CategoriaResponse:
        """Cria uma nova categoria"""
        # Verifica se já existe categoria com a mesma descrição
        if self.repo.buscar_por_descricao(req.descricao):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma categoria com esta descrição."
            )
        
        # Se tem parent_id, verifica se a categoria pai existe
        if req.parent_id:
            parent = self.repo.buscar_por_id(req.parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Categoria pai não encontrada."
                )
            if not parent.ativo:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Categoria pai está inativa."
                )

        # Cria a categoria
        categoria = self.repo.criar_categoria(
            descricao=req.descricao,
            parent_id=req.parent_id,
            ativo=1 if req.ativo else 0
        )

        self.db.commit()
        self.db.refresh(categoria)

        return CategoriaResponse(
            categoria=CategoriaBaseDTO.model_validate(categoria, from_attributes=True)
        )

    def buscar_categoria_por_id(self, categoria_id: int) -> CategoriaResponse:
        """Busca uma categoria por ID"""
        categoria = self._categoria_or_404(categoria_id)
        
        return CategoriaResponse(
            categoria=CategoriaBaseDTO.model_validate(categoria, from_attributes=True)
        )

    def listar_categorias_paginado(
        self, 
        page: int, 
        limit: int, 
        apenas_ativas: bool = True,
        parent_id: Optional[int] = None
    ) -> CategoriasPaginadasResponse:
        """Lista categorias com paginação"""
        offset = (page - 1) * limit
        
        # Busca categorias com contadores
        resultados = self.repo.buscar_categorias_com_contadores(offset, limit)
        
        # Se especificou parent_id, filtra os resultados
        if parent_id is not None:
            resultados = [r for r in resultados if r['categoria'].parent_id == parent_id]
        
        # Se especificou apenas ativas, filtra os resultados
        if apenas_ativas:
            resultados = [r for r in resultados if r['categoria'].ativo == 1]

        data = []
        for resultado in resultados:
            categoria = resultado['categoria']
            parent_descricao = None
            
            if categoria.parent_id:
                parent = self.repo.buscar_por_id(categoria.parent_id)
                parent_descricao = parent.descricao if parent else None
            
            data.append(CategoriaListItem(
                id=categoria.id,
                descricao=categoria.descricao,
                ativo=bool(categoria.ativo),
                parent_id=categoria.parent_id,
                parent_descricao=parent_descricao,
                total_filhos=resultado['total_filhos']
            ))

        total = self.repo.contar_total(apenas_ativas, parent_id)
        
        return CategoriasPaginadasResponse(
            data=data,
            total=total,
            page=page,
            limit=limit,
            has_more=offset + limit < total
        )

    def atualizar_categoria(
        self, 
        categoria_id: int, 
        req: AtualizarCategoriaRequest
    ) -> CategoriaResponse:
        """Atualiza uma categoria existente"""
        categoria = self._categoria_or_404(categoria_id)

        # Se está alterando a descrição, verifica se já existe
        if req.descricao and req.descricao != categoria.descricao:
            if self.repo.buscar_por_descricao(req.descricao):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Já existe uma categoria com esta descrição."
                )

        # Se está alterando o parent_id, verifica se a categoria pai existe
        if req.parent_id is not None and req.parent_id != categoria.parent_id:
            if req.parent_id == categoria.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uma categoria não pode ser pai de si mesma."
                )
            
            if req.parent_id:
                parent = self.repo.buscar_por_id(req.parent_id)
                if not parent:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Categoria pai não encontrada."
                    )
                if not parent.ativo:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Categoria pai está inativa."
                    )

        # Prepara dados para atualização
        dados_atualizacao = {}
        if req.descricao is not None:
            dados_atualizacao['descricao'] = req.descricao
        if req.parent_id is not None:
            dados_atualizacao['parent_id'] = req.parent_id
        if req.ativo is not None:
            dados_atualizacao['ativo'] = 1 if req.ativo else 0

        # Atualiza a categoria
        categoria_atualizada = self.repo.atualizar_categoria(categoria_id, **dados_atualizacao)
        if not categoria_atualizada:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao atualizar categoria."
            )

        self.db.commit()
        self.db.refresh(categoria_atualizada)

        return CategoriaResponse(
            categoria=CategoriaBaseDTO.model_validate(categoria_atualizada, from_attributes=True)
        )

    def deletar_categoria(self, categoria_id: int) -> dict:
        """Deleta uma categoria (soft delete)"""
        categoria = self._categoria_or_404(categoria_id)

        # Verifica se pode deletar (não tem filhos ativos)
        if not self.repo.verificar_se_pode_deletar(categoria_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível deletar categoria que possui subcategorias ativas."
            )

        # Deleta a categoria
        sucesso = self.repo.deletar_categoria(categoria_id)
        if not sucesso:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao deletar categoria."
            )

        self.db.commit()

        return {"message": "Categoria deletada com sucesso."}

    def buscar_categorias_por_termo(
        self, 
        termo: str, 
        page: int, 
        limit: int,
        apenas_ativas: bool = True
    ) -> CategoriasPaginadasResponse:
        """Busca categorias por termo de pesquisa"""
        offset = (page - 1) * limit
        categorias = self.repo.buscar_categorias_por_termo(termo, offset, limit, apenas_ativas)
        total = self.repo.contar_busca_total(termo, apenas_ativas)

        data = []
        for categoria in categorias:
            parent_descricao = None
            if categoria.parent_id:
                parent = self.repo.buscar_por_id(categoria.parent_id)
                parent_descricao = parent.descricao if parent else None
            
            # Conta filhos
            total_filhos = self.repo.contar_total(apenas_ativas, categoria.id)
            
            data.append(CategoriaListItem(
                id=categoria.id,
                descricao=categoria.descricao,
                ativo=bool(categoria.ativo),
                parent_id=categoria.parent_id,
                parent_descricao=parent_descricao,
                total_filhos=total_filhos
            ))

        return CategoriasPaginadasResponse(
            data=data,
            total=total,
            page=page,
            limit=limit,
            has_more=offset + limit < total
        )

    def buscar_arvore_categorias(self, apenas_ativas: bool = True) -> CategoriaArvoreResponse:
        """Busca todas as categorias organizadas em árvore"""
        categorias_raiz = self.repo.buscar_arvore_categorias(apenas_ativas)
        
        def construir_arvore(categorias: List) -> List[CategoriaComFilhosDTO]:
            resultado = []
            for categoria in categorias:
                categoria_dto = CategoriaComFilhosDTO.model_validate(categoria, from_attributes=True)
                if categoria.children:
                    categoria_dto.children = construir_arvore(categoria.children)
                resultado.append(categoria_dto)
            return resultado

        arvore = construir_arvore(categorias_raiz)
        
        return CategoriaArvoreResponse(categorias=arvore)

    def buscar_categorias_raiz(self, apenas_ativas: bool = True) -> List[CategoriaListItem]:
        """Busca apenas categorias raiz (sem pai)"""
        categorias = self.repo.buscar_categorias_raiz(apenas_ativas)
        
        data = []
        for categoria in categorias:
            total_filhos = self.repo.contar_total(apenas_ativas, categoria.id)
            
            data.append(CategoriaListItem(
                id=categoria.id,
                descricao=categoria.descricao,
                ativo=bool(categoria.ativo),
                parent_id=categoria.parent_id,
                parent_descricao=None,
                total_filhos=total_filhos
            ))
        
        return data

    def buscar_filhos_da_categoria(
        self, 
        parent_id: int, 
        apenas_ativas: bool = True
    ) -> List[CategoriaListItem]:
        """Busca filhos de uma categoria específica"""
        # Verifica se a categoria pai existe
        self._categoria_or_404(parent_id)
        
        filhos = self.repo.buscar_filhos_da_categoria(parent_id, apenas_ativas)
        
        data = []
        for categoria in filhos:
            total_filhos = self.repo.contar_total(apenas_ativas, categoria.id)
            
            data.append(CategoriaListItem(
                id=categoria.id,
                descricao=categoria.descricao,
                ativo=bool(categoria.ativo),
                parent_id=categoria.parent_id,
                parent_descricao=None,  # Já sabemos que é filho da categoria especificada
                total_filhos=total_filhos
            ))
        
        return data
