from __future__ import annotations

from decimal import Decimal
from typing import Optional
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.cadastros.models.model_mesa import StatusMesa
from app.api.cadastros.repositories.repo_mesas import MesaRepository
from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.pedidos.models.model_pedido_unificado import TipoEntrega
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.catalogo.contracts.adicional_contract import IAdicionalContract
from app.api.catalogo.contracts.combo_contract import IComboContract
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
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal as PyDecimal


# Schemas de request para pedidos de mesa
class PedidoMesaCreate(BaseModel):
    empresa_id: int
    mesa_id: int  # Código da mesa
    cliente_id: Optional[int] = None
    observacoes: Optional[str] = None
    num_pessoas: Optional[int] = None
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


class FecharContaMesaRequest(BaseModel):
    meio_pagamento_id: Optional[int] = None
    troco_para: Optional[float] = None


class AtualizarObservacoesRequest(BaseModel):
    observacoes: str


class AtualizarStatusPedidoRequest(BaseModel):
    status: PedidoStatusEnum
from app.api.catalogo.models.model_receita import ReceitaModel
from app.api.catalogo.models.model_combo import ComboModel
from app.api.catalogo.models.model_adicional import AdicionalModel
from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
from app.api.pedidos.utils.adicionais import resolve_produto_adicionais
from app.api.pedidos.services.service_pedido_helpers import _dec
from app.utils.logger import logger


class PedidoMesaService:
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

    # -------- Pedido --------
    def criar_pedido(self, payload: PedidoMesaCreate) -> PedidoResponseCompleto:
        # Busca mesa pelo código ao invés do ID
        # payload.mesa_id agora representa o código da mesa
        from decimal import Decimal
        try:
            codigo = Decimal(str(payload.mesa_id))
            mesa = self.repo_mesa.get_by_codigo(codigo, empresa_id=payload.empresa_id)
        except Exception as e:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Mesa com código {payload.mesa_id} não encontrada"
            )
        
        # Usa o ID real da mesa encontrada
        mesa_id_real = mesa.id
        if mesa.empresa_id != payload.empresa_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Mesa não pertence à empresa informada."
            )
        # Valida num_pessoas contra capacidade da mesa, quando informado
        if payload.num_pessoas is not None and payload.num_pessoas > (mesa.capacidade or 0):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Número de pessoas excede a capacidade da mesa"
            )
        # Se a mesa não estiver ocupada, ocupa automaticamente ao abrir o pedido
        if mesa.status != StatusMesa.OCUPADA:
            self.repo_mesa.ocupar_mesa(mesa_id_real, empresa_id=payload.empresa_id)

        pedido = self.repo.criar_pedido_mesa(
            mesa_id=mesa_id_real,
            empresa_id=payload.empresa_id,
            cliente_id=payload.cliente_id,
            observacoes=payload.observacoes,
            num_pessoas=payload.num_pessoas,
        )

        # itens iniciais
        if payload.itens:
            for it in payload.itens:
                self.repo.add_item(
                    pedido.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    observacao=it.observacao,
                )
            pedido = self.repo.get(pedido.id, TipoEntrega.MESA)

        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def adicionar_item(self, pedido_id: int, body: AdicionarItemRequest) -> PedidoResponseCompleto:
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        pedido = self.repo.add_item(
            pedido_id,
            produto_cod_barras=body.produto_cod_barras,
            quantidade=body.quantidade,
            observacao=body.observacao,
        )
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def adicionar_produto_generico(
        self, 
        pedido_id: int, 
        body: AdicionarProdutoGenericoRequest
    ) -> PedidoResponseCompleto:
        """
        Adiciona um produto genérico ao pedido (produto normal, receita ou combo).
        Identifica automaticamente o tipo baseado nos campos preenchidos.
        """
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        
        empresa_id = pedido.empresa_id
        qtd = max(int(body.quantidade or 1), 1)
        
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
            
            observacao_completa = f"Receita #{receita.id} - {receita.nome}"
            if body.observacao:
                observacao_completa += f" | {body.observacao}"
            
            # Cria item de receita no banco
            preco_unit_com_receita = preco_rec + (adicionais_total / qtd)
            pedido = self.repo.add_item(
                pedido_id,
                receita_id=body.receita_id,
                quantidade=qtd,
                preco_unitario=preco_unit_com_receita,
                observacao=observacao_completa,
                produto_descricao_snapshot=receita.nome or receita.descricao,
                adicionais_snapshot=adicionais_snapshot if adicionais_snapshot else None,
            )
            
        elif body.combo_id:
            # Combo - mesma lógica do balcão
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
        
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "É obrigatório informar 'produto_cod_barras', 'receita_id' ou 'combo_id'"
            )
        
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def remover_item(self, pedido_id: int, item_id: int) -> RemoverItemResponse:
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        pedido = self.repo.remove_item(pedido_id, item_id)
        return RemoverItemResponse(ok=True, pedido_id=pedido.id, valor_total=float(pedido.valor_total or 0))

    def cancelar(self, pedido_id: int) -> PedidoResponseCompleto:
        # Obtém o pedido antes de cancelar para pegar o mesa_id
        pedido_antes = self.repo.get(pedido_id, TipoEntrega.MESA)
        mesa_id = pedido_antes.mesa_id
        
        # Cancela o pedido (muda status para CANCELADO)
        pedido = self.repo.cancelar(pedido_id)

        
        # IMPORTANTE: Força refresh da sessão para garantir que a query veja o status atualizado
        self.db.expire_all()
        
        # IMPORTANTE: Não muda o status da mesa imediatamente ao cancelar o pedido
        # Verifica se ainda há outros pedidos abertos nesta mesa (tanto de mesa quanto de balcão)
        # O pedido que acabou de ser cancelado já não será contado (status CANCELADO)
        pedidos_mesa_abertos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.MESA, empresa_id=pedido_antes.empresa_id)
        pedidos_balcao_abertos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.BALCAO, empresa_id=pedido_antes.empresa_id)
        
        logger.info(
            f"[Pedidos Mesa] Cancelar - pedido_id={pedido_id}, mesa_id={mesa_id}, "
            f"pedidos_mesa_abertos={len(pedidos_mesa_abertos)}, pedidos_balcao_abertos={len(pedidos_balcao_abertos)}"
        )
        
        # Só libera a mesa se realmente não houver mais nenhum pedido em aberto (nem de mesa nem de balcão)
        if len(pedidos_mesa_abertos) == 0 and len(pedidos_balcao_abertos) == 0:
            # Verifica se a mesa está ocupada antes de liberar
            mesa = self.repo_mesa.get_by_id(mesa_id)
            if mesa.empresa_id != pedido_antes.empresa_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mesa não pertence à empresa")
            if mesa.status == StatusMesa.OCUPADA:
                logger.info(f"[Pedidos Mesa] Liberando mesa automaticamente (cancelar) - mesa_id={mesa_id} (sem pedidos abertos)")
                self.repo_mesa.liberar_mesa(mesa_id, empresa_id=pedido_antes.empresa_id)
        else:
            logger.info(
                f"[Pedidos Mesa] Mesa NÃO liberada (cancelar) - mesa_id={mesa_id} "
                f"(ainda há {len(pedidos_mesa_abertos)} pedidos de mesa e {len(pedidos_balcao_abertos)} de balcão abertos)"
            )
        
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def confirmar(self, pedido_id: int) -> PedidoResponseCompleto:
        pedido = self.repo.confirmar(pedido_id)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def atualizar_status(self, pedido_id: int, payload: AtualizarStatusPedidoRequest) -> PedidoResponseCompleto:
        novo_status = payload.status
        if novo_status == PedidoStatusEnum.C:
            return self.cancelar(pedido_id)
        if novo_status == PedidoStatusEnum.E:
            return self.fechar_conta(pedido_id, None)
        if novo_status == PedidoStatusEnum.I:
            return self.confirmar(pedido_id)
        pedido = self.repo.atualizar_status(pedido_id, novo_status)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def fechar_conta(self, pedido_id: int, payload: FecharContaMesaRequest | None = None) -> PedidoResponseCompleto:
        # Obtém o pedido antes de fechar para pegar o mesa_id
        pedido_antes = self.repo.get(pedido_id, TipoEntrega.MESA)
        mesa_id = pedido_antes.mesa_id
        
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
        
        # IMPORTANTE: Força refresh da sessão para garantir que a query veja o status atualizado
        self.db.expire_all()
        
        # IMPORTANTE: Não muda o status da mesa imediatamente ao fechar a conta
        # Verifica se ainda há outros pedidos abertos nesta mesa (tanto de mesa quanto de balcão)
        # O pedido que acabou de ser fechado já não será contado (status ENTREGUE)
        pedidos_mesa_abertos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.MESA, empresa_id=pedido_antes.empresa_id)
        pedidos_balcao_abertos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.BALCAO, empresa_id=pedido_antes.empresa_id)
        
        logger.info(
            f"[Pedidos Mesa] Fechar conta - pedido_id={pedido_id}, mesa_id={mesa_id}, "
            f"pedidos_mesa_abertos={len(pedidos_mesa_abertos)}, pedidos_balcao_abertos={len(pedidos_balcao_abertos)}"
        )
        
        # Só libera a mesa se realmente não houver mais nenhum pedido em aberto (nem de mesa nem de balcão)
        if len(pedidos_mesa_abertos) == 0 and len(pedidos_balcao_abertos) == 0:
            # Verifica se a mesa está ocupada antes de liberar
            mesa = self.repo_mesa.get_by_id(mesa_id)
            if mesa.empresa_id != pedido_antes.empresa_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mesa não pertence à empresa")
            if mesa.status == StatusMesa.OCUPADA:
                logger.info(f"[Pedidos Mesa] Liberando mesa automaticamente - mesa_id={mesa_id} (sem pedidos abertos)")
                self.repo_mesa.liberar_mesa(mesa_id, empresa_id=pedido_antes.empresa_id)
        else:
            logger.info(
                f"[Pedidos Mesa] Mesa NÃO liberada - mesa_id={mesa_id} "
                f"(ainda há {len(pedidos_mesa_abertos)} pedidos de mesa e {len(pedidos_balcao_abertos)} de balcão abertos)"
            )
        
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def reabrir(self, pedido_id: int) -> PedidoResponseCompleto:
        pedido = self.repo.reabrir(pedido_id)
        logger.info(f"[Pedidos Mesa] Reabrindo pedido - pedido_id={pedido_id}, novo_status=PENDENTE, mesa_id={pedido.mesa_id}")
        # Ao reabrir o pedido, garantir que a mesa vinculada esteja marcada como OCUPADA
        self.repo_mesa.ocupar_mesa(pedido.mesa_id, empresa_id=pedido.empresa_id)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    # Fluxo cliente
    def fechar_conta_cliente(self, pedido_id: int, cliente_id: int, payload: FecharContaMesaRequest) -> PedidoResponseCompleto:
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        if pedido.cliente_id and pedido.cliente_id != cliente_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Pedido não pertence ao cliente")

        # Salva dados de pagamento nos campos diretos
        if payload.troco_para is not None:
            pedido.troco_para = payload.troco_para
        if payload.meio_pagamento_id is not None:
            pedido.meio_pagamento_id = payload.meio_pagamento_id

        self.db.commit()
        self.db.refresh(pedido)

        # Obtém o mesa_id antes de fechar
        mesa_id = pedido.mesa_id

        # Fecha pedido (muda status para ENTREGUE)
        pedido = self.repo.fechar_conta(pedido_id)
        
        # IMPORTANTE: Força refresh da sessão para garantir que a query veja o status atualizado
        self.db.expire_all()
        
        # IMPORTANTE: Não muda o status da mesa imediatamente ao fechar a conta
        # Verifica se ainda há outros pedidos abertos nesta mesa (tanto de mesa quanto de balcão)
        pedidos_mesa_abertos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.MESA, empresa_id=pedido.empresa_id)
        pedidos_balcao_abertos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.BALCAO, empresa_id=pedido.empresa_id)
        
        logger.info(
            f"[Pedidos Mesa] Fechar conta cliente - pedido_id={pedido_id}, mesa_id={mesa_id}, "
            f"pedidos_mesa_abertos={len(pedidos_mesa_abertos)}, pedidos_balcao_abertos={len(pedidos_balcao_abertos)}"
        )
        
        # Só libera a mesa se realmente não houver mais nenhum pedido em aberto (nem de mesa nem de balcão)
        if len(pedidos_mesa_abertos) == 0 and len(pedidos_balcao_abertos) == 0:
            # Verifica se a mesa está ocupada antes de liberar
            mesa = self.repo_mesa.get_by_id(mesa_id)
            if mesa.empresa_id != pedido.empresa_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mesa não pertence à empresa")
            if mesa.status == StatusMesa.OCUPADA:
                logger.info(f"[Pedidos Mesa] Liberando mesa automaticamente (cliente) - mesa_id={mesa_id} (sem pedidos abertos)")
                self.repo_mesa.liberar_mesa(mesa_id, empresa_id=pedido.empresa_id)
        else:
            logger.info(
                f"[Pedidos Mesa] Mesa NÃO liberada (cliente) - mesa_id={mesa_id} "
                f"(ainda há {len(pedidos_mesa_abertos)} pedidos de mesa e {len(pedidos_balcao_abertos)} de balcão abertos)"
            )
        
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    # -------- Consultas --------
    def get_pedido(self, pedido_id: int) -> PedidoResponseCompleto:
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)

    def list_pedidos_abertos(self, empresa_id: int, mesa_id: Optional[int] = None) -> list[PedidoResponseCompleto]:
        if mesa_id is not None:
            pedidos = self.repo.list_abertos_by_mesa(mesa_id, TipoEntrega.MESA, empresa_id=empresa_id)
        else:
            pedidos = self.repo.list_abertos_all(TipoEntrega.MESA, empresa_id=empresa_id)
        return [PedidoResponseBuilder.pedido_to_response_completo(p) for p in pedidos]

    def list_pedidos_finalizados(self, mesa_id: int, data_filtro: Optional[date] = None, *, empresa_id: int) -> list[PedidoResponseCompleto]:
        """Retorna todos os pedidos finalizados (ENTREGUE) de uma mesa, opcionalmente filtrando por data"""
        # Valida se a mesa existe
        mesa = self.repo_mesa.get_by_id(mesa_id)
        if mesa.empresa_id != empresa_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mesa não pertence à empresa")
        pedidos = self.repo.list_finalizados(TipoEntrega.MESA, data_filtro, empresa_id=empresa_id, mesa_id=mesa_id)
        return [PedidoResponseBuilder.pedido_to_response_completo(p) for p in pedidos]

    def list_pedidos_by_cliente(self, cliente_id: int, *, empresa_id: int, skip: int = 0, limit: int = 50) -> list[PedidoResponseCompleto]:
        """Lista todos os pedidos de mesa/balcão de um cliente específico"""
        pedidos = self.repo.list_by_cliente_id(cliente_id, TipoEntrega.MESA, skip=skip, limit=limit, empresa_id=empresa_id)
        return [PedidoResponseBuilder.pedido_to_response_completo(p) for p in pedidos]

    def atualizar_observacoes(self, pedido_id: int, payload: AtualizarObservacoesRequest) -> PedidoResponseCompleto:
        """Atualiza as observações de um pedido"""
        pedido = self.repo.get(pedido_id, TipoEntrega.MESA)
        pedido.observacoes = payload.observacoes
        self.db.commit()
        self.db.refresh(pedido)
        return PedidoResponseBuilder.pedido_to_response_completo(pedido)


