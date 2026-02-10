from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal

from app.api.catalogo.models.model_complemento import ComplementoModel
from app.api.catalogo.models.model_complemento_vinculo_item import ComplementoVinculoItemModel
from app.api.catalogo.repositories.repo_complemento import ComplementoRepository
from app.api.catalogo.repositories.repo_complemento_item import ComplementoItemRepository
from app.api.catalogo.schemas.schema_complemento import (
    ComplementoResponse,
    CriarComplementoRequest,
    AtualizarComplementoRequest,
    AdicionalResponse,
    VincularComplementosProdutoRequest,
    VincularComplementosProdutoResponse,
    VincularComplementosReceitaRequest,
    VincularComplementosReceitaResponse,
    VincularComplementosComboRequest,
    VincularComplementosComboResponse,
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

    def _validar_itens_empresa(self, empresa_id: int, items: list) -> None:
        """Garante que cada item (produto/receita/combo) existe e pertence à empresa."""
        from app.api.catalogo.models.model_receita import ReceitaModel
        from app.api.catalogo.models.model_combo import ComboModel

        for it in items:
            if it.produto_cod_barras is not None:
                pe = self.repo_produto.get_produto_emp(empresa_id, it.produto_cod_barras)
                if not pe:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Produto {it.produto_cod_barras} não encontrado ou não pertence à empresa.",
                    )
            elif it.receita_id is not None:
                r = self.db.query(ReceitaModel).filter_by(id=it.receita_id).first()
                if not r or r.empresa_id != empresa_id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Receita {it.receita_id} não encontrada ou não pertence à empresa.",
                    )
            else:
                c = self.db.query(ComboModel).filter_by(id=it.combo_id).first()
                if not c or c.empresa_id != empresa_id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Combo {it.combo_id} não encontrado ou não pertence à empresa.",
                    )

    def criar_complemento(self, req: CriarComplementoRequest) -> ComplementoResponse:
        """Cria um novo complemento.
        
        NOTA: obrigatorio, quantitativo, minimo_itens e maximo_itens não são mais
        definidos aqui. Essas configurações são definidas na vinculação.
        """
        self._empresa_or_404(req.empresa_id)
        
        complemento = self.repo.criar_complemento(
            empresa_id=req.empresa_id,
            nome=req.nome,
            descricao=req.descricao,
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
        self.db.commit()  # Garante que as mudanças sejam persistidas
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
        # Preparar payload_dump (sem log)
        try:
            payload_dump = req.model_dump()
        except Exception:
            payload_dump = str(req)
        produto = self.repo_produto.buscar_por_cod_barras(cod_barras)
        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produto {cod_barras} não encontrado."
            )
        
        # Processa formato completo ou simples
        # Prioriza configuracoes se fornecido e não vazio
        if req.configuracoes is not None and len(req.configuracoes) > 0:
            # Formato completo: usa configurações detalhadas
            complemento_ids = [cfg.complemento_id for cfg in req.configuracoes]
            ordens = [cfg.ordem if cfg.ordem is not None else idx for idx, cfg in enumerate(req.configuracoes)]
            obrigatorios = [cfg.obrigatorio for cfg in req.configuracoes]
            quantitativos = [cfg.quantitativo for cfg in req.configuracoes]
            # Se quantitativo for False, minimo_itens e maximo_itens devem ser None
            minimos_itens = [None if not cfg.quantitativo else cfg.minimo_itens for cfg in req.configuracoes]
            maximos_itens = [None if not cfg.quantitativo else cfg.maximo_itens for cfg in req.configuracoes]
        else:
            # Formato simples: compatibilidade (usa valores padrão)
            if not req.complemento_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Deve fornecer 'complemento_ids' ou 'configuracoes'"
                )
            complemento_ids = req.complemento_ids
            ordens = req.ordens
            obrigatorios = None  # Usa False como padrão no repositório
            quantitativos = None  # Usa False como padrão no repositório
            minimos_itens = None
            maximos_itens = None
        
        self.repo.vincular_complementos_produto(
            cod_barras, 
            complemento_ids, 
            ordens, 
            obrigatorios, 
            quantitativos,
            minimos_itens, 
            maximos_itens
        )
        self.db.commit()
        
        # Busca os complementos vinculados para retornar
        complementos_com_vinculacao = self.repo.listar_por_produto(cod_barras, apenas_ativos=True)
        complementos_vinculados = [
            ComplementoResumidoResponse(
                id=c.id,
                nome=c.nome,
                obrigatorio=obrigatorio,  # Da vinculação
                quantitativo=quantitativo,  # Da vinculação
                minimo_itens=minimo_itens,  # Da vinculação
                maximo_itens=maximo_itens,  # Da vinculação
                ordem=ordem,
            )
            for c, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens in complementos_com_vinculacao
        ]
        
        return VincularComplementosProdutoResponse(
            produto_cod_barras=cod_barras,
            complementos_vinculados=complementos_vinculados,
        )

    def listar_complementos_produto(self, cod_barras: str, apenas_ativos: bool = True) -> List[ComplementoResponse]:
        """Lista todos os complementos de um produto específico."""
        complementos_com_vinculacao = self.repo.listar_por_produto(cod_barras, apenas_ativos=apenas_ativos, carregar_adicionais=True)
        # Cria responses usando configurações da vinculação
        responses = []
        for c, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens in complementos_com_vinculacao:
            resp = self.complemento_to_response(c)
            # Sobrescreve com valores da vinculação
            resp.obrigatorio = obrigatorio
            resp.quantitativo = quantitativo
            resp.minimo_itens = minimo_itens
            resp.maximo_itens = maximo_itens
            resp.ordem = ordem
            responses.append(resp)
        return responses

    def vincular_complementos_receita(self, receita_id: int, req: VincularComplementosReceitaRequest) -> VincularComplementosReceitaResponse:
        """Vincula múltiplos complementos a uma receita."""
        from app.api.catalogo.models.model_receita import ReceitaModel
        
        receita = self.db.query(ReceitaModel).filter_by(id=receita_id).first()
        if not receita:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Receita {receita_id} não encontrada."
            )
        
        # Processa formato completo ou simples
        # Prioriza configuracoes se fornecido
        if req.configuracoes is not None:
            # Formato completo: usa configurações detalhadas
            if len(req.configuracoes) > 0:
                complemento_ids = [cfg.complemento_id for cfg in req.configuracoes]
                ordens = [cfg.ordem if cfg.ordem is not None else idx for idx, cfg in enumerate(req.configuracoes)]
                obrigatorios = [cfg.obrigatorio for cfg in req.configuracoes]
                quantitativos = [cfg.quantitativo for cfg in req.configuracoes]
                # Se quantitativo for False, minimo_itens e maximo_itens devem ser None
                minimos_itens = [None if not cfg.quantitativo else cfg.minimo_itens for cfg in req.configuracoes]
                maximos_itens = [None if not cfg.quantitativo else cfg.maximo_itens for cfg in req.configuracoes]
            else:
                # Lista vazia: remove todas as vinculações
                complemento_ids = []
                ordens = []
                obrigatorios = []
                quantitativos = []
                minimos_itens = []
                maximos_itens = []
        else:
            # Formato simples: compatibilidade (usa valores padrão)
            if req.complemento_ids is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Deve fornecer 'complemento_ids' ou 'configuracoes'"
                )
            # Lista vazia é permitida (remove todas as vinculações)
            complemento_ids = req.complemento_ids if req.complemento_ids is not None else []
            ordens = req.ordens
            obrigatorios = None  # Usa False como padrão no repositório
            quantitativos = None  # Usa False como padrão no repositório
            minimos_itens = None
            maximos_itens = None
        
        self.repo.vincular_complementos_receita(
            receita_id, 
            complemento_ids, 
            ordens, 
            obrigatorios, 
            quantitativos,
            minimos_itens, 
            maximos_itens
        )
        self.db.commit()  # Garante que as vinculações sejam persistidas
        
        # Busca os complementos vinculados para retornar (sem filtro de ativos para garantir que retorne os vinculados)
        complementos_com_vinculacao = self.repo.listar_por_receita(receita_id, apenas_ativos=False, carregar_adicionais=False)
        complementos_vinculados = [
            ComplementoResumidoResponse(
                id=c.id,
                nome=c.nome,
                obrigatorio=obrigatorio,  # Da vinculação
                quantitativo=quantitativo,  # Da vinculação
                minimo_itens=minimo_itens,  # Da vinculação
                maximo_itens=maximo_itens,  # Da vinculação
                ordem=ordem,
            )
            for c, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens in complementos_com_vinculacao
        ]
        
        return VincularComplementosReceitaResponse(
            receita_id=receita_id,
            complementos_vinculados=complementos_vinculados,
        )

    def listar_complementos_receita(self, receita_id: int, apenas_ativos: bool = True) -> List[ComplementoResponse]:
        """Lista todos os complementos de uma receita específica."""
        complementos_com_vinculacao = self.repo.listar_por_receita(receita_id, apenas_ativos=apenas_ativos, carregar_adicionais=True)
        # Cria responses usando configurações da vinculação
        responses = []
        for c, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens in complementos_com_vinculacao:
            resp = self.complemento_to_response(c)
            # Sobrescreve com valores da vinculação
            resp.obrigatorio = obrigatorio
            resp.quantitativo = quantitativo
            resp.minimo_itens = minimo_itens
            resp.maximo_itens = maximo_itens
            resp.ordem = ordem
            responses.append(resp)
        return responses

    def vincular_complementos_combo(self, combo_id: int, req: VincularComplementosComboRequest) -> VincularComplementosComboResponse:
        """Vincula múltiplos complementos a um combo."""
        from app.api.catalogo.models.model_combo import ComboModel
        
        combo = self.db.query(ComboModel).filter_by(id=combo_id).first()
        if not combo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Combo {combo_id} não encontrado."
            )
        
        # Processa formato completo ou simples
        # Prioriza configuracoes se fornecido e não vazio
        if req.configuracoes is not None and len(req.configuracoes) > 0:
            # Formato completo: usa configurações detalhadas
            complemento_ids = [cfg.complemento_id for cfg in req.configuracoes]
            ordens = [cfg.ordem if cfg.ordem is not None else idx for idx, cfg in enumerate(req.configuracoes)]
            obrigatorios = [cfg.obrigatorio for cfg in req.configuracoes]
            quantitativos = [cfg.quantitativo for cfg in req.configuracoes]
            # Se quantitativo for False, minimo_itens e maximo_itens devem ser None
            minimos_itens = [None if not cfg.quantitativo else cfg.minimo_itens for cfg in req.configuracoes]
            maximos_itens = [None if not cfg.quantitativo else cfg.maximo_itens for cfg in req.configuracoes]
        else:
            # Formato simples: compatibilidade (usa valores padrão)
            # Lista vazia é permitida (remove todas as vinculações)
            complemento_ids = req.complemento_ids if req.complemento_ids is not None else []
            ordens = req.ordens
            obrigatorios = None  # Usa False como padrão no repositório
            quantitativos = None  # Usa False como padrão no repositório
            minimos_itens = None
            maximos_itens = None
        
        # Valida se os complementos existem e pertencem à mesma empresa
        if complemento_ids:
            complementos_existentes = (
                self.db.query(ComplementoModel)
                .filter(ComplementoModel.id.in_(complemento_ids))
                .all()
            )
            
            if len(complementos_existentes) != len(complemento_ids):
                encontrados_ids = {c.id for c in complementos_existentes}
                nao_encontrados = [cid for cid in complemento_ids if cid not in encontrados_ids]
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Complementos não encontrados: {nao_encontrados}"
                )
            
            # Valida se todos os complementos pertencem à mesma empresa do combo
            for complemento in complementos_existentes:
                if complemento.empresa_id != combo.empresa_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Complemento {complemento.id} pertence a empresa diferente do combo."
                    )
        
        self.repo.vincular_complementos_combo(
            combo_id, 
            complemento_ids, 
            ordens, 
            obrigatorios, 
            quantitativos,
            minimos_itens, 
            maximos_itens
        )
        self.db.commit()  # Garante que as vinculações sejam persistidas
        
        # Busca os complementos vinculados para retornar (sem filtro de ativos para garantir que retorne os vinculados)
        complementos_com_vinculacao = self.repo.listar_por_combo(combo_id, apenas_ativos=False, carregar_adicionais=False)
        complementos_vinculados = [
            ComplementoResumidoResponse(
                id=c.id,
                nome=c.nome,
                obrigatorio=obrigatorio,  # Da vinculação
                quantitativo=quantitativo,  # Da vinculação
                minimo_itens=minimo_itens,  # Da vinculação
                maximo_itens=maximo_itens,  # Da vinculação
                ordem=ordem,
            )
            for c, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens in complementos_com_vinculacao
        ]
        
        return VincularComplementosComboResponse(
            combo_id=combo_id,
            complementos_vinculados=complementos_vinculados,
        )

    def listar_complementos_combo(self, combo_id: int, apenas_ativos: bool = True) -> List[ComplementoResponse]:
        """Lista todos os complementos de um combo específico."""
        complementos_com_vinculacao = self.repo.listar_por_combo(combo_id, apenas_ativos=apenas_ativos, carregar_adicionais=True)
        # Cria responses usando configurações da vinculação
        responses = []
        for c, ordem, obrigatorio, quantitativo, minimo_itens, maximo_itens in complementos_com_vinculacao:
            resp = self.complemento_to_response(c)
            # Sobrescreve com valores da vinculação
            resp.obrigatorio = obrigatorio
            resp.quantitativo = quantitativo
            resp.minimo_itens = minimo_itens
            resp.maximo_itens = maximo_itens
            resp.ordem = ordem
            responses.append(resp)
        return responses

    # ------ Vincular itens (produto/receita/combo) a complementos ------
    def vincular_itens_complemento(self, complemento_id: int, req: VincularItensComplementoRequest) -> VincularItensComplementoResponse:
        """Vincula múltiplos itens (produto/receita/combo) a um complemento."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        self._validar_itens_empresa(complemento.empresa_id, req.items)

        items_dict: List[dict] = []
        ordens_list: List[int] = []
        precos_list: List[Optional[Decimal]] = []
        for i, it in enumerate(req.items):
            items_dict.append({
                "produto_cod_barras": it.produto_cod_barras,
                "receita_id": it.receita_id,
                "combo_id": it.combo_id,
            })
            ordens_list.append(it.ordem if it.ordem is not None else (req.ordens[i] if req.ordens and i < len(req.ordens) else i))
            p = it.preco_complemento
            if p is not None:
                precos_list.append(Decimal(str(p)))
            elif req.precos and i < len(req.precos) and req.precos[i] is not None:
                precos_list.append(Decimal(str(req.precos[i])))
            else:
                precos_list.append(None)

        try:
            self.repo_item.vincular_itens_complemento(
                complemento_id=complemento_id,
                items=items_dict,
                ordens=ordens_list,
                precos=precos_list,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        self.db.commit()

        itens_com_ordem = self.repo_item.listar_itens_complemento(
            complemento_id, apenas_ativos=False, empresa_id=complemento.empresa_id
        )
        adicionais = [
            self._vinculo_to_adicional_response(v, complemento.empresa_id, ordem)
            for v, ordem in itens_com_ordem
        ]
        return VincularItensComplementoResponse(
            complemento_id=complemento_id,
            adicionais=adicionais,
            message="Itens vinculados com sucesso",
        )

    def vincular_item_complemento(self, complemento_id: int, req: VincularItemComplementoRequest) -> VincularItemComplementoResponse:
        """Vincula um único item (produto/receita/combo) a um complemento."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        self._validar_itens_empresa(complemento.empresa_id, [req])

        preco = Decimal(str(req.preco_complemento)) if req.preco_complemento is not None else None
        try:
            v = self.repo_item.vincular_item_complemento(
                complemento_id=complemento_id,
                produto_cod_barras=req.produto_cod_barras,
                receita_id=req.receita_id,
                combo_id=req.combo_id,
                ordem=req.ordem,
                preco_complemento=preco,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        self.db.commit()

        item_vinculado = self._vinculo_to_adicional_response(v, complemento.empresa_id, v.ordem)
        return VincularItemComplementoResponse(
            complemento_id=complemento_id,
            item_vinculado=item_vinculado,
            message="Item vinculado com sucesso",
        )

    def desvincular_item_complemento(self, complemento_id: int, item_id: int):
        """Remove a vinculação de um item (vinculo) com um complemento. item_id = id do vínculo."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        v = self.repo_item.buscar_por_id(item_id)
        if not v or v.complemento_id != complemento_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {item_id} não encontrado no complemento {complemento_id}."
            )
        self.repo_item.desvincular_item_complemento(complemento_id, item_id)
        self.db.commit()

    def listar_itens_complemento(self, complemento_id: int, apenas_ativos: bool = True) -> List[AdicionalResponse]:
        """Lista todos os itens (produto/receita/combo) vinculados a um complemento. Retorno mantém nome `adicionais`."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        itens_com_ordem = self.repo_item.listar_itens_complemento(
            complemento_id, apenas_ativos=apenas_ativos, empresa_id=complemento.empresa_id
        )
        return [
            self._vinculo_to_adicional_response(v, complemento.empresa_id, ordem)
            for v, ordem in itens_com_ordem
        ]

    def atualizar_ordem_itens(self, complemento_id: int, req: AtualizarOrdemItensRequest):
        """Atualiza a ordem dos itens em um complemento. item_id = id do vínculo."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        if req.item_ids:
            item_ordens_dict = [
                {"item_id": iid, "ordem": idx}
                for idx, iid in enumerate(req.item_ids)
            ]
        elif req.item_ordens:
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
        self.db.commit()

    def atualizar_preco_item_complemento(
        self,
        complemento_id: int,
        item_id: int,
        req: AtualizarPrecoItemComplementoRequest,
    ) -> AdicionalResponse:
        """Atualiza o preço específico de um item (vínculo) dentro de um complemento. item_id = id do vínculo."""
        complemento = self.repo.buscar_por_id(complemento_id)
        if not complemento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complemento {complemento_id} não encontrado."
            )
        v = self.repo_item.buscar_por_id(item_id)
        if not v or v.complemento_id != complemento_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item {item_id} não encontrado no complemento {complemento_id}."
            )
        preco_decimal = Decimal(str(req.preco))
        self.repo_item.atualizar_preco_item_complemento(
            complemento_id=complemento_id,
            vinculo_id=item_id,
            preco_complemento=preco_decimal,
        )
        self.db.commit()
        v = self.repo_item.buscar_por_id(item_id)
        return self._vinculo_to_adicional_response(v, complemento.empresa_id, v.ordem)

    # ------ Helpers ------
    def complemento_to_response(self, complemento: ComplementoModel) -> ComplementoResponse:
        """Converte ComplementoModel para ComplementoResponse. Itens vêm de complemento_vinculo_item (expostos como adicionais)."""
        itens_com_ordem = self.repo_item.listar_itens_complemento(
            complemento.id, apenas_ativos=False, empresa_id=complemento.empresa_id
        )
        adicionais = [
            self._vinculo_to_adicional_response(v, complemento.empresa_id, ordem)
            for v, ordem in itens_com_ordem
        ]
        return ComplementoResponse(
            id=complemento.id,
            empresa_id=complemento.empresa_id,
            nome=complemento.nome,
            descricao=complemento.descricao,
            obrigatorio=None,
            quantitativo=None,
            minimo_itens=None,
            maximo_itens=None,
            ordem=complemento.ordem,
            ativo=complemento.ativo,
            adicionais=adicionais,
            created_at=complemento.created_at,
            updated_at=complemento.updated_at,
        )

    def _vinculo_to_adicional_response(
        self,
        v: ComplementoVinculoItemModel,
        empresa_id: int,
        ordem: Optional[int] = None,
    ) -> AdicionalResponse:
        """Converte ComplementoVinculoItemModel (produto/receita/combo) para AdicionalResponse. Mantém nome adicionais."""
        preco, custo = self.repo_item.preco_e_custo_vinculo(v, empresa_id)
        nome = v.nome or ""
        return AdicionalResponse(
            id=v.id,
            nome=nome,
            descricao=v.descricao,
            imagem=v.imagem,
            preco=float(preco),
            custo=float(custo),
            ativo=v.ativo,
            ordem=ordem if ordem is not None else int(v.ordem),
            created_at=v.created_at,
            updated_at=v.updated_at,
        )

