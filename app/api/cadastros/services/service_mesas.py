from typing import Optional, List
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.api.cadastros.models.model_mesa import MesaModel, StatusMesa
from app.api.cadastros.repositories.repo_mesas import MesaRepository
from app.api.cadastros.schemas.schema_mesa import MesaCreate, MesaUpdate
from app.api.pedidos.repositories.repo_pedidos import PedidoRepository
from app.api.pedidos.models.model_pedido_unificado import TipoEntrega, StatusPedido
from app.api.cadastros.schemas.schema_mesa import PedidoAbertoMesa


class MesaService:
    """Service para operações com mesas."""

    def __init__(self, db: Session):
        self.repo = MesaRepository(db)
        self.pedido_repo = PedidoRepository(db)

    def _get_pedidos_abertos(self, mesa_id: int, empresa_id: int) -> List[PedidoAbertoMesa]:
        """Obtém pedidos abertos de uma mesa."""
        pedidos_mesa = self.pedido_repo.list_abertos_by_mesa(
            mesa_id, TipoEntrega.MESA, empresa_id=empresa_id
        )
        pedidos_balcao = self.pedido_repo.list_abertos_by_mesa(
            mesa_id, TipoEntrega.BALCAO, empresa_id=empresa_id
        )
        
        todos_pedidos = []
        
        # Adiciona pedidos de mesa
        for pedido in pedidos_mesa:
            todos_pedidos.append(
                PedidoAbertoMesa(
                    id=pedido.id,
                    numero_pedido=getattr(pedido, "numero_pedido", None) or str(pedido.id),
                    status=pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status),
                    num_pessoas=pedido.num_pessoas if hasattr(pedido, "num_pessoas") else None,
                    valor_total=pedido.valor_total or Decimal("0"),
                    cliente_id=pedido.cliente_id,
                    cliente_nome=pedido.cliente.nome if pedido.cliente else None,
                )
            )
        
        # Adiciona pedidos de balcão
        for pedido in pedidos_balcao:
            todos_pedidos.append(
                PedidoAbertoMesa(
                    id=pedido.id,
                    numero_pedido=getattr(pedido, "numero_pedido", None) or str(pedido.id),
                    status=pedido.status.value if hasattr(pedido.status, "value") else str(pedido.status),
                    num_pessoas=None,  # Balcão geralmente não tem num_pessoas
                    valor_total=pedido.valor_total or Decimal("0"),
                    cliente_id=pedido.cliente_id,
                    cliente_nome=pedido.cliente.nome if pedido.cliente else None,
                )
            )
        
        return todos_pedidos

    def _calcular_num_pessoas_atual(self, mesa_id: int, empresa_id: int) -> Optional[int]:
        """Calcula o número atual de pessoas na mesa baseado nos pedidos abertos."""
        pedidos_mesa = self.pedido_repo.list_abertos_by_mesa(
            mesa_id, TipoEntrega.MESA, empresa_id=empresa_id
        )
        
        if not pedidos_mesa:
            return None
        
        total = 0
        for pedido in pedidos_mesa:
            if hasattr(pedido, "num_pessoas") and pedido.num_pessoas:
                total += pedido.num_pessoas
        
        return total if total > 0 else None

    def _mesa_to_dict(self, mesa: MesaModel, empresa_id: int, incluir_pedidos: bool = True) -> dict:
        """Converte uma mesa para dicionário com dados completos."""
        pedidos_abertos = self._get_pedidos_abertos(mesa.id, empresa_id) if incluir_pedidos else []
        num_pessoas_atual = self._calcular_num_pessoas_atual(mesa.id, empresa_id) if incluir_pedidos else None
        
        return {
            "id": mesa.id,
            "codigo": str(mesa.codigo),
            "numero": mesa.numero,
            "descricao": mesa.descricao,
            "capacidade": mesa.capacidade,
            "status": mesa.status.value if hasattr(mesa.status, "value") else str(mesa.status),
            "status_descricao": mesa.status_descricao,
            "ativa": mesa.ativa,
            "label": mesa.label,
            "num_pessoas_atual": num_pessoas_atual,
            "empresa_id": mesa.empresa_id,
            "pedidos_abertos": [pedido.model_dump() for pedido in pedidos_abertos] if pedidos_abertos else [],
        }

    def listar_mesas(self, empresa_id: int) -> List[dict]:
        """Lista todas as mesas de uma empresa."""
        mesas = self.repo.listar_por_empresa(empresa_id, apenas_ativas=False)
        return [self._mesa_to_dict(mesa, empresa_id) for mesa in mesas]

    def buscar_mesas(self, empresa_id: int, q: Optional[str] = None, status: Optional[str] = None,
                     ativa: Optional[str] = None, limit: int = 30, offset: int = 0) -> List[dict]:
        """Busca mesas com filtros."""
        mesas = self.repo.buscar(empresa_id, q=q, status=status, ativa=ativa, limit=limit, offset=offset)
        return [self._mesa_to_dict(mesa, empresa_id) for mesa in mesas]

    def obter_mesa(self, mesa_id: int, empresa_id: int) -> dict:
        """Obtém uma mesa por ID."""
        mesa = self.repo.get_by_id(mesa_id)
        if not mesa:
            raise HTTPException(status_code=404, detail="Mesa não encontrada")
        if mesa.empresa_id != empresa_id:
            raise HTTPException(status_code=403, detail="Mesa não pertence à empresa informada")
        
        return self._mesa_to_dict(mesa, empresa_id)

    def criar_mesa(self, data: MesaCreate) -> dict:
        """Cria uma nova mesa."""
        # Verifica se já existe mesa com o mesmo código
        if self.repo.get_by_codigo(data.codigo, data.empresa_id):
            raise HTTPException(status_code=400, detail=f"Já existe uma mesa com código {data.codigo} nesta empresa")
        
        # Cria o número da mesa a partir do código
        numero = str(int(data.codigo)) if data.codigo == int(data.codigo) else str(data.codigo)
        
        # Verifica se já existe mesa com o mesmo número
        if self.repo.get_by_numero(numero, data.empresa_id):
            raise HTTPException(
                status_code=400,
                detail=f"Já existe uma mesa com número {numero} nesta empresa"
            )
        
        nova_mesa = MesaModel(
            codigo=data.codigo,
            numero=numero,
            descricao=data.descricao,
            capacidade=data.capacidade,
            status=StatusMesa(data.status),
            ativa=data.ativa,
            empresa_id=data.empresa_id,
        )
        
        mesa = self.repo.criar(nova_mesa)
        self.repo.db.commit()
        self.repo.db.refresh(mesa)
        
        return self._mesa_to_dict(mesa, data.empresa_id)

    def atualizar_mesa(self, mesa_id: int, empresa_id: int, data: MesaUpdate) -> dict:
        """Atualiza uma mesa existente."""
        mesa = self.repo.get_by_id(mesa_id)
        if not mesa:
            raise HTTPException(status_code=404, detail="Mesa não encontrada")
        if mesa.empresa_id != empresa_id:
            raise HTTPException(status_code=403, detail="Mesa não pertence à empresa informada")
        
        if data.empresa_id and data.empresa_id != empresa_id:
            raise HTTPException(status_code=400, detail="Não é possível alterar a empresa da mesa")
        
        # Atualiza os campos fornecidos
        update_data = data.model_dump(exclude_unset=True, exclude={"empresa_id"})
        
        for field, value in update_data.items():
            if field == "status" and value:
                setattr(mesa, field, StatusMesa(value))
            else:
                setattr(mesa, field, value)
        
        mesa = self.repo.atualizar(mesa)
        self.repo.db.commit()
        self.repo.db.refresh(mesa)
        
        return self._mesa_to_dict(mesa, empresa_id)

    def deletar_mesa(self, mesa_id: int, empresa_id: int) -> dict:
        """Deleta uma mesa."""
        if not self.repo.deletar(mesa_id, empresa_id):
            raise HTTPException(status_code=404, detail="Mesa não encontrada")
        
        self.repo.db.commit()
        return {}

    def atualizar_status(self, mesa_id: int, empresa_id: int, novo_status: str) -> dict:
        """Atualiza o status de uma mesa."""
        mesa = self.repo.atualizar_status(mesa_id, empresa_id, novo_status)
        return self._mesa_to_dict(mesa, empresa_id)

    def ocupar_mesa(self, mesa_id: int, empresa_id: int) -> dict:
        """Ocupa uma mesa."""
        mesa = self.repo.ocupar_mesa(mesa_id, empresa_id)
        return self._mesa_to_dict(mesa, empresa_id)

    def liberar_mesa(self, mesa_id: int, empresa_id: int) -> dict:
        """Libera uma mesa."""
        mesa = self.repo.liberar_mesa(mesa_id, empresa_id)
        return self._mesa_to_dict(mesa, empresa_id)

    def reservar_mesa(self, mesa_id: int, empresa_id: int) -> dict:
        """Reserva uma mesa."""
        mesa = self.repo.reservar_mesa(mesa_id, empresa_id)
        return self._mesa_to_dict(mesa, empresa_id)

    def obter_stats(self, empresa_id: int) -> dict:
        """Obtém estatísticas das mesas."""
        return self.repo.obter_stats(empresa_id)

