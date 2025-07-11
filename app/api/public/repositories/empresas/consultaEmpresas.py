# app/api/public/repositories/empresas/consultaEmpresas.py
import logging
from typing import List
from sqlalchemy.orm import Session
from app.api.public.models.empresa.empresasModel import Empresa

logger = logging.getLogger(__name__)

class EmpresasRepository:
    def __init__(self, db: Session):
        self.db = db

    def buscar_codigos_ativos(self) -> List[int]:
        empresas = self.db.query(Empresa).filter(Empresa.empr_situacao == "A").all()
        codigos = [int(e.empr_codigo) for e in empresas]
        return codigos

    def buscar_empresas_ativas(self) -> List[Empresa]:
        return self.db.query(Empresa).filter(Empresa.empr_situacao == "A").all()
