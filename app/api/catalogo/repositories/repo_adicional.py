from typing import List
from sqlalchemy.orm import Session

# AdicionalModel removido - não é mais usado
# Adicionais agora são vínculos de produtos/receitas/combos em complementos (complemento_vinculo_item)


class AdicionalRepository:
    """
    Repository DEPRECADO - mantido apenas como stub para compatibilidade.
    AdicionalModel foi removido - adicionais agora são vínculos de produtos/receitas/combos em complementos.
    """

    def __init__(self, db: Session):
        self.db = db

    def listar_por_produto(self, cod_barras: str, apenas_ativos: bool = True) -> List:
        """Retorna lista vazia - adicionais removidos, usar complementos."""
        return []
