from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal

from app.api.catalogo.models.model_adicional import AdicionalModel
from app.api.catalogo.models.model_receita import ReceitaModel
from app.api.catalogo.repositories.repo_adicional import AdicionalRepository
from app.api.catalogo.schemas.schema_adicional import (
    AdicionalResponse,
    CriarAdicionalRequest,
    AtualizarAdicionalRequest,
    VincularAdicionaisProdutoRequest,
)
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.catalogo.repositories.repo_produto import ProdutoMensuraRepository
from app.api.catalogo.repositories.repo_combo import ComboRepository


class AdicionalService:
    """Service para operações de adicionais."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AdicionalRepository(db)
        self.repo_empresa = EmpresaRepository(db)
        self.repo_produto = ProdutoMensuraRepository(db)
        self.repo_combo = ComboRepository(db)

    def _empresa_or_404(self, empresa_id: int):
        """Valida se a empresa existe."""
        empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada."
            )
        return empresa

    def criar_adicional(self, req: CriarAdicionalRequest) -> AdicionalResponse:
        """Cria um novo adicional."""
        self._empresa_or_404(req.empresa_id)
        
        adicional = self.repo.criar_adicional(
            empresa_id=req.empresa_id,
            nome=req.nome,
            descricao=req.descricao,
            preco=Decimal(str(req.preco)),
            custo=Decimal(str(req.custo)),
            ativo=req.ativo,
            obrigatorio=req.obrigatorio,
            permite_multipla_escolha=req.permite_multipla_escolha,
            ordem=req.ordem,
        )
        
        self.db.commit()
        self.db.refresh(adicional)
        
        return AdicionalResponse.model_validate(adicional)

    def listar_adicionais(self, empresa_id: int, apenas_ativos: bool = True) -> List[AdicionalResponse]:
        """Lista todos os adicionais de uma empresa."""
        self._empresa_or_404(empresa_id)
        
        adicionais = self.repo.listar_por_empresa(empresa_id, apenas_ativos)
        return [AdicionalResponse.model_validate(a) for a in adicionais]

    def buscar_por_id(self, adicional_id: int) -> AdicionalResponse:
        """Busca um adicional por ID."""
        adicional = self.repo.buscar_por_id(adicional_id)
        if not adicional:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Adicional não encontrado."
            )
        return AdicionalResponse.model_validate(adicional)

    def atualizar_adicional(self, adicional_id: int, req: AtualizarAdicionalRequest) -> AdicionalResponse:
        """Atualiza um adicional existente."""
        adicional = self.repo.buscar_por_id(adicional_id)
        if not adicional:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Adicional não encontrado."
            )
        
        update_data = {}
        if req.nome is not None:
            update_data["nome"] = req.nome
        if req.descricao is not None:
            update_data["descricao"] = req.descricao
        if req.preco is not None:
            update_data["preco"] = Decimal(str(req.preco))
        if req.custo is not None:
            update_data["custo"] = Decimal(str(req.custo))
        if req.ativo is not None:
            update_data["ativo"] = req.ativo
        if req.obrigatorio is not None:
            update_data["obrigatorio"] = req.obrigatorio
        if req.permite_multipla_escolha is not None:
            update_data["permite_multipla_escolha"] = req.permite_multipla_escolha
        if req.ordem is not None:
            update_data["ordem"] = req.ordem
        
        self.repo.atualizar_adicional(adicional, **update_data)
        self.db.commit()
        self.db.refresh(adicional)
        
        return AdicionalResponse.model_validate(adicional)

    def deletar_adicional(self, adicional_id: int):
        """Deleta um adicional."""
        adicional = self.repo.buscar_por_id(adicional_id)
        if not adicional:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Adicional não encontrado."
            )
        
        self.repo.deletar_adicional(adicional)
        self.db.commit()
        return {"message": "Adicional deletado com sucesso"}

    def vincular_adicionais_produto(self, cod_barras: str, req: VincularAdicionaisProdutoRequest):
        """Vincula múltiplos adicionais a um produto."""
        # Verifica se o produto existe
        produto = self.repo_produto.buscar_por_cod_barras(cod_barras)
        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado."
            )
        
        # Verifica se todos os adicionais existem
        for adicional_id in req.adicional_ids:
            adicional = self.repo.buscar_por_id(adicional_id)
            if not adicional:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Adicional {adicional_id} não encontrado."
                )
        
        self.repo.vincular_adicionais_produto(cod_barras, req.adicional_ids)
        self.db.commit()
        
        # Retorna os adicionais vinculados
        adicionais = self.repo.listar_por_produto(cod_barras, apenas_ativos=False)
        return {
            "produto_cod_barras": cod_barras,
            "adicionais_vinculados": [AdicionalResponse.model_validate(a) for a in adicionais],
            "message": "Adicionais vinculados com sucesso"
        }

    def listar_adicionais_produto(self, cod_barras: str, apenas_ativos: bool = True) -> List[AdicionalResponse]:
        """Lista todos os adicionais de um produto."""
        # Verifica se o produto existe
        produto = self.repo_produto.buscar_por_cod_barras(cod_barras)
        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado."
            )
        
        adicionais = self.repo.listar_por_produto(cod_barras, apenas_ativos)
        return [AdicionalResponse.model_validate(a) for a in adicionais]

    def listar_adicionais_combo(self, combo_id: int, apenas_ativos: bool = True) -> List[AdicionalResponse]:
        """
        Lista adicionais aplicáveis a um combo.

        A regra atual é: agregamos os adicionais de todos os produtos
        que compõem o combo e retornamos o conjunto único.
        """
        combo = self.repo_combo.get_by_id(combo_id)
        if not combo or not combo.ativo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Combo não encontrado."
            )

        adicionais_map: dict[int, AdicionalModel] = {}
        for item in combo.itens:
            if not item.produto_cod_barras:
                continue
            adicionais_produto = self.repo.listar_por_produto(
                item.produto_cod_barras,
                apenas_ativos=apenas_ativos,
            )
            for adicional in adicionais_produto:
                adicionais_map[adicional.id] = adicional

        return [AdicionalResponse.model_validate(a) for a in adicionais_map.values()]

    def listar_adicionais_receita(self, receita_id: int, apenas_ativos: bool = True) -> List[AdicionalResponse]:
        """
        Lista adicionais vinculados a uma receita (ReceitaAdicionalModel -> AdicionalModel).
        """
        receita = self.db.query(ReceitaModel).filter(ReceitaModel.id == receita_id).first()
        if not receita or not receita.ativo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receita não encontrada."
            )

        adicionais_models: dict[int, AdicionalModel] = {}
        for vinculo in receita.adicionais:
            adicional = vinculo.adicional
            if not adicional:
                continue
            if apenas_ativos and not adicional.ativo:
                continue
            adicionais_models[adicional.id] = adicional

        return [AdicionalResponse.model_validate(a) for a in adicionais_models.values()]

