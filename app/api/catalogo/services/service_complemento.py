from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal

from app.api.catalogo.models.model_complemento import ComplementoModel
from app.api.catalogo.models.model_adicional import AdicionalModel
from app.api.catalogo.repositories.repo_complemento import ComplementoRepository
from app.api.catalogo.schemas.schema_complemento import (
    ComplementoResponse,
    CriarComplementoRequest,
    AtualizarComplementoRequest,
    AdicionalResponse,
    CriarAdicionalRequest,
    AtualizarAdicionalRequest,
    VincularComplementosProdutoRequest,
    VincularComplementosProdutoResponse,
    ComplementoResumidoResponse,
)
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.catalogo.repositories.repo_produto import ProdutoMensuraRepository


class ComplementoService:
    """Service para operações de complementos."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ComplementoRepository(db)
        self.repo_empresa = EmpresaRepository(db)
        self.repo_produto = ProdutoMensuraRepository(db)

    def _empresa_or_404(self, empresa_id: int):
        """Valida se a empresa existe."""
        empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada."
            )
        return empresa

    def criar_complemento(self, req: CriarComplementoRequest) -> ComplementoResponse:
        """Cria um novo complemento."""
        self._empresa_or_404(req.empresa_id)
        
        complemento = self.repo.criar_complemento(
            empresa_id=req.empresa_id,
            nome=req.nome,
            descricao=req.descricao,
            obrigatorio=req.obrigatorio,
            quantitativo=req.quantitativo,
            permite_multipla_escolha=req.permite_multipla_escolha,
            ordem=req.ordem,
        )
        
        return self.complemento_to_response(complemento)

    def buscar_por_id(self, complemento_id: int) -> ComplementoResponse:
        """Busca um complemento por ID."""
        complemento = self.repo.buscar_por_id(complemento_id, carregar_adicionais=True)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        return self.complemento_to_response(complemento)

    def listar_complementos(self, empresa_id: int, apenas_ativos: bool = True) -> List[ComplementoResponse]:
        """Lista todos os complementos de uma empresa."""
        self._empresa_or_404(empresa_id)
        complementos = self.repo.listar_por_empresa(empresa_id, apenas_ativos=apenas_ativos, carregar_adicionais=True)
        return [self.complemento_to_response(c) for c in complementos]

    def atualizar_complemento(self, complemento_id: int, req: AtualizarComplementoRequest) -> ComplementoResponse:
        """Atualiza um complemento existente."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        
        self.repo.atualizar_complemento(complemento, **req.model_dump(exclude_unset=True))
        return self.buscar_por_id(complemento_id)

    def deletar_complemento(self, complemento_id: int):
        """Deleta um complemento."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        self.repo.deletar_complemento(complemento)

    def vincular_complementos_produto(self, cod_barras: str, req: VincularComplementosProdutoRequest) -> VincularComplementosProdutoResponse:
        """Vincula múltiplos complementos a um produto."""
        produto = self.repo_produto.buscar_por_cod_barras(cod_barras)
        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produto {cod_barras} não encontrado."
            )
        
        self.repo.vincular_complementos_produto(cod_barras, req.complemento_ids)
        
        # Busca os complementos vinculados para retornar
        complementos = self.repo.listar_por_produto(cod_barras, apenas_ativos=True)
        complementos_vinculados = [
            ComplementoResumidoResponse(
                id=c.id,
                nome=c.nome,
                obrigatorio=c.obrigatorio,
                quantitativo=c.quantitativo,
                permite_multipla_escolha=c.permite_multipla_escolha,
                ordem=c.ordem,
            )
            for c in complementos
        ]
        
        return VincularComplementosProdutoResponse(
            produto_cod_barras=cod_barras,
            complementos_vinculados=complementos_vinculados,
        )

    def listar_complementos_produto(self, cod_barras: str, apenas_ativos: bool = True) -> List[ComplementoResponse]:
        """Lista todos os complementos de um produto específico."""
        complementos = self.repo.listar_por_produto(cod_barras, apenas_ativos=apenas_ativos, carregar_adicionais=True)
        return [self.complemento_to_response(c) for c in complementos]

    # ------ Adicionais dentro de complementos ------
    def criar_adicional(self, complemento_id: int, req: CriarAdicionalRequest) -> AdicionalResponse:
        """Cria um adicional dentro de um complemento."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        
        adicional = AdicionalModel(
            empresa_id=complemento.empresa_id,
            complemento_id=complemento_id,
            nome=req.nome,
            descricao=req.descricao,
            preco=Decimal(str(req.preco)),
            custo=Decimal(str(req.custo)),
            ativo=req.ativo,
            ordem=req.ordem,
        )
        self.db.add(adicional)
        self.db.flush()
        self.db.refresh(adicional)
        
        return self._adicional_to_response(adicional)

    def atualizar_adicional(self, complemento_id: int, adicional_id: int, req: AtualizarAdicionalRequest) -> AdicionalResponse:
        """Atualiza um adicional dentro de um complemento."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        
        adicional = self.db.query(AdicionalModel).filter(
            AdicionalModel.id == adicional_id,
            AdicionalModel.complemento_id == complemento_id,
        ).first()
        
        if not adicional:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Adicional {adicional_id} não encontrado no complemento {complemento_id}."
            )
        
        for key, value in req.model_dump(exclude_unset=True).items():
            if value is not None:
                if key in ['preco', 'custo']:
                    setattr(adicional, key, Decimal(str(value)))
                else:
                    setattr(adicional, key, value)
        
        self.db.flush()
        self.db.refresh(adicional)
        
        return self._adicional_to_response(adicional)

    def deletar_adicional(self, complemento_id: int, adicional_id: int):
        """Deleta um adicional dentro de um complemento."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        
        adicional = self.db.query(AdicionalModel).filter(
            AdicionalModel.id == adicional_id,
            AdicionalModel.complemento_id == complemento_id,
        ).first()
        
        if not adicional:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Adicional {adicional_id} não encontrado no complemento {complemento_id}."
            )
        
        self.db.delete(adicional)
        self.db.flush()

    def listar_adicionais_complemento(self, complemento_id: int, apenas_ativos: bool = True) -> List[AdicionalResponse]:
        """Lista todos os adicionais de um complemento."""
        complemento = self.repo.buscar_por_id(complemento_id, carregar_adicionais=True)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        
        adicionais = complemento.adicionais
        if apenas_ativos:
            adicionais = [a for a in adicionais if a.ativo]
        
        return [self._adicional_to_response(a) for a in sorted(adicionais, key=lambda x: (x.ordem, x.nome))]

    # ------ Helpers ------
    def complemento_to_response(self, complemento: ComplementoModel) -> ComplementoResponse:
        """Converte ComplementoModel para ComplementoResponse."""
        adicionais = []
        if hasattr(complemento, 'adicionais') and complemento.adicionais:
            adicionais = [
                self._adicional_to_response(a)
                for a in sorted(complemento.adicionais, key=lambda x: (x.ordem, x.nome))
            ]
        
        return ComplementoResponse(
            id=complemento.id,
            empresa_id=complemento.empresa_id,
            nome=complemento.nome,
            descricao=complemento.descricao,
            obrigatorio=complemento.obrigatorio,
            quantitativo=complemento.quantitativo,
            permite_multipla_escolha=complemento.permite_multipla_escolha,
            ordem=complemento.ordem,
            ativo=complemento.ativo,
            adicionais=adicionais,
            created_at=complemento.created_at,
            updated_at=complemento.updated_at,
        )

    def _adicional_to_response(self, adicional: AdicionalModel) -> AdicionalResponse:
        """Converte AdicionalModel para AdicionalResponse."""
        return AdicionalResponse(
            id=adicional.id,
            nome=adicional.nome,
            descricao=adicional.descricao,
            preco=float(adicional.preco),
            custo=float(adicional.custo),
            ativo=adicional.ativo,
            ordem=adicional.ordem,
            created_at=adicional.created_at,
            updated_at=adicional.updated_at,
        )

