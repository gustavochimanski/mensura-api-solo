from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal

from app.api.catalogo.models.model_complemento import ComplementoModel
from app.api.catalogo.models.model_adicional import AdicionalModel
from app.api.catalogo.repositories.repo_complemento import ComplementoRepository
from app.api.catalogo.repositories.repo_complemento_item import ComplementoItemRepository
from app.api.catalogo.schemas.schema_complemento import (
    ComplementoResponse,
    CriarComplementoRequest,
    AtualizarComplementoRequest,
    AdicionalResponse,
    CriarAdicionalRequest,
    CriarItemRequest,
    AtualizarAdicionalRequest,
    VincularComplementosProdutoRequest,
    VincularComplementosProdutoResponse,
    VincularItensComplementoRequest,
    VincularItensComplementoResponse,
    VincularItemComplementoRequest,
    VincularItemComplementoResponse,
    AtualizarOrdemItensRequest,
    ComplementoResumidoResponse,
    AtualizarPrecoItemComplementoRequest,
)
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.catalogo.repositories.repo_produto import ProdutoMensuraRepository


class ComplementoService:
    """Service para operações de complementos."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ComplementoRepository(db)
        self.repo_item = ComplementoItemRepository(db)
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
            minimo_itens=req.minimo_itens,
            maximo_itens=req.maximo_itens,
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
                minimo_itens=c.minimo_itens,
                maximo_itens=c.maximo_itens,
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

    # ------ Adicionais dentro de complementos (DEPRECADO - usar criar_item + vincular) ------
    def criar_adicional(self, complemento_id: int, req: CriarAdicionalRequest) -> AdicionalResponse:
        """Cria um adicional e vincula automaticamente a um complemento.
        
        DEPRECADO: Use criar_item() + vincular_itens_complemento() para mais flexibilidade.
        Este método mantém compatibilidade com código legado.
        """
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        
        # Cria o item independente
        item = self.repo_item.criar_item(
            empresa_id=complemento.empresa_id,
            nome=req.nome,
            descricao=req.descricao,
            preco=Decimal(str(req.preco)),
            custo=Decimal(str(req.custo)),
            ativo=req.ativo,
        )
        
        # Vincula ao complemento com a ordem especificada
        ordem = req.ordem if hasattr(req, 'ordem') else 0
        self.repo_item.vincular_itens_complemento(
            complemento_id=complemento_id,
            item_ids=[item.id],
            ordens=[ordem],
        )
        
        return self._adicional_to_response(item, ordem=ordem)

    def atualizar_adicional(self, complemento_id: int, adicional_id: int, req: AtualizarAdicionalRequest) -> AdicionalResponse:
        """Atualiza um adicional dentro de um complemento.
        
        DEPRECADO: Use atualizar_item() diretamente. Este método mantém compatibilidade.
        """
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        
        # Verifica se o item está vinculado ao complemento
        itens_com_ordem = self.repo_item.listar_itens_complemento(complemento_id, apenas_ativos=False)
        item_encontrado = None
        ordem_item = 0
        for item, ordem in itens_com_ordem:
            if item.id == adicional_id:
                item_encontrado = item
                ordem_item = ordem
                break
        
        if not item_encontrado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {adicional_id} não encontrado no complemento {complemento_id}."
            )
        
        # Atualiza o item
        return self.atualizar_item(adicional_id, req)

    def deletar_adicional(self, complemento_id: int, adicional_id: int):
        """Remove a vinculação de um item com um complemento (não deleta o item).
        
        DEPRECADO: Use desvincular_item_complemento() diretamente. Este método mantém compatibilidade.
        """
        self.desvincular_item_complemento(complemento_id, adicional_id)

    def listar_adicionais_complemento(self, complemento_id: int, apenas_ativos: bool = True) -> List[AdicionalResponse]:
        """Lista todos os adicionais de um complemento."""
        complemento = self.repo.buscar_por_id(complemento_id, carregar_adicionais=True)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )

        # Usa o relacionamento N:N via tabela de associação
        itens = self.repo_item.listar_itens_complemento(complemento_id, apenas_ativos)
        return [
            self._adicional_to_response(item, ordem=ordem)
            for item, ordem in itens
        ]

    # ------ Itens de Complemento (Independentes) ------
    def criar_item(self, req: CriarItemRequest) -> AdicionalResponse:
        """Cria um item de complemento independente (não vinculado a nenhum complemento ainda)."""
        self._empresa_or_404(req.empresa_id)
        
        item = self.repo_item.criar_item(
            empresa_id=req.empresa_id,
            nome=req.nome,
            descricao=req.descricao,
            preco=Decimal(str(req.preco)),
            custo=Decimal(str(req.custo)),
            ativo=req.ativo,
        )
        
        return self._adicional_to_response(item)

    def buscar_item_por_id(self, item_id: int) -> AdicionalResponse:
        """Busca um item por ID."""
        item = self.repo_item.buscar_por_id(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {item_id} não encontrado."
            )
        return self._adicional_to_response(item)

    def listar_itens(self, empresa_id: int, apenas_ativos: bool = True) -> List[AdicionalResponse]:
        """Lista todos os itens de uma empresa."""
        self._empresa_or_404(empresa_id)
        itens = self.repo_item.listar_por_empresa(empresa_id, apenas_ativos)
        return [self._adicional_to_response(item) for item in itens]

    def buscar_adicionais(self, empresa_id: int, search: str, apenas_ativos: bool = True) -> List[AdicionalResponse]:
        """
        Busca adicionais por termo (nome ou descrição).

        - Implementação performática: filtro direto no banco usando ILIKE.
        """
        self._empresa_or_404(empresa_id)
        if not search or not search.strip():
            # Se termo vazio, retorna lista completa
            return self.listar_itens(empresa_id, apenas_ativos)
        
        itens = self.repo_item.buscar_por_termo(empresa_id, search.strip(), apenas_ativos)
        return [self._adicional_to_response(item) for item in itens]

    def atualizar_item(self, item_id: int, req: AtualizarAdicionalRequest) -> AdicionalResponse:
        """Atualiza um item existente."""
        item = self.repo_item.buscar_por_id(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {item_id} não encontrado."
            )
        
        update_data = {}
        for key, value in req.model_dump(exclude_unset=True).items():
            if value is not None:
                if key in ['preco', 'custo']:
                    update_data[key] = Decimal(str(value))
                else:
                    update_data[key] = value
        
        self.repo_item.atualizar_item(item, **update_data)
        return self.buscar_item_por_id(item_id)

    def deletar_item(self, item_id: int):
        """Deleta um item (remove automaticamente os vínculos com complementos)."""
        item = self.repo_item.buscar_por_id(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {item_id} não encontrado."
            )
        self.repo_item.deletar_item(item)

    # ------ Vincular Itens a Complementos (N:N) ------
    def vincular_itens_complemento(self, complemento_id: int, req: VincularItensComplementoRequest) -> VincularItensComplementoResponse:
        """Vincula múltiplos itens a um complemento."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        
        # Valida se os itens existem e pertencem à mesma empresa
        itens = []
        for item_id in req.item_ids:
            item = self.repo_item.buscar_por_id(item_id)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Item {item_id} não encontrado."
                )
            if item.empresa_id != complemento.empresa_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item {item_id} pertence a empresa diferente do complemento."
                )
            itens.append(item)
        
        # Vincula os itens
        self.repo_item.vincular_itens_complemento(
            complemento_id=complemento_id,
            item_ids=req.item_ids,
            ordens=req.ordens,
            precos=req.precos,
        )
        
        # Busca os itens vinculados para retornar
        itens_com_ordem = self.repo_item.listar_itens_complemento(complemento_id, apenas_ativos=False)
        
        return VincularItensComplementoResponse(
            complemento_id=complemento_id,
            itens_vinculados=[self._adicional_to_response(item, ordem=ordem) for item, ordem in itens_com_ordem],
            message="Itens vinculados com sucesso"
        )

    def vincular_item_complemento(self, complemento_id: int, req: VincularItemComplementoRequest) -> VincularItemComplementoResponse:
        """Vincula um único item adicional a um complemento."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        
        # Valida se o item existe e pertence à mesma empresa
        item = self.repo_item.buscar_por_id(req.item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {req.item_id} não encontrado."
            )
        
        if item.empresa_id != complemento.empresa_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item {req.item_id} pertence a empresa diferente do complemento."
            )
        
        # Converte preco_complemento para Decimal se fornecido
        preco_complemento = None
        if req.preco_complemento is not None:
            preco_complemento = Decimal(str(req.preco_complemento))
        
        # Vincula o item
        self.repo_item.vincular_item_complemento(
            complemento_id=complemento_id,
            item_id=req.item_id,
            ordem=req.ordem,
            preco_complemento=preco_complemento
        )
        
        # Busca o item vinculado para retornar (com ordem e preço atualizados)
        itens_com_ordem = self.repo_item.listar_itens_complemento(complemento_id, apenas_ativos=False)
        item_vinculado = None
        for item_result, ordem_result in itens_com_ordem:
            if item_result.id == req.item_id:
                item_vinculado = self._adicional_to_response(item_result, ordem=ordem_result)
                break
        
        if not item_vinculado:
            # Fallback: busca o item diretamente
            item_vinculado = self._adicional_to_response(item, ordem=req.ordem or 0)
        
        return VincularItemComplementoResponse(
            complemento_id=complemento_id,
            item_vinculado=item_vinculado,
            message="Item vinculado com sucesso"
        )

    def desvincular_item_complemento(self, complemento_id: int, item_id: int):
        """Remove a vinculação de um item com um complemento."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        
        item = self.repo_item.buscar_por_id(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {item_id} não encontrado."
            )
        
        self.repo_item.desvincular_item_complemento(complemento_id, item_id)

    def listar_itens_complemento(self, complemento_id: int, apenas_ativos: bool = True) -> List[AdicionalResponse]:
        """Lista todos os itens vinculados a um complemento."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        
        itens_com_ordem = self.repo_item.listar_itens_complemento(complemento_id, apenas_ativos)
        return [self._adicional_to_response(item, ordem=ordem) for item, ordem in itens_com_ordem]

    def atualizar_ordem_itens(self, complemento_id: int, req: AtualizarOrdemItensRequest):
        """Atualiza a ordem dos itens em um complemento."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        
        # Converte para lista de dicts
        if req.item_ids:
            # Formato simples: item_ids na ordem desejada (ordem = índice)
            item_ordens_dict = [
                {"item_id": item_id, "ordem": idx} 
                for idx, item_id in enumerate(req.item_ids)
            ]
        elif req.item_ordens:
            # Formato completo: item_ordens com ordem explícita
            item_ordens_dict = [
                {"item_id": io.item_id, "ordem": io.ordem} 
                for io in req.item_ordens
            ]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deve fornecer 'item_ids' ou 'item_ordens'"
            )
        
        self.repo_item.atualizar_ordem_itens(complemento_id, item_ordens_dict)

    def atualizar_preco_item_complemento(
        self,
        complemento_id: int,
        item_id: int,
        req: AtualizarPrecoItemComplementoRequest,
    ) -> AdicionalResponse:
        """Atualiza o preço específico de um item dentro de um complemento.

        - Não altera o preço base do adicional.
        - O preço definido aqui vale apenas para este complemento.
        """
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )

        item = self.repo_item.buscar_por_id(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {item_id} não encontrado."
            )

        # Garante que o item está vinculado ao complemento
        itens_com_ordem = self.repo_item.listar_itens_complemento(complemento_id, apenas_ativos=False)
        vinculado = False
        ordem_item = 0
        for it, ordem in itens_com_ordem:
            if it.id == item_id:
                vinculado = True
                ordem_item = ordem
                break

        if not vinculado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {item_id} não está vinculado ao complemento {complemento_id}."
            )

        # Atualiza o preço específico na tabela de associação
        preco_decimal = Decimal(str(req.preco))
        self.repo_item.atualizar_preco_item_complemento(
            complemento_id=complemento_id,
            item_id=item_id,
            preco_complemento=preco_decimal,
        )

        # Recarrega o item com o preço aplicado neste complemento
        itens_atualizados = self.repo_item.listar_itens_complemento(complemento_id, apenas_ativos=False)
        for it, ordem in itens_atualizados:
            if it.id == item_id:
                return self._adicional_to_response(it, ordem=ordem)

        # Fallback (não deveria acontecer se tudo estiver consistente)
        return self._adicional_to_response(item, ordem=ordem_item)

    # ------ Helpers ------
    def complemento_to_response(self, complemento: ComplementoModel) -> ComplementoResponse:
        """Converte ComplementoModel para ComplementoResponse."""
        # Busca os itens vinculados via relacionamento N:N (retorna tuplas (item, ordem))
        itens_com_ordem = self.repo_item.listar_itens_complemento(complemento.id, apenas_ativos=False)

        adicionais = [
            self._adicional_to_response(item, ordem=ordem)
            for item, ordem in itens_com_ordem
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

    def _adicional_to_response(self, adicional: AdicionalModel, ordem: Optional[int] = None) -> AdicionalResponse:
        """Converte AdicionalModel para AdicionalResponse."""
        # Se houver preço específico aplicado para este complemento, ele vem em adicional.preco_aplicado
        preco_aplicado = getattr(adicional, "preco_aplicado", adicional.preco)
        return AdicionalResponse(
            id=adicional.id,
            nome=adicional.nome,
            descricao=adicional.descricao,
            preco=float(preco_aplicado),
            custo=float(adicional.custo),
            ativo=adicional.ativo,
            ordem=ordem if ordem is not None else getattr(adicional, 'ordem', 0),
            created_at=adicional.created_at,
            updated_at=adicional.updated_at,
        )

