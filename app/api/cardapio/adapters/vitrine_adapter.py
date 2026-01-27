from __future__ import annotations

from typing import List, Dict
from sqlalchemy.orm import Session

from app.api.cardapio.contracts.vitrine_contract import (
    IVitrineContract,
    ComboVitrineDTO,
    ReceitaVitrineDTO,
)
from app.api.cardapio.repositories.repo_home import HomeRepository


class VitrineAdapter(IVitrineContract):
    def __init__(self, db: Session):
        self.repo = HomeRepository(db)

    def listar_combos_por_vitrine_ids(
        self, empresa_id: int, vitrine_ids: List[int]
    ) -> Dict[int, List[ComboVitrineDTO]]:
        combos_por_vitrine = self.repo.listar_combos_por_vitrine_ids(
            empresa_id=empresa_id, vitrine_ids=vitrine_ids
        )
        
        resultado: Dict[int, List[ComboVitrineDTO]] = {}
        for vitrine_id, combos in combos_por_vitrine.items():
            resultado[vitrine_id] = [
                ComboVitrineDTO(
                    id=combo.id,
                    empresa_id=combo.empresa_id,
                    titulo=combo.titulo,
                    descricao=combo.descricao,
                    preco_total=combo.preco_total,
                    imagem=combo.imagem,
                    ativo=combo.ativo,
                    vitrine_id=vitrine_id,
                )
                for combo in combos
            ]
        return resultado

    def listar_receitas_por_vitrine_ids(
        self, empresa_id: int, vitrine_ids: List[int]
    ) -> Dict[int, List[ReceitaVitrineDTO]]:
        receitas_por_vitrine = self.repo.listar_receitas_por_vitrine_ids(
            empresa_id=empresa_id, vitrine_ids=vitrine_ids
        )
        
        resultado: Dict[int, List[ReceitaVitrineDTO]] = {}
        for vitrine_id, receitas in receitas_por_vitrine.items():
            resultado[vitrine_id] = [
                ReceitaVitrineDTO(
                    id=receita.id,
                    empresa_id=receita.empresa_id,
                    nome=receita.nome,
                    descricao=receita.descricao,
                    preco_venda=receita.preco_venda,
                    imagem=receita.imagem,
                    ativo=receita.ativo,
                    disponivel=receita.disponivel,
                    vitrine_id=vitrine_id,
                )
                for receita in receitas
            ]
        return resultado

    def listar_combos_por_vitrine_categoria(
        self, empresa_id: int, categoria_id: int
    ) -> Dict[int, List[ComboVitrineDTO]]:
        combos_por_vitrine = self.repo.listar_combos_por_vitrine_categoria(
            empresa_id=empresa_id, categoria_id=categoria_id
        )
        
        resultado: Dict[int, List[ComboVitrineDTO]] = {}
        for vitrine_id, combos in combos_por_vitrine.items():
            resultado[vitrine_id] = [
                ComboVitrineDTO(
                    id=combo.id,
                    empresa_id=combo.empresa_id,
                    titulo=combo.titulo,
                    descricao=combo.descricao,
                    preco_total=combo.preco_total,
                    imagem=combo.imagem,
                    ativo=combo.ativo,
                    vitrine_id=vitrine_id,
                )
                for combo in combos
            ]
        return resultado

    def listar_receitas_por_vitrine_categoria(
        self, empresa_id: int, categoria_id: int
    ) -> Dict[int, List[ReceitaVitrineDTO]]:
        receitas_por_vitrine = self.repo.listar_receitas_por_vitrine_categoria(
            empresa_id=empresa_id, categoria_id=categoria_id
        )
        
        resultado: Dict[int, List[ReceitaVitrineDTO]] = {}
        for vitrine_id, receitas in receitas_por_vitrine.items():
            resultado[vitrine_id] = [
                ReceitaVitrineDTO(
                    id=receita.id,
                    empresa_id=receita.empresa_id,
                    nome=receita.nome,
                    descricao=receita.descricao,
                    preco_venda=receita.preco_venda,
                    imagem=receita.imagem,
                    ativo=receita.ativo,
                    disponivel=receita.disponivel,
                    vitrine_id=vitrine_id,
                )
                for receita in receitas
            ]
        return resultado

    def listar_combos_por_vitrine_ids_landingpage_store(
        self, empresa_id: int, vitrine_ids: List[int]
    ) -> Dict[int, List[ComboVitrineDTO]]:
        combos_por_vitrine = self.repo.listar_combos_por_vitrine_ids_landingpage_store(
            empresa_id=empresa_id, vitrine_ids=vitrine_ids
        )

        resultado: Dict[int, List[ComboVitrineDTO]] = {}
        for vitrine_id, combos in combos_por_vitrine.items():
            resultado[vitrine_id] = [
                ComboVitrineDTO(
                    id=combo.id,
                    empresa_id=combo.empresa_id,
                    titulo=combo.titulo,
                    descricao=combo.descricao,
                    preco_total=combo.preco_total,
                    imagem=combo.imagem,
                    ativo=combo.ativo,
                    vitrine_id=vitrine_id,
                )
                for combo in combos
            ]
        return resultado

    def listar_receitas_por_vitrine_ids_landingpage_store(
        self, empresa_id: int, vitrine_ids: List[int]
    ) -> Dict[int, List[ReceitaVitrineDTO]]:
        receitas_por_vitrine = self.repo.listar_receitas_por_vitrine_ids_landingpage_store(
            empresa_id=empresa_id, vitrine_ids=vitrine_ids
        )

        resultado: Dict[int, List[ReceitaVitrineDTO]] = {}
        for vitrine_id, receitas in receitas_por_vitrine.items():
            resultado[vitrine_id] = [
                ReceitaVitrineDTO(
                    id=receita.id,
                    empresa_id=receita.empresa_id,
                    nome=receita.nome,
                    descricao=receita.descricao,
                    preco_venda=receita.preco_venda,
                    imagem=receita.imagem,
                    ativo=receita.ativo,
                    disponivel=receita.disponivel,
                    vitrine_id=vitrine_id,
                )
                for receita in receitas
            ]
        return resultado

