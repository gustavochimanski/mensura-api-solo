from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from app.api.catalogo.contracts.complemento_contract import IComplementoContract, ComplementoDTO, AdicionalDTO
from app.api.catalogo.repositories.repo_complemento import ComplementoRepository


class ComplementoAdapter(IComplementoContract):
    def __init__(self, db: Session):
        self.repo = ComplementoRepository(db)

    def listar_por_produto(self, cod_barras: str, apenas_ativos: bool = True) -> List[ComplementoDTO]:
        complementos = self.repo.listar_por_produto(cod_barras, apenas_ativos=apenas_ativos, carregar_adicionais=True)
        return [
            ComplementoDTO(
                id=c.id,
                nome=c.nome,
                descricao=c.descricao,
                obrigatorio=c.obrigatorio,
                quantitativo=c.quantitativo,
                permite_multipla_escolha=c.permite_multipla_escolha,
                ordem=c.ordem,
                adicionais=[
                    AdicionalDTO(
                        id=a.id,
                        nome=a.nome,
                        preco=a.preco,
                        ordem=a.ordem,
                    )
                    for a in sorted(c.adicionais, key=lambda x: (x.ordem, x.nome)) if a.ativo
                ],
            )
            for c in complementos
        ]

    def buscar_por_ids_para_produto(self, cod_barras: str, complemento_ids: List[int]) -> List[ComplementoDTO]:
        vinculados = self.repo.listar_por_produto(cod_barras, apenas_ativos=True, carregar_adicionais=True)
        ids_set = set(complemento_ids or [])
        filtrados = [c for c in vinculados if c.id in ids_set]
        return [
            ComplementoDTO(
                id=c.id,
                nome=c.nome,
                descricao=c.descricao,
                obrigatorio=c.obrigatorio,
                quantitativo=c.quantitativo,
                permite_multipla_escolha=c.permite_multipla_escolha,
                ordem=c.ordem,
                adicionais=[
                    AdicionalDTO(
                        id=a.id,
                        nome=a.nome,
                        preco=a.preco,
                        ordem=a.ordem,
                    )
                    for a in sorted(c.adicionais, key=lambda x: (x.ordem, x.nome)) if a.ativo
                ],
            )
            for c in filtrados
        ]

    def buscar_por_ids(self, empresa_id: int, complemento_ids: List[int]) -> List[ComplementoDTO]:
        complementos = self.repo.listar_por_empresa(empresa_id, apenas_ativos=True, carregar_adicionais=True)
        ids_set = set(complemento_ids or [])
        filtrados = [c for c in complementos if c.id in ids_set]
        return [
            ComplementoDTO(
                id=c.id,
                nome=c.nome,
                descricao=c.descricao,
                obrigatorio=c.obrigatorio,
                quantitativo=c.quantitativo,
                permite_multipla_escolha=c.permite_multipla_escolha,
                ordem=c.ordem,
                adicionais=[
                    AdicionalDTO(
                        id=a.id,
                        nome=a.nome,
                        preco=a.preco,
                        ordem=a.ordem,
                    )
                    for a in sorted(c.adicionais, key=lambda x: (x.ordem, x.nome)) if a.ativo
                ],
            )
            for c in filtrados
        ]

