# app/api/empresas/router/public/router_empresa_public.py
from typing import Union
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.notifications.models.whatsapp_config_model import WhatsAppConfigModel
from app.api.empresas.schemas.schema_empresa_client import (
    EmpresaClientOut,
    EmpresaPublicListItem,
    HorarioDiaOut,
    HorarioIntervaloOut,
)
from app.database.db_connection import get_db


router = APIRouter(prefix="/api/empresas/public/emp", tags=["Public - Empresas"])


@router.get(
    "/lista",
    response_model=Union[EmpresaPublicListItem, list[EmpresaPublicListItem]],
    summary="Listar empresas públicas",
    description="Retorna empresas disponíveis para seleção pública, com filtros opcionais. Se empresa_id for fornecido, retorna um único objeto.",
)
def listar_empresas_publicas(
    empresa_id: int | None = Query(None, description="Filtrar por ID da empresa"),
    q: str | None = Query(None, description="Termo de busca por nome ou slug"),
    cidade: str | None = Query(None, description="Filtrar por cidade"),
    estado: str | None = Query(None, description="Filtrar por estado (sigla)"),
    limit: int = Query(100, ge=1, le=500, description="Limite máximo de empresas retornadas"),
    db: Session = Depends(get_db),
):
    repo_emp = EmpresaRepository(db)
    empresas = repo_emp.search_public(
        empresa_id=empresa_id,
        q=q,
        cidade=cidade,
        estado=estado,
        limit=limit,
    )

    # Fallback de telefone: se `cadastros.empresas.telefone` estiver vazio,
    # tenta usar o número ativo do WhatsApp Business (display_phone_number).
    #
    # Isso evita endpoint "sem telefone" em instalações onde o número foi
    # cadastrado apenas na integração do WhatsApp.
    whatsapp_phone_by_empresa_id: dict[str, str] = {}
    empresas_sem_telefone = [e for e in empresas if not (getattr(e, "telefone", None) or "").strip()]
    if empresas_sem_telefone:
        ids_str = [str(int(e.id)) for e in empresas_sem_telefone if getattr(e, "id", None) is not None]
        if ids_str:
            configs = (
                db.query(WhatsAppConfigModel)
                .filter(
                    WhatsAppConfigModel.empresa_id.in_(ids_str),
                    WhatsAppConfigModel.is_active.is_(True),
                )
                .order_by(WhatsAppConfigModel.updated_at.desc())
                .all()
            )
            for cfg in configs:
                emp_id = str(getattr(cfg, "empresa_id", "") or "")
                phone = (getattr(cfg, "display_phone_number", None) or "").strip()
                if emp_id and phone and emp_id not in whatsapp_phone_by_empresa_id:
                    whatsapp_phone_by_empresa_id[emp_id] = phone
    
    # Se empresa_id foi fornecido, retorna objeto único
    if empresa_id is not None:
        if not empresas:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        empresa = empresas[0]
        # Converte horarios_funcionamento de JSONB para lista de HorarioDiaOut
        horarios = None
        if empresa.horarios_funcionamento:
            horarios = [
                HorarioDiaOut(
                    dia_semana=dia.get("dia_semana"),
                    intervalos=[
                        HorarioIntervaloOut(inicio=intervalo.get("inicio"), fim=intervalo.get("fim"))
                        for intervalo in dia.get("intervalos", [])
                    ]
                )
                for dia in empresa.horarios_funcionamento
            ]
        telefone_publico = (getattr(empresa, "telefone", None) or "").strip() or whatsapp_phone_by_empresa_id.get(str(int(empresa.id)))
        return EmpresaPublicListItem(
            id=empresa.id,
            nome=empresa.nome,
            logo=empresa.logo,
            telefone=telefone_publico,
            bairro=empresa.bairro,
            cidade=empresa.cidade,
            estado=empresa.estado,
            distancia_km=None,
            tema=empresa.cardapio_tema,
            horarios_funcionamento=horarios,
            landingpage_store=empresa.landingpage_store,
        )
        
    
    # Caso contrário, retorna list
    return [
        EmpresaPublicListItem(
            id=empresa.id,
            nome=empresa.nome,
            logo=empresa.logo,
            telefone=(getattr(empresa, "telefone", None) or "").strip() or whatsapp_phone_by_empresa_id.get(str(int(empresa.id))),
            bairro=empresa.bairro,
            cidade=empresa.cidade,
            estado=empresa.estado,
            distancia_km=None,
            tema=empresa.cardapio_tema,
            landingpage_store=empresa.landingpage_store,
        )
        for empresa in empresas
    ]


@router.get("/", response_model=EmpresaClientOut)
def buscar_empresa_client(
    empresa_id: int = Query(..., description="ID da empresa"),
    db: Session = Depends(get_db),
):
    repo_emp = EmpresaRepository(db)
    empresa = repo_emp.get_empresa_by_id(empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa

