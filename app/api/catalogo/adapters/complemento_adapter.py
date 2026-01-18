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

    def _build_complemento_dto(self, complemento, ordem: int = None) -> ComplementoDTO:
        """Monta o DTO de complemento garantindo ordem e preço aplicado por complemento.
        
        Args:
            complemento: Modelo do complemento
            ordem: Ordem do complemento no contexto (produto/receita/combo). 
                   Se None, usa a ordem do complemento em si.
        """
        itens = self.repo_item.listar_itens_complemento(complemento.id, apenas_ativos=True)
        adicionais_dto = [
            AdicionalDTO(
                id=item.id,
                nome=item.nome,
                preco=getattr(item, "preco_aplicado", item.preco),
                ordem=ordem_item,
                imagem=getattr(item, "imagem", None),
            )
            for item, ordem_item in itens
        ]

        # Usa a ordem fornecida (da tabela de associação) ou a ordem do complemento
        ordem_final = ordem if ordem is not None else complemento.ordem

        return ComplementoDTO(
            id=complemento.id,
            nome=complemento.nome,
            descricao=complemento.descricao,
            obrigatorio=complemento.obrigatorio,
            quantitativo=complemento.quantitativo,
            ordem=ordem_final,
            adicionais=adicionais_dto,
        )

    def listar_por_produto(self, cod_barras: str, apenas_ativos: bool = True) -> List[ComplementoDTO]:
        complementos_com_ordem = self.repo.listar_por_produto(
            cod_barras,
            apenas_ativos=apenas_ativos,
            carregar_adicionais=False,
        )
        return [self._build_complemento_dto(c, ordem=ordem) for c, ordem in complementos_com_ordem]

    def buscar_por_ids_para_produto(self, cod_barras: str, complemento_ids: List[int]) -> List[ComplementoDTO]:
        vinculados_com_ordem = self.repo.listar_por_produto(
            cod_barras,
            apenas_ativos=True,
            carregar_adicionais=False,
        )
        ids_set = set(complemento_ids or [])
        filtrados = [(c, ordem) for c, ordem in vinculados_com_ordem if c.id in ids_set]
        return [self._build_complemento_dto(c, ordem=ordem) for c, ordem in filtrados]

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
        complementos_com_ordem = self.repo.listar_por_receita(
            receita_id,
            apenas_ativos=apenas_ativos,
            carregar_adicionais=False,
        )
        return [self._build_complemento_dto(c, ordem=ordem) for c, ordem in complementos_com_ordem]
    
    def listar_por_combo(self, combo_id: int, apenas_ativos: bool = True) -> List[ComplementoDTO]:
        """Lista todos os complementos vinculados a um combo."""
        complementos_com_ordem = self.repo.listar_por_combo(
            combo_id,
            apenas_ativos=apenas_ativos,
            carregar_adicionais=False,
        )
        return [self._build_complemento_dto(c, ordem=ordem) for c, ordem in complementos_com_ordem]

