from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.cadastros.repositories.repo_entregadores import EntregadorRepository
from app.api.cadastros.schemas.schema_entregador import EntregadorCreate, EntregadorUpdate
from app.utils.logger import logger

class EntregadoresService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EntregadorRepository(db)
        self.empresa_repo = EmpresaRepository(db)

    def list(self):
        return self.repo.list()

    def get(self, id_: int):
        obj = self.repo.get(id_)
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Entregador não encontrado")
        return obj

    def create(self, data: EntregadorCreate):
        try:
            logger.info(f"[EntregadoresService] Tentando criar entregador: nome={getattr(data, 'nome', 'N/A')}, empresa_id={getattr(data, 'empresa_id', 'N/A')}")
            
            # Verifica se a empresa existe antes de criar o entregador
            if hasattr(data, 'empresa_id') and data.empresa_id:
                empresa = self.empresa_repo.get_empresa_by_id(data.empresa_id)
                if not empresa:
                    error_msg = f"Empresa com ID {data.empresa_id} não encontrada"
                    logger.error(f"[EntregadoresService] {error_msg}")
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND,
                        error_msg
                    )
            
            result = self.repo.create_with_empresa(**data.model_dump(exclude_unset=True))
            logger.info(f"[EntregadoresService] Entregador criado com sucesso: ID={result.id}")
            return result
        except IntegrityError as e:
            self.db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            
            # Trata erros de chave estrangeira
            if "foreign key" in error_msg.lower() or "violates foreign key constraint" in error_msg.lower():
                if "empresa" in error_msg.lower():
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND,
                        f"Empresa com ID {data.empresa_id} não encontrada"
                    )
                else:
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        "Erro ao criar entregador: referência inválida"
                    )
            

            # Trata outros erros de integridade
            logger.error(f"[EntregadoresService] Erro de integridade ao criar entregador: {error_msg}")
            logger.error(f"[EntregadoresService] Dados recebidos: {data.model_dump()}")
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Erro ao criar entregador: {error_msg}"
            )
        except HTTPException as http_exc:
            # Re-loga HTTPExceptions com mais detalhes
            logger.error(f"[EntregadoresService] HTTPException: {http_exc.status_code} - {http_exc.detail}")
            raise
        except Exception as e:
            self.db.rollback()
            import traceback
            logger.error(f"[EntregadoresService] Erro inesperado ao criar entregador: {str(e)}")
            logger.error(f"[EntregadoresService] Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"Erro ao criar entregador: {str(e)}"
            )

    def update(self, id_: int, data: EntregadorUpdate):
        obj = self.get(id_)
        return self.repo.update(obj, **data.model_dump(exclude_none=True))

    def vincular_empresa(self, entregador_id: int, empresa_id: int):
        try:
            # primeiro garante que o entregador existe
            self.get(entregador_id)
            
            # Verifica se a empresa existe
            empresa = self.empresa_repo.get_empresa_by_id(empresa_id)
            if not empresa:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    f"Empresa com ID {empresa_id} não encontrada"
                )
            
            self.repo.vincular_empresa(entregador_id, empresa_id)
            return self.get(entregador_id)  # retorna o entregador atualizado
        except IntegrityError as e:
            self.db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            
            if "foreign key" in error_msg.lower() or "violates foreign key constraint" in error_msg.lower():
                if "empresa" in error_msg.lower():
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND,
                        f"Empresa com ID {empresa_id} não encontrada"
                    )
            
            logger.error(f"Erro ao vincular empresa: {error_msg}")
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Erro ao vincular empresa ao entregador"
            )
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro inesperado ao vincular empresa: {str(e)}")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"Erro ao vincular empresa: {str(e)}"
            )

    def desvincular_empresa(self, entregador_id: int, empresa_id: int):
        try:
            # garante que o entregador existe
            self.get(entregador_id)
            self.repo.desvincular_empresa(entregador_id, empresa_id)
            return self.get(entregador_id)  # retorna o entregador atualizado
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao desvincular empresa: {str(e)}")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"Erro ao desvincular empresa: {str(e)}"
            )

    def delete(self, id_: int):
        obj = self.get(id_)
        self.repo.delete(obj)
        return {"ok": True}

