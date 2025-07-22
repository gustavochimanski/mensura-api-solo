from app.api.mensura.models.empresas_model import EmpresaModel


class EmpresasRepository:

    def __init__(self, db):
        self.db = db

    def get_cnpj_by_id(self, emp_id: int):
        return self.db.query(EmpresaModel.cnpj).filter(EmpresaModel.id == emp_id).scalar_one()