from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
import re

from fastapi import HTTPException
from starlette import status as http_status
from sqlalchemy import func, or_, and_, text
from sqlalchemy.orm import Session, joinedload, defer, selectinload
from sqlalchemy.exc import IntegrityError

from app.api.cadastros.models.model_mesa import MesaModel
from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
from app.api.pedidos.models.model_pedido_unificado import (
    PedidoUnificadoModel,
    TipoEntrega,
    StatusPedido,
)
from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
from app.api.pedidos.models.model_pedido_historico_unificado import (
    PedidoHistoricoUnificadoModel,
    TipoOperacaoPedido,
)
from app.api.cadastros.models.model_cupom import CupomDescontoModel
from app.api.cadastros.models.model_endereco_dv import EnderecoModel
from app.api.cadastros.models.model_cliente_dv import ClienteModel
from app.api.cardapio.models.model_transacao_pagamento_dv import TransacaoPagamentoModel
from app.api.catalogo.contracts.produto_contract import IProdutoContract, ProdutoEmpDTO
from app.utils.telefone import variantes_telefone_para_busca


# Status abertos para balcão e mesa (mesmos valores)
OPEN_STATUS_PEDIDO_BALCAO_MESA = [
    StatusPedido.PENDENTE.value,
    StatusPedido.IMPRESSAO.value,
    StatusPedido.PREPARANDO.value,
    StatusPedido.EDITADO.value,
    StatusPedido.EM_EDICAO.value,
    StatusPedido.AGUARDANDO_PAGAMENTO.value,
]

# Status abertos para delivery (inclui "Saiu para entrega")
OPEN_STATUS_PEDIDO_DELIVERY = [
    StatusPedido.PENDENTE.value,
    StatusPedido.IMPRESSAO.value,
    StatusPedido.PREPARANDO.value,
    StatusPedido.SAIU_PARA_ENTREGA.value,
    StatusPedido.EDITADO.value,
    StatusPedido.EM_EDICAO.value,
    StatusPedido.AGUARDANDO_PAGAMENTO.value,
]

# Status abertos para todos os tipos de pedido
OPEN_STATUS_PEDIDO_ALL = list(set(OPEN_STATUS_PEDIDO_BALCAO_MESA + OPEN_STATUS_PEDIDO_DELIVERY))


class PedidoRepository:
    def __init__(self, db: Session, produto_contract: IProdutoContract | None = None):
        self.db = db
        self.produto_contract = produto_contract

    # ------------- Número de pedido (concorrência segura) -------------
    def _advisory_lock_numero_pedido(self, *, empresa_id: int, lock_code: int) -> None:
        """
        Serializa a geração de numero_pedido por empresa/canal usando pg_advisory_xact_lock.
        O lock é liberado automaticamente no COMMIT/ROLLBACK.
        """
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(:empresa_id, :lock_code)"),
            {"empresa_id": int(empresa_id), "lock_code": int(lock_code)},
        )

    def _next_numero_prefixado(
        self,
        *,
        empresa_id: int,
        tipo_entrega: str,
        prefixo: str,
        width: int,
        lock_code: int,
        extra_filters: list | None = None,
    ) -> str:
        """
        Próximo numero_pedido no formato '{prefixo}-{seq:0{width}d}' de forma segura:
        - pg_advisory_xact_lock
        - MAX(numero_pedido) + 1 (funciona bem com padding fixo)
        """
        self._advisory_lock_numero_pedido(empresa_id=empresa_id, lock_code=lock_code)

        q = (
            self.db.query(func.max(PedidoUnificadoModel.numero_pedido))
            .filter(
                PedidoUnificadoModel.empresa_id == empresa_id,
                PedidoUnificadoModel.tipo_entrega == tipo_entrega,
                PedidoUnificadoModel.numero_pedido.like(f"{prefixo}-%"),
            )
        )
        for f in extra_filters or []:
            q = q.filter(f)

        max_numero: str | None = q.scalar()
        seq_atual = 0
        if max_numero:
            try:
                seq_atual = int(max_numero.split("-", 1)[1])
            except Exception:
                seq_atual = 0

        return f"{prefixo}-{(seq_atual + 1):0{width}d}"

    # ------------- Geração por sequence (opção B) -------------
    def _seq_name(self, empresa_id: int, prefix: str) -> str:
        """Gera um nome seguro de sequence a partir de empresa_id e prefixo."""
        prefix_clean = re.sub(r"[^0-9A-Za-z_]", "_", str(prefix)).lower()
        return f"pedido_num_seq_{empresa_id}_{prefix_clean}"

    def _ensure_sequence_exists(self, seq_name: str) -> None:
        """Cria a sequence no schema pedidos se não existir."""
        # Identificadores não podem ser bind params, mas seq_name é construído internamente (int + sanitized prefix)
        self.db.execute(text(f"CREATE SEQUENCE IF NOT EXISTS pedidos.{seq_name} START 1"))

    def _next_numero_via_sequence(self, *, empresa_id: int, prefixo: str, width: int) -> str:
        """
        Obtém nextval de uma sequence por empresa/prefixo e formata o numero.
        Sequências são atômicas no BD e previnem colisões sem advisory locks.
        """
        seq_name = self._seq_name(empresa_id, prefixo)
        self._ensure_sequence_exists(seq_name)
        nextv = self.db.execute(text(f"SELECT nextval('pedidos.{seq_name}')")).scalar()
        seq = int(nextv)
        return f"{prefixo}-{seq:0{width}d}"

    # ------------- Validations / Queries -------------
    def get_cliente(self, telefone: str) -> Optional[ClienteModel]:
        candidatos = variantes_telefone_para_busca(telefone)
        if not candidatos:
            return None
        return (
            self.db.query(ClienteModel)
            .filter(ClienteModel.telefone.in_(candidatos))
            .first()
        )

    def get_cliente_by_id(self, id: int) -> Optional[ClienteModel]:
        return self.db.query(ClienteModel).filter(ClienteModel.id == id).first()

    def get_endereco(self, endereco_id: int) -> Optional[EnderecoModel]:
        return self.db.get(EnderecoModel, endereco_id)

    def get_produto_emp(self, empresa_id: int, cod_barras: str) -> Optional[ProdutoEmpModel]:
        return (
            self.db.query(ProdutoEmpModel)
            .options(joinedload(ProdutoEmpModel.produto))
            .filter(
                ProdutoEmpModel.empresa_id == empresa_id,
                ProdutoEmpModel.cod_barras == cod_barras,
            )
            .first()
        )

    def get_cupom(self, cupom_id: int) -> Optional[CupomDescontoModel]:
        return self.db.get(CupomDescontoModel, cupom_id)

    def get_pedido(self, pedido_id: int, tipo_entrega: TipoEntrega | None = None) -> Optional[PedidoUnificadoModel]:
        """Busca um pedido por ID. Se tipo_entrega for fornecido, filtra por tipo."""
        from app.api.pedidos.models.model_pedido_item_complemento import PedidoItemComplementoModel
        from app.api.pedidos.models.model_pedido_item_complemento_adicional import (
            PedidoItemComplementoAdicionalModel,
        )
        query = (
            self.db.query(PedidoUnificadoModel)
            .options(
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .selectinload(PedidoItemComplementoModel.adicionais),
                # Carrega o complemento do catálogo para expor obrigatorio/quantitativo no response
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .joinedload(PedidoItemComplementoModel.complemento),
                # Carrega o adicional do catálogo para expor nome no response
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .selectinload(PedidoItemComplementoModel.adicionais)
                .joinedload(PedidoItemComplementoAdicionalModel.adicional),
                joinedload(PedidoUnificadoModel.cliente).joinedload(ClienteModel.enderecos),
                joinedload(PedidoUnificadoModel.endereco),
                joinedload(PedidoUnificadoModel.mesa),
                joinedload(PedidoUnificadoModel.meio_pagamento),
                # Fonte da verdade (múltiplos meios): transacoes[]
                # Evita SAWarning do SQLAlchemy ao eager-load de `transacao` (singular) quando existir >1 transação.
                joinedload(PedidoUnificadoModel.transacoes).joinedload(TransacaoPagamentoModel.meio_pagamento),
                joinedload(PedidoUnificadoModel.historico),
            )
            .filter(PedidoUnificadoModel.id == pedido_id)
        )
        if tipo_entrega:
            query = query.filter(PedidoUnificadoModel.tipo_entrega == tipo_entrega.value)
        return query.first()
    
    def get(self, pedido_id: int, tipo_entrega: TipoEntrega) -> PedidoUnificadoModel:
        """Busca um pedido por ID e tipo, lança exceção se não encontrar."""
        pedido = self.get_pedido(pedido_id, tipo_entrega)
        if not pedido:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        return pedido

    def get_by_cliente_id(self, cliente_id: int) -> list[PedidoUnificadoModel]:
        """Busca todos os pedidos de um cliente específico"""
        return (
            self.db.query(PedidoUnificadoModel)
            .filter(
                PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value,
                PedidoUnificadoModel.cliente_id == cliente_id
            )
            .all()
        )

    def list_pedidos_em_rota_por_entregador(self, entregador_id: int) -> list[PedidoUnificadoModel]:
        """Retorna pedidos de delivery vinculados ao entregador com status 'Saiu para entrega'."""
        return (
            self.db.query(PedidoUnificadoModel)
            .options(
                joinedload(PedidoUnificadoModel.cliente),
                joinedload(PedidoUnificadoModel.endereco),
            )
            .filter(
                PedidoUnificadoModel.entregador_id == entregador_id,
                PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value,
                PedidoUnificadoModel.status == StatusPedido.SAIU_PARA_ENTREGA.value,
            )
            .order_by(PedidoUnificadoModel.updated_at.asc())
            .all()
        )

    def list_all_kanban(self, date_filter: date, empresa_id: int = 1, limit: int = 500):
        from app.api.shared.schemas.schema_shared_enums import PedidoStatusEnum
        
        # date_filter é sempre obrigatório
        start_dt = datetime.combine(date_filter, datetime.min.time())
        end_dt = start_dt + timedelta(days=1)
        
        query = self.db.query(PedidoUnificadoModel).filter(
            PedidoUnificadoModel.empresa_id == empresa_id,
            PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value
        )
        
        # Busca apenas pedidos CRIADOS naquele dia (qualquer status, exceto cancelados)
        # Isso evita trazer pedidos antigos que foram apenas atualizados no dia
        query = query.filter(
            PedidoUnificadoModel.created_at >= start_dt,
            PedidoUnificadoModel.created_at < end_dt
        )

        query = query.options(
            joinedload(PedidoUnificadoModel.cliente).joinedload(ClienteModel.enderecos),
            joinedload(PedidoUnificadoModel.endereco),
            joinedload(PedidoUnificadoModel.entregador),
            joinedload(PedidoUnificadoModel.meio_pagamento),
            # Fonte da verdade (múltiplos meios): transacoes[]
            # Evita SAWarning do SQLAlchemy ao eager-load de `transacao` (singular) quando existir >1 transação.
            joinedload(PedidoUnificadoModel.transacoes).joinedload(TransacaoPagamentoModel.meio_pagamento),
            selectinload(PedidoUnificadoModel.historico).defer(PedidoHistoricoUnificadoModel.tipo_operacao),
        )

        query = query.order_by(PedidoUnificadoModel.created_at.desc())

        return query.limit(limit).all()

    # -------------------- Mutations -------------------
    # -------------------- Helpers para cálculos -------------------
    def _sum_complementos_total_relacional(self, item: PedidoItemUnificadoModel) -> Decimal:
        """
        Soma totais de complementos usando o modelo relacional.
        """
        total = Decimal("0")

        complementos_rel = getattr(item, "complementos", None) or []
        for comp in complementos_rel:
            try:
                comp_total = Decimal(str(getattr(comp, "total", 0) or 0))
                # Blindagem: se `comp.total` estiver zerado/desatualizado, soma a partir dos adicionais.
                # Isso evita cenários onde o complemento foi atualizado mas o agregado não foi recalculado.
                if comp_total == 0:
                    adicionais_rel = getattr(comp, "adicionais", None) or []
                    for ad in adicionais_rel:
                        try:
                            comp_total += Decimal(str(getattr(ad, "total", 0) or 0))
                        except Exception:
                            continue
                total += comp_total
            except Exception:
                continue

        return total

    def _calc_item_total(self, item: PedidoItemUnificadoModel) -> Decimal:
        """Calcula o total de um item incluindo adicionais."""
        total = (item.preco_unitario or Decimal("0")) * (item.quantidade or 0)
        total += self._sum_complementos_total_relacional(item)
        return total

    def _calc_total(self, pedido: PedidoUnificadoModel) -> Decimal:
        """Calcula o total do pedido somando todos os itens e seus adicionais."""
        total = Decimal("0")
        for item in pedido.itens:
            item_total = self._calc_item_total(item)
            total += item_total
        return total

    def _refresh_total(self, pedido: PedidoUnificadoModel) -> PedidoUnificadoModel:
        """Recalcula e atualiza o valor_total do pedido."""
        pedido.valor_total = self._calc_total(pedido)
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    # -------------------- Mutations -------------------
    def criar_pedido(
        self,
        *,
        cliente_id: int | None,
        empresa_id: int,
        endereco_id: int | None,
        meio_pagamento_id: int,
        status: str = "I",
        tipo_entrega: str,
        origem: str,
        endereco_snapshot: dict | None = None,
        endereco_geo = None,
    ) -> PedidoUnificadoModel:
        """Cria um pedido de delivery (mantido para compatibilidade)."""
        return self.criar_pedido_delivery(
            cliente_id=cliente_id,
            empresa_id=empresa_id,
            endereco_id=endereco_id,
            meio_pagamento_id=meio_pagamento_id,
            status=status,
            tipo_entrega=tipo_entrega,
            origem=origem,
            endereco_snapshot=endereco_snapshot,
            endereco_geo=endereco_geo,
        )

    def criar_pedido_delivery(
        self,
        *,
        cliente_id: int | None,
        empresa_id: int,
        endereco_id: int | None,
        meio_pagamento_id: int,
        status: str = "I",
        tipo_entrega: str,
        origem: str,
        endereco_snapshot: dict | None = None,
        endereco_geo = None,
    ) -> PedidoUnificadoModel:
        """Cria um pedido de delivery."""
        # Gera número único de pedido: DV-{sequencial} por empresa (concorrência segura)
        # Usa sequence por empresa/prefixo para evitar colisões (Opção B)
        numero = self._next_numero_via_sequence(empresa_id=empresa_id, prefixo="DV", width=6)
        
        pedido = PedidoUnificadoModel(
            tipo_entrega=TipoEntrega.DELIVERY.value,
            empresa_id=empresa_id,
            cliente_id=int(cliente_id) if cliente_id is not None else None,
            endereco_id=endereco_id,
            meio_pagamento_id=meio_pagamento_id,
            numero_pedido=numero,
            status=status,
            canal=origem,  # Mapeia origem para canal (WEB, APP, BALCAO)
            endereco_snapshot=endereco_snapshot,
            endereco_geo=endereco_geo,
            subtotal=Decimal("0"),
            desconto=Decimal("0"),
            taxa_entrega=Decimal("0"),
            taxa_servico=Decimal("0"),
            valor_total=Decimal("0"),
        )
        # Commit/flush com retry para cobrir colisões de numero_pedido (concorrência externa)
        max_tentativas = 5
        for _ in range(max_tentativas):
            try:
                self.db.add(pedido)
                self.db.flush()
                self.add_status_historico(pedido.id, status, motivo="Pedido criado")
                return pedido
            except IntegrityError as exc:
                # Rollback da transação atual para limpar estado do session
                self.db.rollback()
                orig = getattr(exc, "orig", None)
                msg = str(orig) if orig is not None else str(exc)
                # Se foi colisão no unique (numero_pedido), gera novo número e tenta novamente
                if "uq_pedidos_empresa_numero" in msg or "UniqueViolation" in msg:
                    pedido.numero_pedido = self._next_numero_prefixado(
                        empresa_id=empresa_id,
                        tipo_entrega=TipoEntrega.DELIVERY.value,
                        prefixo="DV",
                        width=6,
                        lock_code=1001,
                    )
                    continue
                # Re-raise para outros tipos de IntegrityError
                raise
        raise HTTPException(
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Não foi possível criar o pedido de delivery (colisão de numero_pedido).",
        )

    def criar_pedido_balcao(
        self,#
        *,
        empresa_id: int,
        mesa_id: Optional[int],
        cliente_id: int,
        observacoes: Optional[str],
        meio_pagamento_id: Optional[int] = None,
    ) -> PedidoUnificadoModel:
        """Cria um pedido de balcão."""
        # Valida mesa se informada
        if mesa_id is not None:
            mesa = self.db.query(MesaModel).filter(MesaModel.id == mesa_id).first()
            if not mesa:
                raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Mesa não encontrada")
            if mesa.empresa_id != empresa_id:
                raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "Mesa não pertence à empresa informada")

        # Gera número único de pedido: BAL-{sequencial} por empresa (concorrência segura)
        # Usa sequence por empresa/prefixo para balcão
        numero = self._next_numero_via_sequence(empresa_id=empresa_id, prefixo="BAL", width=6)

        pedido = PedidoUnificadoModel(
            tipo_entrega=TipoEntrega.BALCAO.value,
            empresa_id=empresa_id,
            mesa_id=mesa_id,
            cliente_id=cliente_id,
            meio_pagamento_id=meio_pagamento_id,
            numero_pedido=numero,
            observacoes=observacoes,
            status=StatusPedido.IMPRESSAO.value,
            subtotal=Decimal("0"),
            desconto=Decimal("0"),
            taxa_entrega=Decimal("0"),
            taxa_servico=Decimal("0"),
            valor_total=Decimal("0"),
        )
        # Commit com retry para cobrir concorrência com processos antigos/externos
        max_tentativas = 5
        for _ in range(max_tentativas):
            try:
                self.db.add(pedido)
                self.db.commit()
                self.db.refresh(pedido)
                return pedido
            except IntegrityError as exc:
                self.db.rollback()
                if "uq_pedidos_empresa_numero" in str(exc.orig) or "UniqueViolation" in str(exc.orig):
                    pedido.numero_pedido = self._next_numero_prefixado(
                        empresa_id=empresa_id,
                        tipo_entrega=TipoEntrega.BALCAO.value,
                        prefixo="BAL",
                        width=6,
                        lock_code=1002,
                    )
                    continue
                raise
        raise HTTPException(
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Não foi possível criar o pedido de balcão (colisão de numero_pedido).",
        )

    def criar_pedido_mesa(
        self,
        *,
        mesa_id: int,
        empresa_id: int,
        cliente_id: Optional[int],
        observacoes: Optional[str],
        num_pessoas: Optional[int],
        meio_pagamento_id: Optional[int] = None,
    ) -> PedidoUnificadoModel:
        """Cria um pedido de mesa."""
        mesa = (
            self.db.query(MesaModel)
            .filter(
                MesaModel.id == mesa_id,
                MesaModel.empresa_id == empresa_id,
            )
            .first()
        )
        if not mesa:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Mesa não encontrada")

        # número simples: {mesa.numero}-{sequencial curto} (concorrência segura por mesa)
        # Usa sequence por empresa+mesa para gerar numeros por mesa
        numero = self._next_numero_via_sequence(empresa_id=empresa_id, prefixo=str(mesa.numero), width=3)

        pedido = PedidoUnificadoModel(
            tipo_entrega=TipoEntrega.MESA.value,
            empresa_id=empresa_id,
            mesa_id=mesa_id,
            cliente_id=cliente_id,
            meio_pagamento_id=meio_pagamento_id,
            numero_pedido=numero,
            observacoes=observacoes,
            num_pessoas=num_pessoas,
            status=StatusPedido.IMPRESSAO.value,
            subtotal=Decimal("0"),
            desconto=Decimal("0"),
            taxa_entrega=Decimal("0"),
            taxa_servico=Decimal("0"),
            valor_total=Decimal("0"),
        )
        max_tentativas = 5
        for _ in range(max_tentativas):
            try:
                self.db.add(pedido)
                self.db.commit()
                self.db.refresh(pedido)
                return pedido
            except IntegrityError as exc:
                self.db.rollback()
                if "uq_pedidos_empresa_numero" in str(exc.orig) or "UniqueViolation" in str(exc.orig):
                    pedido.numero_pedido = self._next_numero_prefixado(
                        empresa_id=empresa_id,
                        tipo_entrega=TipoEntrega.MESA.value,
                        prefixo=str(mesa.numero),
                        width=3,
                        lock_code=300000 + int(mesa_id),
                        extra_filters=[
                            PedidoUnificadoModel.mesa_id == mesa_id,
                        ],
                    )
                    continue
                raise
        raise HTTPException(
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Não foi possível criar o pedido de mesa (colisão de numero_pedido).",
        )

    def atualizar_totais(
        self,
        pedido: PedidoUnificadoModel,
        *,
        subtotal: Decimal,
        desconto: Decimal,
        taxa_entrega: Decimal,
        taxa_servico: Decimal,
        distancia_km: Optional[Decimal] = None,
    ) -> None:
        # Regra de negócio: pedidos de MESA e BALCÃO NÃO possuem taxa de serviço.
        # Blindagem no nível do repositório para evitar que algum fluxo aplique taxa indevida.
        tipo_entrega = (
            pedido.tipo_entrega.value
            if hasattr(pedido.tipo_entrega, "value")
            else str(pedido.tipo_entrega)
        )
        if str(tipo_entrega).upper() in {"MESA", "BALCAO"}:
            taxa_servico = Decimal("0")

        pedido.subtotal = subtotal
        pedido.desconto = desconto
        pedido.taxa_entrega = taxa_entrega
        pedido.taxa_servico = taxa_servico
        pedido.valor_total = subtotal - desconto + taxa_entrega + taxa_servico
        if pedido.valor_total < 0:
            pedido.valor_total = Decimal("0")
        pedido.distancia_km = distancia_km
        # Apenas flush — não precisa de refresh
        self.db.flush()

    def add_status_historico(
        self, 
        pedido_id: int, 
        status: str, 
        motivo: str | None = None, 
        observacoes: str | None = None,
        criado_por_id: int | None = None,
        ip_origem: str | None = None,
        user_agent: str | None = None
    ):
        hist = PedidoHistoricoUnificadoModel(
            pedido_id=pedido_id,
            status_novo=status,
            motivo=motivo,
            observacoes=observacoes,
            usuario_id=criado_por_id,
            ip_origem=ip_origem,
            user_agent=user_agent,
        )
        self.db.add(hist)

    def _status_para_nome(self, status: str) -> str:
        """Converte código de status para nome simples."""
        mapa = {
            "P": "Pendente",
            "I": "Impressão",
            "R": "Em preparo",
            "S": "Saiu",
            "E": "Entregue",
            "C": "Cancelado",
            "D": "Editado",
            "X": "Editando",
            "A": "Aguardando pagamento",
        }
        return mapa.get(status, status)
    
    def atualizar_status_pedido(self, pedido: PedidoUnificadoModel, novo_status: str, motivo: str | None = None, observacoes: str | None = None, criado_por_id: int | None = None):
        status_anterior = pedido.status
        pedido.status = novo_status
        
        # Formata motivo como transição de status se não fornecido
        if motivo is None:
            status_ant_nome = self._status_para_nome(status_anterior)
            status_novo_nome = self._status_para_nome(novo_status)
            motivo = f"{status_ant_nome} → {status_novo_nome}"
        
        self.add_status_historico(
            pedido.id, 
            novo_status, 
            motivo=motivo,
            observacoes=observacoes,
            criado_por_id=criado_por_id
        )

    def atualizar_status_pedido_com_historico_detalhado(
        self, 
        pedido: PedidoUnificadoModel, 
        novo_status: str, 
        motivo: str | None = None,
        observacoes: str | None = None,
        criado_por_id: int | None = None,
        ip_origem: str | None = None,
        user_agent: str | None = None
    ):
        """Atualiza status do pedido com histórico detalhado em uma única operação"""
        status_anterior = pedido.status
        pedido.status = novo_status
        
        # Formata motivo como transição de status se não fornecido
        if motivo is None:
            status_ant_nome = self._status_para_nome(status_anterior)
            status_novo_nome = self._status_para_nome(novo_status)
            motivo = f"{status_ant_nome} → {status_novo_nome}"
        
        self.add_status_historico(
            pedido_id=pedido.id,
            status=novo_status,
            motivo=motivo,
            observacoes=observacoes,
            criado_por_id=criado_por_id,
            ip_origem=ip_origem,
            user_agent=user_agent
        )

    # ----------------- Transação pagamento -------------
    def criar_transacao_pagamento(
        self,
        *,
        pedido_id: int,
        meio_pagamento_id: int,
        gateway: str,
        metodo: str,
        valor: Decimal,
        moeda: str = "BRL",
        payload_solicitacao: dict | None = None,
        provider_transaction_id: str | None = None,
        qr_code: str | None = None,
        qr_code_base64: str | None = None,
    ) -> TransacaoPagamentoModel:
        tx = TransacaoPagamentoModel(
            pedido_id=pedido_id,
            meio_pagamento_id=meio_pagamento_id,
            gateway=gateway,
            metodo=metodo,
            valor=valor,
            moeda=moeda,
            status="PENDENTE",
            payload_solicitacao=payload_solicitacao,
            provider_transaction_id=provider_transaction_id,
            qr_code=qr_code,
            qr_code_base64=qr_code_base64,
        )
        self.db.add(tx)
        self.db.flush()
        return tx

    def atualizar_transacao_status(
        self,
        tx: TransacaoPagamentoModel,
        *,
        status: str,
        provider_transaction_id: str | None = None,
        payload_retorno: dict | None = None,
        qr_code: str | None = None,
        qr_code_base64: str | None = None,
        timestamp_field: str | None = None,
        payload_solicitacao: dict | None = None,
    ):
        tx.status = status
        if provider_transaction_id is not None:
            tx.provider_transaction_id = provider_transaction_id
        if payload_retorno is not None:
            tx.payload_retorno = payload_retorno
        if qr_code is not None:
            tx.qr_code = qr_code
        if qr_code_base64 is not None:
            tx.qr_code_base64 = qr_code_base64
        if payload_solicitacao is not None:
            tx.payload_solicitacao = payload_solicitacao
        if timestamp_field:
            setattr(tx, timestamp_field, func.now())

    # ---------------- Unit of Work ---------------------
    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    # --------------- ITENS PEDIDO ----------------------
    def get_item_by_id(self, item_id: int) -> Optional[PedidoItemUnificadoModel]:
        return self.db.get(PedidoItemUnificadoModel, item_id)

    def adicionar_item(
        self,
        *,
        pedido_id: int,
        cod_barras: str | None = None,
        receita_id: int | None = None,
        combo_id: int | None = None,
        quantidade: int,
        preco_unitario: Decimal,
        observacao: str | None,
        produto_descricao_snapshot: str | None = None,
        produto_imagem_snapshot: str | None = None,
        complementos: list | None = None,
    ) -> PedidoItemUnificadoModel:
        """
        Adiciona um item ao pedido. Suporta produto (cod_barras), receita (receita_id) ou combo (combo_id).
        Apenas um dos três campos deve ser preenchido.
        """
        # Valida que apenas um tipo está preenchido
        tipos_preenchidos = sum([
            cod_barras is not None,
            receita_id is not None,
            combo_id is not None
        ])
        if tipos_preenchidos != 1:
            raise ValueError("Exatamente um dos campos (cod_barras, receita_id, combo_id) deve ser preenchido")
        
        # Calcula preco_total
        preco_total = preco_unitario * Decimal(str(quantidade))

        produto_id: int | None = None
        if cod_barras is not None:
            produto_id = (
                self.db.query(ProdutoModel.id)
                .filter(ProdutoModel.cod_barras == cod_barras)
                .scalar()
            )
        
        # ⚠️ Evitar passar o objeto pedido E o pedido_id juntos.
        item = PedidoItemUnificadoModel(
            pedido_id=pedido_id,
            produto_id=produto_id,
            produto_cod_barras=cod_barras,
            receita_id=receita_id,
            combo_id=combo_id,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            preco_total=preco_total,
            observacao=observacao,
            produto_descricao_snapshot=produto_descricao_snapshot,
            produto_imagem_snapshot=produto_imagem_snapshot,
        )
        self.db.add(item)
        self.db.flush()

        # Persistência relacional (tabelas do schema pedidos) a partir do request (sem snapshot JSON)
        if complementos:
            self._persistir_complementos_do_request(
                item=item,
                pedido_id=pedido_id,
                complementos_request=complementos,
            )

        return item

    def _persistir_complementos_do_request(
        self,
        *,
        item: PedidoItemUnificadoModel,
        pedido_id: int,
        complementos_request: list,
    ) -> None:
        """
        Persiste complementos/adicionais em tabelas relacionais (schema pedidos)
        DIRETAMENTE a partir do request (ItemComplementoRequest / ItemAdicionalComplementoRequest),
        consultando o catálogo para validar vínculos e obter preço/nome.
        """
        from decimal import Decimal as Dec
        from app.api.catalogo.adapters.complemento_adapter import ComplementoAdapter
        from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel
        from app.api.pedidos.models.model_pedido_item_complemento import PedidoItemComplementoModel
        from app.api.pedidos.models.model_pedido_item_complemento_adicional import (
            PedidoItemComplementoAdicionalModel,
        )

        # Support both legacy list-of-complementos and new dict format:
        # legacy: complementos_request = [ {complemento_id, adicionais: [...]}, ... ]
        # new: complementos_request = { "complementos": [...], "secoes": [...] }
        secoes_selecionadas: list = []
        if not complementos_request:
            return

        if isinstance(complementos_request, dict):
            complementos_list = complementos_request.get("complementos", []) or []
            secoes_selecionadas = complementos_request.get("secoes", []) or []
        else:
            complementos_list = complementos_request if isinstance(complementos_request, list) else []

        complemento_contract = ComplementoAdapter(self.db)

        # Dados do pedido (para fallback por empresa quando necessário)
        pedido = self.db.get(PedidoUnificadoModel, pedido_id)
        empresa_id = getattr(pedido, "empresa_id", None) if pedido is not None else None

        # Extrai seleção do request: complemento_id -> lista de (adicional_id, quantidade)
        complemento_ids: list[int] = []
        selecionados_por_complemento: dict[int, list[dict]] = {}

        for comp_req in complementos_list:
            comp_id = getattr(comp_req, "complemento_id", None)
            if comp_id is None:
                continue
            comp_id_int = int(comp_id)
            complemento_ids.append(comp_id_int)
            adicionais_req = getattr(comp_req, "adicionais", None) or []
            selecionados_por_complemento[comp_id_int] = [
                {
                    "adicional_id": int(getattr(a, "adicional_id")),
                    "quantidade": int(getattr(a, "quantidade", 1) or 1),
                }
                for a in adicionais_req
                if getattr(a, "adicional_id", None) is not None
            ]

        if not complemento_ids and not secoes_selecionadas:
            return

        # Busca/valida complementos conforme tipo do item
        complementos_db = []
        if item.produto_cod_barras:
            complementos_db = complemento_contract.buscar_por_ids_para_produto(
                str(item.produto_cod_barras),
                complemento_ids,
            )
        elif item.combo_id is not None:
            all_db = complemento_contract.listar_por_combo(int(item.combo_id), apenas_ativos=True)
            ids_set = set(complemento_ids)
            complementos_db = [c for c in all_db if getattr(c, "id", None) in ids_set]
        elif item.receita_id is not None:
            all_db = complemento_contract.listar_por_receita(int(item.receita_id), apenas_ativos=True)
            ids_set = set(complemento_ids)
            complementos_db = [c for c in all_db if getattr(c, "id", None) in ids_set]
        elif empresa_id is not None:
            complementos_db = complemento_contract.buscar_por_ids(int(empresa_id), complemento_ids)

        # Persistir complementos tradicionais (se existirem)
        if complementos_db:
            qtd_item = int(getattr(item, "quantidade", 1) or 1)

            for comp in complementos_db:
                comp_id = getattr(comp, "id", None)
                if comp_id is None:
                    continue
                selecionados = selecionados_por_complemento.get(int(comp_id), [])
                if not selecionados:
                    continue

                adicionais_catalogo = {getattr(a, "id", None): a for a in (getattr(comp, "adicionais", None) or [])}
                comp_total = Dec("0")

                # Monta lista de adicionais válidos
                adicionais_rows: list[tuple[int, str, int, Dec, Dec]] = []
                for sel in selecionados:
                    ad_id = sel.get("adicional_id")
                    if ad_id is None or ad_id not in adicionais_catalogo:
                        continue
                    ad = adicionais_catalogo[ad_id]
                    preco_unit = Dec(str(getattr(ad, "preco", 0) or 0))
                    qtd_ad = int(sel.get("quantidade") or 1)
                    if qtd_ad < 1:
                        qtd_ad = 1
                    # Se o complemento não for quantitativo, força qtd_ad = 1
                    if not bool(getattr(comp, "quantitativo", False)):
                        qtd_ad = 1
                    total_ad = preco_unit * Dec(str(qtd_ad)) * Dec(str(qtd_item))
                    comp_total += total_ad
                    adicionais_rows.append((int(ad_id), str(getattr(ad, "nome", "") or ""), qtd_ad, preco_unit, total_ad))

                if not adicionais_rows:
                    continue

                comp_row = PedidoItemComplementoModel(
                    pedido_item_id=item.id,
                    complemento_id=int(comp_id),
                    total=comp_total,
                )
                self.db.add(comp_row)
                self.db.flush()

                for adicional_id, nome, qtd_ad, preco_unit, total_ad in adicionais_rows:
                    self.db.add(
                        PedidoItemComplementoAdicionalModel(
                            item_complemento_id=comp_row.id,
                            adicional_id=adicional_id,
                            quantidade=qtd_ad,
                            preco_unitario=preco_unit,
                            total=total_ad,
                        )
                    )

        # Persistir seleções de seções de combo (novo)
        try:
            if secoes_selecionadas and getattr(item, "combo_id", None) is not None:
                # Import models dinamicamente para evitar ciclo de import
                from app.api.catalogo.models.model_combo_secoes import ComboSecaoModel, ComboSecaoItemModel
                from app.api.pedidos.models.model_pedido_item_combo_secoes import (
                    PedidoItemComboSecaoModel,
                    PedidoItemComboSecaoItemModel,
                )

                for sec_sel in secoes_selecionadas:
                    secao_id = int(sec_sel.get("secao_id"))
                    itens_sel = sec_sel.get("itens", []) or []
                    sec_model = self.db.query(ComboSecaoModel).filter(ComboSecaoModel.id == secao_id).first()
                    sec_titulo = getattr(sec_model, "titulo", None) if sec_model is not None else None

                    sec_row = PedidoItemComboSecaoModel(
                        pedido_item_id=item.id,
                        secao_id=secao_id,
                        secao_titulo_snapshot=sec_titulo,
                        ordem=getattr(sec_model, "ordem", 0) if sec_model is not None else 0,
                    )
                    self.db.add(sec_row)
                    self.db.flush()

                    # Persistir itens selecionados da seção
                    for it_sel in itens_sel:
                        item_id = int(it_sel.get("id"))
                        qtd_it = int(it_sel.get("quantidade", 1) or 1)
                        cat_item = self.db.query(ComboSecaoItemModel).filter(ComboSecaoItemModel.id == item_id).first()
                        preco_inc = getattr(cat_item, "preco_incremental", 0) if cat_item is not None else 0
                        prod_cod = getattr(cat_item, "produto_cod_barras", None) if cat_item is not None else None
                        receita_snap = getattr(cat_item, "receita_id", None) if cat_item is not None else None

                        sec_item_row = PedidoItemComboSecaoItemModel(
                            pedido_item_secao_id=sec_row.id,
                            combo_secoes_item_id=item_id,
                            produto_cod_barras_snapshot=prod_cod,
                            receita_id_snapshot=receita_snap,
                            preco_incremental_snapshot=preco_inc,
                            quantidade=qtd_it,
                        )
                        self.db.add(sec_item_row)
                self.db.flush()
        except Exception:
            # Não falhar toda a persistência de complementos caso algo dê errado ao gravar seções
            pass
        # end _persistir_complementos_do_request

    def atualizar_item(
        self,
        item_id: int,
        quantidade: int | None = None,
        observacao: str | None = None
    ) -> PedidoItemUnificadoModel:
        item = self.get_item_by_id(item_id)
        if not item:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, f"Item {item_id} não encontrado")
        if quantidade is not None:
            item.quantidade = quantidade
            # Recalcula preco_total se quantidade mudou
            item.preco_total = item.preco_unitario * Decimal(str(quantidade))
        if observacao is not None:
            item.observacao = observacao
        self.db.flush()
        return item

    # -------------------- Métodos específicos para produtos, receitas e combos -------------------
    def adicionar_item_produto(
        self,
        *,
        pedido_id: int,
        cod_barras: str,
        quantidade: int,
        preco_unitario: Decimal,
        observacao: str | None,
        produto_descricao_snapshot: str | None = None,
        produto_imagem_snapshot: str | None = None,
        complementos: list | None = None,
    ) -> PedidoItemUnificadoModel:
        """Adiciona um item de produto ao pedido."""
        return self.adicionar_item(
            pedido_id=pedido_id,
            cod_barras=cod_barras,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            observacao=observacao,
            produto_descricao_snapshot=produto_descricao_snapshot,
            produto_imagem_snapshot=produto_imagem_snapshot,
            complementos=complementos,
        )

    def adicionar_item_receita(
        self,
        *,
        pedido_id: int,
        receita_id: int,
        quantidade: int,
        preco_unitario: Decimal,
        observacao: str | None,
        complementos: list | None = None,
    ) -> PedidoItemUnificadoModel:
        """Adiciona um item de receita ao pedido."""
        return self.adicionar_item(
            pedido_id=pedido_id,
            receita_id=receita_id,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            observacao=observacao,
            complementos=complementos,
        )

    def adicionar_item_combo(
        self,
        *,
        pedido_id: int,
        combo_id: int,
        quantidade: int,
        preco_unitario: Decimal,
        observacao: str | None,
        complementos: list | None = None,
    ) -> PedidoItemUnificadoModel:
        """Adiciona um item de combo ao pedido."""
        return self.adicionar_item(
            pedido_id=pedido_id,
            combo_id=combo_id,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            observacao=observacao,
            complementos=complementos,
        )

    # -------------------- Métodos unificados para balcão e mesa -------------------
    def add_item(
        self,
        pedido_id: int,
        *,
        produto_cod_barras: str | None = None,
        receita_id: int | None = None,
        combo_id: int | None = None,
        quantidade: int,
        observacao: Optional[str],
        preco_unitario: Optional[Decimal] = None,
        produto_descricao_snapshot: Optional[str] = None,
        produto_imagem_snapshot: Optional[str] = None,
        complementos: list | None = None,
    ) -> PedidoUnificadoModel:
        """Adiciona um item ao pedido (balcão ou mesa). Busca preço automaticamente se for produto."""
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Pedido não encontrado")

        # Valida que apenas um tipo está preenchido
        tipos_preenchidos = sum([
            produto_cod_barras is not None,
            receita_id is not None,
            combo_id is not None
        ])
        if tipos_preenchidos != 1:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                "Exatamente um dos campos (produto_cod_barras, receita_id, combo_id) deve ser preenchido"
            )

        descricao_snapshot = produto_descricao_snapshot
        imagem_snapshot = produto_imagem_snapshot
        
        # Se não foi fornecido preço unitário, busca do produto
        if preco_unitario is None:
            if produto_cod_barras:
                if self.produto_contract is not None:
                    pe_dto = self.produto_contract.obter_produto_emp_por_cod(pedido.empresa_id, produto_cod_barras)
                    if not pe_dto:
                        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Produto não encontrado")
                    if not pe_dto.disponivel or not (pe_dto.produto and bool(pe_dto.produto.ativo)):
                        raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "Produto indisponível")
                    preco_unitario = Decimal(str(pe_dto.preco_venda or 0))
                    if pe_dto.produto:
                        descricao_snapshot = descricao_snapshot or pe_dto.produto.descricao
                        imagem_snapshot = imagem_snapshot or pe_dto.produto.imagem
                else:
                    raise HTTPException(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Contrato de produto não configurado")
            else:
                raise HTTPException(
                    http_status.HTTP_400_BAD_REQUEST,
                    "preco_unitario é obrigatório para receitas e combos"
                )

        # Usa o método adicionar_item unificado
        self.adicionar_item(
            pedido_id=pedido_id,
            cod_barras=produto_cod_barras,
            receita_id=receita_id,
            combo_id=combo_id,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            observacao=observacao,
            produto_descricao_snapshot=descricao_snapshot,
            produto_imagem_snapshot=imagem_snapshot,
            complementos=complementos,
        )
        self.db.commit()
        return self._refresh_total(pedido)

    def remove_item(self, pedido_id: int, item_id: int) -> PedidoUnificadoModel:
        """Remove um item do pedido e recalcula o total."""
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        item = (
            self.db.query(PedidoItemUnificadoModel)
            .filter(PedidoItemUnificadoModel.id == item_id, PedidoItemUnificadoModel.pedido_id == pedido_id)
            .first()
        )
        if not item:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Item não encontrado")
        self.db.delete(item)
        self.db.commit()
        return self._refresh_total(pedido)

    # -------------------- Métodos de status para balcão e mesa -------------------
    def cancelar(self, pedido_id: int) -> PedidoUnificadoModel:
        """Cancela um pedido (balcão ou mesa)."""
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        pedido.status = StatusPedido.CANCELADO.value
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def confirmar(self, pedido_id: int) -> PedidoUnificadoModel:
        """Confirma um pedido (balcão ou mesa) mudando status para IMPRESSAO."""
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        pedido.status = StatusPedido.IMPRESSAO.value
        self.db.commit()
        self.db.refresh(pedido)
        return self._refresh_total(pedido)

    def fechar_conta(self, pedido_id: int) -> PedidoUnificadoModel:
        """Fecha a conta de um pedido (balcão ou mesa) mudando status para ENTREGUE."""
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        pedido.status = StatusPedido.ENTREGUE.value
        self.db.commit()
        self.db.refresh(pedido)
        return self._refresh_total(pedido)

    def reabrir(self, pedido_id: int, novo_status: str = StatusPedido.PENDENTE.value) -> PedidoUnificadoModel:
        """Reabre um pedido cancelado ou entregue."""
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        status_atual = (
            pedido.status
            if isinstance(pedido.status, str)
            else pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status)
        )
        if status_atual != StatusPedido.CANCELADO.value and status_atual != StatusPedido.ENTREGUE.value:
            return pedido
        pedido.status = novo_status
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def atualizar_status(self, pedido_id: int, novo_status) -> PedidoUnificadoModel:
        """Atualiza o status do pedido (aceita enum ou string)."""
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        if hasattr(novo_status, "value"):
            status_value = novo_status.value
        else:
            status_value = str(novo_status)
        pedido.status = status_value
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    # -------------------- Métodos de listagem para balcão e mesa -------------------
    def list_abertos_by_mesa(self, mesa_id: int, tipo_entrega: TipoEntrega, *, empresa_id: Optional[int] = None) -> list[PedidoUnificadoModel]:
        """Lista pedidos abertos de balcão ou mesa associados a uma mesa específica"""
        from app.api.pedidos.models.model_pedido_item_complemento import PedidoItemComplementoModel
        from app.api.pedidos.models.model_pedido_item_complemento_adicional import (
            PedidoItemComplementoAdicionalModel,
        )
        query = (
            self.db.query(PedidoUnificadoModel)
            .options(
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .selectinload(PedidoItemComplementoModel.adicionais),
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .joinedload(PedidoItemComplementoModel.complemento),
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .selectinload(PedidoItemComplementoModel.adicionais)
                .joinedload(PedidoItemComplementoAdicionalModel.adicional),
            )
            .filter(
                PedidoUnificadoModel.tipo_entrega == tipo_entrega.value,
                PedidoUnificadoModel.mesa_id == mesa_id,
                PedidoUnificadoModel.status.in_(OPEN_STATUS_PEDIDO_BALCAO_MESA)
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoUnificadoModel.empresa_id == empresa_id)
        return query.order_by(PedidoUnificadoModel.created_at.desc()).all()

    def list_abertos_all(self, tipo_entrega: TipoEntrega, *, empresa_id: Optional[int] = None) -> list[PedidoUnificadoModel]:
        """Lista todos os pedidos abertos de balcão ou mesa"""
        from app.api.pedidos.models.model_pedido_item_complemento import PedidoItemComplementoModel
        from app.api.pedidos.models.model_pedido_item_complemento_adicional import (
            PedidoItemComplementoAdicionalModel,
        )
        query = (
            self.db.query(PedidoUnificadoModel)
            .options(
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .selectinload(PedidoItemComplementoModel.adicionais),
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .joinedload(PedidoItemComplementoModel.complemento),
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .selectinload(PedidoItemComplementoModel.adicionais)
                .joinedload(PedidoItemComplementoAdicionalModel.adicional),
            )
            .filter(
                PedidoUnificadoModel.tipo_entrega == tipo_entrega.value,
                PedidoUnificadoModel.status.in_(OPEN_STATUS_PEDIDO_BALCAO_MESA)
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoUnificadoModel.empresa_id == empresa_id)
        return query.order_by(PedidoUnificadoModel.created_at.desc()).all()

    def get_aberto_mais_recente(self, mesa_id: int, tipo_entrega: TipoEntrega, *, empresa_id: int | None = None) -> Optional[PedidoUnificadoModel]:
        """Busca o pedido aberto mais recente de uma mesa (apenas para tipo MESA)"""
        query = (
            self.db.query(PedidoUnificadoModel)
            .filter(
                PedidoUnificadoModel.tipo_entrega == tipo_entrega.value,
                PedidoUnificadoModel.mesa_id == mesa_id,
                PedidoUnificadoModel.status.in_(OPEN_STATUS_PEDIDO_BALCAO_MESA)
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoUnificadoModel.empresa_id == empresa_id)
        return query.order_by(PedidoUnificadoModel.created_at.desc()).first()

    def list_finalizados(self, tipo_entrega: TipoEntrega, data_filtro: Optional[date] = None, *, empresa_id: Optional[int] = None, mesa_id: Optional[int] = None) -> list[PedidoUnificadoModel]:
        """Lista pedidos finalizados (ENTREGUE) de balcão ou mesa"""
        from app.api.pedidos.models.model_pedido_item_complemento import PedidoItemComplementoModel
        from app.api.pedidos.models.model_pedido_item_complemento_adicional import (
            PedidoItemComplementoAdicionalModel,
        )
        query = (
            self.db.query(PedidoUnificadoModel)
            .options(
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .selectinload(PedidoItemComplementoModel.adicionais),
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .joinedload(PedidoItemComplementoModel.complemento),
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .selectinload(PedidoItemComplementoModel.adicionais)
                .joinedload(PedidoItemComplementoAdicionalModel.adicional),
            )
            .filter(
                PedidoUnificadoModel.tipo_entrega == tipo_entrega.value,
                PedidoUnificadoModel.status == StatusPedido.ENTREGUE.value
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoUnificadoModel.empresa_id == empresa_id)
        if mesa_id is not None:
            query = query.filter(PedidoUnificadoModel.mesa_id == mesa_id)
        
        # Filtro por data se fornecido
        if data_filtro is not None:
            data_inicio = datetime.combine(data_filtro, datetime.min.time())
            data_fim = datetime.combine(data_filtro, datetime.max.time())
            query = query.filter(
                or_(
                    and_(
                        PedidoUnificadoModel.created_at >= data_inicio,
                        PedidoUnificadoModel.created_at <= data_fim
                    ),
                    and_(
                        PedidoUnificadoModel.updated_at >= data_inicio,
                        PedidoUnificadoModel.updated_at <= data_fim
                    )
                )
            )
        
        return query.order_by(PedidoUnificadoModel.created_at.desc()).all()

    def list_by_cliente_id(self, cliente_id: int, tipo_entrega: TipoEntrega, *, empresa_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> list[PedidoUnificadoModel]:
        """Lista pedidos de um cliente específico por tipo"""
        from app.api.pedidos.models.model_pedido_item_complemento import PedidoItemComplementoModel
        from app.api.pedidos.models.model_pedido_item_complemento_adicional import (
            PedidoItemComplementoAdicionalModel,
        )
        query = (
            self.db.query(PedidoUnificadoModel)
            .options(
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .selectinload(PedidoItemComplementoModel.adicionais),
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .joinedload(PedidoItemComplementoModel.complemento),
                selectinload(PedidoUnificadoModel.itens)
                .selectinload(PedidoItemUnificadoModel.complementos)
                .selectinload(PedidoItemComplementoModel.adicionais)
                .joinedload(PedidoItemComplementoAdicionalModel.adicional),
                joinedload(PedidoUnificadoModel.mesa),
                joinedload(PedidoUnificadoModel.cliente)
            )
            .filter(
                PedidoUnificadoModel.tipo_entrega == tipo_entrega.value,
                PedidoUnificadoModel.cliente_id == cliente_id
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoUnificadoModel.empresa_id == empresa_id)
        return (
            query
            .order_by(PedidoUnificadoModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_abertos_by_cliente_id(self, cliente_id: int, *, empresa_id: Optional[int] = None) -> list[PedidoUnificadoModel]:
        """Lista pedidos em aberto de um cliente específico (todos os tipos)"""
        query = (
            self.db.query(PedidoUnificadoModel)
            .options(
                joinedload(PedidoUnificadoModel.cliente),
                joinedload(PedidoUnificadoModel.mesa)
            )
            .filter(
                PedidoUnificadoModel.cliente_id == cliente_id,
                PedidoUnificadoModel.status.in_(OPEN_STATUS_PEDIDO_ALL)
            )
        )
        if empresa_id is not None:
            query = query.filter(PedidoUnificadoModel.empresa_id == empresa_id)
        return (
            query
            .order_by(PedidoUnificadoModel.created_at.desc())
            .all()
        )

    # -------------------- Histórico unificado -------------------
    def add_historico(
        self,
        pedido_id: int,
        tipo_operacao: TipoOperacaoPedido,
        status_anterior: str | None = None,
        status_novo: str | None = None,
        descricao: str | None = None,
        observacoes: str | None = None,
        cliente_id: int | None = None,
        usuario_id: int | None = None,
        ip_origem: str | None = None,
        user_agent: str | None = None
    ):
        """Adiciona um registro ao histórico do pedido"""
        # Busca o pedido para obter o tipo_entrega (DELIVERY, RETIRADA, BALCAO, MESA)
        pedido = self.get_pedido(pedido_id)
        if not pedido:
            raise ValueError(f"Pedido {pedido_id} não encontrado")
        
        tipo_entrega_value = pedido.tipo_entrega.value if hasattr(pedido.tipo_entrega, "value") else pedido.tipo_entrega
        
        status_anterior_value = (
            status_anterior.value
            if hasattr(status_anterior, "value")
            else status_anterior
        )
        status_novo_value = (
            status_novo.value
            if hasattr(status_novo, "value")
            else status_novo
        )

        historico = PedidoHistoricoUnificadoModel(
            pedido_id=pedido_id,
            cliente_id=cliente_id,
            usuario_id=usuario_id,
            tipo_entrega=tipo_entrega_value,  # DELIVERY, RETIRADA, BALCAO, MESA
            tipo_operacao=tipo_operacao.value if hasattr(tipo_operacao, "value") else tipo_operacao,  # PEDIDO_CRIADO, STATUS_ALTERADO, etc
            status_anterior=status_anterior_value,
            status_novo=status_novo_value,
            descricao=descricao,
            observacoes=observacoes,
            ip_origem=ip_origem,
            user_agent=user_agent
        )
        self.db.add(historico)

    def get_historico(self, pedido_id: int, limit: int = 100) -> list[PedidoHistoricoUnificadoModel]:
        """Busca histórico de um pedido"""
        return (
            self.db.query(PedidoHistoricoUnificadoModel)
            .options(joinedload(PedidoHistoricoUnificadoModel.usuario))
            .filter(PedidoHistoricoUnificadoModel.pedido_id == pedido_id)
            .order_by(PedidoHistoricoUnificadoModel.created_at.desc())
            .limit(limit)
            .all()
        )
