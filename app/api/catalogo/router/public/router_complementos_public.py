from typing import List
from enum import Enum

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.api.catalogo.schemas.schema_complemento import ComplementoResponse
from app.api.catalogo.services.service_complemento import ComplementoService
from app.api.catalogo.models.model_receita import ReceitaModel
from app.api.catalogo.models.model_combo import ComboModel
from app.database.db_connection import get_db
from app.utils.logger import logger


router = APIRouter(
    prefix="/api/catalogo/public/complementos",
    tags=["Public - Catalogo - Complementos"],
)


class TipoProdutoEnum(str, Enum):
    """Tipos de produtos que podem ter complementos"""
    PRODUTO = "produto"
    COMBO = "combo"
    RECEITA = "receita"


class TipoPedidoEnum(str, Enum):
    """Tipos de pedido para filtro de complementos"""
    BALCAO = "balcao"
    MESA = "mesa"
    DELIVERY = "delivery"


@router.get("", response_model=List[ComplementoResponse])
def listar_complementos_unificado(
    tipo: TipoProdutoEnum = Query(..., description="Tipo do produto: produto, combo ou receita"),
    identificador: str = Query(..., description="Código de barras (para produto) ou ID (para combo/receita)"),
    tipo_pedido: TipoPedidoEnum = Query(..., description="Tipo de pedido: balcao, mesa ou delivery"),
    apenas_ativos: bool = Query(True, description="Retornar apenas complementos ativos"),
    db: Session = Depends(get_db),
):
    """
    Endpoint unificado para listar complementos de produtos, combos ou receitas.
    
    Este endpoint substitui os endpoints antigos:
    - GET /api/catalogo/public/complementos/produto/{cod_barras}
    - GET /api/catalogo/public/complementos/combo/{combo_id}
    - GET /api/catalogo/public/complementos/receita/{receita_id}
    
    **Parâmetros obrigatórios:**
    - `tipo`: Tipo do produto (produto, combo ou receita)
    - `identificador`: Código de barras para produtos ou ID numérico para combos/receitas
    - `tipo_pedido`: Tipo de pedido (balcao, mesa ou delivery) - obrigatório para futuras implementações de filtro
    
    **Parâmetros opcionais:**
    - `apenas_ativos`: Se True (padrão), retorna apenas complementos ativos
    
    **Exemplos de uso:**
    - Produto: GET /api/catalogo/public/complementos?tipo=produto&identificador=123456&tipo_pedido=delivery
    - Combo: GET /api/catalogo/public/complementos?tipo=combo&identificador=5&tipo_pedido=mesa
    - Receita: GET /api/catalogo/public/complementos?tipo=receita&identificador=10&tipo_pedido=balcao
    
    Endpoint público - não requer autenticação.
    """
    logger.info(f"[Complementos Public] Listar unificado - tipo={tipo.value}, identificador={identificador}, tipo_pedido={tipo_pedido.value}")
    
    service = ComplementoService(db)
    
    try:
        if tipo == TipoProdutoEnum.PRODUTO:
            # Para produtos, o identificador é o código de barras (string)
            complementos = service.repo.listar_por_produto(
                identificador, 
                apenas_ativos=apenas_ativos, 
                carregar_adicionais=True
            )
            logger.info(f"[Complementos Public] Encontrados {len(complementos)} complementos para produto {identificador}")
            
        elif tipo == TipoProdutoEnum.COMBO:
            # Para combos, o identificador é um ID (int)
            try:
                combo_id = int(identificador)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Para combos, o identificador deve ser um número inteiro. Recebido: {identificador}"
                )
            
            # Valida se o combo existe e está ativo
            combo = db.query(ComboModel).filter(ComboModel.id == combo_id).first()
            if not combo or not combo.ativo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Combo {combo_id} não encontrado ou inativo"
                )
            
            complementos = service.repo.listar_por_combo(
                combo_id, 
                apenas_ativos=apenas_ativos, 
                carregar_adicionais=True
            )
            logger.info(f"[Complementos Public] Encontrados {len(complementos)} complementos para combo {combo_id}")
            
        elif tipo == TipoProdutoEnum.RECEITA:
            # Para receitas, o identificador é um ID (int)
            try:
                receita_id = int(identificador)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Para receitas, o identificador deve ser um número inteiro. Recebido: {identificador}"
                )
            
            # Valida se a receita existe e está ativa/disponível
            receita = db.query(ReceitaModel).filter(ReceitaModel.id == receita_id).first()
            if not receita or not receita.ativo or not receita.disponivel:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Receita {receita_id} não encontrada ou inativa"
                )
            
            complementos = service.repo.listar_por_receita(
                receita_id, 
                apenas_ativos=apenas_ativos, 
                carregar_adicionais=True
            )
            logger.info(f"[Complementos Public] Encontrados {len(complementos)} complementos para receita {receita_id}")
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo inválido: {tipo}. Use 'produto', 'combo' ou 'receita'"
            )
        
        # Converte para response
        result = [service.complemento_to_response(c) for c in complementos]
        
        if not result:
            logger.warning(f"[Complementos Public] Nenhum complemento encontrado para {tipo.value}={identificador} (apenas_ativos={apenas_ativos}, tipo_pedido={tipo_pedido.value})")
        
        # TODO: Implementar filtro por tipo_pedido quando necessário
        # Por enquanto, o parâmetro é obrigatório mas não é usado para filtrar
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Complementos Public] Erro ao listar complementos: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar complementos: {str(e)}"
        )

