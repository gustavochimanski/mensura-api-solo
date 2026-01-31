from datetime import datetime, timezone

from sqlalchemy import func, case
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.api.cadastros.repositories.repo_cliente import ClienteRepository
from app.api.cadastros.schemas.schema_cliente import (
    ClienteCreate,
    ClienteUpdate,
    ClienteRelatorioDetalhadoOut,
    ClienteRelatorioCanalOut,
    ClienteRelatorioTipoEntregaOut,
    ClienteRelatorioEmpresaOut,
)
from app.api.pedidos.models.model_pedido_unificado import (
    PedidoUnificadoModel,
    StatusPedido,
    TipoEntrega,
    CanalPedido,
)
from app.api.empresas.models.empresa_model import EmpresaModel
from app.utils.telefone import normalizar_telefone_para_armazenar


class ClienteService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ClienteRepository(db)
    
    def _normalizar_telefone(self, telefone: str) -> str:
        """
        Compatibilidade: mantém a API interna existente, mas delega para
        `app.utils.telefone.normalizar_telefone_para_armazenar`.
        """
        return normalizar_telefone_para_armazenar(telefone) or ""

    def get_current(self, token: str):
        cli = self.repo.get_by_token(token)
        if not cli:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
        return cli

    def create(self, data: ClienteCreate):
        # Normaliza telefone (adiciona prefixo 55 se necessário)
        telefone_normalizado = self._normalizar_telefone(data.telefone) if data.telefone else None
        
        # Atualiza o telefone no data antes de verificar duplicado
        if telefone_normalizado:
            data.telefone = telefone_normalizado
        
        # verifica telefone duplicado
        if data.telefone and self.repo.get_by_telefone(data.telefone):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Telefone já cadastrado")
        try:
            return self.repo.create(**data.model_dump(exclude_unset=True))
        except IntegrityError as err:
            constraint = getattr(getattr(err.orig, "diag", None), "constraint_name", "")
            message = str(err.orig).lower()
            if constraint == "clientes_telefone_key" or "clientes_telefone_key" in message:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Telefone já cadastrado") from err
            if constraint == "clientes_cpf_key" or "clientes_cpf_key" in message:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "CPF já cadastrado") from err
            if constraint == "clientes_super_token_key" or "clientes_super_token_key" in message:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token já cadastrado, gere um novo") from err
            raise

    def update(self, token: str, data: ClienteUpdate):
        db_obj = self.repo.get_by_token(token)
        if not db_obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não existe")
        
        # Normaliza telefone se estiver sendo atualizado
        if data.telefone:
            telefone_normalizado = self._normalizar_telefone(data.telefone)
            data.telefone = telefone_normalizado
        
        try:
            return self.repo.update(db_obj, **data.model_dump(exclude_none=True))
        except IntegrityError as err:
            constraint = getattr(getattr(err.orig, "diag", None), "constraint_name", "")
            message = str(err.orig).lower()
            if constraint == "clientes_telefone_key" or "clientes_telefone_key" in message:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Telefone já cadastrado") from err
            if constraint == "clientes_cpf_key" or "clientes_cpf_key" in message:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "CPF já cadastrado") from err
            if constraint == "clientes_super_token_key" or "clientes_super_token_key" in message:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token já cadastrado, gere um novo") from err
            raise

    def set_ativo(self, token: str, on: bool):
        obj = self.repo.set_ativo(token, on)
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não existe")
        return obj

    # ---------------- Relatório BI de cliente ----------------
    def relatorio_detalhado(
        self,
        *,
        cliente_id: int,
        inicio: datetime,
        fim: datetime,
    ) -> ClienteRelatorioDetalhadoOut:
        cliente = self.repo.get_by_id(cliente_id)
        if not cliente:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não existe")

        # período fechado: usa [inicio, fim_exclusive)
        from datetime import timedelta as _td

        if (
            getattr(fim, "hour", 0) == 0
            and getattr(fim, "minute", 0) == 0
            and getattr(fim, "second", 0) == 0
            and getattr(fim, "microsecond", 0) == 0
        ):
            fim_exclusive = fim + _td(days=1)
        else:
            fim_exclusive = fim + _td(microseconds=1)

        base_filter = [
            PedidoUnificadoModel.cliente_id == cliente_id,
            PedidoUnificadoModel.created_at >= inicio,
            PedidoUnificadoModel.created_at < fim_exclusive,
        ]

        # agregados gerais
        total_row = (
            self.db.query(
                func.count(PedidoUnificadoModel.id).label("total_pedidos"),
                func.sum(
                    case(
                        (PedidoUnificadoModel.status == StatusPedido.ENTREGUE.value, 1),
                        else_=0,
                    )
                ).label("total_pedidos_entregues"),
                func.sum(
                    case(
                        (PedidoUnificadoModel.status == StatusPedido.CANCELADO.value, 1),
                        else_=0,
                    )
                ).label("total_pedidos_cancelados"),
                func.sum(
                    case(
                        (PedidoUnificadoModel.pago.is_(True), 1),
                        else_=0,
                    )
                ).label("total_pedidos_pagos"),
                func.sum(PedidoUnificadoModel.valor_total).label("valor_total"),
                func.min(PedidoUnificadoModel.created_at).label("primeira_compra"),
                func.max(PedidoUnificadoModel.created_at).label("ultima_compra"),
                func.count(func.distinct(PedidoUnificadoModel.empresa_id)).label(
                    "qtd_empresas"
                ),
                func.sum(
                    case(
                        (PedidoUnificadoModel.cupom_id.isnot(None), 1),
                        else_=0,
                    )
                ).label("total_pedidos_com_cupom"),
                func.sum(PedidoUnificadoModel.desconto).label("valor_total_descontos"),
            )
            .filter(*base_filter)
            .one()
        )

        total_pedidos = int(total_row.total_pedidos or 0)
        total_pedidos_entregues = int(total_row.total_pedidos_entregues or 0)
        total_pedidos_cancelados = int(total_row.total_pedidos_cancelados or 0)
        total_pedidos_pagos = int(total_row.total_pedidos_pagos or 0)
        valor_total = float(total_row.valor_total or 0) if total_row.valor_total is not None else 0.0
        primeira_compra = total_row.primeira_compra
        ultima_compra = total_row.ultima_compra
        qtd_empresas = int(total_row.qtd_empresas or 0)
        total_pedidos_com_cupom = int(total_row.total_pedidos_com_cupom or 0)
        valor_total_descontos = (
            float(total_row.valor_total_descontos or 0)
            if total_row.valor_total_descontos is not None
            else 0.0
        )

        ticket_medio = valor_total / total_pedidos if total_pedidos > 0 else 0.0

        # Usa datetime aware para compatibilidade com datetimes do banco
        agora = datetime.now(timezone.utc)
        recencia_dias = None
        if ultima_compra:
            # Garante que ultima_compra seja aware para fazer a subtração
            if ultima_compra.tzinfo is None:
                # Se for naive, assume UTC
                ultima_compra = ultima_compra.replace(tzinfo=timezone.utc)
            recencia_dias = (agora - ultima_compra).days
        tempo_cliente_dias = None
        if getattr(cliente, "created_at", None):
            cliente_created_at = cliente.created_at
            # Garante que created_at seja aware para fazer a subtração
            if cliente_created_at.tzinfo is None:
                # Se for naive, assume UTC
                cliente_created_at = cliente_created_at.replace(tzinfo=timezone.utc)
            tempo_cliente_dias = (agora - cliente_created_at).days

        # por canal (WEB, APP, BALCAO)
        canais_rows = (
            self.db.query(
                PedidoUnificadoModel.canal,
                func.count(PedidoUnificadoModel.id).label("total"),
                func.sum(PedidoUnificadoModel.valor_total).label("valor"),
            )
            .filter(*base_filter)
            .group_by(PedidoUnificadoModel.canal)
            .all()
        )

        canais: list[ClienteRelatorioCanalOut] = []
        for row in canais_rows:
            canal_raw = row.canal
            if hasattr(canal_raw, "value"):
                canal_str = canal_raw.value
            else:
                canal_str = str(canal_raw) if canal_raw is not None else None

            total = int(row.total or 0)
            valor = float(row.valor or 0) if row.valor is not None else 0.0
            canais.append(
                ClienteRelatorioCanalOut(
                    canal=canal_str,
                    total_pedidos=total,
                    valor_total=valor,
                    ticket_medio=valor / total if total > 0 else 0.0,
                )
            )

        # por tipo de entrega (DELIVERY, RETIRADA, BALCAO, MESA)
        tipos_rows = (
            self.db.query(
                PedidoUnificadoModel.tipo_entrega,
                func.count(PedidoUnificadoModel.id).label("total"),
                func.sum(PedidoUnificadoModel.valor_total).label("valor"),
            )
            .filter(*base_filter)
            .group_by(PedidoUnificadoModel.tipo_entrega)
            .all()
        )

        tipos_entrega: list[ClienteRelatorioTipoEntregaOut] = []
        for row in tipos_rows:
            tipo_raw = row.tipo_entrega
            if hasattr(tipo_raw, "value"):
                tipo_str = tipo_raw.value
            else:
                tipo_str = str(tipo_raw)

            total = int(row.total or 0)
            valor = float(row.valor or 0) if row.valor is not None else 0.0
            tipos_entrega.append(
                ClienteRelatorioTipoEntregaOut(
                    tipo_entrega=tipo_str,
                    total_pedidos=total,
                    valor_total=valor,
                    ticket_medio=valor / total if total > 0 else 0.0,
                )
            )

        # por empresa
        empresas_rows = (
            self.db.query(
                PedidoUnificadoModel.empresa_id,
                func.count(PedidoUnificadoModel.id).label("total_pedidos"),
                func.sum(
                    case(
                        (PedidoUnificadoModel.status == StatusPedido.ENTREGUE.value, 1),
                        else_=0,
                    )
                ).label("total_pedidos_entregues"),
                func.sum(
                    case(
                        (PedidoUnificadoModel.status == StatusPedido.CANCELADO.value, 1),
                        else_=0,
                    )
                ).label("total_pedidos_cancelados"),
                func.sum(
                    case(
                        (PedidoUnificadoModel.pago.is_(True), 1),
                        else_=0,
                    )
                ).label("total_pedidos_pagos"),
                func.sum(PedidoUnificadoModel.valor_total).label("valor_total"),
                func.min(PedidoUnificadoModel.created_at).label("primeira_compra"),
                func.max(PedidoUnificadoModel.created_at).label("ultima_compra"),
            )
            .filter(*base_filter)
            .group_by(PedidoUnificadoModel.empresa_id)
            .all()
        )

        empresas_ids = [row.empresa_id for row in empresas_rows if row.empresa_id is not None]
        empresas_nomes_map: dict[int, str] = {}
        if empresas_ids:
            empresas = (
                self.db.query(EmpresaModel)
                .filter(EmpresaModel.id.in_(empresas_ids))
                .all()
            )
            empresas_nomes_map = {e.id: e.nome for e in empresas}

        empresas_out: list[ClienteRelatorioEmpresaOut] = []
        for row in empresas_rows:
            emp_id = row.empresa_id
            if emp_id is None:
                continue
            total_emp = int(row.total_pedidos or 0)
            total_entregues_emp = int(row.total_pedidos_entregues or 0)
            total_cancelados_emp = int(row.total_pedidos_cancelados or 0)
            total_pagos_emp = int(row.total_pedidos_pagos or 0)
            valor_emp = float(row.valor_total or 0) if row.valor_total is not None else 0.0
            primeira_emp = row.primeira_compra
            ultima_emp = row.ultima_compra

            ticket_medio_emp = valor_emp / total_emp if total_emp > 0 else 0.0
            ticket_medio_entregues_emp = (
                valor_emp / total_entregues_emp if total_entregues_emp > 0 else 0.0
            )

            empresas_out.append(
                ClienteRelatorioEmpresaOut(
                    empresa_id=emp_id,
                    empresa_nome=empresas_nomes_map.get(emp_id),
                    total_pedidos=total_emp,
                    total_pedidos_entregues=total_entregues_emp,
                    total_pedidos_cancelados=total_cancelados_emp,
                    total_pedidos_pagos=total_pagos_emp,
                    valor_total=valor_emp,
                    ticket_medio=ticket_medio_emp,
                    ticket_medio_entregues=ticket_medio_entregues_emp,
                    primeira_compra_em=primeira_emp,
                    ultima_compra_em=ultima_emp,
                )
            )

        return ClienteRelatorioDetalhadoOut(
            cliente_id=cliente.id,
            nome=cliente.nome,
            cpf=cliente.cpf,
            telefone=cliente.telefone,
            email=cliente.email,
            data_nascimento=cliente.data_nascimento,
            ativo=cliente.ativo,
            created_at=cliente.created_at,
            inicio=inicio,
            fim=fim,
            total_pedidos=total_pedidos,
            total_pedidos_entregues=total_pedidos_entregues,
            total_pedidos_cancelados=total_pedidos_cancelados,
            total_pedidos_pagos=total_pedidos_pagos,
            valor_total=valor_total,
            ticket_medio=ticket_medio,
            primeira_compra_em=primeira_compra,
            ultima_compra_em=ultima_compra,
            recencia_dias=recencia_dias,
            tempo_cliente_dias=tempo_cliente_dias,
            qtd_empresas=qtd_empresas,
            total_pedidos_com_cupom=total_pedidos_com_cupom,
            valor_total_descontos=valor_total_descontos,
            canais=canais,
            tipos_entrega=tipos_entrega,
            empresas=empresas_out,
        )
