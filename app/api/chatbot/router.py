from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database.db_connection import get_db
from .schemas import ProductQueryOut, TaxaRequest, TaxaResponse, CadastroRequest, ResumoRequest
from .services import ProductFAQService, DeliveryFeeService, CustomerService, OrderSummaryService
from app.api.notifications.services.notification_service import NotificationService
from app.api.notifications.repositories.notification_repository import NotificationRepository
from app.api.notifications.repositories.subscription_repository import SubscriptionRepository
from app.api.notifications.repositories.event_repository import EventRepository
from app.api.notifications.adapters.channel_config_adapters import (
    DefaultChannelConfigAdapter,
    DatabaseChannelConfigAdapter,
    CompositeChannelConfigAdapter,
)
from app.api.notifications.services.message_dispatch_service import MessageDispatchService
from app.api.notifications.adapters.recipient_adapters import ClienteRecipientAdapter, CompositeRecipientAdapter
from app.api.notifications.schemas.message_dispatch_schemas import DispatchMessageRequest
from app.api.notifications.schemas.notification_schemas import (
    MessageType,
    NotificationChannel,
    NotificationPriority,
)

router = APIRouter(prefix="/api/chatbot", tags=["API - Chatbot Minimal"])


@router.get("/product", response_model=Optional[ProductQueryOut])
def product_info(q: str, empresa_id: int = 1, db: Session = Depends(get_db)):
    svc = ProductFAQService(db)
    prod = svc.find_product(empresa_id, q)
    if not prod:
        return None
    return ProductQueryOut(
        cod_barras=prod.get("cod_barras"),
        descricao=prod.get("descricao"),
        preco_venda=prod.get("preco_venda"),
        imagem=prod.get("imagem"),
        disponivel=prod.get("disponivel"),
    )


@router.post("/taxa", response_model=TaxaResponse)
def calcular_taxa(body: TaxaRequest, db: Session = Depends(get_db)):
    svc = DeliveryFeeService(db)
    try:
        out = svc.calcular(body.empresa_id, body.endereco, body.tipo_entrega)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return TaxaResponse(**out)


@router.post("/cadastro")
def cadastro_rapido(body: CadastroRequest, db: Session = Depends(get_db)):
    svc = CustomerService(db)
    try:
        cliente = svc.cadastrar_rapido(body.nome, body.telefone, body.email)
        return {"success": True, "cliente_id": getattr(cliente, "id", None), "nome": getattr(cliente, "nome", None)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resumo")
def enviar_resumo(body: ResumoRequest, db: Session = Depends(get_db)):
    svc = OrderSummaryService(db)
    msg = svc.build_summary(body.pedido_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # Resolve telefone: prioridade para body.phone_number, fallback para cliente do pedido
    telefone = body.phone_number
    if not telefone:
        try:
            pedido = svc.pedido_repo.get_pedido(body.pedido_id)
            cliente = getattr(pedido, "cliente", None) if pedido is not None else None
            telefone = getattr(cliente, "telefone", None) if cliente is not None else None
        except Exception:
            telefone = None

    if not telefone:
        # Retorna a mensagem formatada, mas informa que não foi possível enviar automaticamente.
        return {"mensagem": msg, "sent": False, "reason": "telefone do cliente não encontrado"}

    # Cria MessageDispatchService (mesma fábrica usada no módulo de notifications)
    notification_repo = NotificationRepository(db)
    subscription_repo = SubscriptionRepository(db)
    event_repo = EventRepository(db)

    channel_config_provider = CompositeChannelConfigAdapter([
        DatabaseChannelConfigAdapter(db),
        DefaultChannelConfigAdapter()
    ])

    notification_service = NotificationService(
        notification_repo,
        subscription_repo,
        event_repo,
        channel_config_provider=channel_config_provider
    )

    cliente_adapter = ClienteRecipientAdapter(db)
    recipient_provider = CompositeRecipientAdapter([cliente_adapter])

    dispatch_service = MessageDispatchService(
        notification_service,
        db=db,
        recipient_provider=recipient_provider
    )

    # Monta requisição de dispatch para WhatsApp
    dispatch_req = DispatchMessageRequest(
        empresa_id=str(body.empresa_id) if body.empresa_id is not None else "1",
        message_type=MessageType.TRANSACTIONAL,
        title=f"Resumo do pedido {body.pedido_id}",
        message=msg,
        recipient_phones=[telefone],
        channels=[NotificationChannel.WHATSAPP],
        priority=NotificationPriority.NORMAL,
        event_type=f"resumo_pedido",
        event_data={"pedido_id": str(body.pedido_id)}
    )

    # Executa o dispatch (assíncrono)
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(dispatch_service.dispatch_message(dispatch_req))
    except RuntimeError:
        # Se já estamos em loop (ex: uvicorn), await diretamente
        result = asyncio.run(dispatch_service.dispatch_message(dispatch_req))

    return {"mensagem": msg, "sent": True, "dispatch": result}

