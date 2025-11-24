from __future__ import annotations

from decimal import Decimal
from typing import Optional
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.mesas.repositories.repo_mesas import MesaRepository
from app.api.mesas.repositories.repo_pedidos_mesa import PedidoMesaRepository
from app.api.mesas.models.model_mesa import StatusMesa
from app.api.balcao.repositories.repo_pedidos_balcao import PedidoBalcaoRepository
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.catalogo.contracts.adicional_contract import IAdicionalContract
from app.api.catalogo.contracts.combo_contract import IComboContract
from app.api.balcao.models.model_pedido_balcao_historico import TipoOperacaoPedidoBalcao
from app.api.balcao.schemas.schema_pedido_balcao import (
    PedidoBalcaoCreate,
    PedidoBalcaoOut,
    AdicionarItemRequest,
    AdicionarProdutoGenericoRequest,
    RemoverItemResponse,
    StatusPedidoBalcaoEnum,
    FecharContaBalcaoRequest,
    AtualizarStatusPedidoRequest,
)
from app.api.catalogo.models.model_receita import ReceitaModel
from app.api.catalogo.models.model_combo import ComboModel
from app.api.catalogo.models.model_adicional import AdicionalModel
from app.api.balcao.models.model_pedido_balcao_item import PedidoBalcaoItemModel
from app.api.pedidos.utils.adicionais import resolve_produto_adicionais
from app.api.cardapio.services.pedidos.service_pedido_helpers import _dec
from app.api.balcao.schemas.schema_pedido_balcao_historico import (
    PedidoBalcaoHistoricoOut,
    HistoricoPedidoBalcaoResponse,
)


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
        self.repo_mesa_pedidos = PedidoMesaRepository(db, produto_contract=produto_contract)
        self.repo = PedidoBalcaoRepository(db, produto_contract=produto_contract)
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
    def criar_pedido(self, payload: PedidoBalcaoCreate) -> PedidoBalcaoOut:
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

        pedido = self.repo.create(
            empresa_id=payload.empresa_id,
            mesa_id=mesa_id_real,
            cliente_id=payload.cliente_id,
            observacoes=payload.observacoes,
        )

        # Registra histórico de criação
        self.repo.add_historico(
            pedido_id=pedido.id,
            tipo_operacao=TipoOperacaoPedidoBalcao.PEDIDO_CRIADO,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} criado",
            cliente_id=payload.cliente_id,
        )
        if mesa_id_real:
            self.repo.add_historico(
                pedido_id=pedido.id,
                tipo_operacao=TipoOperacaoPedidoBalcao.MESA_ASSOCIADA,
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
                    tipo_operacao=TipoOperacaoPedidoBalcao.ITEM_ADICIONADO,
                    descricao=f"Item adicionado: {it.produto_cod_barras} (qtd: {it.quantidade})",
                )
            self.repo.commit()
            pedido = self.repo.get(pedido.id)

        return PedidoBalcaoOut.model_validate(pedido)

    def adicionar_item(self, pedido_id: int, body: AdicionarItemRequest, usuario_id: int | None = None) -> PedidoBalcaoOut:
        pedido = self.repo.get(pedido_id)
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
            tipo_operacao=TipoOperacaoPedidoBalcao.ITEM_ADICIONADO,
            descricao=f"Item adicionado: {body.produto_cod_barras} (qtd: {body.quantidade})",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return PedidoBalcaoOut.model_validate(pedido)

    def adicionar_produto_generico(
        self, 
        pedido_id: int, 
        body: AdicionarProdutoGenericoRequest, 
        usuario_id: int | None = None
    ) -> PedidoBalcaoOut:
        """
        Adiciona um produto genérico ao pedido (produto normal, receita ou combo).
        Identifica automaticamente o tipo baseado nos campos preenchidos.
        """
        pedido = self.repo.get(pedido_id)
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
            # Receita
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
            
            # Cria item para a receita (usa um código de barras especial ou cria um item genérico)
            # Por enquanto, vamos criar um item com observação indicando que é receita
            # Nota: O modelo atual não suporta receitas diretamente, então vamos criar como item normal
            # com observação especial. Em uma versão futura, pode ser necessário criar uma tabela específica.
            observacao_completa = f"Receita #{receita.id} - {receita.nome}"
            if body.observacao:
                observacao_completa += f" | {body.observacao}"
            
            # Cria item com preço da receita + adicionais
            preco_total_item = preco_rec + (adicionais_total / qtd)
            pedido = self.repo.add_item(
                pedido_id,
                produto_cod_barras=f"RECEITA_{receita.id}",  # Código especial para receitas
                quantidade=qtd,
                observacao=observacao_completa,
                adicionais_snapshot=adicionais_snapshot if adicionais_snapshot else None,
            )
            # Atualiza o preço unitário do item criado para incluir receita + adicionais
            item_criado = (
                self.db.query(PedidoBalcaoItemModel)
                .filter(
                    PedidoBalcaoItemModel.pedido_id == pedido_id,
                    PedidoBalcaoItemModel.produto_cod_barras == f"RECEITA_{receita.id}"
                )
                .order_by(PedidoBalcaoItemModel.id.desc())
                .first()
            )
            if item_criado:
                item_criado.preco_unitario = preco_total_item
                self.db.commit()
            
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
            
            # Distribui preço do combo igualmente pelos itens do combo
            total_unidades = sum(i.quantidade for i in combo.itens) or 1
            preco_unit_medio = preco_combo / total_unidades
            
            # Cria itens do combo
            for item_combo in combo.itens:
                observacao_completa = f"Combo #{combo.id} - {combo.titulo or combo.descricao}"
                if body.observacao:
                    observacao_completa += f" | {body.observacao}"
                
                pedido = self.repo.add_item(
                    pedido_id,
                    produto_cod_barras=item_combo.produto_cod_barras,
                    quantidade=item_combo.quantidade * qtd,
                    observacao=observacao_completa,
                    adicionais_snapshot=adicionais_snapshot if adicionais_snapshot and item_combo == combo.itens[0] else None,
                )
                # Atualiza preço unitário para incluir proporção do combo + adicionais (apenas no primeiro item)
                if item_combo == combo.itens[0]:
                    item_criado = (
                        self.db.query(PedidoBalcaoItemModel)
                        .filter(
                            PedidoBalcaoItemModel.pedido_id == pedido_id,
                            PedidoBalcaoItemModel.produto_cod_barras == item_combo.produto_cod_barras
                        )
                        .order_by(PedidoBalcaoItemModel.id.desc())
                        .first()
                    )
                    if item_criado:
                        # Adiciona proporção dos adicionais ao primeiro item
                        adicionais_por_item = adicionais_total / len(combo.itens) / (item_combo.quantidade * qtd) if combo.itens else Decimal("0")
                        item_criado.preco_unitario = preco_unit_medio + adicionais_por_item
                        self.db.commit()
            
            descricao_historico = f"Combo adicionado: {combo.titulo or combo.descricao} (ID: {body.combo_id}, qtd: {qtd})"
        
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "É obrigatório informar 'produto_cod_barras', 'receita_id' ou 'combo_id'"
            )
        
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedidoBalcao.ITEM_ADICIONADO,
            descricao=descricao_historico,
            usuario_id=usuario_id,
        )
        self.repo.commit()
        
        return PedidoBalcaoOut.model_validate(pedido)

    def remover_item(self, pedido_id: int, item_id: int, usuario_id: int | None = None) -> RemoverItemResponse:
        pedido = self.repo.get(pedido_id)
        if pedido.status in ("C", "E"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido fechado/cancelado")
        pedido = self.repo.remove_item(pedido_id, item_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedidoBalcao.ITEM_REMOVIDO,
            descricao=f"Item removido: ID {item_id}",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return RemoverItemResponse(ok=True, pedido_id=pedido.id, valor_total=float(pedido.valor_total or 0))

    def cancelar(self, pedido_id: int, usuario_id: int | None = None) -> PedidoBalcaoOut:
        pedido_antes = self.repo.get(pedido_id)
        status_anterior = self._status_value(pedido_antes.status)
        pedido = self.repo.cancelar(pedido_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedidoBalcao.PEDIDO_CANCELADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} cancelado",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return PedidoBalcaoOut.model_validate(pedido)

    def confirmar(self, pedido_id: int, usuario_id: int | None = None) -> PedidoBalcaoOut:
        pedido_antes = self.repo.get(pedido_id)
        status_anterior = self._status_value(pedido_antes.status)
        pedido = self.repo.confirmar(pedido_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedidoBalcao.PEDIDO_CONFIRMADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} confirmado",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return PedidoBalcaoOut.model_validate(pedido)

    def atualizar_status(
        self,
        pedido_id: int,
        payload: AtualizarStatusPedidoRequest,
        usuario_id: int | None = None
    ) -> PedidoBalcaoOut:
        novo_status = payload.status
        if novo_status == StatusPedidoBalcaoEnum.CANCELADO:
            return self.cancelar(pedido_id, usuario_id=usuario_id)
        if novo_status == StatusPedidoBalcaoEnum.ENTREGUE:
            return self.fechar_conta(pedido_id, payload=None, usuario_id=usuario_id)
        if novo_status == StatusPedidoBalcaoEnum.IMPRESSAO:
            return self.confirmar(pedido_id, usuario_id=usuario_id)

        pedido_atual = self.repo.get(pedido_id)
        status_anterior = self._status_value(pedido_atual.status)
        pedido = self.repo.atualizar_status(pedido_id, novo_status)
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedidoBalcao.STATUS_ALTERADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Status atualizado para {self._status_value(pedido.status)}",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return PedidoBalcaoOut.model_validate(pedido)

    def fechar_conta(self, pedido_id: int, payload: FecharContaBalcaoRequest | None = None, usuario_id: int | None = None) -> PedidoBalcaoOut:
        pedido_antes = self.repo.get(pedido_id)
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
            pedidos_balcao_abertos = self.repo.list_abertos_by_mesa(mesa_id, empresa_id=pedido.empresa_id)
            # Verifica pedidos abertos de mesa na mesa
            pedidos_mesa_abertos = self.repo_mesa_pedidos.list_abertos_by_mesa(mesa_id, empresa_id=pedido.empresa_id)
            
            # Só libera a mesa se não houver mais nenhum pedido aberto (nem de balcão nem de mesa)
            if len(pedidos_balcao_abertos) == 0 and len(pedidos_mesa_abertos) == 0:
                mesa = self.repo_mesa.get_by_id(mesa_id, empresa_id=pedido.empresa_id)
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
            tipo_operacao=TipoOperacaoPedidoBalcao.PEDIDO_FECHADO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} fechado",
            observacoes=observacoes_historico,
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return PedidoBalcaoOut.model_validate(pedido)

    def reabrir(self, pedido_id: int, usuario_id: int | None = None) -> PedidoBalcaoOut:
        pedido_antes = self.repo.get(pedido_id)
        status_anterior = self._status_value(pedido_antes.status)
        pedido = self.repo.reabrir(pedido_id)
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            tipo_operacao=TipoOperacaoPedidoBalcao.PEDIDO_REABERTO,
            status_anterior=status_anterior,
            status_novo=self._status_value(pedido.status),
            descricao=f"Pedido {pedido.numero_pedido} reaberto",
            usuario_id=usuario_id,
        )
        self.repo.commit()
        return PedidoBalcaoOut.model_validate(pedido)

    # -------- Consultas --------
    def get_pedido(self, pedido_id: int) -> PedidoBalcaoOut:
        """
        Busca um pedido de balcão e retorna no formato padronizado.
        
        Segue o padrão definido em PADRAO_RETORNO_PEDIDOS.md:
        - Constrói o campo 'produtos' com itens, receitas e combos
        - Recalcula 'valor_total' incluindo receitas, combos e adicionais
        """
        from app.api.pedidos.utils.produtos_builder import build_produtos_out_from_items
        
        # Busca pedido (o repositório já carrega os itens via joinedload)
        pedido = self.repo.get(pedido_id)
        
        # Constrói o campo produtos usando a função utilitária
        produtos_snapshot = getattr(pedido, "produtos_snapshot", None)
        produtos = build_produtos_out_from_items(pedido.itens, produtos_snapshot)
        
        # Recalcula valor_total incluindo receitas, combos e adicionais
        # Usa a mesma lógica do repositório
        valor_total_calculado = float(self.repo._calc_total(pedido))
        
        # Constrói a resposta manualmente para garantir que produtos e valor_total estejam corretos
        # O model_validate não constrói corretamente produtos e não recalcula valor_total
        
        # Normaliza status para o enum do schema
        status_str = str(pedido.status) if not isinstance(pedido.status, str) else pedido.status
        status_enum = StatusPedidoBalcaoEnum(status_str) if status_str in [e.value for e in StatusPedidoBalcaoEnum] else StatusPedidoBalcaoEnum.PENDENTE
        
        # Usa a propriedade status_descricao do modelo
        status_descricao = getattr(pedido, "status_descricao", status_str)
        
        pedido_dict = {
            "id": pedido.id,
            "empresa_id": pedido.empresa_id,
            "numero_pedido": pedido.numero_pedido,
            "mesa_id": pedido.mesa_id,
            "cliente_id": pedido.cliente_id,
            "status": status_enum,
            "status_descricao": status_descricao,
            "observacoes": pedido.observacoes,
            "valor_total": valor_total_calculado,  # Valor recalculado
            "itens": pedido.itens or [],
            "created_at": pedido.created_at,
            "updated_at": getattr(pedido, "updated_at", None),
            "produtos": produtos,  # Produtos construídos corretamente
        }
        
        return PedidoBalcaoOut(**pedido_dict)

    def list_pedidos_abertos(self, *, empresa_id: Optional[int] = None) -> list[PedidoBalcaoOut]:
        pedidos = self.repo.list_abertos_all(empresa_id=empresa_id)
        return [PedidoBalcaoOut.model_validate(p) for p in pedidos]

    def list_pedidos_finalizados(self, data_filtro: Optional[date] = None, *, empresa_id: Optional[int] = None) -> list[PedidoBalcaoOut]:
        """Retorna todos os pedidos finalizados (ENTREGUE), opcionalmente filtrando por data"""
        pedidos = self.repo.list_finalizados(data_filtro, empresa_id=empresa_id)
        return [PedidoBalcaoOut.model_validate(p) for p in pedidos]

    def list_pedidos_by_cliente(self, cliente_id: int, *, empresa_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> list[PedidoBalcaoOut]:
        """Lista todos os pedidos de balcão de um cliente específico"""
        pedidos = self.repo.list_by_cliente_id(cliente_id, empresa_id=empresa_id, skip=skip, limit=limit)
        return [PedidoBalcaoOut.model_validate(p) for p in pedidos]

    # -------- Histórico --------
    def get_historico(self, pedido_id: int, limit: int = 100) -> HistoricoPedidoBalcaoResponse:
        """Busca histórico completo de um pedido de balcão"""
        # Verifica se o pedido existe
        pedido = self.repo.get(pedido_id)
        
        # Busca histórico
        historicos = self.repo.get_historico(pedido_id, limit)
        
        # Converte para schema incluindo nome do usuário
        historicos_out = []
        for h in historicos:
            hist_dict = PedidoBalcaoHistoricoOut.model_validate(h).model_dump()
            # Adiciona nome do usuário se disponível
            if h.usuario:
                hist_dict["usuario"] = h.usuario.nome
            historicos_out.append(PedidoBalcaoHistoricoOut(**hist_dict))
        
        return HistoricoPedidoBalcaoResponse(
            pedido_id=pedido_id,
            historicos=historicos_out
        )

