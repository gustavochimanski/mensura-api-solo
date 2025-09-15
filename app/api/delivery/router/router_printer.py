"""
Router para operações relacionadas à Printer API
"""
from typing import List, Optional
from fastapi import APIRouter, status, Path, Query, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.delivery.services.printer_service import PrinterService
from app.api.delivery.schemas.schema_printer import (
    RespostaImpressaoPrinter,
    RespostaImpressaoMultipla,
    StatusPrinterResponse,
    ConfigImpressaoPrinter,
    ImpressaoMultiplaRequest
)
from app.core.admin_dependencies import get_current_user
from app.api.mensura.models.user_model import UserModel
from app.database.db_connection import get_db
from app.utils.logger import logger

router = APIRouter(prefix="/api/delivery/printer", tags=["Printer"])


# ======================================================================
# ==================== VERIFICAR STATUS PRINTER =======================
@router.get(
    "/status",
    response_model=StatusPrinterResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
async def verificar_status_printer(
    db: Session = Depends(get_db),
):
    """
    Verifica se a Printer API está funcionando.
    """
    logger.info("[Printer] Verificar status da Printer API")
    printer_service = PrinterService(db)
    return await printer_service.verificar_status_printer()


# ======================================================================
# ==================== IMPRIMIR PEDIDO ESPECÍFICO =====================
@router.post(
    "/imprimir/{pedido_id}",
    response_model=RespostaImpressaoPrinter,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)]
)
async def imprimir_pedido(
    pedido_id: int = Path(..., description="ID do pedido a ser impresso"),
    config: Optional[ConfigImpressaoPrinter] = Query(None, description="Configurações de impressão"),
    db: Session = Depends(get_db),
):
    """
    Imprime um pedido específico via Printer API.
    """
    logger.info(f"[Printer] Imprimir pedido - pedido_id={pedido_id}")
    printer_service = PrinterService(db)
    return await printer_service.imprimir_pedido(pedido_id, config)


# ======================================================================
# ==================== IMPRIMIR TODOS OS PENDENTES ====================
@router.post(
    "/imprimir-pendentes",
    response_model=RespostaImpressaoMultipla,
    status_code=status.HTTP_200_OK,
)
async def imprimir_pedidos_pendentes(
    empresa_id: int = Query(..., description="ID da empresa"),
    limite: int = Query(10, ge=1, le=50, description="Número máximo de pedidos para imprimir"),
    config: Optional[ConfigImpressaoPrinter] = Query(None, description="Configurações de impressão"),
    db: Session = Depends(get_db),
):
    """
    Imprime todos os pedidos pendentes de impressão de uma empresa via Printer API.
    """
    logger.info(f"[Printer] Imprimir pendentes - empresa_id={empresa_id}, limite={limite}")
    printer_service = PrinterService(db)
    return await printer_service.imprimir_pedidos_pendentes(empresa_id, limite, config)


# ======================================================================
# ==================== LISTAR PEDIDOS PENDENTES =======================
@router.get(
    "/pedidos-pendentes",
    status_code=status.HTTP_200_OK,
)
async def listar_pedidos_pendentes_impressao(
    empresa_id: int = Query(..., description="ID da empresa"),
    limite: int = Query(50, ge=1, le=100, description="Número máximo de pedidos para listar"),
    db: Session = Depends(get_db),
):
    """
    Lista todos os pedidos pendentes de impressão de uma empresa.
    """
    logger.info(f"[Printer] Listar pendentes - empresa_id={empresa_id}, limite={limite}")
    printer_service = PrinterService(db)
    return printer_service.listar_pedidos_pendentes_impressao(empresa_id, limite)


# ======================================================================
# ==================== MARCAR PEDIDO COMO IMPRESSO ====================
@router.put(
    "/marcar-impresso/{pedido_id}",
    response_model=RespostaImpressaoPrinter,
    status_code=status.HTTP_200_OK,
)
async def marcar_pedido_impresso_manual(
    pedido_id: int = Path(..., description="ID do pedido"),
    db: Session = Depends(get_db),
):
    """
    Marca um pedido como impresso manualmente (sem usar Printer API).
    Útil quando a impressão é feita externamente.
    """
    logger.info(f"[Printer] Marcar como impresso manualmente - pedido_id={pedido_id}")
    printer_service = PrinterService(db)
    return printer_service.marcar_pedido_impresso_manual(pedido_id)


# ======================================================================
# ==================== ESTATÍSTICAS DE IMPRESSÃO ======================
@router.get(
    "/estatisticas",
    status_code=status.HTTP_200_OK,
)
async def get_estatisticas_impressao(
    empresa_id: int = Query(..., description="ID da empresa"),
    db: Session = Depends(get_db),
):
    """
    Retorna estatísticas de impressão para uma empresa.
    """
    logger.info(f"[Printer] Estatísticas - empresa_id={empresa_id}")
    printer_service = PrinterService(db)
    return printer_service.get_estatisticas_impressao(empresa_id)


# ======================================================================
# ==================== IMPRIMIR MÚLTIPLOS PEDIDOS =====================
@router.post(
    "/imprimir-multiplos",
    response_model=RespostaImpressaoMultipla,
    status_code=status.HTTP_200_OK,
)
async def imprimir_multiplos_pedidos(
    request: ImpressaoMultiplaRequest,
    db: Session = Depends(get_db),
):
    """
    Imprime múltiplos pedidos com configurações personalizadas.
    """
    logger.info(f"[Printer] Imprimir múltiplos - empresa_id={request.empresa_id}, limite={request.limite}")
    printer_service = PrinterService(db)
    return await printer_service.imprimir_pedidos_pendentes(
        request.empresa_id, 
        request.limite, 
        request.config
    )


# ======================================================================
# ==================== VALIDAR CONFIGURAÇÃO PRINTER ===================
@router.post(
    "/validar-config",
    status_code=status.HTTP_200_OK,
)
async def validar_configuracao_printer(
    config: ConfigImpressaoPrinter,
    db: Session = Depends(get_db),
):
    """
    Valida uma configuração de impressão.
    """
    logger.info("[Printer] Validar configuração")
    
    # Aqui você pode implementar validações específicas
    # Por exemplo, verificar se a impressora existe, se as fontes estão disponíveis, etc.
    
    return {
        "valida": True,
        "mensagem": "Configuração válida",
        "config": config
    }


# ======================================================================
# ==================== TESTE DE IMPRESSÃO =============================
@router.post(
    "/teste-impressao",
    response_model=RespostaImpressaoPrinter,
    status_code=status.HTTP_200_OK,
)
async def teste_impressao(
    config: Optional[ConfigImpressaoPrinter] = Query(None, description="Configurações de impressão"),
    db: Session = Depends(get_db),
):
    """
    Executa um teste de impressão com dados de exemplo.
    """
    logger.info("[Printer] Teste de impressão")
    
    from app.api.delivery.schemas.schema_printer import PedidoPrinterRequest, ItemPedidoPrinter
    from datetime import datetime
    
    # Cria um pedido de teste
    pedido_teste = PedidoPrinterRequest(
        numero=999,
        cliente="Cliente Teste",
        telefone_cliente="(11) 99999-9999",
        itens=[
            ItemPedidoPrinter(
                descricao="Produto Teste 1",
                quantidade=2,
                preco=10.50
            ),
            ItemPedidoPrinter(
                descricao="Produto Teste 2",
                quantidade=1,
                preco=25.00
            )
        ],
        subtotal=46.00,
        desconto=0.0,
        taxa_entrega=5.00,
        taxa_servico=1.00,
        total=52.00,
        tipo_pagamento="DINHEIRO",
        troco=52.00,
        observacao_geral="Este é um teste de impressão",
        endereco="Rua Teste, 123 - Bairro Teste",
        data_criacao=datetime.now()
    )
    
    printer_service = PrinterService(db)
    resultado = await printer_service.printer_client.imprimir_pedido(pedido_teste.model_dump())
    
    return RespostaImpressaoPrinter(
        sucesso=resultado.get("sucesso", False),
        mensagem=resultado.get("mensagem", "Teste de impressão executado"),
        numero_pedido=999
    )
