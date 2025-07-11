from sqlalchemy.orm import Session

from app.api.BI.models.meta_model import Meta
from app.api.BI.schemas.metas_types import TypeInserirMetaRequest
from app.api.BI.repositories.metas.metasRepo import buscar_meta, inserir_meta, atualizar_valor_meta
from datetime import datetime

def salvar_ou_atualizar_meta(request: TypeInserirMetaRequest, db: Session) -> str:
    try:
        data_convertida = datetime.strptime(request.data, "%Y-%m-%d").date()

        meta = buscar_meta(db, request.empresa, request.data, request.tipo)

        if meta:
            atualizar_valor_meta(meta, request.valor)
            mensagem = "Meta atualizada com sucesso!"
        else:
            nova_meta = Meta(
                mefi_codempresa=request.empresa,
                mefi_data=data_convertida,
                mefi_descricao=request.tipo,
                mefi_valor=request.valor,
            )
            inserir_meta(db, nova_meta)
            mensagem = "Nova meta adicionada com sucesso!"

        db.commit()
        return mensagem

    except Exception as e:
        db.rollback()
        return f"Erro ao salvar meta: {e}"
