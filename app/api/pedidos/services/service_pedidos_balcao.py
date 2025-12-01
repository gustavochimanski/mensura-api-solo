from __future__ import annotations

from decimal import Decimal
from typing import Optional
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.cadastros.models.model_mesa import StatusMesa
from app.api.cadastros.repositories.repo_mesas import MesaRepository
from app.api.pedidos.models.model_pedido_unificado import TipoPedido
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.catalogo.contracts.adicional_contract import IAdicionalContract
from app.api.catalogo.contracts.combo_contract import IComboContract
from app.api.pedidos.models.model_pedido_historico_unificado import TipoOperacaoPedido
from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
from app.api.pedidos.schemas.schema_pedido import (
    ItemPedidoRequest,
    ReceitaPedidoRequest,
    ComboPedidoRequest,
    PedidoResponseCompleto,
    ItemAdicionalRequest,
)
from app.api.pedidos.services.service_pedido_responses import PedidoResponseBuilder
from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum
from app.api.pedidos.models.model_pedido_unificado import StatusPedido
from app.api.pedidos.schemas.schema_pedido_status_historico import PedidoStatusHistoricoOut, HistoricoDoPedidoResponse
from pydantic import BaseModel
from typing import Optional, List


# Schemas de request para pedidos de balcão
class PedidoBalcaoCreate(BaseModel):
    empresa_id: int
    mesa_id: Optional[int] = None  # Código da mesa (opcional)
    cliente_id: Optional[int] = None
    observacoes: Optional[str] = None
    itens: Optional[List[ItemPedidoRequest]] = None


class AdicionarItemRequest(BaseModel):
    produto_cod_barras: str
    quantidade: int
    observacao: Optional[str] = None


class AdicionarProdutoGenericoRequest(BaseModel):
    produto_cod_barras: Optional[str] = None
    receita_id: Optional[int] = None
    combo_id: Optional[int] = None
    quantidade: int = 1
    observacao: Optional[str] = None
    adicionais: Optional[List[ItemAdicionalRequest]] = None
    adicionais_ids: Optional[List[int]] = None


class RemoverItemResponse(BaseModel):
    ok: bool
    pedido_id: int
    valor_total: float


class FecharContaBalcaoRequest(BaseModel):
    meio_pagamento_id: Optional[int] = None
    troco_para: Optional[float] = None


class AtualizarStatusPedidoRequest(BaseModel):
    status: PedidoStatusEnum

from app.api.catalogo.models.model_receita import ReceitaModel
from app.api.catalogo.models.model_combo import ComboModel
from app.api.catalogo.models.model_adicional import AdicionalModel
from app.api.pedidos.utils.adicionais import resolve_produto_adicionais
from app.api.pedidos.services.service_pedido_helpers import _dec


class PedidoBalcaoService:
    def __init__(
        self,
        db: Session,
        produto_contract: IProdutoContract | None = None,
        adicional_contract: IAdicionalContract | None = None,
        combo_contract: IComboContract | None = None,
    ):
        self.db = db
        self.repo_mesa = MesaRepository(db)
        self.repo = PedidoRepository(db, produto_contract=produto_contract)
        self.produto_contract = produto_contract
        self.adicional_contract = adicional_contract
        self.combo_contract = combo_contract

    @staticmethod
    def _status_value(status_obj):
        """Normaliza valor de status para string."""
        if hasattr(status_obj, "value"):
            return status_obj.value
        return status_obj
    

    # -------- Pedido --------
    def criar_pedido(self, payload: PedidoBalcaoCreate) -> PedidoResponseCompleto:
        # Se mesa_id informado, busca a mesa pelo código
        mesa_id_real = None
        if payload.mesa_id is not None:
            from decimal import Decimal
            try:
                codigo = Decimal(str(payload.mesa_id))
                mesa = self.repo_mesa.get_by_codigo(codigo)
                mesa_id_real = mesa.id
            except Exception as e:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    f"Mesa com código {payload.mesa_id} não encontrada"
                )

        pedido = self.repo.criar_pedido_balcao(
            empresa_id=payload.empresa_id,
            mesa_id=mesa_id_real,
            cliente_id=payload.cliente_id,
            observacoes=payload.observacoes,
        )

        # Registra histórico de criação
        self.repo.add_historico(
            pedido_id=pedido.id,
            tipo_pedido=TipoOperacaoPedido.PEDIDO_CRIADO,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} criado",
            cliente_id=payload.cliente_id,
        )
        if mesa_id_real:
            self.repo.add_historico(
                pedido_id=pedido.id,
                tipo_pedido=TipoOperacaoPedido.MESA_ASSOCIADA,
                descricao=f"Mesa associada ao pedido",
            )
        self.repo.commit()

        # itens iniciais
        if payload.itens:
            for it in payload.itens:
                self.repo.add_item(
                    pedido.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    observacao=it.observacao,
                )
                # Registra histórico de item adicionado
                self.repo.add_historico(
                    pedido_id=pedido.id,
                    tipo_pedido=TipoOperacaoPedido.ITEM_ADICIONADO,
                    descricao=f"Item adicionado: {it.produto_cod_barras} (qtd: {it.quantidade})",
                )
            self.repo.commit()
            pedido = self.repo.get(pedido.id, TipoPedido.BALCAO)

        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def adicionar_item(self, pedido_id: int, body: AdicionarItemRequest, usuario_id: int | None = None) -> PedidoResponseCompleto:
        pedido = self.repo.get(pedido_id, TipoPedido.BALCAO)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        pedido = self.repo.add_item(
            pedido_id,
            produto_cod_barras=body.produto_cod_barras,
            quantidade=body.quantidade,
            observacao=body.observacao,
        )
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_pedido=TipoOperacaoPedido.ITEM_ADICIONADO,
            descricao=f"Item adicionado: {body.produto_cod_barras} (qtd: {body.quantidade})",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoPedido.BALCAO)  # Recarrega com itens atualizados
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def adicionar_produto_generico(
        self, 
        pedido_id: int, 
        body: AdicionarProdutoGenericoRequest, 
        usuario_id: int | None = None
    ) -> PedidoResponseCompleto:
        """
        Adiciona um produto genérico ao pedido (produto normal, receita ou combo).
        Identifica automaticamente o tipo baseado nos campos preenchidos.
        """
        pedido = self.repo.get(pedido_id, TipoPedido.BALCAO)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        
        empresa_id = pedido.empresa_id
        qtd = max(int(body.quantidade or 1), 1)
        descricao_historico = ""
        
        # Identifica e processa o tipo de produto
        if body.produto_cod_barras:
            # Item normal (produto com código de barras)
            adicionais_total, adicionais_snapshot = resolve_produto_adicionais(
                adicional_contract=self.adicional_contract,
                produto_cod_barras=body.produto_cod_barras,
                adicionais_request=body.adicionais,
                adicionais_ids=body.adicionais_ids,
                quantidade_item=qtd,
            )
            
            pedido = self.repo.add_item(
                pedido_id,
                produto_cod_barras=body.produto_cod_barras,
                quantidade=qtd,
                observacao=body.observacao,
                adicionais_snapshot=adicionais_snapshot,
            )
            descricao_historico = f"Produto adicionado: {body.produto_cod_barras} (qtd: {qtd})"
            
        elif body.receita_id:
            # Receita - cria item com receita_id
            receita = self.db.query(ReceitaModel).filter(ReceitaModel.id == body.receita_id).first()
            if not receita or not receita.ativo or not receita.disponivel:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    f"Receita {body.receita_id} não encontrada ou inativa"
                )
            if receita.empresa_id != empresa_id:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Receita {body.receita_id} não pertence à empresa {empresa_id}"
                )
            
            preco_rec = _dec(receita.preco_venda)
            
            # Processa adicionais da receita
            adicionais_req = body.adicionais or []
            if body.adicionais_ids:
                # Converte formato legado para novo formato
                from types import SimpleNamespace
                adicionais_req = [
                    SimpleNamespace(adicional_id=ad_id, quantidade=1) 
                    for ad_id in body.adicionais_ids
                ]
            
            # Calcula total de adicionais e monta snapshot
            adicionais_total = Decimal("0")
            adicionais_snapshot = []
            if adicionais_req:
                adicionais_db = (
                    self.db.query(AdicionalModel)
                    .filter(
                        AdicionalModel.id.in_([a.adicional_id for a in adicionais_req if hasattr(a, 'adicional_id')]),
                        AdicionalModel.empresa_id == empresa_id,
                        AdicionalModel.ativo.is_(True),
                    )
                    .all()
                )
                
                for req in adicionais_req:
                    ad_id = getattr(req, "adicional_id", None)
                    if not ad_id:
                        continue
                    qtd_adicional = max(int(getattr(req, "quantidade", 1) or 1), 1)
                    adicional = next((a for a in adicionais_db if a.id == ad_id), None)
                    if not adicional:
                        continue
                    preco_adicional = _dec(adicional.preco)
                    total_adicional = preco_adicional * qtd_adicional * qtd
                    adicionais_total += total_adicional
                    adicionais_snapshot.append({
                        "adicional_id": ad_id,
                        "nome": adicional.nome,
                        "quantidade": qtd_adicional,
                        "preco_unitario": float(preco_adicional),
                        "total": float(total_adicional),
                    })
            
            # Cria item de receita no banco
            preco_unit_com_receita = preco_rec + (adicionais_total / qtd)
            pedido = self.repo.add_item(
                pedido_id,
                receita_id=body.receita_id,
                quantidade=qtd,
                preco_unitario=preco_unit_com_receita,
                observacao=body.observacao,
                produto_descricao_snapshot=receita.nome or receita.descricao,
                adicionais_snapshot=adicionais_snapshot if adicionais_snapshot else None,
            )
            
            descricao_historico = f"Receita adicionada: {receita.nome} (ID: {body.receita_id}, qtd: {qtd})"
            
        elif body.combo_id:
            # Combo
            combo = self.combo_contract.buscar_por_id(body.combo_id) if self.combo_contract else None
            if not combo or not combo.ativo:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    f"Combo {body.combo_id} não encontrado ou inativo"
                )
            if combo.empresa_id != empresa_id:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Combo {body.combo_id} não pertence à empresa {empresa_id}"
                )
            
            preco_combo = _dec(combo.preco_total)
            
            # Processa adicionais do combo
            adicionais_req = body.adicionais or []
            if body.adicionais_ids:
                from types import SimpleNamespace
                adicionais_req = [
                    SimpleNamespace(adicional_id=ad_id, quantidade=1) 
                    for ad_id in body.adicionais_ids
                ]
            
            # Calcula total de adicionais
            adicionais_total = Decimal("0")
            adicionais_snapshot = []
            if adicionais_req:
                adicionais_db = (
                    self.db.query(AdicionalModel)
                    .filter(
                        AdicionalModel.id.in_([a.adicional_id for a in adicionais_req if hasattr(a, 'adicional_id')]),
                        AdicionalModel.empresa_id == empresa_id,
                        AdicionalModel.ativo.is_(True),
                    )
                    .all()
                )
                
                for req in adicionais_req:
                    ad_id = getattr(req, "adicional_id", None)
                    if not ad_id:
                        continue
                    qtd_adicional = max(int(getattr(req, "quantidade", 1) or 1), 1)
                    adicional = next((a for a in adicionais_db if a.id == ad_id), None)
                    if not adicional:
                        continue
                    preco_adicional = _dec(adicional.preco)
                    total_adicional = preco_adicional * qtd_adicional * qtd
                    adicionais_total += total_adicional
                    adicionais_snapshot.append({
                        "adicional_id": ad_id,
                        "nome": adicional.nome,
                        "quantidade": qtd_adicional,
                        "preco_unitario": float(preco_adicional),
                        "total": float(total_adicional),
                    })
            
            # Cria item de combo no banco (um item por combo, não itens individuais)
            preco_unit_combo = preco_combo + (adicionais_total / qtd)
            observacao_completa = f"Combo #{combo.id} - {combo.titulo or combo.descricao}"
            if body.observacao:
                observacao_completa += f" | {body.observacao}"
            
            pedido = self.repo.add_item(
                pedido_id,
                combo_id=body.combo_id,
                quantidade=qtd,
                preco_unitario=preco_unit_combo,
                observacao=observacao_completa,
                produto_descricao_snapshot=combo.titulo or combo.descricao,
                adicionais_snapshot=adicionais_snapshot if adicionais_snapshot else None,
            )
            
            descricao_historico = f"Combo adicionado: {combo.titulo or combo.descricao} (ID: {body.combo_id}, qtd: {qtd})"
        
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "É obrigatório informar 'produto_cod_barras', 'receita_id' ou 'combo_id'"
            )
        
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_pedido=TipoOperacaoPedido.ITEM_ADICIONADO,
            descricao=descricao_historico,
            usuario_id=usuario_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoPedido.BALCAO)  # Recarrega com itens atualizados
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def remover_item(self, pedido_id: int, item_id: int, usuario_id: int | None = None) -> RemoverItemResponse:
        pedido = self.repo.get(pedido_id, TipoPedido.BALCAO)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        pedido = self.repo.remove_item(pedido_id, item_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_pedido=TipoOperacaoPedido.ITEM_REMOVIDO,
            descricao=f"Item removido: ID {item_id}",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return RemoverItemResponse(ok=True, pedido_id=pedido.id, valor_total=float(pedido.valor_total or 0))

    def cancelar(self, pedido_id: int, usuario_id: int | None = None) -> PedidoResponseCompleto:
        pedido_antes = self.repo.get(pedido_id, TipoPedido.BALCAO)
        status_anterior = self._status_value(pedido_antes.status)
        pedido = self.repo.cancelar(pedido_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_pedido=TipoOperacaoPedido.PEDIDO_CANCELADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} cancelado",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoPedido.BALCAO)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def confirmar(self, pedido_id: int, usuario_id: int | None = None) -> PedidoResponseCompleto:
        pedido_antes = self.repo.get(pedido_id, TipoPedido.BALCAO)
        status_anterior = self._status_value(pedido_antes.status)
        pedido = self.repo.confirmar(pedido_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_pedido=TipoOperacaoPedido.PEDIDO_CONFIRMADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} confirmado",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoPedido.BALCAO)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def atualizar_status(
        self,
        pedido_id: int,
        payload: AtualizarStatusPedidoRequest,
        usuario_id: int | None = None
    ) -> PedidoResponseCompleto:
        novo_status = payload.status
        if novo_status == PedidoStatusEnum.CANCELADO:
            return self.cancelar(pedido_id, usuario_id=usuario_id)
        if novo_status == PedidoStatusEnum.ENTREGUE:
            return self.fechar_conta(pedido_id, payload=None, usuario_id=usuario_id)
        if novo_status == PedidoStatusEnum.IMPRESSAO:
            return self.confirmar(pedido_id, usuario_id=usuario_id)

        pedido_atual = self.repo.get(pedido_id)
        status_anterior = self._status_value(pedido_atual.status)
        pedido = self.repo.atualizar_status(pedido_id, novo_status)
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_pedido=TipoOperacaoPedido.STATUS_ALTERADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Status atualizado para {self._status_value(pedido.status)}",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoPedido.BALCAO)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def fechar_conta(self, pedido_id: int, payload: FecharContaBalcaoRequest | None = None, usuario_id: int | None = None) -> PedidoResponseCompleto:
        pedido_antes = self.repo.get(pedido_id, TipoPedido.BALCAO)
        status_anterior = self._status_value(pedido_antes.status)
        mesa_id = pedido_antes.mesa_id  # Guarda mesa_id antes de fechar
        
        # Se receber payload, salva dados de pagamento nos campos diretos
        if payload is not None:
            if payload.troco_para is not None:
                pedido_antes.troco_para = payload.troco_para
            if payload.meio_pagamento_id is not None:
                pedido_antes.meio_pagamento_id = payload.meio_pagamento_id
            self.db.commit()
            self.db.refresh(pedido_antes)

        # Fecha o pedido (muda status para ENTREGUE)
        pedido = self.repo.fechar_conta(pedido_id)
        
        # Se o pedido tinha mesa associada, verifica se há outros pedidos abertos antes de liberar
        if mesa_id is not None:
            # Verifica pedidos abertos de balcão na mesa
            pedidos_balcao_abertos = self.repo.list_abertos_by_mesa(mesa_id, TipoPedido.BALCAO, empresa_id=pedido.empresa_id)
            # Verifica pedidos abertos de mesa na mesa
            from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
            repo_mesa_pedidos = PedidoRepository(self.db, produto_contract=self.produto_contract)
            pedidos_mesa_abertos = repo_mesa_pedidos.list_abertos_by_mesa(mesa_id, TipoPedido.MESA, empresa_id=pedido.empresa_id)
            
            # Só libera a mesa se não houver mais nenhum pedido aberto (nem de balcão nem de mesa)
            if len(pedidos_balcao_abertos) == 0 and len(pedidos_mesa_abertos) == 0:
                mesa = self.repo_mesa.get_by_id(mesa_id)
                if mesa.empresa_id != pedido.empresa_id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mesa não pertence à empresa")
                if mesa.status == StatusMesa.OCUPADA:
                    self.repo_mesa.liberar_mesa(mesa_id, empresa_id=pedido.empresa_id)
        
        # Registra histórico
        observacoes_historico = None
        if payload:
            if payload.meio_pagamento_id:
                observacoes_historico = f"Meio pagamento: {payload.meio_pagamento_id}"
            if payload.troco_para:
                observacoes_historico = (observacoes_historico or "") + f" | Troco para: {payload.troco_para}"
        
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_pedido=TipoOperacaoPedido.PEDIDO_FECHADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} fechado",
            observacoes=observacoes_historico,
            usuario_id=usuario_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoPedido.BALCAO)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def reabrir(self, pedido_id: int, usuario_id: int | None = None) -> PedidoResponseCompleto:
        pedido_antes = self.repo.get(pedido_id, TipoPedido.BALCAO)
        status_anterior = self._status_value(pedido_antes.status)
        pedido = self.repo.reabrir(pedido_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_pedido=TipoOperacaoPedido.PEDIDO_REABERTO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} reaberto",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        pedido = self.repo.get(pedido_id, TipoPedido.BALCAO)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    # -------- Consultas --------
    def get_pedido(self, pedido_id: int) -> PedidoResponseCompleto:
        """
        Busca um pedido de balcão e retorna no formato padronizado.
        
        Segue o padrão definido em PADRAO_RETORNO_PEDIDOS.md:
        - Constrói o campo 'produtos' com itens, receitas e combos
        - Recalcula 'valor_total' incluindo receitas, combos e adicionais
        - Itens ficam apenas dentro de produtos.itens (não na raiz)
        """
        # Busca pedido (o repositório já carrega os itens via joinedload)
        pedido = self.repo.get(pedido_id, TipoPedido.BALCAO)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def list_pedidos_abertos(self, *, empresa_id: Optional[int] = None) -> list[PedidoResponseCompleto]:
        pedidos = self.repo.list_abertos_all(TipoPedido.BALCAO, empresa_id=empresa_id)
        return [PedidoResponseBuilder.pedido_to_response_completo(p) for p in pedidos]

    def list_pedidos_finalizados(self, data_filtro: Optional[date] = None, *, empresa_id: Optional[int] = None) -> list[PedidoResponseCompleto]:
        """Retorna todos os pedidos finalizados (ENTREGUE), opcionalmente filtrando por data"""
        pedidos = self.repo.list_finalizados(TipoPedido.BALCAO, data_filtro, empresa_id=empresa_id)
        return [PedidoResponseBuilder.pedido_to_response_completo(p) for p in pedidos]

    def list_pedidos_by_cliente(self, cliente_id: int, *, empresa_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> list[PedidoResponseCompleto]:
        """Lista todos os pedidos de balcão de um cliente específico"""
        pedidos = self.repo.list_by_cliente_id(cliente_id, empresa_id=empresa_id, skip=skip, limit=limit)
        return [PedidoResponseBuilder.pedido_to_response_completo(p) for p in pedidos]

    # -------- Histórico --------
    def get_historico(self, pedido_id: int, limit: int = 100) -> HistoricoDoPedidoResponse:
        """Busca histórico completo de um pedido de balcão"""
        # Verifica se o pedido existe
        pedido = self.repo.get(pedido_id, TipoPedido.BALCAO)
        
        # Busca histórico
        historicos = self.repo.get_historico(pedido_id, limit)
        
        # Converte para schema unificado
        historicos_out = []
        for h in historicos:
            historico_out = PedidoResponseBuilder.build_historico_response(h)
            historicos_out.append(historico_out)
        
        return HistoricoDoPedidoResponse(
            pedido_id=pedido_id,
            historicos=historicos_out
        )

