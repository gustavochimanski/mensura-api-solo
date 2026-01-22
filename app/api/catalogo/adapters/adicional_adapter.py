from typing import List
from sqlalchemy.orm import Session

from app.api.catalogo.contracts.adicional_contract import IAdicionalContract, AdicionalDTO
from app.api.catalogo.repositories.repo_adicional import AdicionalRepository


class AdicionalAdapter(IAdicionalContract):
    """
    Adapter DEPRECADO - mantido apenas como stub para compatibilidade.
    AdicionalModel foi removido - adicionais agora são vínculos de produtos/receitas/combos em complementos.
    """
    
    def __init__(self, db: Session):
        self.repo = AdicionalRepository(db)

    def listar_por_produto(self, cod_barras: str, apenas_ativos: bool = True) -> List[AdicionalDTO]:
        """Retorna lista vazia - adicionais removidos, usar complementos."""
        return []

    def buscar_por_ids_para_produto(self, cod_barras: str, adicional_ids: List[int]) -> List[AdicionalDTO]:
        """Retorna lista vazia - adicionais removidos, usar complementos."""
        return []
