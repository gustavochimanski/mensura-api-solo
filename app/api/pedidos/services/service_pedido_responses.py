from __future__ import annotations

from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel
from app.api.cadastros.schemas.schema_cliente import ClienteOut
from app.api.cadastros.schemas.schema_cupom import CupomOut
from app.api.cadastros.schemas.schema_endereco import EnderecoOut
from app.api.cadastros.schemas.schema_entregador import EntregadorOut
from app.api.cadastros.schemas.schema_meio_pagamento import MeioPagamentoResponse
from app.api.pedidos.schemas.schema_pedido import (
    EnderecoPedidoDetalhe,
    ItemPedidoResponse,
    PedidoResponse,
    PedidoResponseCompleto,
    PedidoResponseCompletoComEndereco,
    PedidoResponseCompletoTotal,
    PedidoResponseSimplificado,
)
from app.api.pedidos.schemas.schema_pedido_status_historico import PedidoStatusHistoricoOut
from app.api.shared.schemas.schema_shared_enums import (
    OrigemPedidoEnum,
    PedidoStatusEnum,
    TipoEntregaEnum,
)
from app.api.cardapio.schemas.schema_transacao_pagamento import TransacaoResponse
from app.api.pedidos.services.service_pedido_helpers import build_pagamento_resumo
from app.api.pedidos.utils.produtos_builder import build_produtos_out_from_items
from app.api.empresas.schemas.schema_empresa import EmpresaResponse


class PedidoResponseBuilder:
    """Classe responsável por converter modelos de pedido em diferentes tipos de responses."""

    @staticmethod
    def _build_produtos(pedido: PedidoUnificadoModel):
        # produtos_snapshot foi removido - receitas e combos agora estão nos itens do pedido
        return build_produtos_out_from_items(pedido.itens, None)

    @staticmethod
    def pedido_to_response(pedido: PedidoUnificadoModel) -> PedidoResponse:
        """Converte pedido para PedidoResponse padrão."""
        pagamento = build_pagamento_resumo(pedido)
        return PedidoResponse(
            id=pedido.id,
            status=PedidoStatusEnum(pedido.status),
            cliente_id=pedido.cliente.id if pedido.cliente else None,
            telefone_cliente=pedido.cliente.telefone if pedido.cliente else None,
            empresa_id=pedido.empresa_id,
            entregador_id=getattr(pedido, "entregador_id", None),
            endereco_id=pedido.endereco_id,
            meio_pagamento_id=pedido.meio_pagamento_id,
            tipo_entrega=pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                        else TipoEntregaEnum(pedido.tipo_entrega),
            origem=OrigemPedidoEnum(pedido.canal.value if hasattr(pedido.canal, 'value') else pedido.canal) if pedido.canal else OrigemPedidoEnum.WEB,
            subtotal=float(pedido.subtotal or 0),
            desconto=float(pedido.desconto or 0),
            taxa_entrega=float(pedido.taxa_entrega or 0),
            taxa_servico=float(pedido.taxa_servico or 0),
            valor_total=float(pedido.valor_total or 0),
            previsao_entrega=getattr(pedido, "previsao_entrega", None),
            distancia_km=(float(pedido.distancia_km) if getattr(pedido, "distancia_km", None) is not None else None),
            observacao_geral=getattr(pedido, "observacao_geral", None),
            troco_para=(float(pedido.troco_para) if getattr(pedido, "troco_para", None) is not None else None),
            cupom_id=getattr(pedido, "cupom_id", None),
            endereco_snapshot=getattr(pedido, "endereco_snapshot", None),
            endereco_geography=str(getattr(pedido, "endereco_geo", None)) if getattr(pedido, "endereco_geo", None) is not None else None,
            data_criacao=getattr(pedido, "data_criacao", getattr(pedido, "created_at", None)),
            data_atualizacao=getattr(pedido, "data_atualizacao", getattr(pedido, "updated_at", None)),
            itens=[
                ItemPedidoResponse(
                    id=it.id,
                    produto_cod_barras=getattr(it, "produto_cod_barras", None),
                    combo_id=getattr(it, "combo_id", None),
                    receita_id=getattr(it, "receita_id", None),
                    quantidade=it.quantidade,
                    preco_unitario=float(it.preco_unitario),
                    observacao=it.observacao,
                    produto_descricao_snapshot=getattr(it, "produto_descricao_snapshot", None),
                    produto_imagem_snapshot=getattr(it, "produto_imagem_snapshot", None),
                )
                for it in pedido.itens
            ],
            transacao=TransacaoResponse.model_validate(pedido.transacao) if pedido.transacao else None,
            pagamento=pagamento,
            acertado_entregador=getattr(pedido, "acertado_entregador", None),
            produtos=PedidoResponseBuilder._build_produtos(pedido),
        )

    @staticmethod
    def pedido_to_response_completo(pedido: PedidoUnificadoModel) -> PedidoResponseCompleto:
        """Converte pedido para PedidoResponseCompleto."""
        pagamento = build_pagamento_resumo(pedido)
        return PedidoResponseCompleto(
            id=pedido.id,
            status=PedidoStatusEnum(pedido.status),
            cliente=ClienteOut.model_validate(pedido.cliente) if pedido.cliente else None,
            empresa_id=pedido.empresa_id,
            entregador_id=getattr(pedido, "entregador_id", None),
            endereco_id=pedido.endereco_id,
            meio_pagamento_id=pedido.meio_pagamento_id,
            tipo_entrega=pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                        else TipoEntregaEnum(pedido.tipo_entrega),
            origem=OrigemPedidoEnum(pedido.canal.value if hasattr(pedido.canal, 'value') else pedido.canal) if pedido.canal else OrigemPedidoEnum.WEB,
            subtotal=float(pedido.subtotal or 0),
            desconto=float(pedido.desconto or 0),
            taxa_entrega=float(pedido.taxa_entrega or 0),
            taxa_servico=float(pedido.taxa_servico or 0),
            valor_total=float(pedido.valor_total or 0),
            previsao_entrega=getattr(pedido, "previsao_entrega", None),
            distancia_km=(float(pedido.distancia_km) if getattr(pedido, "distancia_km", None) is not None else None),
            observacao_geral=getattr(pedido, "observacao_geral", None),
            troco_para=(float(pedido.troco_para) if getattr(pedido, "troco_para", None) is not None else None),
            cupom_id=getattr(pedido, "cupom_id", None),
            endereco_snapshot=getattr(pedido, "endereco_snapshot", None),
            endereco_geography=str(getattr(pedido, "endereco_geo", None)) if getattr(pedido, "endereco_geo", None) is not None else None,
            data_criacao=getattr(pedido, "data_criacao", getattr(pedido, "created_at", None)),
            data_atualizacao=getattr(pedido, "data_atualizacao", getattr(pedido, "updated_at", None)),
            itens=[
                ItemPedidoResponse(
                    id=it.id,
                    produto_cod_barras=getattr(it, "produto_cod_barras", None),
                    combo_id=getattr(it, "combo_id", None),
                    receita_id=getattr(it, "receita_id", None),
                    quantidade=it.quantidade,
                    preco_unitario=float(it.preco_unitario or 0),
                    observacao=it.observacao,
                    produto_descricao_snapshot=getattr(it, "produto_descricao_snapshot", None),
                    produto_imagem_snapshot=getattr(it, "produto_imagem_snapshot", None),
                )
                for it in pedido.itens
            ],
            pagamento=pagamento,
            produtos=PedidoResponseBuilder._build_produtos(pedido),
        )

    @staticmethod
    def pedido_to_response_completo_com_endereco(pedido: PedidoUnificadoModel) -> PedidoResponseCompletoComEndereco:
        """Converte pedido para PedidoResponseCompletoComEndereco."""
        pagamento = build_pagamento_resumo(pedido)
        return PedidoResponseCompletoComEndereco(
            id=pedido.id,
            status=PedidoStatusEnum(pedido.status),
            cliente=ClienteOut.model_validate(pedido.cliente) if pedido.cliente else None,
            endereco=EnderecoOut.model_validate(pedido.endereco) if pedido.endereco else None,
            empresa_id=pedido.empresa_id,
            entregador_id=getattr(pedido, "entregador_id", None),
            meio_pagamento_id=pedido.meio_pagamento_id,
            tipo_entrega=pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                        else TipoEntregaEnum(pedido.tipo_entrega),
            origem=OrigemPedidoEnum(pedido.canal.value if hasattr(pedido.canal, 'value') else pedido.canal) if pedido.canal else OrigemPedidoEnum.WEB,
            subtotal=float(pedido.subtotal or 0),
            desconto=float(pedido.desconto or 0),
            taxa_entrega=float(pedido.taxa_entrega or 0),
            taxa_servico=float(pedido.taxa_servico or 0),
            valor_total=float(pedido.valor_total or 0),
            previsao_entrega=getattr(pedido, "previsao_entrega", None),
            distancia_km=(float(pedido.distancia_km) if getattr(pedido, "distancia_km", None) is not None else None),
            observacao_geral=getattr(pedido, "observacao_geral", None),
            troco_para=(float(pedido.troco_para) if getattr(pedido, "troco_para", None) is not None else None),
            cupom_id=getattr(pedido, "cupom_id", None),
            endereco_snapshot=getattr(pedido, "endereco_snapshot", None),
            endereco_geography=str(getattr(pedido, "endereco_geo", None)) if getattr(pedido, "endereco_geo", None) is not None else None,
            data_criacao=getattr(pedido, "data_criacao", getattr(pedido, "created_at", None)),
            data_atualizacao=getattr(pedido, "data_atualizacao", getattr(pedido, "updated_at", None)),
            itens=[
                ItemPedidoResponse(
                    id=it.id,
                    produto_cod_barras=getattr(it, "produto_cod_barras", None),
                    combo_id=getattr(it, "combo_id", None),
                    receita_id=getattr(it, "receita_id", None),
                    quantidade=it.quantidade,
                    preco_unitario=float(it.preco_unitario or 0),
                    observacao=it.observacao,
                    produto_descricao_snapshot=getattr(it, "produto_descricao_snapshot", None),
                    produto_imagem_snapshot=getattr(it, "produto_imagem_snapshot", None),
                )
                for it in pedido.itens
            ],
            pagamento=pagamento,
            produtos=PedidoResponseBuilder._build_produtos(pedido),
        )

    @staticmethod
    def build_endereco_selecionado(pedido: PedidoUnificadoModel) -> EnderecoOut | dict | None:
        """Constrói endereço selecionado do pedido."""
        if pedido.endereco_snapshot:
            return pedido.endereco_snapshot

        if pedido.endereco:
            return EnderecoOut.model_validate(pedido.endereco)

        return None

    @staticmethod
    def build_outros_enderecos(pedido: PedidoUnificadoModel) -> list[EnderecoOut | dict]:
        """Constrói lista de outros endereços do cliente (exceto o selecionado)."""
        if not pedido.cliente or not getattr(pedido.cliente, "enderecos", None):
            return []

        endereco_id_selecionado = None
        if pedido.endereco_snapshot and isinstance(pedido.endereco_snapshot, dict):
            endereco_id_selecionado = pedido.endereco_snapshot.get("id")
        elif pedido.endereco_id:
            endereco_id_selecionado = pedido.endereco_id

        outros = []
        for endereco in pedido.cliente.enderecos:
            if endereco_id_selecionado and getattr(endereco, "id", None) == endereco_id_selecionado:
                continue
            outros.append(EnderecoOut.model_validate(endereco))

        return outros


    @staticmethod
    def build_historico_response(historico):
        """Converte histórico do modelo unificado para o formato de resposta."""
        from app.api.cadastros.schemas.schema_shared_enums import PedidoStatusEnum
        
        # Extrai username do UserModel
        criado_por_str = None
        if hasattr(historico, 'usuario') and historico.usuario:
            if hasattr(historico.usuario, 'username'):
                criado_por_str = historico.usuario.username
        elif hasattr(historico, 'criado_por') and historico.criado_por:
            if hasattr(historico.criado_por, 'username'):
                criado_por_str = historico.criado_por.username
            elif isinstance(historico.criado_por, str):
                criado_por_str = historico.criado_por
        
        # Determina status (prioriza status_novo, depois status_anterior, depois status direto)
        status = None
        if hasattr(historico, 'status_novo') and historico.status_novo:
            status = PedidoStatusEnum(historico.status_novo.value) if hasattr(historico.status_novo, 'value') else PedidoStatusEnum(historico.status_novo)
        elif hasattr(historico, 'status_anterior') and historico.status_anterior:
            status = PedidoStatusEnum(historico.status_anterior.value) if hasattr(historico.status_anterior, 'value') else PedidoStatusEnum(historico.status_anterior)
        elif hasattr(historico, 'status') and historico.status:
            status = PedidoStatusEnum(historico.status.value) if hasattr(historico.status, 'value') else PedidoStatusEnum(historico.status)
        
        status_anterior = None
        if hasattr(historico, 'status_anterior') and historico.status_anterior:
            status_anterior = PedidoStatusEnum(historico.status_anterior.value) if hasattr(historico.status_anterior, 'value') else PedidoStatusEnum(historico.status_anterior)
        
        status_novo = None
        if hasattr(historico, 'status_novo') and historico.status_novo:
            status_novo = PedidoStatusEnum(historico.status_novo.value) if hasattr(historico.status_novo, 'value') else PedidoStatusEnum(historico.status_novo)
        
        # Cria um dicionário com os dados do histórico
        historico_dict = {
            'id': historico.id,
            'pedido_id': historico.pedido_id,
            'status': status,
            'status_anterior': status_anterior,
            'status_novo': status_novo,
            'tipo_operacao': historico.tipo_operacao.value if hasattr(historico, 'tipo_operacao') and historico.tipo_operacao and hasattr(historico.tipo_operacao, 'value') else (historico.tipo_operacao if hasattr(historico, 'tipo_operacao') else None),
            'descricao': getattr(historico, 'descricao', None),
            'motivo': getattr(historico, 'motivo', None),
            'observacoes': getattr(historico, 'observacoes', None),
            'criado_em': getattr(historico, 'created_at', getattr(historico, 'criado_em', None)),
            'criado_por': criado_por_str,
            'usuario_id': getattr(historico, 'usuario_id', None),
            'cliente_id': getattr(historico, 'cliente_id', None),
            'ip_origem': getattr(historico, 'ip_origem', None),
            'user_agent': getattr(historico, 'user_agent', None),
        }
        
        return PedidoStatusHistoricoOut.model_validate(historico_dict)

    @staticmethod
    def pedido_to_response_completo_total(pedido: PedidoUnificadoModel) -> PedidoResponseCompletoTotal:
        """Converte pedido para PedidoResponseCompletoTotal com todos os relacionamentos."""
        pagamento = build_pagamento_resumo(pedido)
        return PedidoResponseCompletoTotal(
            id=pedido.id,
            status=PedidoStatusEnum(pedido.status),
            cliente=ClienteOut.model_validate(pedido.cliente) if pedido.cliente else None,
            endereco=EnderecoPedidoDetalhe(
                endereco_selecionado=PedidoResponseBuilder.build_endereco_selecionado(pedido),
                outros_enderecos=PedidoResponseBuilder.build_outros_enderecos(pedido),
            ),
            empresa=EmpresaResponse.model_validate(pedido.empresa) if pedido.empresa else None,
            entregador=EntregadorOut.model_validate(pedido.entregador) if pedido.entregador else None,
            meio_pagamento=MeioPagamentoResponse.model_validate(pedido.meio_pagamento) if pedido.meio_pagamento else None,
            cupom=CupomOut.model_validate(pedido.cupom) if pedido.cupom else None,
            transacao=TransacaoResponse.model_validate(pedido.transacao) if pedido.transacao else None,
            historicos=[PedidoResponseBuilder.build_historico_response(h) for h in pedido.historicos] if pedido.historicos else [],
            tipo_entrega=pedido.tipo_entrega if isinstance(pedido.tipo_entrega, TipoEntregaEnum)
                        else TipoEntregaEnum(pedido.tipo_entrega),
            origem=OrigemPedidoEnum(pedido.canal.value if hasattr(pedido.canal, 'value') else pedido.canal) if pedido.canal else OrigemPedidoEnum.WEB,
            subtotal=float(pedido.subtotal or 0),
            desconto=float(pedido.desconto or 0),
            taxa_entrega=float(pedido.taxa_entrega or 0),
            taxa_servico=float(pedido.taxa_servico or 0),
            valor_total=float(pedido.valor_total or 0),
            previsao_entrega=getattr(pedido, "previsao_entrega", None),
            distancia_km=(float(pedido.distancia_km) if getattr(pedido, "distancia_km", None) is not None else None),
            observacao_geral=getattr(pedido, "observacao_geral", None),
            troco_para=(float(pedido.troco_para) if getattr(pedido, "troco_para", None) is not None else None),
            endereco_snapshot=getattr(pedido, "endereco_snapshot", None),
            endereco_geography=str(getattr(pedido, "endereco_geo", None)) if getattr(pedido, "endereco_geo", None) is not None else None,
            data_criacao=getattr(pedido, "data_criacao", getattr(pedido, "created_at", None)),
            data_atualizacao=getattr(pedido, "data_atualizacao", getattr(pedido, "updated_at", None)),
            itens=[
                ItemPedidoResponse(
                    id=it.id,
                    produto_cod_barras=getattr(it, "produto_cod_barras", None),
                    combo_id=getattr(it, "combo_id", None),
                    receita_id=getattr(it, "receita_id", None),
                    quantidade=it.quantidade,
                    preco_unitario=float(it.preco_unitario or 0),
                    observacao=it.observacao,
                    produto_descricao_snapshot=getattr(it, "produto_descricao_snapshot", None),
                    produto_imagem_snapshot=getattr(it, "produto_imagem_snapshot", None),
                )
                for it in pedido.itens
            ],
            pagamento=pagamento,
            produtos=PedidoResponseBuilder._build_produtos(pedido),
        )

    @staticmethod
    def pedido_to_response_simplificado(pedido: PedidoUnificadoModel) -> PedidoResponseSimplificado:
        """Converte pedido para formato simplificado com apenas campos essenciais."""
        # Obtém nome do meio de pagamento
        meio_pagamento_nome = None
        if pedido.meio_pagamento:
            meio_pagamento_nome = pedido.meio_pagamento.display()
        
        pagamento = build_pagamento_resumo(pedido)
        return PedidoResponseSimplificado(
            id=pedido.id,
            status=PedidoStatusEnum(pedido.status),
            cliente_nome=pedido.cliente.nome if pedido.cliente else "Cliente não informado",
            cliente_telefone=pedido.cliente.telefone if pedido.cliente else None,
            subtotal=float(pedido.subtotal or 0),
            desconto=float(pedido.desconto or 0),
            taxa_entrega=float(pedido.taxa_entrega or 0),
            taxa_servico=float(pedido.taxa_servico or 0),
            valor_total=float(pedido.valor_total or 0),
            previsao_entrega=getattr(pedido, "previsao_entrega", None),
            observacao_geral=getattr(pedido, "observacao_geral", None),
            troco_para=(float(pedido.troco_para) if getattr(pedido, "troco_para", None) is not None else None),
            endereco_snapshot=getattr(pedido, "endereco_snapshot", None),
            data_criacao=getattr(pedido, "data_criacao", getattr(pedido, "created_at", None)),
            data_atualizacao=getattr(pedido, "data_atualizacao", getattr(pedido, "updated_at", None)),
            itens=[
                ItemPedidoResponse(
                    id=it.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    preco_unitario=float(it.preco_unitario or 0),
                    observacao=it.observacao,
                    produto_descricao_snapshot=it.produto_descricao_snapshot,
                    produto_imagem_snapshot=it.produto_imagem_snapshot
                ) for it in pedido.itens
            ],
            meio_pagamento_nome=meio_pagamento_nome,
            pagamento=pagamento,
            produtos=PedidoResponseBuilder._build_produtos(pedido),
        )

