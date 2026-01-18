from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.catalogo.repositories.repo_produto import ProdutoMensuraRepository
from app.api.catalogo.schemas.schema_produtos import ProdutoListItem, CriarNovoProdutoResponse, ProdutoEmpDTO, \
    ProdutoBaseDTO, CriarNovoProdutoRequest, AtualizarProdutoRequest
from app.api.catalogo.repositories.repo_adicional import AdicionalRepository
from app.api.catalogo.repositories.repo_receitas import ReceitasRepository


class ProdutosMensuraService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProdutoMensuraRepository(db)
        self.empresa_repo = EmpresaRepository(db)
        self.repo_adicional = AdicionalRepository(db)
        self.repo_receitas = ReceitasRepository(db)

    def _empresa_or_404(self, empresa_id: int):
        empresa = self.empresa_repo.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada."
            )
        return empresa

    def criar_novo_produto(self, empresa_id: int, req: CriarNovoProdutoRequest) -> CriarNovoProdutoResponse:
        # garante que a empresa existe antes de prosseguir
        self._empresa_or_404(empresa_id)

        # Se cod_barras não foi fornecido ou está vazio, gera automaticamente
        if not req.cod_barras or (isinstance(req.cod_barras, str) and req.cod_barras.strip() == ""):
            req.cod_barras = self.repo.gerar_proximo_cod_barras()

        if self.repo.buscar_por_cod_barras(req.cod_barras):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Produto já existe.")

        # produto base (sem categoria)
        prod = self.repo.criar_produto(
            cod_barras=req.cod_barras,
            descricao=req.descricao,
            imagem=req.imagem,
            data_cadastro=req.data_cadastro,
            ativo=req.ativo,
            unidade_medida=req.unidade_medida,
        )

        # Se preço for zero, marca como indisponível automaticamente
        preco_venda_decimal = Decimal(str(req.preco_venda))
        disponivel = req.disponivel if preco_venda_decimal > 0 else False
        
        # vínculo com empresa (sem vitrine)
        pe = self.repo.upsert_produto_emp(
            empresa_id=empresa_id,
            cod_barras=prod.cod_barras,
            preco_venda=preco_venda_decimal,
            custo=(Decimal(str(req.custo)) if req.custo is not None else None),
            sku_empresa=req.sku_empresa,
            disponivel=disponivel,
            exibir_delivery=req.exibir_delivery,
        )

        self.db.commit()
        self.db.refresh(prod)
        self.db.refresh(pe)

        # Verifica se o produto tem receita
        tem_receita = self.repo_receitas.produto_tem_receita(prod.cod_barras)

        produto_dto = ProdutoBaseDTO.model_validate(prod, from_attributes=True)
        produto_dto.tem_receita = tem_receita

        return CriarNovoProdutoResponse(
            produto=produto_dto,
            produto_emp=ProdutoEmpDTO(
                empresa_id=pe.empresa_id,
                cod_barras=pe.cod_barras,
                preco_venda=float(pe.preco_venda),
                custo=(float(pe.custo) if pe.custo is not None else None),
                vitrine_id=None,
                sku_empresa=pe.sku_empresa,
                disponivel=pe.disponivel,
                exibir_delivery=pe.exibir_delivery,
                created_at=pe.created_at,
                updated_at=pe.updated_at,
            ),
        )

    def listar_paginado(self, empresa_id: int, page: int, limit: int, apenas_disponiveis: bool = False):
        offset = (page - 1) * limit
        # Se apenas_disponiveis=False, também não filtra por delivery para mostrar todos os produtos
        apenas_delivery = apenas_disponiveis
        produtos = self.repo.buscar_produtos_da_empresa(
            empresa_id, offset, limit,
            apenas_disponiveis=apenas_disponiveis,
            apenas_delivery=apenas_delivery,
        )
        total = self.repo.contar_total(
            empresa_id,
            apenas_disponiveis=apenas_disponiveis,
            apenas_delivery=apenas_delivery,
        )

        data = []
        for p in produtos:
            pe = next((x for x in p.produtos_empresa if x.empresa_id == empresa_id), None)
            if not pe:
                continue
            
            # Busca adicionais vinculados ao produto (sem depender de diretivas)
            adicionais = None
            adicionais_list = self.repo_adicional.listar_por_produto(p.cod_barras, apenas_ativos=True)
            if adicionais_list:
                adicionais = [
                    {
                        "id": a.id,
                        "nome": a.nome,
                        "preco": float(a.preco),
                        "obrigatorio": a.obrigatorio,
                        "imagem": getattr(a, "imagem", None),
                    }
                    for a in adicionais_list
                ]
            
            # Verifica se o produto tem receita
            tem_receita = self.repo_receitas.produto_tem_receita(p.cod_barras)
            
            data.append(ProdutoListItem(
                cod_barras=p.cod_barras,
                descricao=p.descricao,
                imagem=p.imagem,
                preco_venda=float(pe.preco_venda),
                custo=(float(pe.custo) if pe.custo is not None else None),
                disponivel=pe.disponivel and p.ativo,
                exibir_delivery=pe.exibir_delivery,
                tem_receita=tem_receita,
                adicionais=adicionais,
            ))

        return {"data": data, "total": total, "page": page, "limit": limit, "has_more": offset + limit < total}

    def buscar_paginado(
        self,
        empresa_id: int,
        q: Optional[str],
        page: int,
        limit: int,
        apenas_disponiveis: bool = False,
    ):
        termo = (q or "").strip()
        if termo:
            return self.buscar_produtos(
                empresa_id=empresa_id,
                termo=termo,
                page=page,
                limit=limit,
                apenas_disponiveis=apenas_disponiveis,
            )
        return self.listar_paginado(
            empresa_id=empresa_id,
            page=page,
            limit=limit,
            apenas_disponiveis=apenas_disponiveis,
        )

    def atualizar_produto(self, empresa_id: int, cod_barras: str, req: AtualizarProdutoRequest) -> CriarNovoProdutoResponse:
        """Atualiza um produto existente"""
        # garante que a empresa existe antes de prosseguir
        self._empresa_or_404(empresa_id)

        # verifica se o produto existe
        produto = self.repo.buscar_por_cod_barras(cod_barras)
        if not produto:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado.")

        # verifica se o produto está vinculado à empresa
        produto_emp = self.repo.get_produto_emp(empresa_id, cod_barras)
        if not produto_emp:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não está vinculado a esta empresa.")

        # atualiza produto base in-place
        if req.descricao is not None:
            produto.descricao = req.descricao
        if req.imagem is not None:
            produto.imagem = req.imagem
        if req.ativo is not None:
            produto.ativo = req.ativo
        if req.unidade_medida is not None:
            produto.unidade_medida = req.unidade_medida
        # diretivas removido

        # atualiza produto da empresa in-place
        if req.preco_venda is not None:
            preco_venda_decimal = Decimal(str(req.preco_venda))
            produto_emp.preco_venda = preco_venda_decimal
            # Se preço for zero, marca como indisponível automaticamente
            if preco_venda_decimal == 0:
                produto_emp.disponivel = False
        if req.custo is not None:
            produto_emp.custo = Decimal(str(req.custo))
        if req.sku_empresa is not None:
            produto_emp.sku_empresa = req.sku_empresa
        if req.disponivel is not None:
            # Só permite marcar como disponível se o preço for maior que zero
            if req.disponivel and produto_emp.preco_venda == 0:
                produto_emp.disponivel = False
            else:
                produto_emp.disponivel = req.disponivel
        if req.exibir_delivery is not None:
            produto_emp.exibir_delivery = req.exibir_delivery

        # commit das alterações
        self.db.commit()
        self.db.refresh(produto)
        self.db.refresh(produto_emp)

        # Verifica se o produto tem receita
        tem_receita = self.repo_receitas.produto_tem_receita(produto.cod_barras)

        produto_dto = ProdutoBaseDTO.model_validate(produto, from_attributes=True)
        produto_dto.tem_receita = tem_receita

        return CriarNovoProdutoResponse(
            produto=produto_dto,
            produto_emp=ProdutoEmpDTO(
                empresa_id=produto_emp.empresa_id,
                cod_barras=produto_emp.cod_barras,
                preco_venda=float(produto_emp.preco_venda),
                custo=(float(produto_emp.custo) if produto_emp.custo is not None else None),
                vitrine_id=None,
                sku_empresa=produto_emp.sku_empresa,
                disponivel=produto_emp.disponivel,
                exibir_delivery=produto_emp.exibir_delivery,
                created_at=produto_emp.created_at,
                updated_at=produto_emp.updated_at,
            ),
        )

    def buscar_produtos(self, empresa_id: int, termo: str, page: int, limit: int, apenas_disponiveis: bool = False):
        """Busca produtos por termo de pesquisa"""
        # garante que a empresa existe antes de prosseguir
        self._empresa_or_404(empresa_id)

        offset = (page - 1) * limit
        # Se apenas_disponiveis=False, também não filtra por delivery para mostrar todos os produtos
        apenas_delivery = apenas_disponiveis
        produtos = self.repo.buscar_produtos_por_termo(
            empresa_id, termo, offset, limit,
            apenas_disponiveis=apenas_disponiveis,
            apenas_delivery=apenas_delivery,
        )
        total = self.repo.contar_busca_total(
            empresa_id, termo,
            apenas_disponiveis=apenas_disponiveis,
            apenas_delivery=apenas_delivery,
        )

        data = []
        for p in produtos:
            pe = next((x for x in p.produtos_empresa if x.empresa_id == empresa_id), None)
            if not pe:
                continue
            
            # Busca adicionais vinculados ao produto (sem depender de diretivas)
            adicionais = None
            adicionais_list = self.repo_adicional.listar_por_produto(p.cod_barras, apenas_ativos=True)
            if adicionais_list:
                adicionais = [
                    {
                        "id": a.id,
                        "nome": a.nome,
                        "preco": float(a.preco),
                        "obrigatorio": a.obrigatorio,
                        "imagem": getattr(a, "imagem", None),
                    }
                    for a in adicionais_list
                ]
            
            # Verifica se o produto tem receita
            tem_receita = self.repo_receitas.produto_tem_receita(p.cod_barras)
            
            data.append(ProdutoListItem(
                cod_barras=p.cod_barras,
                descricao=p.descricao,
                imagem=p.imagem,
                preco_venda=float(pe.preco_venda),
                custo=(float(pe.custo) if pe.custo is not None else None),
                disponivel=pe.disponivel and p.ativo,
                exibir_delivery=pe.exibir_delivery,
                tem_receita=tem_receita,
                adicionais=adicionais,
            ))

        return {"data": data, "total": total, "page": page, "limit": limit, "has_more": offset + limit < total}

    def deletar_produto(self, empresa_id: int, cod_barras: str):
        """Remove o vínculo entre produto e empresa"""
        # garante que a empresa existe antes de prosseguir
        self._empresa_or_404(empresa_id)

        # verifica se o produto está vinculado à empresa
        produto_emp = self.repo.get_produto_emp(empresa_id, cod_barras)
        if not produto_emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não está vinculado a esta empresa."
            )

        # remove o vínculo
        self.db.delete(produto_emp)
        self.db.commit()

