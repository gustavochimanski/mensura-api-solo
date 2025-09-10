from math import isclose

from sqlalchemy.orm import Session
from app.api.delivery.models.model_regiao_entrega import RegiaoEntregaModel

class RegiaoEntregaRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_empresa(self, empresa_id: int):
        return self.db.query(RegiaoEntregaModel).filter_by(empresa_id=empresa_id).all()

    def get(self, regiao_id: int):
        return self.db.query(RegiaoEntregaModel).filter_by(id=regiao_id).first()

    def get_by_location(self, empresa_id: int, bairro: str, cidade: str, uf: str):
        return (
            self.db.query(RegiaoEntregaModel)
            .filter(
                RegiaoEntregaModel.empresa_id == empresa_id,
                RegiaoEntregaModel.bairro.ilike(bairro.strip()),
                RegiaoEntregaModel.cidade.ilike(cidade.strip()),
                RegiaoEntregaModel.uf.ilike(uf.strip()),
            )
            .first()
        )

    def get_by_coordinates(self, empresa_id: int, lat: float, lon: float, tolerance: float = 0.001):
        """Retorna se já existe região com coordenadas próximas (~100m de raio)"""
        results = (
            self.db.query(RegiaoEntregaModel)
            .filter(RegiaoEntregaModel.empresa_id == empresa_id)
            .all()
        )
        for r in results:
            if r.latitude and r.longitude:
                if isclose(r.latitude, lat, abs_tol=tolerance) and isclose(r.longitude, lon, abs_tol=tolerance):
                    return r
        return None

    def create(self, regiao: RegiaoEntregaModel):
        self.db.add(regiao)
        self.db.commit()
        self.db.refresh(regiao)
        return regiao

    def update(self, regiao: RegiaoEntregaModel, data: dict):
        for k, v in data.items():
            setattr(regiao, k, v)
        self.db.commit()
        self.db.refresh(regiao)
        return regiao

    def delete(self, regiao: RegiaoEntregaModel):
        self.db.delete(regiao)
        self.db.commit()
