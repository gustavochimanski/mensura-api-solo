"""
Service unificado para pedids.
"""
from __future__ import annotations

from typing import Optional, List
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.pedidos.models.model_pedido_unificado import TipoEntrega, StatusPedido
from app.api.pedidos.schemas.schema_pedido import (
    PedidoCreate,
    PedidoOut,
    PedidoUpdate,
    PedidoItemIn,
    StatusPedidoEnum,
)
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.pedidos.utils.helpers import enum_value


class PedidoService:
    """Service unificado para todos os tipos de pedids."""
    
    def __init__(self, db: Session, produto_contract: IProdutoContract | None = None):
        self.db = db
        self.produto_contract = produto_contract
        self.repo = PedidoRepository(db, produto_contract=produto_contract)

    # -------- CRUD --------
    def criar_pedido(self, payload: PedidoCreate, usuario_id: Optional[int] = None) -> PedidoOut:
        """Cria um novo pedido."""
        # Prepara dados para criação
        data = payload.model_dump(exclude={"itens"}, exclude_none=True)
        
        # Cria o pedido
        pedido = self.repo.create(**data)
        
        # Registra histórico de criação
        self.repo.add_historico(
            pedido_id=pedido.id,
            status_novo=enum_value(pedido.status),
            observacao=f"Pedido {pedido.numero_pedido} criado",
            usuario_id=usuario_id
        )
        
        # Adiciona itens se fornecidos
        if payload.itens:
            for item_in in payload.itens:
                self.adicionar_item(
                    pedido_id=pedido.id,
                    item=item_in,
                    usuario_id=usuario_id
                )
        
        self.repo.commit()
        
        # Atualiza pedido após adicionar itens
        pedido = self.repo.get(pedido.id)
        return PedidoOut.model_validate(pedido)

    def get_pedido(self, pedido_id: int) -> PedidoOut:
        """Busca um pedido por ID."""
        pedido = self.repo.get(pedido_id)
        return PedidoOut.model_validate(pedido)

    def atualizar_pedido(
        self,
        pedido_id: int,
        payload: PedidoUpdate,
        usuario_id: Optional[int] = None
    ) -> PedidoOut:
        """Atualiza um pedido existente."""
        pedido_antes = self.repo.get(pedido_id)
        status_anterior = enum_value(pedido_antes.status)
        
        # Prepara dados para atualização
        data = payload.model_dump(exclude_none=True)
        
        # Se está atualizando status, registra histórico
        novo_status = data.get("status")
        if novo_status:
            novo_status_value = enum_value(novo_status)
            data["status"] = novo_status_value
            
            self.repo.add_historico(
                pedido_id=pedido_id,
                status_anterior=status_anterior,
                status_novo=novo_status_value,
                observacao=f"Status atualizado para {novo_status_value}",
                usuario_id=usuario_id
            )
        
        pedido = self.repo.update(pedido_id, **data)
        self.repo.commit()
        
        return PedidoOut.model_validate(pedido)

    # -------- Itens --------
    def adicionar_item(
        self,
        pedido_id: int,
        item: PedidoItemIn,
        usuario_id: Optional[int] = None
    ) -> PedidoOut:
        """Adiciona um item ao pedido."""
        pedido = self.repo.get(pedido_id)
        
        if pedido.status in (StatusPedido.CANCELADO.value, StatusPedido.ENTREGUE.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível adicionar itens a um pedido fechado/cancelado"
            )
        
        # Prepara dados do item
        item_data = item.model_dump(exclude_none=True)
        quantidade = item_data.get("quantidade", 1)
        
        # Busca informações do produto/combo se necessário
        nome_item = "Item"
        descricao_item = None
        preco_unitario = Decimal("0")
        
        # Se tem produto_id, busca pelo ID (futuro)
        if item_data.get("produto_id"):
            # TODO: Implementar busca por produto_id quando necessário
            pass
        
        # Se tem produto_cod_barras, busca pelo código de barras
        if item_data.get("produto_cod_barras") and self.produto_contract:
            pe_dto = self.produto_contract.obter_produto_emp_por_cod(
                pedido.empresa_id,
                item_data["produto_cod_barras"]
            )
            if not pe_dto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Produto não encontrado"
                )
            if not pe_dto.disponivel or not (pe_dto.produto and bool(pe_dto.produto.ativo)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Produto indisponível"
                )
            preco_unitario = Decimal(str(pe_dto.preco_venda or 0))
            if pe_dto.produto:
                nome_item = pe_dto.produto.descricao or "Item"
                descricao_item = pe_dto.produto.descricao
        
        # Se não encontrou preço e não foi informado, retorna erro
        if preco_unitario == 0 and not item_data.get("preco_unitario"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Preço unitário não informado e produto não encontrado"
            )
        
        # Usa preço informado ou o encontrado
        preco_unitario = Decimal(str(item_data.get("preco_unitario", preco_unitario)))
        
        # Adiciona nome e descrição ao item_data
        item_data["nome"] = item_data.get("nome") or nome_item
        item_data["descricao"] = item_data.get("descricao") or descricao_item
        item_data["preco_unitario"] = preco_unitario
        
        # Serializa adicionais se houver
        if item_data.get("adicionais"):
            import json
            item_data["adicionais"] = json.dumps(item_data["adicionais"])
        
        pedido = self.repo.add_item(pedido_id, **item_data)
        
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            observacao=f"Item adicionado: {item_data.get('nome', 'N/A')} (qtd: {quantidade})",
            usuario_id=usuario_id
        )
        
        self.repo.commit()
        return PedidoOut.model_validate(pedido)

    def remover_item(
        self,
        pedido_id: int,
        item_id: int,
        usuario_id: Optional[int] = None
    ) -> PedidoOut:
        """Remove um item do pedido."""
        pedido = self.repo.remove_item(pedido_id, item_id)
        
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            observacao=f"Item removido: ID {item_id}",
            usuario_id=usuario_id
        )
        
        self.repo.commit()
        return PedidoOut.model_validate(pedido)

    # -------- Fluxo Pedido --------
    def cancelar_pedido(self, pedido_id: int, usuario_id: Optional[int] = None) -> PedidoOut:
        """Cancela um pedido."""
        pedido_antes = self.repo.get(pedido_id)
        status_anterior = enum_value(pedido_antes.status)
        
        pedido = self.repo.cancelar(pedido_id)
        
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            status_anterior=status_anterior,
            status_novo=enum_value(pedido.status),
            observacao=f"Pedido {pedido.numero_pedido} cancelado",
            usuario_id=usuario_id
        )
        
        self.repo.commit()
        return PedidoOut.model_validate(pedido)

    def finalizar_pedido(self, pedido_id: int, usuario_id: Optional[int] = None) -> PedidoOut:
        """Finaliza um pedido (marca como entregue)."""
        pedido_antes = self.repo.get(pedido_id)
        status_anterior = enum_value(pedido_antes.status)
        
        pedido = self.repo.finalizar(pedido_id)
        
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            status_anterior=status_anterior,
            status_novo=enum_value(pedido.status),
            observacao=f"Pedido {pedido.numero_pedido} finalizado",
            usuario_id=usuario_id
        )
        
        self.repo.commit()
        return PedidoOut.model_validate(pedido)

    def atualizar_status(
        self,
        pedido_id: int,
        novo_status: StatusPedidoEnum,
        usuario_id: Optional[int] = None
    ) -> PedidoOut:
        """Atualiza o status do pedido."""
        pedido_antes = self.repo.get(pedido_id)
        status_anterior = enum_value(pedido_antes.status)
        
        novo_status_value = enum_value(novo_status)
        
        pedido = self.repo.atualizar_status(pedido_id, novo_status_value)
        
        # Registra histórico
        self.repo.add_historico(
            pedido_id=pedido_id,
            status_anterior=status_anterior,
            status_novo=novo_status_value,
            observacao=f"Status atualizado para {novo_status_value}",
            usuario_id=usuario_id
        )
        
        self.repo.commit()
        return PedidoOut.model_validate(pedido)

    # -------- Consultas --------
    def list_pedidos_abertos(
        self,
        *,
        empresa_id: Optional[int] = None,
        tipo_pedido: Optional[str] = None
    ) -> List[PedidoOut]:
        """Lista todos os pedidos abertos."""
        pedidos = self.repo.list_abertos(empresa_id=empresa_id, tipo_pedido=tipo_pedido)
        return [PedidoOut.model_validate(p) for p in pedidos]

    def list_pedidos_finalizados(
        self,
        data_filtro: Optional[date] = None,
        *,
        empresa_id: Optional[int] = None,
        tipo_pedido: Optional[str] = None
    ) -> List[PedidoOut]:
        """Lista pedidos finalizados, opcionalmente filtrando por data."""
        if data_filtro is None:
            data_filtro = date.today()
        
        pedidos = self.repo.list_finalizados(
            data_filtro,
            empresa_id=empresa_id,
            tipo_pedido=tipo_pedido
        )
        return [PedidoOut.model_validate(p) for p in pedidos]

    def list_pedidos_by_cliente(
        self,
        cliente_id: int,
        *,
        empresa_id: Optional[int] = None,
        tipo_pedido: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[PedidoOut]:
        """Lista pedidos de um cliente específico."""
        pedidos = self.repo.list_by_cliente(
            cliente_id,
            empresa_id=empresa_id,
            tipo_pedido=tipo_pedido,
            skip=skip,
            limit=limit
        )
        return [PedidoOut.model_validate(p) for p in pedidos]

    def list_pedidos_by_tipo(
        self,
        tipo_pedido: str,
        *,
        empresa_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[PedidoOut]:
        """Lista pedidos filtrados por tipo."""
        pedidos = self.repo.list_by_tipo(
            tipo_pedido,
            empresa_id=empresa_id,
            status=status,
            skip=skip,
            limit=limit
        )
        return [PedidoOut.model_validate(p) for p in pedidos]

    def get_historico(self, pedido_id: int, limit: int = 100):
        """Busca histórico completo de um pedido."""
        # Verifica se o pedido existe
        pedido = self.repo.get(pedido_id)
        
        # Busca histórico
        historicos = self.repo.get_historico(pedido_id, limit)
        
        # Converte para dicionário incluindo nome do usuário
        historicos_out = []
        for h in historicos:
            hist_dict = {
                "id": h.id,
                "pedido_id": h.pedido_id,
                "status_anterior": h.status_anterior,
                "status_novo": h.status_novo,
                "observacao": h.observacao,
                "usuario_id": h.usuario_id,
                "usuario_nome": h.usuario.nome if h.usuario else None,
                "created_at": h.created_at
            }
            historicos_out.append(hist_dict)
        
        return {
            "pedido_id": pedido_id,
            "historicos": historicos_out
        }

