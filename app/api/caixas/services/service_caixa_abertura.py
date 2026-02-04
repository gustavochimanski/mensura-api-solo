from typing import Optional, List
from datetime import date
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.caixas.repositories.repo_caixa_abertura import CaixaAberturaRepository
from app.api.caixas.repositories.repo_retirada import RetiradaRepository
from app.api.caixas.repositories.repo_caixa_crud import CaixaCRUDRepository
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.cadastros.repositories.usuarios_repo import UsuarioRepository
from app.api.caixas.schemas.schema_caixa import (
    CaixaAberturaCreate,
    CaixaAberturaFechamentoRequest,
    CaixaAberturaResponse,
    CaixaAberturaResumoResponse,
    CaixaAberturaValoresEsperadosResponse,
    CaixaConferenciaEsperadoResponse,
    CaixaAberturaConferenciaResumoResponse,
    ConferenciaMeioPagamentoResponse,
    RetiradaCreate,
    RetiradaResponse
)
from app.api.caixas.models.model_caixa_abertura import CaixaAberturaModel
from app.utils.logger import logger


class CaixaAberturaService:
    """Service para aberturas de caixa"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = CaixaAberturaRepository(db)
        self.repo_retirada = RetiradaRepository(db)
        self.repo_caixa = CaixaCRUDRepository(db)
        self.repo_empresa = EmpresaRepository(db)
        self.repo_usuario = UsuarioRepository(db)

    def _empresa_or_404(self, empresa_id: int):
        """Valida se empresa existe"""
        empresa = self.repo_empresa.get_empresa_by_id(empresa_id)
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não encontrada"
            )
        return empresa

    def _usuario_or_404(self, usuario_id: int):
        """Valida se usuário existe"""
        usuario = self.repo_usuario.get(usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        return usuario

    def abrir_caixa(self, data: CaixaAberturaCreate, usuario_id: int) -> CaixaAberturaResponse:
        """Abre um novo caixa para a empresa"""
        # Valida empresa
        self._empresa_or_404(data.empresa_id)
        
        # Valida caixa
        caixa = self.repo_caixa.get_by_id(data.caixa_id)
        if not caixa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caixa não encontrado"
            )
        
        if not caixa.ativo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Caixa está inativo"
            )
        
        # Valida usuário
        self._usuario_or_404(usuario_id)
        
        # Verifica se já existe abertura aberta para este caixa
        abertura_aberta = self.repo.get_caixa_aberto(data.empresa_id, data.caixa_id)
        if abertura_aberta:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe uma abertura aberta para este caixa (ID: {abertura_aberta.id}). Feche a abertura antes de abrir uma nova."
            )
        
        # Cria a abertura
        abertura = self.repo.create(
            caixa_id=data.caixa_id,
            empresa_id=data.empresa_id,
            usuario_id_abertura=usuario_id,
            valor_inicial=data.valor_inicial,
            data_hora_abertura=data.data_hora_abertura,
            observacoes_abertura=data.observacoes_abertura,
            status="ABERTO"
        )
        
        logger.info(f"[CaixaAbertura] Aberto caixa_abertura_id={abertura.id} caixa_id={data.caixa_id} empresa_id={data.empresa_id}")
        
        return self._abertura_to_response(abertura)

    def fechar_caixa(
        self,
        caixa_abertura_id: int,
        data: CaixaAberturaFechamentoRequest,
        usuario_id: int
    ) -> CaixaAberturaResponse:
        """Fecha uma abertura de caixa"""
        # Busca a abertura
        abertura = self.repo.get_by_id(caixa_abertura_id)
        if not abertura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Abertura de caixa não encontrada"
            )
        
        # Valida se está aberta
        if abertura.status != "ABERTO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Abertura já está fechada (status: {abertura.status})"
            )
        
        # Valida usuário
        self._usuario_or_404(usuario_id)
        
        # Calcula saldo esperado antes de fechar
        try:
            self.repo.calcular_saldo_esperado(caixa_abertura_id, abertura.empresa_id)
            abertura = self.repo.get_by_id(caixa_abertura_id)
        except Exception as e:
            logger.warning(f"[CaixaAbertura] Erro ao calcular saldo esperado: {e}")
        
        # Calcula valores esperados por meio de pagamento
        valores_esperados = self.repo.calcular_valores_esperados_por_meio(caixa_abertura_id, abertura.empresa_id)
        
        # Processa conferências
        if data.conferencias:
            conferencias_para_salvar = []
            for conf_req in data.conferencias:
                valor_esperado_dict = next(
                    (v for v in valores_esperados if v['meio_pagamento_id'] == conf_req.meio_pagamento_id),
                    None
                )
                valor_esperado = valor_esperado_dict['valor_esperado'] if valor_esperado_dict else Decimal('0')
                qtd_transacoes = valor_esperado_dict['quantidade_transacoes'] if valor_esperado_dict else 0
                
                conferencias_para_salvar.append({
                    'meio_pagamento_id': conf_req.meio_pagamento_id,
                    'valor_esperado': valor_esperado,
                    'valor_conferido': float(conf_req.valor_conferido),
                    'quantidade_transacoes': qtd_transacoes,
                    'observacoes': conf_req.observacoes
                })
            
            self.repo.criar_conferencias(caixa_abertura_id, conferencias_para_salvar)
        
        # Fecha a abertura
        abertura = self.repo.fechar_caixa(
            caixa_abertura=abertura,
            saldo_real=data.saldo_real,
            data_hora_fechamento=data.data_hora_fechamento,
            observacoes_fechamento=data.observacoes_fechamento,
            usuario_id_fechamento=usuario_id
        )
        
        logger.info(f"[CaixaAbertura] Fechado caixa_abertura_id={caixa_abertura_id} saldo_real={data.saldo_real}")
        
        return self._abertura_to_response(abertura)

    def get_caixa_aberto(self, empresa_id: int, caixa_id: Optional[int] = None) -> Optional[CaixaAberturaResponse]:
        """Busca a abertura aberta de uma empresa"""
        self._empresa_or_404(empresa_id)
        abertura = self.repo.get_caixa_aberto(empresa_id, caixa_id)
        if not abertura:
            return None
        return self._abertura_to_response(abertura)

    def get_by_id(self, caixa_abertura_id: int) -> CaixaAberturaResponse:
        """Busca uma abertura por ID"""
        abertura = self.repo.get_by_id(caixa_abertura_id)
        if not abertura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Abertura de caixa não encontrada"
            )
        return self._abertura_to_response(abertura)

    def list(
        self,
        empresa_id: Optional[int] = None,
        caixa_id: Optional[int] = None,
        status: Optional[str] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[CaixaAberturaResumoResponse]:
        """Lista aberturas com filtros"""
        if empresa_id:
            self._empresa_or_404(empresa_id)
        
        aberturas = self.repo.list(
            empresa_id=empresa_id,
            caixa_id=caixa_id,
            status=status,
            data_inicio=data_inicio,
            data_fim=data_fim,
            skip=skip,
            limit=limit
        )
        
        return [self._abertura_to_resumo(a) for a in aberturas]

    def get_valores_esperados(self, caixa_abertura_id: int) -> CaixaAberturaValoresEsperadosResponse:
        """Retorna valores esperados por tipo de pagamento para uma abertura aberta"""
        abertura = self.repo.get_by_id(caixa_abertura_id)
        if not abertura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Abertura de caixa não encontrada"
            )
        
        if abertura.status != "ABERTO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Só é possível consultar valores esperados de aberturas abertas"
            )
        
        valores_por_meio = self.repo.calcular_valores_esperados_por_meio(caixa_abertura_id, abertura.empresa_id)
        
        try:
            saldo_esperado_dinheiro = self.repo.calcular_saldo_esperado(caixa_abertura_id, abertura.empresa_id)
            abertura = self.repo.get_by_id(caixa_abertura_id)
        except Exception as e:
            logger.warning(f"[CaixaAbertura] Erro ao calcular saldo esperado: {e}")
            saldo_esperado_dinheiro = Decimal('0')
        
        valores_por_meio_response = [
            CaixaConferenciaEsperadoResponse(
                meio_pagamento_id=v['meio_pagamento_id'],
                meio_pagamento_nome=v['meio_pagamento_nome'],
                meio_pagamento_tipo=v['meio_pagamento_tipo'],
                valor_esperado=v['valor_esperado'],
                quantidade_transacoes=v['quantidade_transacoes']
            )
            for v in valores_por_meio
        ]
        
        return CaixaAberturaValoresEsperadosResponse(
            caixa_abertura_id=abertura.id,
            caixa_id=abertura.caixa_id,
            empresa_id=abertura.empresa_id,
            data_abertura=abertura.data_abertura,
            valor_inicial_dinheiro=float(abertura.valor_inicial),
            valores_por_meio=valores_por_meio_response,
            total_esperado_dinheiro=float(saldo_esperado_dinheiro)
        )

    def get_conferencias(self, caixa_abertura_id: int) -> CaixaAberturaConferenciaResumoResponse:
        """Retorna todas as conferências de uma abertura fechada"""
        abertura = self.repo.get_by_id(caixa_abertura_id)
        if not abertura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Abertura de caixa não encontrada"
            )
        
        conferencias = self.repo.get_conferencias_by_caixa_abertura(caixa_abertura_id)
        
        conferencias_response = [
            ConferenciaMeioPagamentoResponse(
                meio_pagamento_id=c.meio_pagamento_id,
                meio_pagamento_nome=c.meio_pagamento.nome if c.meio_pagamento else "Desconhecido",
                meio_pagamento_tipo=c.meio_pagamento.tipo.value if c.meio_pagamento and hasattr(c.meio_pagamento.tipo, 'value') else str(c.meio_pagamento.tipo) if c.meio_pagamento else "",
                valor_esperado=float(c.valor_esperado),
                valor_conferido=float(c.valor_conferido),
                diferenca=float(c.diferenca),
                quantidade_transacoes=c.quantidade_transacoes,
                observacoes=c.observacoes
            )
            for c in conferencias
        ]
        
        return CaixaAberturaConferenciaResumoResponse(
            caixa_abertura_id=caixa_abertura_id,
            conferencias=conferencias_response
        )

    def calcular_saldo_esperado(self, caixa_abertura_id: int) -> CaixaAberturaResponse:
        """Recalcula o saldo esperado da abertura"""
        abertura = self.repo.get_by_id(caixa_abertura_id)
        if not abertura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Abertura de caixa não encontrada"
            )
        
        if abertura.status != "ABERTO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Só é possível recalcular saldo de aberturas abertas"
            )
        
        try:
            self.repo.calcular_saldo_esperado(caixa_abertura_id, abertura.empresa_id)
            abertura = self.repo.get_by_id(caixa_abertura_id)
            logger.info(f"[CaixaAbertura] Saldo recalculado caixa_abertura_id={caixa_abertura_id}")
        except Exception as e:
            logger.error(f"[CaixaAbertura] Erro ao recalcular saldo: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao recalcular saldo: {str(e)}"
            )
        
        return self._abertura_to_response(abertura)

    def criar_retirada(
        self,
        caixa_abertura_id: int,
        data: RetiradaCreate,
        usuario_id: int
    ) -> RetiradaResponse:
        """Cria uma nova retirada da abertura"""
        abertura = self.repo.get_by_id(caixa_abertura_id)
        if not abertura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Abertura de caixa não encontrada"
            )
        
        if abertura.status != "ABERTO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas aberturas abertas podem receber retiradas"
            )
        
        if data.tipo == "DESPESA" and not data.observacoes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Observação é obrigatória para despesas"
            )
        
        self._usuario_or_404(usuario_id)
        
        retirada = self.repo_retirada.create(
            empresa_id=abertura.empresa_id,
            caixa_abertura_id=caixa_abertura_id,
            usuario_id=usuario_id,
            tipo=data.tipo.value,
            valor=float(data.valor),
            observacoes=data.observacoes
        )
        
        self.db.commit()
        
        try:
            self.repo.calcular_saldo_esperado(caixa_abertura_id, abertura.empresa_id)
        except Exception as e:
            logger.warning(f"[CaixaAbertura] Erro ao recalcular saldo após retirada: {e}")
        
        logger.info(f"[CaixaAbertura] Retirada criada retirada_id={retirada.id} caixa_abertura_id={caixa_abertura_id}")
        
        return self._retirada_to_response(retirada)

    def listar_retiradas(
        self,
        caixa_abertura_id: int,
        tipo: Optional[str] = None
    ) -> List[RetiradaResponse]:
        """Lista retiradas de uma abertura"""
        abertura = self.repo.get_by_id(caixa_abertura_id)
        if not abertura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Abertura de caixa não encontrada"
            )
        
        retiradas = self.repo_retirada.list_by_caixa_abertura(abertura.empresa_id, caixa_abertura_id, tipo)
        return [self._retirada_to_response(r) for r in retiradas]

    def excluir_retirada(self, retirada_id: int, empresa_id: Optional[int] = None) -> None:
        """Exclui uma retirada (apenas de aberturas abertas)"""
        retirada = self.repo_retirada.get_by_id(retirada_id, empresa_id)
        if not retirada:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Retirada não encontrada"
            )
        
        abertura = self.repo.get_by_id(retirada.caixa_abertura_id)
        if not abertura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Abertura de caixa não encontrada"
            )
        
        # Valida se a retirada pertence à empresa
        if empresa_id and retirada.empresa_id != empresa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Retirada não pertence à empresa informada"
            )
        
        if abertura.status != "ABERTO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas retiradas de aberturas abertas podem ser excluídas"
            )
        
        caixa_abertura_id = retirada.caixa_abertura_id
        self.repo_retirada.delete(retirada)
        self.db.commit()
        
        try:
            self.repo.calcular_saldo_esperado(caixa_abertura_id, abertura.empresa_id)
        except Exception as e:
            logger.warning(f"[CaixaAbertura] Erro ao recalcular saldo após exclusão: {e}")
        
        logger.info(f"[CaixaAbertura] Retirada excluída retirada_id={retirada_id}")

    def _abertura_to_response(self, abertura: CaixaAberturaModel) -> CaixaAberturaResponse:
        """Converte model para response"""
        return CaixaAberturaResponse(
            id=abertura.id,
            caixa_id=abertura.caixa_id,
            empresa_id=abertura.empresa_id,
            usuario_id_abertura=abertura.usuario_id_abertura,
            usuario_id_fechamento=abertura.usuario_id_fechamento,
            valor_inicial=float(abertura.valor_inicial),
            valor_final=float(abertura.valor_final) if abertura.valor_final is not None else None,
            saldo_esperado=float(abertura.saldo_esperado) if abertura.saldo_esperado is not None else None,
            saldo_real=float(abertura.saldo_real) if abertura.saldo_real is not None else None,
            diferenca=float(abertura.diferenca) if abertura.diferenca is not None else None,
            status=abertura.status,
            data_abertura=abertura.data_abertura,
            data_fechamento=abertura.data_fechamento,
            data_hora_abertura=abertura.data_hora_abertura,
            data_hora_fechamento=abertura.data_hora_fechamento,
            observacoes_abertura=abertura.observacoes_abertura,
            observacoes_fechamento=abertura.observacoes_fechamento,
            created_at=abertura.created_at,
            updated_at=abertura.updated_at,
            caixa_nome=abertura.caixa.nome if abertura.caixa else None,
            empresa_nome=abertura.empresa.nome if abertura.empresa else None,
            usuario_abertura_nome=abertura.usuario_abertura.username if abertura.usuario_abertura else None,
            usuario_fechamento_nome=abertura.usuario_fechamento.username if abertura.usuario_fechamento else None,
        )

    def _abertura_to_resumo(self, abertura: CaixaAberturaModel) -> CaixaAberturaResumoResponse:
        """Converte model para resumo"""
        return CaixaAberturaResumoResponse(
            id=abertura.id,
            caixa_id=abertura.caixa_id,
            caixa_nome=abertura.caixa.nome if abertura.caixa else None,
            empresa_id=abertura.empresa_id,
            empresa_nome=abertura.empresa.nome if abertura.empresa else None,
            usuario_abertura_nome=abertura.usuario_abertura.username if abertura.usuario_abertura else None,
            valor_inicial=float(abertura.valor_inicial),
            valor_final=float(abertura.valor_final) if abertura.valor_final is not None else None,
            saldo_esperado=float(abertura.saldo_esperado) if abertura.saldo_esperado is not None else None,
            saldo_real=float(abertura.saldo_real) if abertura.saldo_real is not None else None,
            diferenca=float(abertura.diferenca) if abertura.diferenca is not None else None,
            status=abertura.status,
            data_abertura=abertura.data_abertura,
            data_fechamento=abertura.data_fechamento,
            data_hora_abertura=abertura.data_hora_abertura,
            data_hora_fechamento=abertura.data_hora_fechamento,
        )

    def _retirada_to_response(self, retirada) -> RetiradaResponse:
        """Converte model de retirada para response"""
        return RetiradaResponse(
            id=retirada.id,
            empresa_id=retirada.empresa_id,
            caixa_abertura_id=retirada.caixa_abertura_id,
            tipo=retirada.tipo,
            valor=float(retirada.valor),
            observacoes=retirada.observacoes,
            usuario_id=retirada.usuario_id,
            usuario_nome=retirada.usuario.username if retirada.usuario else None,
            created_at=retirada.created_at
        )

