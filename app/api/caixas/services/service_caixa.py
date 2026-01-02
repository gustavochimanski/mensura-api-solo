from typing import Optional, List
from datetime import date
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.caixas.repositories.repo_caixa import CaixaRepository
from app.api.caixas.repositories.repo_retirada import RetiradaRepository
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.cadastros.repositories.usuarios_repo import UsuarioRepository
from app.api.caixas.schemas.schema_caixa import (
    CaixaCreate,
    CaixaUpdate,
    CaixaFechamentoRequest,
    CaixaResponse,
    CaixaResumoResponse,
    CaixaValoresEsperadosResponse,
    CaixaConferenciaEsperadoResponse,
    CaixaConferenciaResumoResponse,
    ConferenciaMeioPagamentoResponse,
    RetiradaCreate,
    RetiradaResponse
)
from app.api.caixas.models.model_caixa import CaixaModel
from app.utils.logger import logger


class CaixaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CaixaRepository(db)
        self.repo_retirada = RetiradaRepository(db)
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

    def abrir_caixa(self, data: CaixaCreate, usuario_id: int) -> CaixaResponse:
        """Abre um novo caixa para a empresa"""
        # Valida empresa
        self._empresa_or_404(data.empresa_id)
        
        # Valida usuário
        self._usuario_or_404(usuario_id)
        
        # Verifica se já existe caixa aberto
        caixa_aberto = self.repo.get_caixa_aberto(data.empresa_id)
        if caixa_aberto:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe um caixa aberto para esta empresa (ID: {caixa_aberto.id}). Feche o caixa antes de abrir um novo."
            )
        
        # Cria o caixa
        caixa = self.repo.create(
            empresa_id=data.empresa_id,
            usuario_id_abertura=usuario_id,
            valor_inicial=data.valor_inicial,
            data_hora_abertura=data.data_hora_abertura,
            observacoes_abertura=data.observacoes_abertura,
            status="ABERTO"
        )
        
        logger.info(f"[Caixa] Aberto caixa_id={caixa.id} empresa_id={data.empresa_id} usuario_id={usuario_id}")
        
        return self._caixa_to_response(caixa)

    def fechar_caixa(
        self,
        caixa_id: int,
        data: CaixaFechamentoRequest,
        usuario_id: int
    ) -> CaixaResponse:
        """Fecha um caixa"""
        # Busca o caixa
        caixa = self.repo.get_by_id(caixa_id)
        if not caixa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caixa não encontrado"
            )
        
        # Valida se está aberto
        if caixa.status != "ABERTO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Caixa já está fechado (status: {caixa.status})"
            )
        
        # Valida usuário
        self._usuario_or_404(usuario_id)
        
        # Calcula saldo esperado antes de fechar
        try:
            self.repo.calcular_saldo_esperado(caixa_id, caixa.empresa_id)
            # Recarrega para pegar o saldo_esperado atualizado
            caixa = self.repo.get_by_id(caixa_id)
        except Exception as e:
            logger.warning(f"[Caixa] Erro ao calcular saldo esperado: {e}")
        
        # Calcula valores esperados por meio de pagamento
        valores_esperados = self.repo.calcular_valores_esperados_por_meio(caixa_id, caixa.empresa_id)
        
        # Processa conferências
        if data.conferencias:
            # Monta lista de conferências para salvar
            conferencias_para_salvar = []
            for conf_req in data.conferencias:
                # Busca o valor esperado para este meio de pagamento
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
            
            # Cria registros de conferência
            self.repo.criar_conferencias(caixa_id, conferencias_para_salvar)
        
        # Fecha o caixa
        caixa = self.repo.fechar_caixa(
            caixa=caixa,
            saldo_real=data.saldo_real,
            data_hora_fechamento=data.data_hora_fechamento,
            observacoes_fechamento=data.observacoes_fechamento,
            usuario_id_fechamento=usuario_id
        )
        
        logger.info(f"[Caixa] Fechado caixa_id={caixa_id} saldo_real={data.saldo_real} diferenca={caixa.diferenca}")
        
        return self._caixa_to_response(caixa)

    def get_caixa_aberto(self, empresa_id: int) -> Optional[CaixaResponse]:
        """Busca o caixa aberto de uma empresa"""
        self._empresa_or_404(empresa_id)
        caixa = self.repo.get_caixa_aberto(empresa_id)
        if not caixa:
            return None
        return self._caixa_to_response(caixa)

    def get_by_id(self, caixa_id: int) -> CaixaResponse:
        """Busca um caixa por ID"""
        caixa = self.repo.get_by_id(caixa_id)
        if not caixa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caixa não encontrado"
            )
        return self._caixa_to_response(caixa)

    def list(
        self,
        empresa_id: Optional[int] = None,
        status: Optional[str] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[CaixaResumoResponse]:
        """Lista caixas com filtros"""
        if empresa_id:
            self._empresa_or_404(empresa_id)
        
        caixas = self.repo.list(
            empresa_id=empresa_id,
            status=status,
            data_inicio=data_inicio,
            data_fim=data_fim,
            skip=skip,
            limit=limit
        )
        
        return [self._caixa_to_resumo(c) for c in caixas]

    def get_valores_esperados(self, caixa_id: int) -> CaixaValoresEsperadosResponse:
        """
        Retorna valores esperados por tipo de pagamento para um caixa aberto.
        Útil antes do fechamento para conferência.
        """
        caixa = self.repo.get_by_id(caixa_id)
        if not caixa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caixa não encontrado"
            )
        
        if caixa.status != "ABERTO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Só é possível consultar valores esperados de caixas abertos"
            )
        
        # Calcula valores por meio de pagamento
        valores_por_meio = self.repo.calcular_valores_esperados_por_meio(caixa_id, caixa.empresa_id)
        
        # Calcula saldo esperado de dinheiro
        try:
            saldo_esperado_dinheiro = self.repo.calcular_saldo_esperado(caixa_id, caixa.empresa_id)
            caixa = self.repo.get_by_id(caixa_id)  # Recarrega
        except Exception as e:
            logger.warning(f"[Caixa] Erro ao calcular saldo esperado: {e}")
            saldo_esperado_dinheiro = Decimal('0')
        
        # Formata valores por meio
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
        
        return CaixaValoresEsperadosResponse(
            caixa_id=caixa.id,
            empresa_id=caixa.empresa_id,
            data_abertura=caixa.data_abertura,
            valor_inicial_dinheiro=float(caixa.valor_inicial),
            valores_por_meio=valores_por_meio_response,
            total_esperado_dinheiro=float(saldo_esperado_dinheiro)
        )

    def get_conferencias(self, caixa_id: int) -> CaixaConferenciaResumoResponse:
        """Retorna todas as conferências de um caixa fechado"""
        caixa = self.repo.get_by_id(caixa_id)
        if not caixa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caixa não encontrado"
            )
        
        conferencias = self.repo.get_conferencias_by_caixa(caixa_id)
        
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
        
        return CaixaConferenciaResumoResponse(
            caixa_id=caixa_id,
            conferencias=conferencias_response
        )

    def calcular_saldo_esperado(self, caixa_id: int) -> CaixaResponse:
        """Recalcula o saldo esperado do caixa"""
        caixa = self.repo.get_by_id(caixa_id)
        if not caixa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caixa não encontrado"
            )
        
        if caixa.status != "ABERTO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Só é possível recalcular saldo de caixas abertos"
            )
        
        try:
            self.repo.calcular_saldo_esperado(caixa_id, caixa.empresa_id)
            # Recarrega
            caixa = self.repo.get_by_id(caixa_id)
            logger.info(f"[Caixa] Saldo recalculado caixa_id={caixa_id} saldo_esperado={caixa.saldo_esperado}")
        except Exception as e:
            logger.error(f"[Caixa] Erro ao recalcular saldo: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao recalcular saldo: {str(e)}"
            )
        
        return self._caixa_to_response(caixa)

    def _caixa_to_response(self, caixa: CaixaModel) -> CaixaResponse:
        """Converte model para response"""
        return CaixaResponse(
            id=caixa.id,
            empresa_id=caixa.empresa_id,
            usuario_id_abertura=caixa.usuario_id_abertura,
            usuario_id_fechamento=caixa.usuario_id_fechamento,
            valor_inicial=float(caixa.valor_inicial),
            valor_final=float(caixa.valor_final) if caixa.valor_final else None,
            saldo_esperado=float(caixa.saldo_esperado) if caixa.saldo_esperado else None,
            saldo_real=float(caixa.saldo_real) if caixa.saldo_real else None,
            diferenca=float(caixa.diferenca) if caixa.diferenca else None,
            status=caixa.status,
            data_abertura=caixa.data_abertura,
            data_fechamento=caixa.data_fechamento,
            data_hora_abertura=caixa.data_hora_abertura,
            data_hora_fechamento=caixa.data_hora_fechamento,
            observacoes_abertura=caixa.observacoes_abertura,
            observacoes_fechamento=caixa.observacoes_fechamento,
            created_at=caixa.created_at,
            updated_at=caixa.updated_at,
            empresa_nome=caixa.empresa.nome if caixa.empresa else None,
            usuario_abertura_nome=caixa.usuario_abertura.username if caixa.usuario_abertura else None,
            usuario_fechamento_nome=caixa.usuario_fechamento.username if caixa.usuario_fechamento else None,
        )

    def _caixa_to_resumo(self, caixa: CaixaModel) -> CaixaResumoResponse:
        """Converte model para resumo"""
        return CaixaResumoResponse(
            id=caixa.id,
            empresa_id=caixa.empresa_id,
            empresa_nome=caixa.empresa.nome if caixa.empresa else None,
            usuario_abertura_nome=caixa.usuario_abertura.username if caixa.usuario_abertura else None,
            valor_inicial=float(caixa.valor_inicial),
            valor_final=float(caixa.valor_final) if caixa.valor_final else None,
            saldo_esperado=float(caixa.saldo_esperado) if caixa.saldo_esperado else None,
            saldo_real=float(caixa.saldo_real) if caixa.saldo_real else None,
            diferenca=float(caixa.diferenca) if caixa.diferenca else None,
            status=caixa.status,
            data_abertura=caixa.data_abertura,
            data_fechamento=caixa.data_fechamento,
            data_hora_abertura=caixa.data_hora_abertura,
            data_hora_fechamento=caixa.data_hora_fechamento,
        )

    # ==================== MÉTODOS DE RETIRADA ====================

    def criar_retirada(
        self,
        caixa_id: int,
        data: RetiradaCreate,
        usuario_id: int
    ) -> RetiradaResponse:
        """Cria uma nova retirada do caixa"""
        # Valida caixa
        caixa = self.repo.get_by_id(caixa_id)
        if not caixa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caixa não encontrado"
            )
        
        # Valida se está aberto
        if caixa.status != "ABERTO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas caixas abertos podem receber retiradas"
            )
        
        # Valida observação para DESPESA
        if data.tipo == "DESPESA" and not data.observacoes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Observação é obrigatória para despesas"
            )
        
        # Valida usuário
        self._usuario_or_404(usuario_id)
        
        # Cria a retirada
        retirada = self.repo_retirada.create(
            caixa_id=caixa_id,
            usuario_id=usuario_id,
            tipo=data.tipo.value,
            valor=float(data.valor),
            observacoes=data.observacoes
        )
        
        self.db.commit()
        
        # Recalcula saldo esperado
        try:
            self.repo.calcular_saldo_esperado(caixa_id, caixa.empresa_id)
        except Exception as e:
            logger.warning(f"[Caixa] Erro ao recalcular saldo após retirada: {e}")
        
        logger.info(f"[Caixa] Retirada criada retirada_id={retirada.id} caixa_id={caixa_id} tipo={data.tipo} valor={data.valor}")
        
        return self._retirada_to_response(retirada)

    def listar_retiradas(
        self,
        caixa_id: int,
        tipo: Optional[str] = None
    ) -> List[RetiradaResponse]:
        """Lista retiradas de um caixa"""
        # Valida caixa
        caixa = self.repo.get_by_id(caixa_id)
        if not caixa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caixa não encontrado"
            )
        
        retiradas = self.repo_retirada.list_by_caixa(caixa_id, tipo)
        return [self._retirada_to_response(r) for r in retiradas]

    def excluir_retirada(self, retirada_id: int) -> None:
        """Exclui uma retirada (apenas de caixas abertos)"""
        retirada = self.repo_retirada.get_by_id(retirada_id)
        if not retirada:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Retirada não encontrada"
            )
        
        # Valida se o caixa está aberto
        caixa = self.repo.get_by_id(retirada.caixa_id)
        if not caixa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caixa não encontrado"
            )
        
        if caixa.status != "ABERTO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas retiradas de caixas abertos podem ser excluídas"
            )
        
        caixa_id = retirada.caixa_id
        self.repo_retirada.delete(retirada)
        self.db.commit()
        
        # Recalcula saldo esperado
        try:
            self.repo.calcular_saldo_esperado(caixa_id, caixa.empresa_id)
        except Exception as e:
            logger.warning(f"[Caixa] Erro ao recalcular saldo após exclusão de retirada: {e}")
        
        logger.info(f"[Caixa] Retirada excluída retirada_id={retirada_id} caixa_id={caixa_id}")

    def _retirada_to_response(self, retirada) -> RetiradaResponse:
        """Converte model de retirada para response"""
        return RetiradaResponse(
            id=retirada.id,
            caixa_id=retirada.caixa_id,
            tipo=retirada.tipo,
            valor=float(retirada.valor),
            observacoes=retirada.observacoes,
            usuario_id=retirada.usuario_id,
            usuario_nome=retirada.usuario.username if retirada.usuario else None,
            created_at=retirada.created_at
        )

