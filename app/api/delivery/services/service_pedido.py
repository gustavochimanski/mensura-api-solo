from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.delivery.models.pedido_dv_model import PedidoDeliveryModel
from app.api.delivery.repositories.repo_pedidos import PedidoRepository
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.delivery.schemas.schema_pedido_dv import (
    FinalizarPedidoRequest, ItemPedidoRequest, PedidoResponse, ItemPedidoResponse, PedidoKanbanResponse
)
from app.api.delivery.schemas.schema_shared_enums import (
    PedidoStatusEnum, TipoEntregaEnum, OrigemPedidoEnum,
    PagamentoMetodoEnum, PagamentoGatewayEnum, PagamentoStatusEnum
)
from app.api.delivery.services.service_pagamento_gateway import PaymentGatewayClient
from app.utils.logger import logger

QTD_MAX_ITENS = 200

def _dec(value: float | Decimal | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class PedidoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PedidoRepository(db)
        self.repo_empresa = EmpresaRepository(db)
        self.gateway = PaymentGatewayClient()  # MOCK

    # ---------- Helper: monta a resposta padronizada ----------
    def _pedido_to_response(self, pedido) -> PedidoResponse:
        return PedidoResponse(
            id=pedido.id,
            status=PedidoStatusEnum(pedido.status),
            telefone_cliente=pedido.cliente_telefone,
            empresa_id=pedido.empresa_id,
            entregador_id=getattr(pedido, "entregador_id", None),
            endereco_id=pedido.endereco_id,
            tipo_entrega=(
                pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                else TipoEntregaEnum(pedido.tipo_entrega)
            ),
            origem=(
                pedido.origem if isinstance(pedido.origem, OrigemPedidoEnum)
                else OrigemPedidoEnum(pedido.origem)
            ),
            subtotal=float(pedido.subtotal or 0),
            desconto=float(pedido.desconto or 0),
            taxa_entrega=float(pedido.taxa_entrega or 0),
            taxa_servico=float(pedido.taxa_servico or 0),
            valor_total=float(pedido.valor_total or 0),
            previsao_entrega=getattr(pedido, "previsao_entrega", None),
            distancia_km=(
                float(pedido.distancia_km) if getattr(pedido, "distancia_km", None) is not None else None
            ),
            observacao_geral=getattr(pedido, "observacao_geral", None),
            troco_para=(
                float(pedido.troco_para) if getattr(pedido, "troco_para", None) is not None else None
            ),
            cupom_id=getattr(pedido, "cupom_id", None),
            data_criacao=getattr(pedido, "data_criacao", getattr(pedido, "created_at", None)),
            data_atualizacao=getattr(pedido, "data_atualizacao", getattr(pedido, "updated_at", None)),
            itens=[
                ItemPedidoResponse(
                    id=it.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    preco_unitario=float(it.preco_unitario),
                    observacao=it.observacao,
                    produto_descricao_snapshot=it.produto_descricao_snapshot,
                    produto_imagem_snapshot=it.produto_imagem_snapshot,
                )
                for it in pedido.itens
            ],
        )

    def _calcular_taxas(self, *, tipo_entrega: TipoEntregaEnum, subtotal: Decimal) -> tuple[Decimal, Decimal]:
        taxa_entrega = _dec(8.90) if tipo_entrega == TipoEntregaEnum.DELIVERY else _dec(0)
        taxa_servico = (subtotal * Decimal("0.05")).quantize(Decimal("0.01"))
        return taxa_entrega, taxa_servico

    def _aplicar_cupom(self, *, cupom_id: Optional[int], subtotal: Decimal) -> Decimal:
        if not cupom_id:
            return _dec(0)
        cupom = self.repo.get_cupom(cupom_id)
        if not cupom or not cupom.ativo:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cupom inválido ou inativo")

        # validade e mínimo
        if cupom.validade_inicio and cupom.validade_fim:
            from datetime import datetime, timezone
            now = datetime.now(tz=timezone.utc)
            if not (cupom.validade_inicio <= now <= cupom.validade_fim):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cupom fora de validade")
        if cupom.minimo_compra and subtotal < cupom.minimo_compra:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Subtotal abaixo do mínimo do cupom")

        desconto = Decimal("0")
        if cupom.desconto_valor:
            desconto += _dec(cupom.desconto_valor)
        if cupom.desconto_percentual:
            desconto += (subtotal * (Decimal(cupom.desconto_percentual) / Decimal("100"))).quantize(Decimal("0.01"))

        return min(desconto, subtotal)

    # ---------- Fluxo 1 ----------
    def finalizar_pedido(self, payload: FinalizarPedidoRequest, telefone_cliente: str) -> PedidoResponse:
        if not payload.itens:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido vazio")
        if len(payload.itens) > QTD_MAX_ITENS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Itens demais no pedido")

        empresa = self.repo_empresa.get_empresa_by_id(payload.empresa_id)
        if not empresa:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

        # validações de cliente/endereço
        if telefone_cliente:
            cliente = self.repo.get_cliente(telefone_cliente)
            if not cliente:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")

            if payload.tipo_entrega == TipoEntregaEnum.DELIVERY and not payload.endereco_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço é obrigatório para delivery")

            if payload.endereco_id:
                endereco = self.repo.get_endereco(payload.endereco_id)
                if not endereco or endereco.cliente_telefone != telefone_cliente:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço inválido para o cliente")

        try:
            pedido = self.repo.criar_pedido(
                cliente_telefone=telefone_cliente,
                empresa_id=payload.empresa_id,
                endereco_id=payload.endereco_id,
                status=PedidoStatusEnum.P.value,
                tipo_entrega=payload.tipo_entrega,
                origem=payload.origem.value,
            )

            subtotal = Decimal("0")
            for it in payload.itens:
                pe = self.repo.get_produto_emp(payload.empresa_id, it.produto_cod_barras)
                if not pe:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Produto {it.produto_cod_barras} não encontrado")
                if not pe.disponivel or not (pe.produto and pe.produto.ativo):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Produto indisponível: {it.produto_cod_barras}")

                preco = _dec(pe.preco_venda)
                subtotal += preco * it.quantidade

                self.repo.adicionar_item(
                    pedido_id=pedido.id,
                    cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    preco_unitario=preco,
                    observacao=it.observacao,
                    produto_descricao_snapshot=pe.produto.descricao if pe.produto else None,
                    produto_imagem_snapshot=pe.produto.imagem if pe.produto else None,
                )

            desconto = self._aplicar_cupom(cupom_id=payload.cupom_id, subtotal=subtotal)
            taxa_entrega, taxa_servico = self._calcular_taxas(
                tipo_entrega=payload.tipo_entrega, subtotal=subtotal
            )

            self.repo.atualizar_totais(
                pedido,
                subtotal=subtotal,
                desconto=desconto,
                taxa_entrega=taxa_entrega,
                taxa_servico=taxa_servico,
            )

            pedido.observacao_geral = payload.observacao_geral
            if payload.troco_para:
                pedido.troco_para = _dec(payload.troco_para)

            self.repo.commit()
            self.db.refresh(pedido)

        except HTTPException:
            self.repo.rollback()
            raise
        except Exception as e:
            self.repo.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao finalizar pedido: {e}")

        return self._pedido_to_response(pedido)

    # ---------- Fluxo 2 ----------
    async def confirmar_pagamento(
        self,
        *,
        pedido_id: int,
        metodo: PagamentoMetodoEnum = PagamentoMetodoEnum.PIX,
        gateway: PagamentoGatewayEnum = PagamentoGatewayEnum.PIX_INTERNO,
    ) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        if pedido.valor_total is None or pedido.valor_total <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Valor total inválido para pagamento")

        # idempotência simples
        if pedido.transacao and pedido.transacao.status in ("PAGO", "AUTORIZADO"):
            return self._pedido_to_response(pedido)

        try:
            tx = self.repo.criar_transacao_pagamento(
                pedido_id=pedido.id,
                gateway=gateway.value,
                metodo=metodo.value,
                valor=_dec(pedido.valor_total),
            )

            result = await self.gateway.charge(
                order_id=pedido.id,
                amount=_dec(pedido.valor_total),
                metodo=metodo,
                gateway=gateway,
                metadata={"empresa_id": pedido.empresa_id},
            )

            if result.status == PagamentoStatusEnum.PAGO:
                self.repo.atualizar_transacao_status(
                    tx,
                    status="PAGO",
                    provider_transaction_id=result.provider_transaction_id,
                    payload_retorno=result.payload,
                    qr_code=result.qr_code,
                    qr_code_base64=result.qr_code_base64,
                    timestamp_field="pago_em",
                )
                self.repo.atualizar_status_pedido(pedido, PedidoStatusEnum.A.value, motivo="Pagamento confirmado")
            else:
                self.repo.atualizar_transacao_status(
                    tx,
                    status="RECUSADO",
                    provider_transaction_id=result.provider_transaction_id,
                    payload_retorno=result.payload,
                )

            self.repo.commit()
            # recarrega para garantir itens/transação atualizados
            pedido = self.repo.get_pedido(pedido.id)
            return self._pedido_to_response(pedido)

        except Exception as e:
            self.repo.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao confirmar pagamento: {e}")


    def listar_pedidos(self, cliente_telefone: str, skip: int = 0, limit: int = 50) -> list[PedidoResponse]:
        logger.info(cliente_telefone)
        pedidos = self.repo.db.query(PedidoDeliveryModel)\
            .filter(PedidoDeliveryModel.cliente_telefone == cliente_telefone)\
            .order_by(PedidoDeliveryModel.data_criacao.desc())\
            .offset(skip).limit(limit).all()
        return [self._pedido_to_response(p) for p in pedidos]

    def get_pedido_by_id(self, pedido_id: int) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        return self._pedido_to_response(pedido)

    def editar_pedido(self, pedido_id: int, payload: FinalizarPedidoRequest) -> PedidoResponse:
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")

        # Só altera itens/quantidades e observação (não altera cliente/endereço)
        pedido.itens.clear()  # remove itens antigos

        subtotal = Decimal("0")
        for it in payload.itens:
            pe = self.repo.get_produto_emp(payload.empresa_id, it.produto_cod_barras)
            if not pe:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Produto {it.produto_cod_barras} não encontrado")
            preco = _dec(pe.preco_venda)
            subtotal += preco * it.quantidade

            self.repo.adicionar_item(
                pedido_id=pedido.id,
                cod_barras=it.produto_cod_barras,
                quantidade=it.quantidade,
                preco_unitario=preco,
                observacao=it.observacao,
                produto_descricao_snapshot=pe.produto.descricao if pe.produto else None,
                produto_imagem_snapshot=pe.produto.imagem if pe.produto else None,
            )

        desconto = self._aplicar_cupom(cupom_id=payload.cupom_id, subtotal=subtotal)
        taxa_entrega, taxa_servico = self._calcular_taxas(tipo_entrega=pedido.tipo_entrega, subtotal=subtotal)

        self.repo.atualizar_totais(
            pedido,
            subtotal=subtotal,
            desconto=desconto,
            taxa_entrega=taxa_entrega,
            taxa_servico=taxa_servico,
        )

        pedido.observacao_geral = payload.observacao_geral
        if payload.troco_para:
            pedido.troco_para = _dec(payload.troco_para)

        self.repo.commit()
        self.db.refresh(pedido)
        return self._pedido_to_response(pedido)



    # ======================================================================
    # ============================ ADMIN ===================================
    # ======================================================================
    def list_all(self, limit: int = 500):
        # Limite pra não estourar
        pedidos = self.repo.list_all(limit)


        Você disse:
        import apiAdmin from "@cardapio/app/api/apiAdmin";
        import { extractErrorMessage } from "@cardapio/lib/extractErrorMessage";
        import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
        import { toast } from "sonner";
        import React from "react";
        import { Pedido } from "@cardapio/types/pedido";
        import { apiClienteAdmin } from "@cardapio/app/api/apiClienteAdmin";

        /** 🔎 Tipo de um pedido resumido */
        export interface PedidoItem {
            id: number;
        cliente_nome: string;
        status: string;
        valor_total: number;
        data_criacao: string;
        }

        /** ⏳ debounce simples para evitar flood no servidor enquanto digita */
        function useDebounced<T>(value: T, delay = 300) {
            const [debounced, setDebounced] = React.useState(value);
        React.useEffect(() => {
            const t = setTimeout(() => setDebounced(value), delay);
        return () => clearTimeout(t);
        }, [value, delay]);
        return debounced;
    }

    // ==========================================================================
    // ================= Listar pedidos =================
    // ==========================================================================
    export function usePedidos() {
    return useQuery<Pedido[]>({
        queryKey: ["pedidos"],
        queryFn: async () => {
        const { data } = await apiClienteAdmin.get<Pedido[]>("/delivery/pedidos/");
    return data;
    },
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
    });
    }

    // ==========================================================================
    // ================= Hook para buscar pedido por ID =========================
    // ==========================================================================
    export function usePedidoById(pedidoId: number | null, opts?: { enabled?: boolean }) {
        const qc = useQueryClient();
    const seed = pedidoId ? qc.getQueryData<PedidoItem>(["pedido", pedidoId]) : undefined;

return useQuery({
    queryKey: ["pedido", pedidoId],
    queryFn: async () => {
    const { data } = await apiAdmin.get<PedidoItem>(/delivery/pedidos/${pedidoId});
return data;
},
initialData: seed,
enabled: !!pedidoId && (opts?.enabled ?? true),
refetchOnMount: false,
refetchOnWindowFocus: false,
refetchOnReconnect: false,
staleTime: 5 * 60 * 1000,
gcTime: 30 * 60 * 1000,
});
}

// ==========================================================================
// =========== Buscar pedidos com filtro q (server-side) ====================
// ==========================================================================
export function usePedidosSearch(
    q: string,
opts: {
    limit?: number;
offset?: number;
enabled?: boolean;
minLength?: number;
debounceMs?: number;
allowEmpty?: boolean;
} = {}
) {
    const {
    limit = 30,
offset = 0,
enabled = true,
minLength = 2,
debounceMs = 300,
allowEmpty = false,
} = opts;

const qDeb = useDebounced(q ?? "", debounceMs);
const hasTerm = qDeb.trim().length >= minLength;
const canRun = enabled && (allowEmpty || hasTerm);

return useQuery({
    queryKey: ["pedidos_search", allowEmpty ? qDeb : hasTerm ? qDeb : "", limit, offset],
queryFn: async () => {
    const params: Record<string, any> = { limit, offset };
if (allowEmpty || hasTerm) params.q = qDeb.trim();
const { data } = await apiAdmin.get<PedidoItem[]>("/delivery/pedidos/search", { params });
return data;
},
enabled: canRun,
staleTime: 10 * 60 * 1000,
gcTime: 30 * 60 * 1000,
refetchOnWindowFocus: false,
refetchOnReconnect: false,
refetchOnMount: false,
placeholderData: (old) => old,
});
}

export function usePesquisarPedidos(q: string, opts?: { limit?: number; offset?: number }) {
    const { data, isLoading, refetch } = usePedidosSearch(q, { ...opts, allowEmpty: true });
return { pedidos: data ?? [], isLoading, refetch };
}



// ==========================================================================
// ==========  Mutations para criar/atualizar/remover pedidos ===============
// ==========================================================================
export function useMutatePedido() {
const qc = useQueryClient();

const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["pedidos"] });
qc.invalidateQueries({ queryKey: ["pedidos_search"] });
};

const create = useMutation({
    mutationFn: (body: Partial<PedidoItem>) => apiAdmin.post("/delivery/pedidos", body),
onSuccess: () => {
    toast.success("Pedido criado com sucesso!");
invalidate();
},
onError: (err) => toast.error(extractErrorMessage(err)),
});

const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
apiAdmin.patch(/delivery/pedidos/${id}/status, { status }),
onSuccess: () => {
    toast.success("Status do pedido atualizado!");
invalidate();
},
onError: (err) => toast.error(extractErrorMessage(err)),
});


const remove = useMutation({
    mutationFn: (id: number) => apiAdmin.delete(/delivery/pedidos/${id}),
onSuccess: () => {
    toast.success("Pedido removido!");
invalidate();
},
onError: (err) => toast.error(extractErrorMessage(err)),
});

return { create, updateStatus, remove };
}

implemente pesquisar e atualizar a pagina aqui
"use client";

import React from "react";
import {
Card,
CardHeader,
CardTitle,
CardContent
} from "@cardapio/components/Shared/ui/card";
import {
Accordion,
AccordionItem,
AccordionTrigger,
AccordionContent
} from "@cardapio/components/Shared/ui/accordion";
import { format, isToday, isYesterday, subDays, subWeeks } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Pedido } from "@cardapio/types/pedido";
import { usePedidos } from "@cardapio/services/useQueryPedido";

const statusClasses: Record<Pedido["status"], string> = {
P: "bg-yellow-100 text-yellow-800", // PENDENTE
R: "bg-purple-100 text-purple-800", // EM PREPARO
S: "bg-blue-100 text-blue-800", // SAIU PARA ENTREGA
E: "bg-green-100 text-green-800", // ENTREGUE
C: "bg-red-100 text-red-800" // CANCELADO
};

const statusLabels: Record<Pedido["status"], string> = {
P: "Pendente",
R: "Em preparo",
E: "Entregue",
S: "Saiu para Entrega",
C: " Cancelado"
};

function getDateGroupLabel(dateStr: string): string {
const date = new Date(dateStr);
if (isToday(date)) return "Hoje";
if (isYesterday(date)) return "Ontem";
if (date > subDays(new Date(), 7)) return "Esta semana";
if (date > subWeeks(new Date(), 4)) return "Mês passado";
return "Mais antigos";
}

function groupOrdersByDate(orders: Pedido[]) {
const groups = new Map<string, Pedido[]>();
for (const order of orders) {
    const label = getDateGroupLabel(order.data_criacao);
if (!groups.has(label)) groups.set(label, []);
groups.get(label)!.push(order);
}
return groups;
}

function sortGroups(groups: Map<string, Pedido[]>) {
const order = ["Hoje", "Ontem", "Esta semana", "Mês passado", "Mais antigos"];
return [...groups.entries()].sort(([a], [b]) => order.indexOf(a) - order.indexOf(b));
}

export default function RoutePedidos() {
const { data: pedidos = [], isLoading } = usePedidos();

if (isLoading) return <div>Carregando pedidos...</div>;

const groupedOrders = groupOrdersByDate(pedidos);

return (
    <div className="min-h-screen flex flex-col gap-6 p-6">
    {sortGroups(groupedOrders).map(([group, orders]) => (
    <Card key={group} className="w-full p-0 gap-0">
    <CardHeader className="p-4 bg-primary h-12 items-center rounded-t-xl text-background">
    <CardTitle>{group}</CardTitle>
    </CardHeader>

    <CardContent className="p-0">
    <Accordion type="single" collapsible className="w-full">
    {orders.map((order) => {
    const date = new Date(order.data_criacao);
const formattedDate = isToday(date)
? "Hoje" \
: format(date, "dd/MM/yyyy HH:mm", { locale: ptBR });

return (
    <AccordionItem key={order.id} value={String(order.id)}>
<AccordionTrigger className="flex justify-between items-center px-4">
                            <div className="flex flex-col gap-2 text-left flex-1">
                                           <span className="font-semibold text-foreground">Pedido #{order.id}</span>
                                                           <span className="text-xs text-muted-foreground">
                                                                           {formattedDate} • {order.itens.length} itens
                                                                                                                  </span>
                                                                                                                    </div>

                                                                                                                      <div className="flex gap-2 items-start flex-col mt-1 mb-3">
                                                                                                                                     <span className="text-sm font-bold text-foreground">
                                                                                                                                                     R$ {order.valor_total.toFixed(2)}
                                                                                                                                                        </span>
                                                                                                                                                          <span className={inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${statusClasses[order.status]}}>
{statusLabels[order.status]}
</span>
  </div>
    </AccordionTrigger>

      <AccordionContent className="border-t p-3">
                                  <ul className="divide-y divide-muted [&>li:nth-child(even)]:bg-muted">
                                                {order.itens.map((item) => (
    <li key={item.id} className="p-2 flex items-center gap-4 rounded">
    <div className="flex-1">
    <p className="font-medium text-foreground">{item.produto_descricao_snapshot}</p>
    {item.observacao && <p className="text-xs text-muted-foreground">{item.observacao}</p>}
    </div>
    <div className="text-sm text-muted-foreground text-right">
    {item.quantidade} × R$ {item.preco_unitario.toFixed(2)}
</div>
  </li>
))}
</ul>

  <div className="mt-4 space-y-1 text-sm text-foreground">
                 <div className="flex justify-between">
                                <span>Taxa de entrega</span>
                                                       <span>R$ {order.taxa_entrega.toFixed(2)}</span>
                                                                                                 </div>
                                                                                                   <div className="flex justify-between font-bold text-emerald-600">
                                                                                                                  <span>Total</span>
                                                                                                                               <span>R$ {order.valor_total.toFixed(2)}</span>
                                                                                                                                                                        </div>
                                                                                                                                                                          </div>
                                                                                                                                                                            </AccordionContent>
                                                                                                                                                                              </AccordionItem>
);
})}
</Accordion>
  </CardContent>
    </Card>
))}
</div>
);
}

O ChatGPT disse:
Beleza! Vamos integrar a pesquisa de pedidos e permitir atualizar a página quando o usuário buscar algo, usando o hook usePesquisarPedidos que você já tem. Vou te mostrar como adicionar:

Um input de pesquisa.

Atualização dinâmica da lista de pedidos conforme o usuário digita.

Um botão de "refresh" para forçar o refetch.

Segue a versão ajustada do seu componente: \

"use client";

import React, { useState } from "react";
import {
    Card,
    CardHeader,
    CardTitle,
    CardContent
} from "@cardapio/components/Shared/ui/card";
import {
    Accordion,
    AccordionItem,
    AccordionTrigger,
    AccordionContent
} from "@cardapio/components/Shared/ui/accordion";
import { format, isToday, isYesterday, subDays, subWeeks } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Pedido } from "@cardapio/types/pedido";
import { usePesquisarPedidos, usePedidos } from "@cardapio/services/useQueryPedido";
import { Input } from "@cardapio/components/Shared/ui/input";
import { Button } from "@cardapio/components/Shared/ui/button";

const statusClasses: Record<Pedido["status"], string> = {
    P: "bg-yellow-100 text-yellow-800",
    R: "bg-purple-100 text-purple-800",
    S: "bg-blue-100 text-blue-800",
    E: "bg-green-100 text-green-800",
    C: "bg-red-100 text-red-800"
};

const statusLabels: Record<Pedido["status"], string> = {
    P: "Pendente",
    R: "Em preparo",
    E: "Entregue",
    S: "Saiu para Entrega",
    C: "Cancelado"
};

function getDateGroupLabel(dateStr: string): string {
    const date = new Date(dateStr);
if (isToday(date)) return "Hoje";
if (isYesterday(date)) return "Ontem";
if (date > subDays(new Date(), 7)) return "Esta semana";
if (date > subWeeks(new Date(), 4)) return "Mês passado";
return "Mais antigos";
}

function groupOrdersByDate(orders: Pedido[]) {
const groups = new Map<string, Pedido[]>();
for (const order of orders) {
    const label = getDateGroupLabel(order.data_criacao);
if (!groups.has(label)) groups.set(label, []);
groups.get(label)!.push(order);
}
return groups;
}

function sortGroups(groups: Map<string, Pedido[]>) {
const order = ["Hoje", "Ontem", "Esta semana", "Mês passado", "Mais antigos"];
return [...groups.entries()].sort(([a], [b]) => order.indexOf(a) - order.indexOf(b));
}

export default function RoutePedidos() {
const [search, setSearch] = useState("");
const { pedidos, isLoading, refetch } = usePesquisarPedidos(search);

const groupedOrders = groupOrdersByDate(pedidos);

return (
    <div className="min-h-screen flex flex-col gap-6 p-6">
    {/* Pesquisa e Refresh */}
    <div className="flex gap-2 mb-4">
    <Input
    placeholder="Pesquisar pedidos..."
    value={search}
    onChange={(e) => setSearch(e.target.value)}
/>
<Button onClick={() => refetch()}>Atualizar</Button>
                                             </div>

                                               {isLoading ? (
    <div>Carregando pedidos...</div>
) : groupedOrders.size === 0 ? (
    <div>Nenhum pedido encontrado.</div>
) : (
    sortGroups(groupedOrders).map(([group, orders]) => (
<Card key={group} className="w-full p-0 gap-0">
<CardHeader className="p-4 bg-primary h-12 items-center rounded-t-xl text-background">
<CardTitle>{group}</CardTitle>
</CardHeader>

<CardContent className="p-0">
<Accordion type="single" collapsible className="w-full">
{orders.map((order) => {
    const date = new Date(order.data_criacao);
const formattedDate = isToday(date)
? "Hoje" \
: format(date, "dd/MM/yyyy HH:mm", { locale: ptBR });

return (
    <AccordionItem key={order.id} value={String(order.id)}>
<AccordionTrigger className="flex justify-between items-center px-4">
                            <div className="flex flex-col gap-2 text-left flex-1">
                                           <span className="font-semibold text-foreground">Pedido #{order.id}</span>
                                                           <span className="text-xs text-muted-foreground">
                                                                           {formattedDate} • {order.itens.length} itens
                                                                                                                  </span>
                                                                                                                    </div>

                                                                                                                      <div className="flex gap-2 items-start flex-col mt-1 mb-3">
                                                                                                                                     <span className="text-sm font-bold text-foreground">
                                                                                                                                                     R$ {order.valor_total.toFixed(2)}
                                                                                                                                                        </span>
                                                                                                                                                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${statusClasses[order.status]}`}>
{statusLabels[order.status]}
</span>
  </div>
    </AccordionTrigger>

      <AccordionContent className="border-t p-3">
                                  <ul className="divide-y divide-muted [&>li:nth-child(even)]:bg-muted">
                                                {order.itens.map((item) => (
    <li key={item.id} className="p-2 flex items-center gap-4 rounded">
    <div className="flex-1">
    <p className="font-medium text-foreground">{item.produto_descricao_snapshot}</p>
    {item.observacao && <p className="text-xs text-muted-foreground">{item.observacao}</p>}
    </div>
    <div className="text-sm text-muted-foreground text-right">
    {item.quantidade} × R$ {item.preco_unitario.toFixed(2)}
</div>
  </li>
))}
</ul>

  <div className="mt-4 space-y-1 text-sm text-foreground">
                 <div className="flex justify-between">
                                <span>Taxa de entrega</span>
                                                       <span>R$ {order.taxa_entrega.toFixed(2)}</span>
                                                                                                 </div>
                                                                                                   <div className="flex justify-between font-bold text-emerald-600">
                                                                                                                  <span>Total</span>
                                                                                                                               <span>R$ {order.valor_total.toFixed(2)}</span>
                                                                                                                                                                        </div>
                                                                                                                                                                          </div>
                                                                                                                                                                            </AccordionContent>
                                                                                                                                                                              </AccordionItem>
);
})}
</Accordion>
  </CardContent>
    </Card>
))
)}
</div>
);
}
✅ O que mudou:

Adicionei um input <Input /> controlado pelo estado search.

Usei usePesquisarPedidos(search) para buscar os pedidos filtrados.

Adicionei um botão Atualizar que chama refetch().

Mostro uma mensagem caso não haja pedidos encontrados.

Mantive o agrupamento por data e o estilo existente.

Se você quiser, posso melhorar ainda mais e fazer pesquisa em tempo real com debounce, sem precisar do botão “Atualizar”, deixando a UX mais fluida.

Quer que eu faça isso também?

Você disse:
Argument of type 'PedidoItem[]' is not assignable to parameter of type 'Pedido[]'.
Type 'PedidoItem' is missing the following properties from type 'Pedido': empresa_id, tipo_entrega, origem, subtotal, and 5 more.ts(2345)
O ChatGPT disse:
Ah! Entendi exatamente o problema: você está usando o hook usePesquisarPedidos, que retorna PedidoItem[], mas o componente espera Pedido[] (que é mais completo, com campos como empresa_id, tipo_entrega, subtotal, etc).

Ou seja, tipos incompatíveis. 🤓

Existem algumas maneiras de resolver isso, dependendo do que você quer:

Opção 1 – Ajustar seu hook para buscar Pedido[]
Se você quer a lista completa de pedidos (com todos os campos), então o hook usePesquisarPedidos precisa usar usePedidosSearch<Pedido> em vez de PedidoItem.

Exemplo rápido:

export function usePesquisarPedidos(q: string, opts?: { limit?: number; offset?: number }) {
    const { data, isLoading, refetch } = useQuery<Pedido[]>({
    queryKey: ["pedidos_search", q],
    queryFn: async () => {
    const params = { q, limit: opts?.limit, offset: opts?.offset };
const { data } = await apiAdmin.get<Pedido[]>("/delivery/pedidos/search", { params });
return data;
},
enabled: true,
});

return { pedidos: data ?? [], isLoading, refetch };
}
Assim, o componente RoutePedidos continua esperando Pedido[] e não dá mais erro de tipo.

Opção 2 – Transformar PedidoItem em Pedido no frontend
Se a busca de pedidos retorna apenas dados resumidos (PedidoItem), você precisa mapear para algo compatível ou adaptar o componente para aceitar PedidoItem.

Por exemplo:

const adaptedPedidos: Pedido[] = pedidos.map(p => ({
                                                       id: p.id,
                                                       cliente_nome: p.cliente_nome,
                                                       status: p.status,
                                                       valor_total: p.valor_total,
                                                       data_criacao: p.data_criacao,
                                                       itens: [],            // se você não tem os itens, deixa vazio ou busca depois
                                                   empresa_id: 0,        // placeholder
                                                   tipo_entrega: "DELIVERY",
                                                   origem: "APP",
                                                   subtotal: p.valor_total,
                                                   taxa_entrega: 0,
                                                   taxa_servico: 0,
                                                   }));
Mas isso é meio gambiarra — se você precisa realmente mostrar itens, melhor usar Pedido[] desde o backend.

💡 Resumo:
O erro ocorre porque PedidoItem é uma versão resumida de Pedido. Para manter o componente intacto, o hook de pesquisa deve retornar Pedido[] completo, ou você precisa adaptar o componente para lidar com PedidoItem.

Se você quiser, posso reescrever o seu RoutePedidos com pesquisa em tempo real, debounce, e compatível com Pedido[] sem precisar do botão “Atualizar”, já corrigindo o problema de tipo.

Quer que eu faça isso?

Você disse:
ele deve começar com todos os pedidos e fazer a requisicao só quando tiver mais de 2 caracteres
O ChatGPT disse:
Perfeito! Então a lógica será:

Ao montar o componente, carrega todos os pedidos usando usePedidos().

Quando o usuário digitar no input:

Se tiver menos de 3 caracteres, continua mostrando os pedidos já carregados.

Se tiver 3 ou mais caracteres, dispara a busca no backend usando usePesquisarPedidos().

Mantemos debounce para não floodar o servidor.

Segue a implementação ajustada: \

"use client";

import React, { useState } from "react";
import {
Card,
CardHeader,
CardTitle,
CardContent
} from "@cardapio/components/Shared/ui/card";
import {
Accordion,
AccordionItem,
AccordionTrigger,
AccordionContent
} from "@cardapio/components/Shared/ui/accordion";
import { format, isToday, isYesterday, subDays, subWeeks } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Pedido } from "@cardapio/types/pedido";
import { usePesquisarPedidos, usePedidos } from "@cardapio/services/useQueryPedido";
import { Input } from "@cardapio/components/Shared/ui/input";

function useDebounced<T>(value: T, delay = 300) {
const [debounced, setDebounced] = React.useState(value);
React.useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
return () => clearTimeout(t);
}, [value, delay]);
return debounced;
}

const statusClasses: Record<Pedido["status"], string> = {
P: "bg-yellow-100 text-yellow-800",
R: "bg-purple-100 text-purple-800",
S: "bg-blue-100 text-blue-800",
E: "bg-green-100 text-green-800",
C: "bg-red-100 text-red-800"
};

const statusLabels: Record<Pedido["status"], string> = {
P: "Pendente",
R: "Em preparo",
E: "Entregue",
S: "Saiu para Entrega",
C: "Cancelado"
};

function getDateGroupLabel(dateStr: string): string {
const date = new Date(dateStr);
if (isToday(date)) return "Hoje";
if (isYesterday(date)) return "Ontem";
if (date > subDays(new Date(), 7)) return "Esta semana";
if (date > subWeeks(new Date(), 4)) return "Mês passado";
return "Mais antigos";
}

function groupOrdersByDate(orders: Pedido[]) {
const groups = new Map<string, Pedido[]>();
for (const order of orders) {
    const label = getDateGroupLabel(order.data_criacao);
if (!groups.has(label)) groups.set(label, []);
groups.get(label)!.push(order);
}
return groups;
}

function sortGroups(groups: Map<string, Pedido[]>) {
const order = ["Hoje", "Ontem", "Esta semana", "Mês passado", "Mais antigos"];
return [...groups.entries()].sort(([a], [b]) => order.indexOf(a) - order.indexOf(b));
}

export default function RoutePedidos() {
const { data: pedidosAll = [], isLoading: loadingAll } = usePedidos();
const [search, setSearch] = useState("");
const searchDebounced = useDebounced(search, 300);

const shouldSearch = searchDebounced.trim().length >= 3;
const { pedidos: searchResults = [], isLoading: loadingSearch } = usePesquisarPedidos(
    shouldSearch ? searchDebounced : "",
{ limit: 50 }
);

const pedidosToShow = shouldSearch ? searchResults : pedidosAll;
const groupedOrders = groupOrdersByDate(pedidosToShow);

return (
    <div className="min-h-screen flex flex-col gap-6 p-6">
    <Input
    placeholder="Pesquisar pedidos..."
    value={search}
    onChange={(e) => setSearch(e.target.value)}
className="mb-4"
          />

          {(loadingAll || loadingSearch) ? (
    <div>Carregando pedidos...</div>
) : groupedOrders.size === 0 ? (
    <div>Nenhum pedido encontrado.</div>
) : (
    sortGroups(groupedOrders).map(([group, orders]) => (
<Card key={group} className="w-full p-0 gap-0">
<CardHeader className="p-4 bg-primary h-12 items-center rounded-t-xl text-background">
<CardTitle>{group}</CardTitle>
</CardHeader>

<CardContent className="p-0">
<Accordion type="single" collapsible className="w-full">
{orders.map((order) => {
    const date = new Date(order.data_criacao);
const formattedDate = isToday(date)
? "Hoje" \
: format(date, "dd/MM/yyyy HH:mm", { locale: ptBR });

return (
    <AccordionItem key={order.id} value={String(order.id)}>
<AccordionTrigger className="flex justify-between items-center px-4">
                            <div className="flex flex-col gap-2 text-left flex-1">
                                           <span className="font-semibold text-foreground">Pedido #{order.id}</span>
                                                           <span className="text-xs text-muted-foreground">
                                                                           {formattedDate} • {order.itens.length} itens
                                                                                                                  </span>
                                                                                                                    </div>

                                                                                                                      <div className="flex gap-2 items-start flex-col mt-1 mb-3">
                                                                                                                                     <span className="text-sm font-bold text-foreground">
                                                                                                                                                     R$ {order.valor_total.toFixed(2)}
                                                                                                                                                        </span>
                                                                                                                                                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${statusClasses[order.status]}`}>
{statusLabels[order.status]}
</span>
  </div>
    </AccordionTrigger>

      <AccordionContent className="border-t p-3">
                                  <ul className="divide-y divide-muted [&>li:nth-child(even)]:bg-muted">
                                                {order.itens.map((item) => (
    <li key={item.id} className="p-2 flex items-center gap-4 rounded">
    <div className="flex-1">
    <p className="font-medium text-foreground">{item.produto_descricao_snapshot}</p>
    {item.observacao && <p className="text-xs text-muted-foreground">{item.observacao}</p>}
    </div>
    <div className="text-sm text-muted-foreground text-right">
    {item.quantidade} × R$ {item.preco_unitario.toFixed(2)}
</div>
  </li>
))}
</ul>

  <div className="mt-4 space-y-1 text-sm text-foreground">
                 <div className="flex justify-between">
                                <span>Taxa de entrega</span>
                                                       <span>R$ {order.taxa_entrega.toFixed(2)}</span>
                                                                                                 </div>
                                                                                                   <div className="flex justify-between font-bold text-emerald-600">
                                                                                                                  <span>Total</span>
                                                                                                                               <span>R$ {order.valor_total.toFixed(2)}</span>
                                                                                                                                                                        </div>
                                                                                                                                                                          </div>
                                                                                                                                                                            </AccordionContent>
                                                                                                                                                                              </AccordionItem>
);
})}
</Accordion>
  </CardContent>
    </Card>
))
)}
</div>
);
}
✅ Comportamento agora:

Começa mostrando todos os pedidos (usePedidos).

Quando o usuário digita 3 ou mais caracteres, dispara a busca (usePesquisarPedidos) no servidor.

Debounce de 300ms para não floodar requisições.

Mantém agrupamento e estilo atual.

Se você quiser, posso também mesclar os resultados de pesquisa com os itens já carregados, evitando que alguns pedidos desapareçam se o backend não retornar todos os correspondentes.

Quer que eu faça isso?

Você disse:
export function usePesquisarPedidos(q: string, opts?: { limit?: number; offset?: number }) {
    const { data, isLoading, refetch } = useQuery<Pedido[]>({
    queryKey: ["pedidos_search", q],
    queryFn: async () => {
    const params = { q, limit: opts?.limit, offset: opts?.offset };
const { data } = await apiAdmin.get<Pedido[]>("/delivery/pedidos/search", { params });
return data;
},
enabled: true,
});

return { pedidos: data ?? [], isLoading, refetch };
}

coloque aqui que só vai executar apartir de 2 caracteres
O ChatGPT disse:
Perfeito! Basta usar a opção enabled do useQuery e só ativar a query quando o termo tiver 2 ou mais caracteres. Vou ajustar seu hook:

export function usePesquisarPedidos(
q: string,
opts?: { limit?: number; offset?: number }
) {
const queryKey = ["pedidos_search", q];

const { data, isLoading, refetch } = useQuery<Pedido[]>({
    queryKey,
    queryFn: async () => {
    const params = { q, limit: opts?.limit, offset: opts?.offset };
const { data } = await apiAdmin.get<Pedido[]>("/delivery/pedidos/search", { params });
return data;
},
enabled: q.trim().length >= 2, // só executa a query se tiver 2 ou mais caracteres
staleTime: 10 * 60 * 1000,
refetchOnWindowFocus: false,
refetchOnReconnect: false,
});

return { pedidos: data ?? [], isLoading, refetch };
}
✅ O que mudou:

enabled: q.trim().length >= 2 → garante que a query só roda se o termo tiver 2 ou mais caracteres.

Mantive staleTime e outros comportamentos para cache e performance.

Se quiser, posso combinar isso com o componente de pedidos para que comece com todos os pedidos carregados e só busque no servidor quando tiver mais de 2 caracteres, mantendo debounce.

Quer que eu faça essa integração também?

Você disse:
crie aqui o pesquisar pedidos
from fastapi import APIRouter, status, Path, Query, Depends
from sqlalchemy.orm import Session

from app.api.delivery.models.cliente_dv_model import ClienteDeliveryModel
from app.api.delivery.schemas.schema_pedido_dv import FinalizarPedidoRequest, PedidoResponse, PedidoKanbanResponse
from app.api.delivery.schemas.schema_shared_enums import PagamentoMetodoEnum, PagamentoGatewayEnum, PedidoStatusEnum
from app.api.delivery.services.service_pedido import PedidoService
from app.api.mensura.models.user_model import UserModel
from app.core.admin_dependencies import get_current_user
from app.core.client_dependecies import get_cliente_by_super_token
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/pedidos", tags=["Pedidos"])


         # ======================================================================
         # ============================ ADMIN ===================================
         # ======================================================================
         @router.get(
"/admin/kanban",
response_model=list[PedidoKanbanResponse],
status_code=status.HTTP_200_OK,
dependencies=[Depends(get_current_user)]
)
def listar_pedidos_admin_kanban(
        db: Session = Depends(get_db),
):
    """
    Lista pedidos do sistema (para admin, versão resumida pro Kanban)
    """
    return PedidoService(db).list_all()

@router.put(
    "/status/{pedido_id}",
    response_model=PedidoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def atualizar_status_pedido(
        pedido_id: int = Path(..., description="ID do pedido"),
        status: PedidoStatusEnum = Query(..., description="Novo status do pedido"),
        db: Session = Depends(get_db),
):
    """
    Atualiza o status de um pedido (somente admin).
    """
    logger.info(f"[Pedidos] Atualizar status - pedido_id={pedido_id} -> {status}")
    svc = PedidoService(db)
    return svc.atualizar_status(pedido_id=pedido_id, novo_status=status)




# ======================================================================
# ============================ CLIENTE =================================
# ======================================================================

@router.post("/checkout", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
def checkout(
        payload: FinalizarPedidoRequest,
        db: Session = Depends(get_db),
        cliente: ClienteDeliveryModel = Depends(get_cliente_by_super_token),
):
    logger.info(f"[Pedidos] Checkout iniciado")
    svc = PedidoService(db)
    return svc.finalizar_pedido(payload, cliente.telefone)

@router.post("/{pedido_id}/confirmar-pagamento", response_model=PedidoResponse, status_code=status.HTTP_200_OK)
async def confirmar_pagamento(
        pedido_id: int = Path(..., description="ID do pedido"),
        metodo: PagamentoMetodoEnum = PagamentoMetodoEnum.PIX,
        gateway: PagamentoGatewayEnum = PagamentoGatewayEnum.PIX_INTERNO,
        db: Session = Depends(get_db),
):
    logger.info(f"[Pedidos] Confirmar pagamento - pedido_id={pedido_id} metodo={metodo} gateway={gateway}")
    svc = PedidoService(db)
    return await svc.confirmar_pagamento(pedido_id=pedido_id, metodo=metodo, gateway=gateway)

@router.get("/", response_model=list[PedidoResponse], status_code=status.HTTP_200_OK)
def listar_pedidos(
        cliente: ClienteDeliveryModel = Depends(get_cliente_by_super_token),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
        db: Session = Depends(get_db),
):
    svc = PedidoService(db)
    return svc.listar_pedidos(cliente_telefone=cliente.telefone, skip=skip, limit=limit)

@router.get("/{pedido_id}", response_model=PedidoResponse, status_code=status.HTTP_200_OK)
def get_pedido(pedido_id: int = Path(..., description="ID do pedido"), db: Session = Depends(get_db)):
    svc = PedidoService(db)
    return svc.get_pedido_by_id(pedido_id)

O ChatGPT disse:
Perfeito! Para criar a rota de pesquisar pedidos no backend, podemos seguir o mesmo padrão das outras rotas do admin, usando query params (q, limit, offset) e integrando ao PedidoService. Vou te mostrar uma implementação que:

Só dispara a pesquisa se q tiver 2 ou mais caracteres.

Retorna uma lista de PedidoKanbanResponse (resumido, ideal para lista ou kanban).

# ======================================================================
# ============================ PESQUISAR PEDIDOS =======================
# ======================================================================

@router.get(
    "/search",
    response_model=list[PedidoKanbanResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def pesquisar_pedidos_admin(
        q: str = Query(..., description="Termo de busca (mínimo 2 caracteres)"),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
        db: Session = Depends(get_db),
):
    """
    Pesquisa pedidos (admin) pelo termo `q`.
    Só executa se q tiver pelo menos 2 caracteres.
    Retorna lista resumida para Kanban.
    """
    if len(q.strip()) < 2:
        return []

    svc = PedidoService(db)
    return svc.search(q=q.strip(), skip=skip, limit=limit)
O que precisa no PedidoService
Você precisa criar um método search que faça algo como:

def search(self, q: str, skip: int = 0, limit: int = 50) -> list[PedidoKanbanResponse]:
    """
    Busca pedidos pelo termo `q` no nome do cliente, número do pedido ou outro campo.
    """
    query = self.db.query(PedidoDeliveryModel).join(ClienteDeliveryModel)

    # Pesquisar pelo nome do cliente ou ID do pedido
    query = query.filter(
        or_(
            ClienteDeliveryModel.nome.ilike(f"%{q}%"),
            PedidoDeliveryModel.id.cast(String).ilike(f"%{q}%")
        )
    )

    query = query.offset(skip).limit(limit).order_by(PedidoDeliveryModel.data_criacao.desc())

    results = query.all()

    # Mapear para PedidoKanbanResponse
    return [PedidoKanbanResponse.from_orm(p) for p in results]
✅ Resumo:

Rota /api/delivery/pedidos/search para admin.

Query param q com mínimo de 2 caracteres.

Suporte a skip e limit.

Retorna lista resumida (PedidoKanbanResponse) pronta para o frontend.

Se você quiser, posso fazer a versão completa para o frontend que combina todos os pedidos carregados + pesquisa a partir de 2 caracteres, usando React Query com debounce, pronta para o seu componente RoutePedidos.

Quer que eu faça isso agora?

Você disse:
arrume aqui e simplifique
// ==========================================================================
// ================= Hook para buscar pedido por ID =========================
// ==========================================================================
export function usePedidoById(pedidoId: number | null, opts?: { enabled?: boolean }) {
    const qc = useQueryClient();
const seed = pedidoId ? qc.getQueryData<PedidoItem>(["pedido", pedidoId]) : undefined;

return useQuery({
    queryKey: ["pedido", pedidoId],
    queryFn: async () => {
    const { data } = await apiAdmin.get<PedidoItem>(/delivery/pedidos/${pedidoId});
return data;
},
initialData: seed,
enabled: !!pedidoId && (opts?.enabled ?? true),
refetchOnMount: false,
refetchOnWindowFocus: false,
refetchOnReconnect: false,
staleTime: 5 * 60 * 1000,
gcTime: 30 * 60 * 1000,
});
}

// ==========================================================================
// =========== Buscar pedidos com filtro q (server-side) ====================
// ==========================================================================
export function usePedidosSearch(
    q: string,
opts: {
    limit?: number;
offset?: number;
enabled?: boolean;
minLength?: number;
debounceMs?: number;
allowEmpty?: boolean;
} = {}
) {
    const {
    limit = 30,
offset = 0,
enabled = true,
minLength = 2,
debounceMs = 300,
allowEmpty = false,
} = opts;

const qDeb = useDebounced(q ?? "", debounceMs);
const hasTerm = qDeb.trim().length >= minLength;
const canRun = enabled && (allowEmpty || hasTerm);

return useQuery({
    queryKey: ["pedidos_search", allowEmpty ? qDeb : hasTerm ? qDeb : "", limit, offset],
queryFn: async () => {
    const params: Record<string, any> = { limit, offset };
if (allowEmpty || hasTerm) params.q = qDeb.trim();
const { data } = await apiAdmin.get<PedidoItem[]>("/delivery/pedidos/search", { params });
return data;
},
enabled: canRun,
staleTime: 10 * 60 * 1000,
gcTime: 30 * 60 * 1000,
refetchOnWindowFocus: false,
refetchOnReconnect: false,
refetchOnMount: false,
placeholderData: (old) => old,
});
}

export function usePesquisarPedidos(
    q: string,
opts?: { limit?: number; offset?: number }
) {
    const queryKey = ["pedidos_search", q];

const { data, isLoading, refetch } = useQuery<Pedido[]>({
    queryKey,
    queryFn: async () => {
const params = { q, limit: opts?.limit, offset: opts?.offset };
const { data } = await apiAdmin.get<Pedido[]>("/delivery/pedidos/search", { params });
return data;
},
enabled: q.trim().length >= 2, // só executa a query se tiver 2 ou mais caracteres
staleTime: 10 * 60 * 1000,
refetchOnWindowFocus: false,
refetchOnReconnect: false,
});

return { pedidos: data ?? [], isLoading, refetch };
}
O ChatGPT disse:
Beleza! Dá pra simplificar tudo mantendo a funcionalidade:

usePedidoById fica enxuto.

usePesquisarPedidos já incorpora debounce e mínima quantidade de caracteres (minLength = 2).

usePedidosSearch não é mais necessário, podemos manter só usePesquisarPedidos.

Aqui vai a versão limpa:

import { useQuery, useQueryClient } from "@tanstack/react-query";
import apiAdmin from "@cardapio/app/api/apiAdmin";
import { Pedido } from "@cardapio/types/pedido";
import { useDebounced } from "./useDebounced"; // seu hook de debounce

                                                              // ==========================================================================
// ================= Hook para buscar pedido por ID =========================
// ==========================================================================
export function usePedidoById(pedidoId: number | null, enabled = true) {
const qc = useQueryClient();
const seed = pedidoId ? qc.getQueryData<Pedido>(["pedido", pedidoId]) : undefined;

return useQuery<Pedido>({
    queryKey: ["pedido", pedidoId],
    queryFn: async () => {
    const { data } = await apiAdmin.get<Pedido>(`/delivery/pedidos/${pedidoId}`);
return data;
},
initialData: seed,
enabled: !!pedidoId && enabled,
staleTime: 5 * 60 * 1000,
refetchOnMount: false,
refetchOnWindowFocus: false,
refetchOnReconnect: false,
});
}

// ==========================================================================
// ================= Hook para pesquisar pedidos ============================
// ==========================================================================
interface PesquisarPedidosOpts {
    limit?: number;
offset?: number;
minLength?: number;
debounceMs?: number;
}

export function usePesquisarPedidos(q: string, opts: PesquisarPedidosOpts = {}) {
    const { limit = 30, offset = 0, minLength = 2, debounceMs = 300 } = opts;
const qDebounced = useDebounced(q, debounceMs);
const canSearch = qDebounced.trim().length >= minLength;

const { data, isLoading, refetch } = useQuery<Pedido[]>({
    queryKey: ["pedidos_search", qDebounced, limit, offset],
    queryFn: async () => {
const { data } = await apiAdmin.get<Pedido[]>("/delivery/pedidos/search", {
    params: { q: qDebounced.trim(), limit, offset },
                                              });
return data;
},
enabled: canSearch,
staleTime: 10 * 60 * 1000,
refetchOnMount: false,
refetchOnWindowFocus: false,
refetchOnReconnect: false,
});

return { pedidos: data ?? [], isLoading, refetch };
}
✅ O que mudou / foi simplificado:

usePedidoById agora recebe apenas pedidoId e enabled, removeu opções desnecessárias.

usePesquisarPedidos:

Usa debounce interno.

Só pesquisa se tiver minLength caracteres.

QueryKey mais simples.

usePedidosSearch antigo foi removido, pois ficava redundante.

Se você quiser, posso fazer a versão final do RoutePedidos já usando esse hook simplificado, com todos os pedidos carregados inicialmente e pesquisa a partir de 2 caracteres, pronta para produção.

Quer que eu faça isso?

Você disse:
aqui agora
"use client";

import React, { useMemo, useState } from "react";
import { ScrollArea, ScrollBar } from "@supervisor/components/ui/scroll-area";
import {
DropdownMenu,
DropdownMenuContent,
DropdownMenuItem,
DropdownMenuTrigger,
} from "@supervisor/components/ui/dropdown-menu";
import { ArrowLeft, ArrowRight, CircleX, MoreVertical, Trash2 } from "lucide-react";
import { PedidoKanban, PedidoStatus } from "@supervisor/types/pedido";
import {  useFetchPedidosAdminKanban, useMutatePedidoAdmin } from "@supervisor/services/useQueryPedidoAdmin";

// ---------------- Status Map completo ----------------
type StatusMeta = { label: string; headerClass: string };
const statusMap: Record<PedidoStatus, StatusMeta> = {
P: { label: "Pendente", headerClass: "bg-yellow-500 text-white" },
R: { label: "Em preparo", headerClass: "bg-purple-600 text-white" },
S: { label: "Saiu para entrega", headerClass: "bg-[hsl(var(--primary))] text-white" },
E: { label: "Entregue", headerClass: "bg-green-600 text-white" },
C: { label: "Cancelados", headerClass: "bg-red-600 text-white" },
};

// ---------------- PedidoCard ----------------
const PedidoCard = React.memo(
({
    pedido,
    onMover,
    selecionado,
    onToggleSelecionado,
    onMoverSelecionadosPara,
    temSelecionados,
}: {
pedido: PedidoKanban;
onMover: (id: number, novoStatus: PedidoStatus) => void;
selecionado: boolean;
onToggleSelecionado: (id: number) => void;
onMoverSelecionadosPara: (novoStatus: PedidoStatus) => void;
temSelecionados: boolean;
}) => {
    const statusKeys = Object.keys(statusMap) as PedidoStatus[];
const index = statusKeys.indexOf(pedido.status);
const anterior = statusKeys[index - 1];
const proximo = statusKeys[index + 1];

return (
    <div className="bg-background border rounded-xl p-3 shadow-sm flex flex-col gap-2">
    <div className="flex items-center justify-between gap-3">
    <div className="flex items-center gap-2">
    <input
    type="checkbox"
    checked={selecionado}
    onChange={() => onToggleSelecionado(pedido.id)}
className="accent-primary"
          />
          <div className="text-sm">
                         <p className="font-semibold text-primary">#{pedido.id}</p>
                                      <p className="text-muted-foreground text-xs">
                                                   Cliente: {pedido.telefone_cliente || "—"}
                                                            </p>
                                                              <p className="text-green-600 font-bold text-sm">
                                                                           R$ {pedido.valor_total.toFixed(2)}
                                                                              </p>
                                                                                </div>
                                                                                  </div>

                                                                                    <DropdownMenu>
                                                                                    <DropdownMenuTrigger asChild>
                                                                                                         <button className="text-muted-foreground hover:text-primary transition">
                                                                                                                           <MoreVertical size={18} />
                                                                                                                                              </button>
                                                                                                                                                </DropdownMenuTrigger>
                                                                                                                                                  <DropdownMenuContent align="end">
                                                                                                                                                                             {anterior && (
                                                                                                                                                                                 <DropdownMenuItem
                                                                                                                                                                                 onClick={() =>
temSelecionados
? onMoverSelecionadosPara(anterior)
: onMover(pedido.id, anterior)
}
>
<ArrowLeft size={16} className="mr-2" />
                               Mover para {statusMap[anterior].label}
                                          </DropdownMenuItem>
)}
{proximo && (
    <DropdownMenuItem
    onClick={() =>
temSelecionados
? onMoverSelecionadosPara(proximo)
: onMover(pedido.id, proximo)
}
>
<ArrowRight size={16} className="mr-2" />
                                Mover para {statusMap[proximo].label}
                                           </DropdownMenuItem>
)}

<DropdownMenuItem onClick={() => onMover(pedido.id, "C")}>
<CircleX /> Cancelar
 </DropdownMenuItem>
   </DropdownMenuContent>
     </DropdownMenu>
       </div>
         </div>
);
}
);
PedidoCard.displayName = "PedidoCard";

// ---------------- KanbanColuna ----------------
const KanbanColuna = React.memo(
    ({
        statusMeta,
        pedidos,
        onMover,
        selecionados,
        onToggleSelecionado,
        onMoverSelecionadosPara,
    }: {
    statusMeta: StatusMeta;
    pedidos: PedidoKanban[];
    onMover: (id: number, novoStatus: PedidoStatus) => void;
selecionados: Set<number>;
onToggleSelecionado: (id: number) => void;
onMoverSelecionadosPara: (novoStatus: PedidoStatus) => void;
}) => (
<div className="flex flex-col h-full flex-1 bg-muted rounded shadow overflow-hidden min-w-[250px]">
<h2 className={text-center font-bold p-2 border-b ${statusMeta.headerClass}}>
{statusMeta.label}
</h2>
<ScrollArea className="flex-1 min-h-0">
<div className="flex flex-col gap-2 p-2">
{pedidos.length > 0 ? (
    pedidos.map((pedido) => (
<PedidoCard
key={pedido.id}
pedido={pedido}
onMover={onMover}
selecionado={selecionados.has(pedido.id)}
onToggleSelecionado={onToggleSelecionado}
onMoverSelecionadosPara={onMoverSelecionadosPara}
temSelecionados={selecionados.size > 0}
                />
))
) : (
    <p className="text-sm text-center text-gray-500">Sem pedidos</p>
)}
</div>
<ScrollBar orientation="vertical" />
</ScrollArea>
</div>
)
);
KanbanColuna.displayName = "KanbanColuna";

// ---------------- KanbanPedidos principal ----------------
const KanbanPedidos = () => {
    const [selecionados, setSelecionados] = useState<Set<number>>(new Set());
const [colunasVisiveis, setColunasVisiveis] = useState<Record<PedidoStatus, boolean>>(() =>
Object.keys(statusMap).reduce((acc, key) => ({ ...acc, [key]: true }), {} as Record<PedidoStatus, boolean>)
);

const { data: pedidos = [], isLoading } = useFetchPedidosAdminKanban();
const { atualizarStatus } = useMutatePedidoAdmin();

// ---------------- Agrupando pedidos por status ----------------
const pedidosPorStatus = useMemo(() => {
    const agrupados: Record<PedidoStatus, PedidoKanban[]> = {} as Record<PedidoStatus, PedidoKanban[]>;
(Object.keys(statusMap) as PedidoStatus[]).forEach((s) => (agrupados[s] = []));
pedidos.forEach((pedido) => {
    agrupados[pedido.status]?.push(pedido);
});
return agrupados;
}, [pedidos]);

const toggleSelecionado = (id: number) => {
    setSelecionados((prev) => {
    const novo = new Set(prev);
novo.has(id) ? novo.delete(id) : novo.add(id);
return novo;
});
};

const handleToggleColuna = (key: PedidoStatus) => {
    setColunasVisiveis((prev) => ({ ...prev, [key]: !prev[key] }));
};

const handleMoverPedido = (id: number, novoStatus: PedidoStatus) => {
    atualizarStatus.mutate({ id, status: novoStatus });
};

const handleMoverSelecionados = (novoStatus: PedidoStatus) => {
    selecionados.forEach((id) => atualizarStatus.mutate({ id, status: novoStatus }));
setSelecionados(new Set());
};

if (isLoading) return <p>Carregando pedidos...</p>;

return (
    <div className="h-[calc(100vh-100px)] flex flex-col p-4 space-y-4">
    <div className="flex flex-wrap gap-4 items-center">
    {Object.entries(statusMap).map(([key, meta]) => (
    <label key={key} className="flex items-center gap-2 text-sm">
    <input
    type="checkbox"
    checked={colunasVisiveis[key as PedidoStatus]}
    onChange={() => handleToggleColuna(key as PedidoStatus)}
className="accent-blue-500"
          />
          {meta.label}
          </label>
))}

<select
className="border rounded px-2 py-1 text-sm"
value=""
onChange={(e) => {
if (!e.target.value) return;
handleMoverSelecionados(e.target.value as PedidoStatus);
}}
>
<option value="">Mover selecionados para...</option>
                                             {Object.entries(statusMap).map(([key, meta]) => (
    <option key={key} value={key}>
    {meta.label}
    </option>
))}
</select>

  {selecionados.size > 0 && (
<span className="text-sm text-muted-foreground">{selecionados.size} selecionado(s)</span>
)}
</div>

  <div className="flex-1 overflow-x-auto">
                 <div className="flex gap-4 h-full">
                                {Object.entries(statusMap)
                                .filter(([key]) => colunasVisiveis[key as PedidoStatus])
.map(([statusKey, meta]) => (
    <KanbanColuna
    key={statusKey}
    statusMeta={meta}
    pedidos={pedidosPorStatus[statusKey as PedidoStatus] || []}
    onMover={handleMoverPedido}
    selecionados={selecionados}
    onToggleSelecionado={toggleSelecionado}
    onMoverSelecionadosPara={handleMoverSelecionados}
    />
))}
</div>
  </div>
    </div>
);
};

export default KanbanPedidos;
O ChatGPT disse:
Beleza! Podemos adicionar pesquisa ao seu Kanban mantendo a lista inicial de pedidos e só filtrando no servidor quando tiver 2 ou mais caracteres. Também podemos integrar o debounce para não floodar a API. Aqui vai uma versão adaptada: \

"use client";

import React, { useMemo, useState } from "react";
import { ScrollArea, ScrollBar } from "@supervisor/components/ui/scroll-area";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@supervisor/components/ui/dropdown-menu";
import { ArrowLeft, ArrowRight, CircleX, MoreVertical } from "lucide-react";
import { PedidoKanban, PedidoStatus } from "@supervisor/types/pedido";
import { useDebounced } from "@supervisor/hooks/useDebounced";
import { usePesquisarPedidos, useMutatePedidoAdmin } from "@supervisor/services/useQueryPedidoAdmin";

// ---------------- Status Map completo ----------------
type StatusMeta = { label: string; headerClass: string };
const statusMap: Record<PedidoStatus, StatusMeta> = {
    P: { label: "Pendente", headerClass: "bg-yellow-500 text-white" },
    R: { label: "Em preparo", headerClass: "bg-purple-600 text-white" },
    S: { label: "Saiu para entrega", headerClass: "bg-[hsl(var(--primary))] text-white" },
    E: { label: "Entregue", headerClass: "bg-green-600 text-white" },
    C: { label: "Cancelados", headerClass: "bg-red-600 text-white" },
};

// ---------------- KanbanPedidos principal ----------------
const KanbanPedidos = () => {
    const [selecionados, setSelecionados] = useState<Set<number>>(new Set());
const [colunasVisiveis, setColunasVisiveis] = useState<Record<PedidoStatus, boolean>>(
() => Object.keys(statusMap).reduce((acc, key) => ({ ...acc, [key]: true }), {} as Record<PedidoStatus, boolean>)
);

const [searchTerm, setSearchTerm] = useState("");
const debouncedSearch = useDebounced(searchTerm, 300);

// ---------------- Fetch pedidos (todos ou filtrados) ----------------
const { pedidos: pedidosFiltrados, isLoading } = usePesquisarPedidos(debouncedSearch, { limit: 100 });

const { atualizarStatus } = useMutatePedidoAdmin();

// ---------------- Agrupando pedidos por status ----------------
const pedidosPorStatus = useMemo(() => {
    const agrupados: Record<PedidoStatus, PedidoKanban[]> = {} as Record<PedidoStatus, PedidoKanban[]>;
(Object.keys(statusMap) as PedidoStatus[]).forEach((s) => (agrupados[s] = []));
pedidosFiltrados.forEach((pedido) => {
    agrupados[pedido.status]?.push(pedido);
});
return agrupados;
}, [pedidosFiltrados]);

const toggleSelecionado = (id: number) => {
    setSelecionados((prev) => {
    const novo = new Set(prev);
novo.has(id) ? novo.delete(id) : novo.add(id);
return novo;
});
};

const handleToggleColuna = (key: PedidoStatus) => {
    setColunasVisiveis((prev) => ({ ...prev, [key]: !prev[key] }));
};

const handleMoverPedido = (id: number, novoStatus: PedidoStatus) => {
    atualizarStatus.mutate({ id, status: novoStatus });
};

const handleMoverSelecionados = (novoStatus: PedidoStatus) => {
    selecionados.forEach((id) => atualizarStatus.mutate({ id, status: novoStatus }));
setSelecionados(new Set());
};

if (isLoading) return <p>Carregando pedidos...</p>;

return (
    <div className="h-[calc(100vh-100px)] flex flex-col p-4 space-y-4">
    {/* ---------------- Barra de pesquisa e filtros ---------------- */}
    <div className="flex flex-wrap gap-4 items-center">
    <input
    type="text"
    placeholder="Pesquisar pedidos..."
    value={searchTerm}
    onChange={(e) => setSearchTerm(e.target.value)}
className="border rounded px-2 py-1 text-sm flex-1 min-w-[200px]"
          />

          {Object.entries(statusMap).map(([key, meta]) => (
    <label key={key} className="flex items-center gap-2 text-sm">
    <input
    type="checkbox"
    checked={colunasVisiveis[key as PedidoStatus]}
    onChange={() => handleToggleColuna(key as PedidoStatus)}
className="accent-blue-500"
          />
          {meta.label}
          </label>
))}

<select
className="border rounded px-2 py-1 text-sm"
value=""
onChange={(e) => {
if (!e.target.value) return;
handleMoverSelecionados(e.target.value as PedidoStatus);
}}
>
<option value="">Mover selecionados para...</option>
                                             {Object.entries(statusMap).map(([key, meta]) => (
    <option key={key} value={key}>
    {meta.label}
    </option>
))}
</select>

  {selecionados.size > 0 && (
<span className="text-sm text-muted-foreground">{selecionados.size} selecionado(s)</span>
)}
</div>

  {/* ---------------- Kanban ---------------- */}
<div className="flex-1 overflow-x-auto">
               <div className="flex gap-4 h-full">
                              {Object.entries(statusMap)
                              .filter(([key]) => colunasVisiveis[key as PedidoStatus])
.map(([statusKey, meta]) => (
    <KanbanColuna
    key={statusKey}
    statusMeta={meta}
    pedidos={pedidosPorStatus[statusKey as PedidoStatus] || []}
    onMover={handleMoverPedido}
    selecionados={selecionados}
    onToggleSelecionado={toggleSelecionado}
    onMoverSelecionadosPara={handleMoverSelecionados}
    />
))}
</div>
  </div>
    </div>
);
};

export default KanbanPedidos;
✅ O que mudou / simplificado:
Adicionado input de pesquisa no topo.

Usando useDebounced para não floodar a API enquanto digita.

usePesquisarPedidos só executa se o termo tiver 2 ou mais caracteres (já implementado no hook).

Mantido todo o fluxo de seleção, mover pedidos e colunas visíveis.

Se você quiser, posso incluir um fallback que carrega todos os pedidos quando o input estiver vazio, para manter a visão completa do Kanban antes de digitar.

Quer que eu faça isso também?

Você disse: \
"use client";

import React, { useState } from "react";
import {
    Card,
    CardHeader,
    CardTitle,
    CardContent
} from "@cardapio/components/Shared/ui/card";
import {
    Accordion,
    AccordionItem,
    AccordionTrigger,
    AccordionContent
} from "@cardapio/components/Shared/ui/accordion";
import { format, isToday, isYesterday, subDays, subWeeks } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Pedido } from "@cardapio/types/pedido";
import { usePesquisarPedidos, usePedidos } from "@cardapio/services/useQueryPedido";
import { Input } from "@cardapio/components/Shared/ui/input";
import { Button } from "@cardapio/components/Shared/ui/button";

const statusClasses: Record<Pedido["status"], string> = {
    P: "bg-yellow-100 text-yellow-800",
    R: "bg-purple-100 text-purple-800",
    S: "bg-blue-100 text-blue-800",
    E: "bg-green-100 text-green-800",
    C: "bg-red-100 text-red-800"
};

const statusLabels: Record<Pedido["status"], string> = {
    P: "Pendente",
    R: "Em preparo",
    E: "Entregue",
    S: "Saiu para Entrega",
    C: "Cancelado"
};

function getDateGroupLabel(dateStr: string): string {
    const date = new Date(dateStr);
if (isToday(date)) return "Hoje";
if (isYesterday(date)) return "Ontem";
if (date > subDays(new Date(), 7)) return "Esta semana";
if (date > subWeeks(new Date(), 4)) return "Mês passado";
return "Mais antigos";
}

function groupOrdersByDate(orders: Pedido[]) {
const groups = new Map<string, Pedido[]>();
for (const order of orders) {
    const label = getDateGroupLabel(order.data_criacao);
if (!groups.has(label)) groups.set(label, []);
groups.get(label)!.push(order);
}
return groups;
}

function sortGroups(groups: Map<string, Pedido[]>) {
const order = ["Hoje", "Ontem", "Esta semana", "Mês passado", "Mais antigos"];
return [...groups.entries()].sort(([a], [b]) => order.indexOf(a) - order.indexOf(b));
}

export default function RoutePedidos() {
const [search, setSearch] = useState("");
const { pedidos, isLoading, refetch } = usePesquisarPedidos(search);

const groupedOrders = groupOrdersByDate(pedidos);

return (
    <div className="min-h-screen flex flex-col gap-6 p-6">
    {/* Pesquisa e Refresh */}
    <div className="flex gap-2 mb-4">
    <Input
    placeholder="Pesquisar pedidos..."
    value={search}
    onChange={(e) => setSearch(e.target.value)}
/>
<Button onClick={() => refetch()}>Atualizar</Button>
                                             </div>

                                               {isLoading ? (
    <div>Carregando pedidos...</div>
) : groupedOrders.size === 0 ? (
    <div>Nenhum pedido encontrado.</div>
) : (
    sortGroups(groupedOrders).map(([group, orders]) => (
<Card key={group} className="w-full p-0 gap-0">
<CardHeader className="p-4 bg-primary h-12 items-center rounded-t-xl text-background">
<CardTitle>{group}</CardTitle>
</CardHeader>

<CardContent className="p-0">
<Accordion type="single" collapsible className="w-full">
{orders.map((order) => {
    const date = new Date(order.data_criacao);
const formattedDate = isToday(date)
? "Hoje" \
: format(date, "dd/MM/yyyy HH:mm", { locale: ptBR });

return (
    <AccordionItem key={order.id} value={String(order.id)}>
<AccordionTrigger className="flex justify-between items-center px-4">
                            <div className="flex flex-col gap-2 text-left flex-1">
                                           <span className="font-semibold text-foreground">Pedido #{order.id}</span>
                                                           <span className="text-xs text-muted-foreground">
                                                                           {formattedDate} • {order.itens.length} itens
                                                                                                                  </span>
                                                                                                                    </div>

                                                                                                                      <div className="flex gap-2 items-start flex-col mt-1 mb-3">
                                                                                                                                     <span className="text-sm font-bold text-foreground">
                                                                                                                                                     R$ {order.valor_total.toFixed(2)}
                                                                                                                                                        </span>
                                                                                                                                                          <span className={inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${statusClasses[order.status]}}>
{statusLabels[order.status]}
</span>
  </div>
    </AccordionTrigger>

      <AccordionContent className="border-t p-3">
                                  <ul className="divide-y divide-muted [&>li:nth-child(even)]:bg-muted">
                                                {order.itens.map((item) => (
    <li key={item.id} className="p-2 flex items-center gap-4 rounded">
    <div className="flex-1">
    <p className="font-medium text-foreground">{item.produto_descricao_snapshot}</p>
    {item.observacao && <p className="text-xs text-muted-foreground">{item.observacao}</p>}
    </div>
    <div className="text-sm text-muted-foreground text-right">
    {item.quantidade} × R$ {item.preco_unitario.toFixed(2)}
</div>
  </li>
))}
</ul>

  <div className="mt-4 space-y-1 text-sm text-foreground">
                 <div className="flex justify-between">
                                <span>Taxa de entrega</span>
                                                       <span>R$ {order.taxa_entrega.toFixed(2)}</span>
                                                                                                 </div>
                                                                                                   <div className="flex justify-between font-bold text-emerald-600">
                                                                                                                  <span>Total</span>
                                                                                                                               <span>R$ {order.valor_total.toFixed(2)}</span>
                                                                                                                                                                        </div>
                                                                                                                                                                          </div>
                                                                                                                                                                            </AccordionContent>
                                                                                                                                                                              </AccordionItem>
);
})}
</Accordion>
  </CardContent>
    </Card>
))
)}
</div>
);
}

retire o pesquisar e me de completo
O ChatGPT disse:
Beleza! Você quer a versão completa do componente de pedidos, mas sem a barra de pesquisa — ou seja, ele sempre carrega todos os pedidos (ou os que o backend retornar). Aqui está a versão limpa e completa: \

"use client";

import React from "react";
import {
    Card,
    CardHeader,
    CardTitle,
    CardContent
} from "@cardapio/components/Shared/ui/card";
import {
    Accordion,
    AccordionItem,
    AccordionTrigger,
    AccordionContent
} from "@cardapio/components/Shared/ui/accordion";
import { format, isToday, isYesterday, subDays, subWeeks } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Pedido } from "@cardapio/types/pedido";
import { usePedidos } from "@cardapio/services/useQueryPedido";

const statusClasses: Record<Pedido["status"], string> = {
    P: "bg-yellow-100 text-yellow-800",
    R: "bg-purple-100 text-purple-800",
    S: "bg-blue-100 text-blue-800",
    E: "bg-green-100 text-green-800",
    C: "bg-red-100 text-red-800"
};

const statusLabels: Record<Pedido["status"], string> = {
    P: "Pendente",
    R: "Em preparo",
    E: "Entregue",
    S: "Saiu para Entrega",
    C: "Cancelado"
};

function getDateGroupLabel(dateStr: string): string {
    const date = new Date(dateStr);
if (isToday(date)) return "Hoje";
if (isYesterday(date)) return "Ontem";
if (date > subDays(new Date(), 7)) return "Esta semana";
if (date > subWeeks(new Date(), 4)) return "Mês passado";
return "Mais antigos";
}

function groupOrdersByDate(orders: Pedido[]) {
const groups = new Map<string, Pedido[]>();
for (const order of orders) {
    const label = getDateGroupLabel(order.data_criacao);
if (!groups.has(label)) groups.set(label, []);
groups.get(label)!.push(order);
}
return groups;
}

function sortGroups(groups: Map<string, Pedido[]>) {
const order = ["Hoje", "Ontem", "Esta semana", "Mês passado", "Mais antigos"];
return [...groups.entries()].sort(([a], [b]) => order.indexOf(a) - order.indexOf(b));
}

export default function RoutePedidos() {
const { pedidos, isLoading } = usePedidos(); // pega todos os pedidos

const groupedOrders = groupOrdersByDate(pedidos);

return (
    <div className="min-h-screen flex flex-col gap-6 p-6">
    {isLoading ? (
    <div>Carregando pedidos...</div>
) : groupedOrders.size === 0 ? (
    <div>Nenhum pedido encontrado.</div>
) : (
    sortGroups(groupedOrders).map(([group, orders]) => (
<Card key={group} className="w-full p-0 gap-0">
<CardHeader className="p-4 bg-primary h-12 items-center rounded-t-xl text-background">
<CardTitle>{group}</CardTitle>
</CardHeader>

<CardContent className="p-0">
<Accordion type="single" collapsible className="w-full">
{orders.map((order) => {
    const date = new Date(order.data_criacao);
const formattedDate = isToday(date)
? "Hoje" \
: format(date, "dd/MM/yyyy HH:mm", { locale: ptBR });

return (
    <AccordionItem key={order.id} value={String(order.id)}>
<AccordionTrigger className="flex justify-between items-center px-4">
                            <div className="flex flex-col gap-2 text-left flex-1">
                                           <span className="font-semibold text-foreground">Pedido #{order.id}</span>
                                                           <span className="text-xs text-muted-foreground">
                                                                           {formattedDate} • {order.itens.length} itens
                                                                                                                  </span>
                                                                                                                    </div>

                                                                                                                      <div className="flex gap-2 items-start flex-col mt-1 mb-3">
                                                                                                                                     <span className="text-sm font-bold text-foreground">
                                                                                                                                                     R$ {order.valor_total.toFixed(2)}
                                                                                                                                                        </span>
                                                                                                                                                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${statusClasses[order.status]}`}>
{statusLabels[order.status]}
</span>
  </div>
    </AccordionTrigger>

      <AccordionContent className="border-t p-3">
                                  <ul className="divide-y divide-muted [&>li:nth-child(even)]:bg-muted">
                                                {order.itens.map((item) => (
    <li key={item.id} className="p-2 flex items-center gap-4 rounded">
    <div className="flex-1">
    <p className="font-medium text-foreground">{item.produto_descricao_snapshot}</p>
    {item.observacao && <p className="text-xs text-muted-foreground">{item.observacao}</p>}
    </div>
    <div className="text-sm text-muted-foreground text-right">
    {item.quantidade} × R$ {item.preco_unitario.toFixed(2)}
</div>
  </li>
))}
</ul>

  <div className="mt-4 space-y-1 text-sm text-foreground">
                 <div className="flex justify-between">
                                <span>Taxa de entrega</span>
                                                       <span>R$ {order.taxa_entrega.toFixed(2)}</span>
                                                                                                 </div>
                                                                                                   <div className="flex justify-between font-bold text-emerald-600">
                                                                                                                  <span>Total</span>
                                                                                                                               <span>R$ {order.valor_total.toFixed(2)}</span>
                                                                                                                                                                        </div>
                                                                                                                                                                          </div>
                                                                                                                                                                            </AccordionContent>
                                                                                                                                                                              </AccordionItem>
);
})}
</Accordion>
  </CardContent>
    </Card>
))
)}
</div>
);
}
✅ O que foi feito:
Removido o input de pesquisa e botão de atualizar.

Continua usando o hook usePedidos() para pegar todos os pedidos do backend.

Mantida a lógica de agrupamento por data (Hoje, Ontem, Esta semana, etc.).

Mantida a exibição de itens, status e total dentro de cada AccordionItem.

Se você quiser, posso criar uma versão ainda mais enxuta, sem Accordion, apenas mostrando cards simples agrupados por dia, que fica mais limpo visualmente.

Quer que eu faça isso também?

Você disse:
Argument of type 'Pedido[] | undefined' is not assignable to parameter of type 'Pedido[]'.
Type 'undefined' is not assignable to type 'Pedido[]'.ts(2345)
O ChatGPT disse:
Ah, esse erro é clássico do TypeScript: ele está reclamando porque groupOrdersByDate espera sempre um array de Pedido[], mas você está passando algo que pode ser undefined (pedidos do seu hook).

No seu código, você tem:

const { pedidos, isLoading } = usePedidos();
const groupedOrders = groupOrdersByDate(pedidos);
O pedidos pode ser undefined enquanto o hook ainda carrega os dados. Para resolver, você só precisa garantir que sempre passe um array, mesmo que vazio. Ou seja, faça assim:

const groupedOrders = groupOrdersByDate(pedidos ?? []);
Ou, de forma mais segura já no hook:

const { pedidos = [], isLoading } = usePedidos();
const groupedOrders = groupOrdersByDate(pedidos);
💡 Explicação:

pedidos ?? [] → se pedidos for undefined, usa array vazio.

Isso remove o erro do TypeScript, porque agora groupOrdersByDate sempre recebe um Pedido[], nunca undefined.

Quer que eu já te passe a versão completa do RoutePedidos corrigida com isso aplicado?

Você disse:
    @router.get(
    "/admin/kanban",
    response_model=list[PedidoKanbanResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
def listar_pedidos_admin_kanban(
        db: Session = Depends(get_db),
):
    """
    Lista pedidos do sistema (para admin, versão resumida pro Kanban)
    """
    return PedidoService(db).list_all()


    # ======================================================================
    # ============================ ADMIN ===================================
    # ======================================================================
    def list_all(self):
        # Limite pra não estourar
        return self.repo.list_all(limit=500)


    def list_all(self, limit: int = 500):
        return (
            self.db.query(PedidoDeliveryModel)
            .order_by(PedidoDeliveryModel.data_criacao.desc())
            .limit(limit)
            .all()
        )


quero que ele retore o nome do cliente de acordo com o numero

import base64
import hashlib
import secrets

from sqlalchemy import Column, String, Date, Boolean, DateTime, func, Index
from sqlalchemy.orm import relationship
from app.database.db_connection import Base
from pydantic import ConfigDict

def default_super_token():
    raw = secrets.token_bytes(32)
    hashed = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(hashed).rstrip(b'=').decode('ascii')

class ClienteDeliveryModel(Base):
    __tablename__ = "clientes_dv"
    __table_args__ = (
        Index("idx_clientes_cpf", "cpf"),
        Index("idx_clientes_email", "email"),
        {"schema": "delivery"},
    )

    telefone = Column(String(20), primary_key=True)  # PK principal
    nome = Column(String(100), nullable=False)
    cpf = Column(String(14), unique=True, nullable=True)
    email = Column(String(100), nullable=True)
    data_nascimento = Column(Date, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    super_token = Column(String, unique=True, nullable=False, default=default_super_token)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    pedidos = relationship(
        "PedidoDeliveryModel",
        back_populates="cliente",
        cascade="all, delete-orphan",
        foreign_keys="PedidoDeliveryModel.cliente_telefone"  # especifica a FK correta
    )

    enderecos = relationship("EnderecoDeliveryModel", back_populates="cliente", cascade="all, delete-orphan")

    model_config = ConfigDict(from_attributes=True)
#
O ChatGPT disse:
Perfeito! Você quer que o endpoint de Kanban admin retorne os pedidos incluindo o nome do cliente, não apenas o telefone. Para isso, precisamos fazer um join entre PedidoDeliveryModel e ClienteDeliveryModel na query. Vou te mostrar como refatorar o serviço e o repositório de forma simples e eficiente.

1️⃣ Repositório de Pedidos (ou service) com join
from sqlalchemy.orm import Session, joinedload
from app.api.delivery.models.pedido_dv_model import PedidoDeliveryModel
from app.api.delivery.models.cliente_dv_model import ClienteDeliveryModel
from app.api.delivery.schemas.schema_pedido_dv import PedidoKanbanResponse

class PedidoRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self, limit: int = 500):
        """
        Retorna pedidos com dados do cliente (nome e telefone), ordenados por data de criação
        """
        return (
            self.db.query(PedidoDeliveryModel)
            .options(joinedload(PedidoDeliveryModel.cliente))  # traz cliente junto
            .order_by(PedidoDeliveryModel.data_criacao.desc())
            .limit(limit)
            .all()
        )
2️⃣ Service de Pedidos
class PedidoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PedidoRepository(db)


    def list_all(self, limit: int = 500):
        pedidos = self.repo.list_all(limit)
        resultados = []

        for p in pedidos:
            cliente = p.cliente
            endereco = cliente.enderecos[0] if cliente and cliente.enderecos else None

            resultados.append(
                PedidoKanbanResponse(
                    id=p.id,
                    status=p.status,
                    valor_total=p.valor_total,
                    data_criacao=p.data_criacao,
                    telefone_cliente=cliente.telefone if cliente else None,
                    nome_cliente=cliente.nome if cliente else None,
                    endereco_cliente={
                        "rua": endereco.rua,
                        "numero": endereco.numero,
                        "bairro": endereco.bairro,
                        "cidade": endereco.cidade,
                        "cep": endereco.cep,
                        "complemento": endereco.complemento,
                    } if endereco else None,
                )
            )

        return resultados

    def atualizar_status(self, pedido_id: int, novo_status: str):
        pedido = self.db.query(PedidoDeliveryModel).filter_by(id=pedido_id).first()
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido não encontrado"
            )

        pedido.status = novo_status
        self.db.commit()
        self.db.refresh(pedido)
        return pedido
