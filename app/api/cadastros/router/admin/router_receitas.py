from fastapi import APIRouter, Depends, Body, Path, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.cadastros.services.service_receitas import ReceitasService
from app.api.cadastros.schemas.schema_receitas import (
    IngredienteIn,
    IngredienteOut,
    AdicionalIn,
    AdicionalOut,
)
from app.database.db_connection import get_db
from app.core.admin_dependencies import get_current_user


router = APIRouter(
    prefix="/api/cadastros/admin/receitas",
    tags=["Admin - Mensura - Receitas"],
    dependencies=[Depends(get_current_user)]
)


# Ingredientes
@router.get("/{cod_barras}/ingredientes", response_model=list[IngredienteOut])
def list_ingredientes(
    cod_barras: str = Path(..., description="ID da receita (passado como cod_barras para compatibilidade)"),
    db: Session = Depends(get_db),
):
    from app.api.catalogo.model_ingrediente import IngredienteModel
    
    # Busca os ingredientes
    receita_ingredientes = ReceitasService(db).list_ingredientes(cod_barras)
    
    # Transforma para o schema de saída com dados do ingrediente
    resultado = []
    for ri in receita_ingredientes:
        # Carrega o ingrediente se não estiver carregado
        if not ri.ingrediente:
            ri.ingrediente = db.query(IngredienteModel).filter_by(id=ri.ingrediente_id).first()
        
        # Converte quantidade para float (None se não houver)
        quantidade = float(ri.quantidade) if ri.quantidade is not None else None
        
        # Converte custo para Decimal (None se não houver)
        ingrediente_custo = ri.ingrediente.custo if ri.ingrediente and ri.ingrediente.custo is not None else None
        
        resultado.append(IngredienteOut(
            id=ri.id,
            receita_id=ri.receita_id,
            ingrediente_id=ri.ingrediente_id,
            quantidade=quantidade,
            ingrediente_nome=ri.ingrediente.nome if ri.ingrediente else None,
            ingrediente_descricao=ri.ingrediente.descricao if ri.ingrediente else None,
            ingrediente_unidade_medida=ri.ingrediente.unidade_medida if ri.ingrediente else None,
            ingrediente_custo=ingrediente_custo,
            produto_cod_barras=str(ri.receita_id),  # Compatibilidade: receita_id como string
            ingrediente_cod_barras=str(ri.ingrediente_id) if ri.ingrediente_id else None,  # Compatibilidade: ingrediente_id como string
            unidade=ri.ingrediente.unidade_medida if ri.ingrediente else None,  # Compatibilidade: alias para ingrediente_unidade_medida
        ))
    
    return resultado


@router.post("/ingredientes", response_model=IngredienteOut, status_code=status.HTTP_201_CREATED)
def add_ingrediente(
    body: IngredienteIn,
    db: Session = Depends(get_db),
):
    return ReceitasService(db).add_ingrediente(body)


@router.put("/ingredientes/{ingrediente_id}", response_model=IngredienteOut)
def update_ingrediente(
    ingrediente_id: int = Path(...),
    quantidade: Optional[float] = Body(None),
    unidade: Optional[str] = Body(None),
    db: Session = Depends(get_db),
):
    return ReceitasService(db).update_ingrediente(ingrediente_id, quantidade, unidade)


@router.delete("/ingredientes/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_ingrediente(
    ingrediente_id: int,
    db: Session = Depends(get_db),
):
    ReceitasService(db).remove_ingrediente(ingrediente_id)
    return {"ok": True}


# Adicionais
@router.get("/{cod_barras}/adicionais", response_model=list[AdicionalOut])
def list_adicionais(
    cod_barras: str,
    db: Session = Depends(get_db),
):
    # Busca os adicionais
    receita_adicionais = ReceitasService(db).list_adicionais(cod_barras)
    
    # Transforma para o schema de saída
    resultado = []
    for ra in receita_adicionais:
        resultado.append(AdicionalOut(
            id=ra.id,
            produto_cod_barras=str(ra.receita_id),  # Compatibilidade: receita_id como string
            adicional_id=ra.adicional_id,
            preco=ra.preco,
        ))
    
    return resultado


@router.post("/adicionais", response_model=AdicionalOut, status_code=status.HTTP_201_CREATED)
def add_adicional(
    body: AdicionalIn,
    db: Session = Depends(get_db),
):
    return ReceitasService(db).add_adicional(body)


@router.delete("/adicionais/{adicional_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_adicional(
    adicional_id: int,
    db: Session = Depends(get_db),
):
    ReceitasService(db).remove_adicional(adicional_id)
    return {"ok": True}


