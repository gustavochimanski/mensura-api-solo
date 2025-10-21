from __future__ import annotations
from typing import Optional, List
from sqlalchemy import select, func, or_, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.mesas.models.model_mesa import MesaModel, StatusMesa
from app.api.mesas.schemas.schema_mesa import MesaIn, StatusMesaEnum


class MesaRepository:
    def __init__(self, db: Session):
        self.db = db

    # -------- CRUD --------
    def create(self, data: MesaIn) -> MesaModel:
        from app.utils.logger import logger
        
        logger.info(f"[Mesas] Criando mesa no repositório - numero={data.numero}, capacidade={data.capacidade}")
        
        # Verifica se já existe mesa com o mesmo número
        existe = self.db.query(MesaModel).filter_by(numero=data.numero).first()
        if existe:
            logger.warning(f"[Mesas] Mesa com número já existe: {data.numero}")
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Já existe uma mesa com esse número."
            )

        # Converte StatusMesaEnum para StatusMesa
        status_mesa = StatusMesa(data.status.value) if data.status else StatusMesa.DISPONIVEL

        nova = MesaModel(
            numero=data.numero,
            descricao=data.descricao,
            capacidade=data.capacidade,
            status=status_mesa,
            posicao_x=data.posicao_x,
            posicao_y=data.posicao_y,
            ativa=data.ativa
        )
        
        logger.info(f"[Mesas] Objeto mesa criado - numero={nova.numero}, status={nova.status}")
        
        self.db.add(nova)
        try:
            self.db.commit()
            self.db.refresh(nova)
            logger.info(f"[Mesas] Mesa salva no banco - id={nova.id}, numero={nova.numero}")
            return nova
        except Exception as e:
            logger.error(f"[Mesas] Erro ao salvar mesa no banco: {e}")
            self.db.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao criar mesa")

    def get_by_id(self, mesa_id: int) -> MesaModel:
        mesa = self.db.query(MesaModel).filter_by(id=mesa_id).first()
        if not mesa:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa não encontrada")
        return mesa

    def get_by_numero(self, numero: str) -> MesaModel:
        mesa = self.db.query(MesaModel).filter_by(numero=numero).first()
        if not mesa:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa não encontrada")
        return mesa

    def list_all(self, ativa: Optional[bool] = None) -> List[MesaModel]:
        """Lista todas as mesas, opcionalmente filtrando por status ativo"""
        query = self.db.query(MesaModel)
        
        if ativa is not None:
            status_filter = "S" if ativa else "N"
            query = query.filter(MesaModel.ativa == status_filter)
        
        return query.order_by(MesaModel.numero).all()

    def list_by_status(self, status: StatusMesa) -> List[MesaModel]:
        """Lista mesas por status"""
        return (
            self.db.query(MesaModel)
            .filter(MesaModel.status == status)
            .filter(MesaModel.ativa == "S")
            .order_by(MesaModel.numero)
            .all()
        )

    def update(self, mesa_id: int, update_data: dict) -> MesaModel:
        from app.utils.logger import logger
        
        logger.info(f"[Mesas] Atualizando mesa - id={mesa_id}, update_data={update_data}")
        
        mesa = self.get_by_id(mesa_id)
        if not mesa:
            logger.error(f"[Mesas] Mesa não encontrada - id={mesa_id}")
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa não encontrada")

        # Verifica se o novo número já existe (se estiver sendo alterado)
        if "numero" in update_data and update_data["numero"] != mesa.numero:
            existe = (
                self.db.query(MesaModel)
                .filter(
                    MesaModel.numero == update_data["numero"],
                    MesaModel.id != mesa_id
                )
                .first()
            )
            if existe:
                logger.warning(f"[Mesas] Número de mesa já existe: {update_data['numero']}")
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Já existe uma mesa com esse número."
                )

        # Converte StatusMesaEnum para StatusMesa se necessário
        if "status" in update_data and update_data["status"]:
            if isinstance(update_data["status"], StatusMesaEnum):
                update_data["status"] = StatusMesa(update_data["status"].value)

        # Atualiza os campos
        for key, value in update_data.items():
            if value is not None:
                logger.info(f"[Mesas] Atualizando campo {key}: {getattr(mesa, key)} -> {value}")
                setattr(mesa, key, value)

        try:
            self.db.commit()
            logger.info(f"[Mesas] Mesa atualizada com sucesso - id={mesa_id}")
        except IntegrityError as e:
            logger.error(f"[Mesas] Erro de integridade ao atualizar mesa: {e}")
            self.db.rollback()
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Violação de unicidade/constraint ao atualizar mesa"
            )
        except Exception as e:
            logger.error(f"[Mesas] Erro ao atualizar mesa: {e}")
            self.db.rollback()
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Erro ao atualizar mesa"
            )

        self.db.refresh(mesa)
        return mesa

    def update_status(self, mesa_id: int, status: StatusMesa) -> MesaModel:
        """Atualiza apenas o status da mesa"""
        from app.utils.logger import logger
        
        logger.info(f"[Mesas] Atualizando status da mesa - id={mesa_id}, status={status}")
        
        mesa = self.get_by_id(mesa_id)
        mesa.status = status
        
        try:
            self.db.commit()
            self.db.refresh(mesa)
            logger.info(f"[Mesas] Status da mesa atualizado - id={mesa_id}, status={status}")
            return mesa
        except Exception as e:
            logger.error(f"[Mesas] Erro ao atualizar status da mesa: {e}")
            self.db.rollback()
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Erro ao atualizar status da mesa"
            )

    def delete(self, mesa_id: int) -> None:
        from app.utils.logger import logger
        
        mesa = self.get_by_id(mesa_id)
        
        # Verifica se a mesa tem pedidos associados
        if mesa.pedidos:
            logger.warning(f"[Mesas] Tentativa de deletar mesa com pedidos - id={mesa_id}")
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Não é possível deletar mesa que possui pedidos associados"
            )
        
        logger.info(f"[Mesas] Deletando mesa - id={mesa_id}, numero={mesa.numero}")
        self.db.delete(mesa)
        self.db.commit()

    # -------- BUSCA --------
    def search(
        self, 
        q: Optional[str] = None, 
        status: Optional[StatusMesa] = None,
        ativa: Optional[bool] = None,
        limit: int = 30, 
        offset: int = 0
    ) -> List[MesaModel]:
        """
        Busca mesas com filtros opcionais
        """
        query = self.db.query(MesaModel)

        # Filtro por termo de busca
        if q and q.strip():
            term = f"%{q.strip()}%"
            query = query.filter(
                or_(
                    MesaModel.numero.ilike(term),
                    MesaModel.descricao.ilike(term)
                )
            )

        # Filtro por status
        if status:
            query = query.filter(MesaModel.status == status)

        # Filtro por ativa
        if ativa is not None:
            status_filter = "S" if ativa else "N"
            query = query.filter(MesaModel.ativa == status_filter)

        return query.order_by(MesaModel.numero).offset(offset).limit(limit).all()

    # -------- ESTATÍSTICAS --------
    def get_stats(self) -> dict:
        """Retorna estatísticas das mesas"""
        total = self.db.query(MesaModel).count()
        disponiveis = self.db.query(MesaModel).filter(MesaModel.status == StatusMesa.DISPONIVEL).count()
        ocupadas = self.db.query(MesaModel).filter(MesaModel.status == StatusMesa.OCUPADA).count()
        livres = self.db.query(MesaModel).filter(MesaModel.status == StatusMesa.LIVRE).count()
        reservadas = self.db.query(MesaModel).filter(MesaModel.status == StatusMesa.RESERVADA).count()
        ativas = self.db.query(MesaModel).filter(MesaModel.ativa == "S").count()
        inativas = self.db.query(MesaModel).filter(MesaModel.ativa == "N").count()

        return {
            "total": total,
            "disponiveis": disponiveis,
            "ocupadas": ocupadas,
            "livres": livres,
            "reservadas": reservadas,
            "ativas": ativas,
            "inativas": inativas
        }

    # -------- OPERAÇÕES DE STATUS --------
    def liberar_mesa(self, mesa_id: int) -> MesaModel:
        """Libera uma mesa (muda status para DISPONIVEL)"""
        return self.update_status(mesa_id, StatusMesa.DISPONIVEL)

    def ocupar_mesa(self, mesa_id: int) -> MesaModel:
        """Ocupa uma mesa (muda status para OCUPADA)"""
        return self.update_status(mesa_id, StatusMesa.OCUPADA)

    def reservar_mesa(self, mesa_id: int) -> MesaModel:
        """Reserva uma mesa (muda status para RESERVADA)"""
        return self.update_status(mesa_id, StatusMesa.RESERVADA)

    def marcar_livre(self, mesa_id: int) -> MesaModel:
        """Marca mesa como livre (muda status para LIVRE)"""
        return self.update_status(mesa_id, StatusMesa.LIVRE)
