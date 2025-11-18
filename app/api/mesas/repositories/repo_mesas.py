from __future__ import annotations
from typing import Optional, List
from sqlalchemy import select, func, or_, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.mesas.models.model_mesa import MesaModel, StatusMesa
from app.api.mesas.models.model_mesa_historico import MesaHistoricoModel, TipoOperacaoMesa
from app.api.mesas.schemas.schema_mesa import MesaIn, StatusMesaEnum


class MesaRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def add_mesa_historico(
        self,
        mesa_id: int,
        tipo_operacao: TipoOperacaoMesa,
        status_anterior: str | None = None,
        status_novo: str | None = None,
        descricao: str | None = None,
        observacoes: str | None = None,
        cliente_id: int | None = None,
        usuario_id: int | None = None,
        ip_origem: str | None = None,
        user_agent: str | None = None
    ):
        """Adiciona um registro ao histórico da mesa (seguindo padrão do histórico de pedidos)"""
        historico = MesaHistoricoModel(
            mesa_id=mesa_id,
            cliente_id=cliente_id,
            usuario_id=usuario_id,
            tipo_operacao=tipo_operacao.value,  # Converte enum para valor string
            status_anterior=status_anterior,
            status_novo=status_novo,
            descricao=descricao,
            observacoes=observacoes,
            ip_origem=ip_origem,
            user_agent=user_agent
        )
        self.db.add(historico)

    def add_mesa_status_historico(
        self,
        mesa_id: int,
        status_anterior: str | None,
        status_novo: str,
        motivo: str | None = None,
        observacoes: str | None = None,
        usuario_id: int | None = None,
        ip_origem: str | None = None,
        user_agent: str | None = None
    ):
        """Adiciona um registro de mudança de status ao histórico da mesa"""
        self.add_mesa_historico(
            mesa_id=mesa_id,
            tipo_operacao=TipoOperacaoMesa.STATUS_ALTERADO,
            status_anterior=status_anterior,
            status_novo=status_novo,
            descricao=motivo or f"Status alterado de '{status_anterior}' para '{status_novo}'",
            observacoes=observacoes,
            usuario_id=usuario_id,
            ip_origem=ip_origem,
            user_agent=user_agent
        )

    # -------- CRUD --------
    def create(self, data: MesaIn) -> MesaModel:
        from app.utils.logger import logger
        
        logger.info(f"[Mesas] Criando mesa no repositório - codigo={data.codigo}, capacidade={data.capacidade}")

        # Verifica se já existe uma mesa com esse código
        mesa_existente = (
            self.db.query(MesaModel)
            .filter(
                MesaModel.empresa_id == data.empresa_id,
                MesaModel.codigo == data.codigo,
            )
            .first()
        )
        if mesa_existente:
            logger.warning(f"[Mesas] Código de mesa já existe: {data.codigo}")
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Já existe uma mesa com o código {data.codigo}."
            )

        # Converte StatusMesaEnum para StatusMesa
        status_mesa = StatusMesa(data.status.value) if data.status else StatusMesa.DISPONIVEL

        # Gera número sequencial por empresa
        seq = (
            self.db.query(func.count(MesaModel.id))
            .filter(MesaModel.empresa_id == data.empresa_id)
            .scalar()
            or 0
        ) + 1
        numero_mesa = f"M{seq:03d}"
        while (
            self.db.query(MesaModel)
            .filter(
                MesaModel.empresa_id == data.empresa_id,
                MesaModel.numero == numero_mesa,
            )
            .first()
        ):
            seq += 1
            numero_mesa = f"M{seq:03d}"
        
        nova = MesaModel(
            empresa_id=data.empresa_id,
            codigo=data.codigo,
            numero=numero_mesa,
            descricao=data.descricao,
            capacidade=data.capacidade,
            status=status_mesa,
            ativa=data.ativa
        )
        
        logger.info(f"[Mesas] Objeto mesa criado - numero={nova.numero}, status={nova.status}")
        
        self.db.add(nova)
        try:
            self.db.commit()
            self.db.refresh(nova)
            
            logger.info(f"[Mesas] Mesa salva no banco - id={nova.id}, numero={nova.numero}")
            
            # Registra no histórico
            self.add_mesa_historico(
                mesa_id=nova.id,
                tipo_operacao=TipoOperacaoMesa.MESA_CRIADA,
                status_novo=nova.status.value,
                descricao=f"Mesa {nova.numero} criada",
                observacoes=f"Capacidade: {nova.capacidade}, Status inicial: {nova.status.value}"
            )
            
            return nova
        except Exception as e:
            logger.error(f"[Mesas] Erro ao salvar mesa no banco: {e}")
            self.db.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro ao criar mesa")

    def get_by_id(self, mesa_id: int, *, empresa_id: int | None = None) -> MesaModel:
        query = self.db.query(MesaModel).filter(MesaModel.id == mesa_id)
        if empresa_id is not None:
            query = query.filter(MesaModel.empresa_id == empresa_id)
        mesa = query.first()
        if not mesa:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa não encontrada")
        return mesa

    def get_by_numero(self, numero: str, *, empresa_id: int | None = None) -> MesaModel:
        query = self.db.query(MesaModel).filter(MesaModel.numero == numero)
        if empresa_id is not None:
            query = query.filter(MesaModel.empresa_id == empresa_id)
        mesa = query.first()
        if not mesa:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa não encontrada")
        return mesa

    def get_by_codigo(self, codigo, *, empresa_id: int | None = None) -> MesaModel:
        """Busca mesa por código numérico"""
        from decimal import Decimal
        if not isinstance(codigo, Decimal):
            codigo = Decimal(str(codigo))
        query = self.db.query(MesaModel).filter(MesaModel.codigo == codigo)
        if empresa_id is not None:
            query = query.filter(MesaModel.empresa_id == empresa_id)
        mesa = query.first()
        if not mesa:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa não encontrada")
        return mesa

    def list_all(self, *, empresa_id: int | None = None, ativa: Optional[bool] = None) -> List[MesaModel]:
        """Lista todas as mesas, opcionalmente filtrando por status ativo"""
        query = self.db.query(MesaModel)
        if empresa_id is not None:
            query = query.filter(MesaModel.empresa_id == empresa_id)
        
        if ativa is not None:
            status_filter = "S" if ativa else "N"
            query = query.filter(MesaModel.ativa == status_filter)
        
        return query.order_by(MesaModel.numero).all()

    def list_by_status(self, status: StatusMesa, *, empresa_id: int | None = None) -> List[MesaModel]:
        """Lista mesas por status"""
        query = (
            self.db.query(MesaModel)
            .filter(MesaModel.status == status)
            .filter(MesaModel.ativa == "S")
        )
        if empresa_id is not None:
            query = query.filter(MesaModel.empresa_id == empresa_id)
        return query.order_by(MesaModel.numero).all()

    def update(self, mesa_id: int, update_data: dict, *, empresa_id: int | None = None) -> MesaModel:
        from app.utils.logger import logger
        
        logger.info(f"[Mesas] Atualizando mesa - id={mesa_id}, update_data={update_data}")
        
        mesa = self.get_by_id(mesa_id, empresa_id=empresa_id)
        if not mesa:
            logger.error(f"[Mesas] Mesa não encontrada - id={mesa_id}")
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa não encontrada")

        empresa_destino = update_data.get("empresa_id", mesa.empresa_id)

        # Verifica se o novo código já existe (se estiver sendo alterado)
        if "codigo" in update_data and update_data["codigo"] != mesa.codigo:
            existe = (
                self.db.query(MesaModel)
                .filter(
                    MesaModel.empresa_id == empresa_destino,
                    MesaModel.codigo == update_data["codigo"],
                    MesaModel.id != mesa_id
                )
                .first()
            )
            if existe:
                logger.warning(f"[Mesas] Código de mesa já existe: {update_data['codigo']}")
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Já existe uma mesa com esse código."
                )
        
        # Verifica se o novo número já existe (se estiver sendo alterado)
        if "numero" in update_data and update_data["numero"] != mesa.numero:
            existe = (
                self.db.query(MesaModel)
                .filter(
                    MesaModel.empresa_id == empresa_destino,
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

        # Guarda valores anteriores para histórico
        status_anterior = mesa.status.value if mesa.status else None
        mudancas = []
        
        # Atualiza os campos
        for key, value in update_data.items():
            if value is not None:
                valor_anterior = getattr(mesa, key)
                logger.info(f"[Mesas] Atualizando campo {key}: {valor_anterior} -> {value}")
                
                # Se for mudança de status, guarda para histórico
                if key == "status":
                    status_anterior = valor_anterior.value if hasattr(valor_anterior, 'value') else str(valor_anterior)
                    mudancas.append(f"Status: {status_anterior} -> {value.value if hasattr(value, 'value') else value}")
                else:
                    mudancas.append(f"{key}: {valor_anterior} -> {value}")
                
                setattr(mesa, key, value)

        try:
            self.db.commit()
            logger.info(f"[Mesas] Mesa atualizada com sucesso - id={mesa_id}")
            
            # Registra no histórico se houver mudanças
            if mudancas:
                status_novo = mesa.status.value if mesa.status else None
                descricao = f"Mesa {mesa.numero} atualizada"
                observacoes = " | ".join(mudancas)
                
                # Se mudou status, usa método específico
                if "status" in update_data:
                    self.add_mesa_status_historico(
                        mesa_id=mesa_id,
                        status_anterior=status_anterior,
                        status_novo=status_novo or "",
                        motivo=descricao,
                        observacoes=observacoes
                    )
                else:
                    self.add_mesa_historico(
                        mesa_id=mesa_id,
                        tipo_operacao=TipoOperacaoMesa.MESA_ATUALIZADA,
                        descricao=descricao,
                        observacoes=observacoes
                    )
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

    def update_status(self, mesa_id: int, status: StatusMesa, *, empresa_id: int | None = None) -> MesaModel:
        """Atualiza apenas o status da mesa"""
        from app.utils.logger import logger
        
        logger.info(f"[Mesas] Atualizando status da mesa - id={mesa_id}, status={status}")
        
        mesa = self.get_by_id(mesa_id, empresa_id=empresa_id)
        status_anterior = mesa.status.value
        mesa.status = status
        
        try:
            self.db.commit()
            self.db.refresh(mesa)
            logger.info(f"[Mesas] Status da mesa atualizado - id={mesa_id}")
            self.add_mesa_status_historico(
                mesa_id=mesa_id,
                status_anterior=status_anterior,
                status_novo=status.value,
                motivo="Status atualizado manualmente",
            )
            return mesa
        except Exception as e:
            logger.error(f"[Mesas] Erro ao atualizar status da mesa: {e}")
            self.db.rollback()
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Erro ao atualizar status da mesa"
            )

    def delete(self, mesa_id: int, *, empresa_id: int | None = None) -> None:
        from app.utils.logger import logger
        
        mesa = self.get_by_id(mesa_id, empresa_id=empresa_id)
        
        # Note: Verificação de pedidos removida - sistema de delivery é separado do sistema de mesas
        
        logger.info(f"[Mesas] Deletando mesa - id={mesa_id}, numero={mesa.numero}")
        
        # Registra no histórico antes de deletar
        self.add_mesa_historico(
            mesa_id=mesa_id,
            tipo_operacao=TipoOperacaoMesa.MESA_DELETADA,
            status_anterior=mesa.status.value if mesa.status else None,
            descricao=f"Mesa {mesa.numero} deletada",
            observacoes=f"Capacidade: {mesa.capacidade}, Status final: {mesa.status.value if mesa.status else 'N/A'}"
        )
        
        self.db.delete(mesa)
        self.db.commit()

    # -------- BUSCA --------
    def search(
        self, 
        q: Optional[str] = None, 
        status: Optional[StatusMesa] = None,
        ativa: Optional[bool] = None,
        limit: int = 30, 
        offset: int = 0,
        *,
        empresa_id: int | None = None,
    ) -> List[MesaModel]:
        """
        Busca mesas com filtros opcionais
        """
        query = self.db.query(MesaModel)
        if empresa_id is not None:
            query = query.filter(MesaModel.empresa_id == empresa_id)

        # Filtro por termo de busca
        if q and q.strip():
            term = f"%{q.strip()}%"
            # Tenta converter para número para buscar por código
            try:
                from decimal import Decimal
                codigo_busca = Decimal(q.strip())
                query = query.filter(
                    or_(
                        MesaModel.numero.ilike(term),
                        MesaModel.descricao.ilike(term),
                        MesaModel.codigo == codigo_busca
                    )
                )
            except (ValueError, Exception):
                # Se não for número, busca apenas por texto
                query = query.filter(
                    or_(
                        MesaModel.numero.ilike(term),
                        MesaModel.descricao.ilike(term)
                    )
                )

        if status is not None:
            query = query.filter(MesaModel.status == status)
        if ativa is not None:
            status_filter = "S" if ativa else "N"
            query = query.filter(MesaModel.ativa == status_filter)

        return query.order_by(MesaModel.numero).offset(offset).limit(limit).all()

    # -------- ESTATÍSTICAS --------
    def get_stats(self, *, empresa_id: int | None = None) -> dict:
        """Retorna estatísticas das mesas"""
        from sqlalchemy.exc import ProgrammingError
        
        try:
            base_query = self.db.query(MesaModel)
            if empresa_id is not None:
                base_query = base_query.filter(MesaModel.empresa_id == empresa_id)

            total = base_query.count()
            disponiveis = base_query.filter(MesaModel.status == StatusMesa.DISPONIVEL).count()
            ocupadas = base_query.filter(MesaModel.status == StatusMesa.OCUPADA).count()
            reservadas = base_query.filter(MesaModel.status == StatusMesa.RESERVADA).count()
            ativas = base_query.filter(MesaModel.ativa == "S").count()
            inativas = base_query.filter(MesaModel.ativa == "N").count()

            return {
                "total": total,
                "disponiveis": disponiveis,
                "ocupadas": ocupadas,
                "reservadas": reservadas,
                "ativas": ativas,
                "inativas": inativas
            }
        except ProgrammingError as e:
            # Se a tabela não existir, retorna estatísticas zeradas
            from app.utils.logger import logger
            logger.warning(f"[Mesas] Tabela cadastros.mesas não existe ainda: {e}")
            return {
                "total": 0,
                "disponiveis": 0,
                "ocupadas": 0,
                "reservadas": 0,
                "ativas": 0,
                "inativas": 0
            }

    # -------- OPERAÇÕES DE STATUS --------
    def liberar_mesa(self, mesa_id: int, *, empresa_id: int | None = None) -> MesaModel:
        """Libera uma mesa (muda status para DISPONIVEL)"""
        return self.update_status(mesa_id, StatusMesa.DISPONIVEL, empresa_id=empresa_id)

    def ocupar_mesa(self, mesa_id: int, *, empresa_id: int | None = None) -> MesaModel:
        """Ocupa uma mesa (muda status para OCUPADA)"""
        return self.update_status(mesa_id, StatusMesa.OCUPADA, empresa_id=empresa_id)

    def reservar_mesa(self, mesa_id: int, *, empresa_id: int | None = None) -> MesaModel:
        """Reserva uma mesa (muda status para RESERVADA)"""
        return self.update_status(mesa_id, StatusMesa.RESERVADA, empresa_id=empresa_id)
    
    def associar_cliente(self, mesa_id: int, cliente_id: int, *, empresa_id: int | None = None) -> MesaModel:
        """Associa um cliente à mesa"""
        from app.utils.logger import logger
        
        mesa = self.get_by_id(mesa_id, empresa_id=empresa_id)
        mesa.cliente_atual_id = cliente_id
        
        try:
            self.db.commit()
            self.db.refresh(mesa)
            logger.info(f"[Mesas] Cliente associado à mesa - mesa_id={mesa_id}, cliente_id={cliente_id}")
            
            # Registra no histórico
            self.add_mesa_historico(
                mesa_id=mesa_id,
                tipo_operacao=TipoOperacaoMesa.CLIENTE_ASSOCIADO,
                cliente_id=cliente_id,
                descricao=f"Cliente associado à mesa {mesa.numero}"
            )
            
            return mesa
        except Exception as e:
            logger.error(f"[Mesas] Erro ao associar cliente à mesa: {e}")
            self.db.rollback()
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Erro ao associar cliente à mesa"
            )
    
    def desassociar_cliente(self, mesa_id: int, *, empresa_id: int | None = None) -> MesaModel:
        """Desassocia o cliente da mesa"""
        from app.utils.logger import logger
        
        mesa = self.get_by_id(mesa_id, empresa_id=empresa_id)
        cliente_id_anterior = mesa.cliente_atual_id
        mesa.cliente_atual_id = None
        
        try:
            self.db.commit()
            self.db.refresh(mesa)
            logger.info(f"[Mesas] Cliente desassociado da mesa - mesa_id={mesa_id}")
            
            # Registra no histórico
            self.add_mesa_historico(
                mesa_id=mesa_id,
                tipo_operacao=TipoOperacaoMesa.CLIENTE_DESASSOCIADO,
                cliente_id=cliente_id_anterior,
                descricao=f"Cliente desassociado da mesa {mesa.numero}"
            )
            
            return mesa
        except Exception as e:
            logger.error(f"[Mesas] Erro ao desassociar cliente da mesa: {e}")
            self.db.rollback()
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Erro ao desassociar cliente da mesa"
            )
    
    def get_historico(self, mesa_id: int, limit: int = 100, *, empresa_id: int | None = None) -> list[MesaHistoricoModel]:
        """Retorna o histórico de uma mesa (seguindo padrão do histórico de pedidos)"""
        query = (
            self.db.query(MesaHistoricoModel)
            .filter(MesaHistoricoModel.mesa_id == mesa_id)
        )
        if empresa_id is not None:
            query = query.join(MesaModel, MesaModel.id == MesaHistoricoModel.mesa_id).filter(MesaModel.empresa_id == empresa_id)
        return query.order_by(MesaHistoricoModel.created_at.desc()).limit(limit).all()
