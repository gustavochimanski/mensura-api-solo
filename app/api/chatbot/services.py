from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.api.catalogo.services.service_produto import ProdutosMensuraService
from app.api.pedidos.services.service_pedido_taxas import TaxaService
from app.api.cadastros.services.service_cliente import ClienteService
from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.shared.schemas.schema_shared_enums import TipoEntregaEnum


class ProductFAQService:
    def __init__(self, db: Session):
        self.db = db
        self.prod_service = ProdutosMensuraService(db)

    def find_product(self, empresa_id: int, termo: str) -> Optional[Dict[str, Any]]:
        res = self.prod_service.buscar_produtos(empresa_id=empresa_id, termo=termo, page=1, limit=1, apenas_disponiveis=True)
        data = res.get("data") if isinstance(res, dict) else None
        if not data:
            return None
        return data[0]


class DeliveryFeeService:
    def __init__(self, db: Session):
        self.db = db
        self.taxa_service = TaxaService(db)

    def calcular(self, empresa_id: int, endereco: dict, tipo_entrega: str = "DELIVERY"):
        tipo_enum = TipoEntregaEnum[tipo_entrega] if isinstance(tipo_entrega, str) else tipo_entrega
        taxa_entrega, taxa_servico, distancia_km, tempo_estimado = self.taxa_service.calcular_taxas(
            tipo_entrega=tipo_enum,
            subtotal=0,  # subtotal desconhecido para cálculo simples
            endereco=endereco,
            empresa_id=empresa_id,
        )
        return {
            "taxa_entrega": float(taxa_entrega),
            "taxa_servico": float(taxa_servico),
            "distancia_km": float(distancia_km) if distancia_km is not None else None,
            "tempo_estimado_min": int(tempo_estimado) if tempo_estimado is not None else None,
        }


class CustomerService:
    def __init__(self, db: Session):
        self.db = db
        self.svc = ClienteService(db)

    def cadastrar_rapido(self, nome: str, telefone: str, email: Optional[str] = None):
        from app.api.cadastros.schemas.schema_cliente import ClienteCreate

        # Tenta criar; ClienteService.create já valida duplicados
        payload = ClienteCreate(nome=nome, telefone=telefone, email=email)
        return self.svc.create(payload)


class OrderSummaryService:
    def __init__(self, db: Session):
        self.db = db
        self.pedido_repo = PedidoRepository(db)

    def build_summary(self, pedido_id: int) -> Optional[str]:
        pedido = self.pedido_repo.get_pedido(pedido_id)
        if not pedido:
            return None

        numero = getattr(pedido, "numero_pedido", str(getattr(pedido, "id", pedido_id)))
        status = getattr(pedido, "status", "")
        total = float(getattr(pedido, "valor_total", 0) or 0)

        linhas = [f"📦 Pedido #{numero} | Status: {status}", ""]
        linhas.append("Itens:")
        itens = getattr(pedido, "itens", []) or []
        if itens:
            for it in itens:
                nome = getattr(it, "produto_descricao_snapshot", None) or getattr(it, "descricao", "Item")
                qtd = int(getattr(it, "quantidade", 1) or 1)
                preco = float(getattr(it, "preco_total", 0) or 0)
                linhas.append(f"• {qtd}x {nome} - R$ {preco:.2f}")
        else:
            linhas.append("Nenhum item encontrado")

        linhas.append("")
        linhas.append(f"*TOTAL: R$ {total:.2f}*")
        return "\n".join(linhas)

