from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from app.api.catalogo.contracts.complemento_contract import IComplementoContract, ComplementoDTO, AdicionalDTO
from app.api.catalogo.repositories.repo_complemento import ComplementoRepository
from app.api.catalogo.repositories.repo_complemento_item import ComplementoItemRepository


class ComplementoAdapter(IComplementoContract):
    def __init__(self, db: Session):
        self.repo = ComplementoRepository(db)
        self.repo_item = ComplementoItemRepository(db)

    def _build_complemento_dto(self, complemento) -> ComplementoDTO:
        """Monta o DTO de complemento garantindo ordem e preço aplicado por complemento."""
        itens = self.repo_item.listar_itens_complemento(complemento.id, apenas_ativos=True)
        adicionais_dto = [
            AdicionalDTO(
                id=item.id,
                nome=item.nome,
                preco=getattr(item, "preco_aplicado", item.preco),
                ordem=ordem,
            )
            for item, ordem in itens
        ]

        return ComplementoDTO(
            id=complemento.id,
            nome=complemento.nome,
            descricao=complemento.descricao,
            obrigatorio=complemento.obrigatorio,
            quantitativo=complemento.quantitativo,
            permite_multipla_escolha=complemento.permite_multipla_escolha,
            ordem=complemento.ordem,
            adicionais=adicionais_dto,
        )

    def listar_por_produto(self, cod_barras: str, apenas_ativos: bool = True) -> List[ComplementoDTO]:
        complementos = self.repo.listar_por_produto(
            cod_barras,
            apenas_ativos=apenas_ativos,
            carregar_adicionais=False,
        )
        return [self._build_complemento_dto(c) for c in complementos]

    def buscar_por_ids_para_produto(self, cod_barras: str, complemento_ids: List[int]) -> List[ComplementoDTO]:
        vinculados = self.repo.listar_por_produto(
            cod_barras,
            apenas_ativos=True,
            carregar_adicionais=False,
        )
        ids_set = set(complemento_ids or [])
        filtrados = [c for c in vinculados if c.id in ids_set]
        return [self._build_complemento_dto(c) for c in filtrados]

    def buscar_por_ids(self, empresa_id: int, complemento_ids: List[int]) -> List[ComplementoDTO]:
        complementos = self.repo.listar_por_empresa(
            empresa_id,
            apenas_ativos=True,
            carregar_adicionais=False,
        )
        ids_set = set(complemento_ids or [])
        filtrados = [c for c in complementos if c.id in ids_set]
        return [self._build_complemento_dto(c) for c in filtrados]
    
    def listar_por_receita(self, receita_id: int, apenas_ativos: bool = True) -> List[ComplementoDTO]:
        """Lista todos os complementos vinculados a uma receita."""
        complementos = self.repo.listar_por_receita(
            receita_id,
            apenas_ativos=apenas_ativos,
            carregar_adicionais=False,
        )
        return [self._build_complemento_dto(c) for c in complementos]
    
    def listar_por_combo(self, combo_id: int, apenas_ativos: bool = True) -> List[ComplementoDTO]:
        """Lista todos os complementos vinculados a um combo."""
        complementos = self.repo.listar_por_combo(
            combo_id,
            apenas_ativos=apenas_ativos,
            carregar_adicionais=False,
        )
        return [self._build_complemento_dto(c) for c in complementos]

