from sqlalchemy.orm import Session
from typing import Optional, List

from app.api.catalogo.repositories.repo_receitas import ReceitasRepository
from app.api.catalogo.schemas.schema_receitas import (
    ReceitaIngredienteIn,
    ReceitaIngredienteDetalhadoOut,
    ReceitaComIngredientesOut,
    AdicionalIn,
    ReceitaIn,
    ReceitaUpdate,
    ReceitaOut,
)


class ReceitasService:
    def __init__(self, db: Session):
        self.repo = ReceitasRepository(db)

    # Receitas - CRUD completo
    def create_receita(self, data: ReceitaIn):
        receita = self.repo.create_receita(data)
        # Calcula o custo_total após criar a receita baseado no custo dos ingredientes
        custo_total = self.repo.calcular_custo_receita(receita.id)
        receita.custo_total = custo_total
        return receita

    def get_receita(self, receita_id: int):
        receita = self.repo.get_receita_by_id(receita_id)
        if receita:
            # Calcula o custo_total da receita baseado no custo dos ingredientes
            custo_total = self.repo.calcular_custo_receita(receita_id)
            receita.custo_total = custo_total
        return receita

    def list_receitas(
        self,
        empresa_id: Optional[int] = None,
        ativo: Optional[bool] = None,
        search: Optional[str] = None,
    ):
        """
        Lista receitas com filtros opcionais e suporte a busca textual.

        - `search`: termo aplicado em nome/descrição (case-insensitive, filtrado no banco).
        """
        receitas = self.repo.list_receitas(empresa_id=empresa_id, ativo=ativo, search=search)
        # Calcula o custo_total para cada receita baseado no custo dos ingredientes
        for receita in receitas:
            custo_total = self.repo.calcular_custo_receita(receita.id)
            receita.custo_total = custo_total
        return receitas
    
    def list_receitas_com_ingredientes(
        self,
        empresa_id: Optional[int] = None,
        ativo: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[ReceitaComIngredientesOut]:
        """Lista receitas com seus ingredientes incluídos, com suporte a busca textual."""
        receitas = self.repo.list_receitas_com_ingredientes(empresa_id=empresa_id, ativo=ativo, search=search)
        
        resultado = []
        for receita in receitas:
            # Monta lista de ingredientes detalhados
            ingredientes_detalhados = []
            for ri in receita.ingredientes:
                # Verifica se é um ingrediente básico ou uma sub-receita
                if ri.ingrediente_id is not None:
                    # Ingrediente básico
                    ingrediente_detalhado = ReceitaIngredienteDetalhadoOut(
                        id=ri.id,
                        receita_id=ri.receita_id,
                        ingrediente_id=ri.ingrediente_id,
                        receita_ingrediente_id=None,
                        quantidade=float(ri.quantidade) if ri.quantidade else None,
                        ingrediente_nome=ri.ingrediente.nome if ri.ingrediente else None,
                        ingrediente_descricao=ri.ingrediente.descricao if ri.ingrediente else None,
                        ingrediente_unidade_medida=ri.ingrediente.unidade_medida if ri.ingrediente else None,
                        ingrediente_custo=ri.ingrediente.custo if ri.ingrediente else None,
                        receita_ingrediente_nome=None,
                        receita_ingrediente_descricao=None,
                        receita_ingrediente_preco_venda=None,
                    )
                else:
                    # Sub-receita
                    ingrediente_detalhado = ReceitaIngredienteDetalhadoOut(
                        id=ri.id,
                        receita_id=ri.receita_id,
                        ingrediente_id=None,
                        receita_ingrediente_id=ri.receita_ingrediente_id,
                        quantidade=float(ri.quantidade) if ri.quantidade else None,
                        ingrediente_nome=None,
                        ingrediente_descricao=None,
                        ingrediente_unidade_medida=None,
                        ingrediente_custo=None,
                        receita_ingrediente_nome=ri.receita_ingrediente.nome if ri.receita_ingrediente else None,
                        receita_ingrediente_descricao=ri.receita_ingrediente.descricao if ri.receita_ingrediente else None,
                        receita_ingrediente_preco_venda=ri.receita_ingrediente.preco_venda if ri.receita_ingrediente else None,
                    )
                ingredientes_detalhados.append(ingrediente_detalhado)
            
            # Calcula o custo_total da receita baseado no custo dos ingredientes
            custo_total = self.repo.calcular_custo_receita(receita.id)
            
            # Cria objeto de resposta com ingredientes
            receita_com_ingredientes = ReceitaComIngredientesOut(
                id=receita.id,
                empresa_id=receita.empresa_id,
                nome=receita.nome,
                descricao=receita.descricao,
                preco_venda=receita.preco_venda,
                custo_total=custo_total,
                imagem=receita.imagem,
                ativo=receita.ativo,
                disponivel=receita.disponivel,
                created_at=receita.created_at,
                updated_at=receita.updated_at,
                ingredientes=ingredientes_detalhados,
            )
            resultado.append(receita_com_ingredientes)
        
        return resultado

    def update_receita(self, receita_id: int, data: ReceitaUpdate):
        receita = self.repo.update_receita(receita_id, data)
        # Calcula o custo_total após atualizar a receita baseado no custo dos ingredientes
        custo_total = self.repo.calcular_custo_receita(receita_id)
        receita.custo_total = custo_total
        return receita

    def delete_receita(self, receita_id: int):
        return self.repo.delete_receita(receita_id)

    # Ingredientes (vinculação a receitas)
    def add_ingrediente(self, data: ReceitaIngredienteIn):
        return self.repo.add_ingrediente(data)

    def list_ingredientes(self, receita_id: int):
        return self.repo.list_ingredientes(receita_id)

    def update_ingrediente(self, receita_ingrediente_id: int, quantidade: Optional[float]):
        return self.repo.update_ingrediente(receita_ingrediente_id, quantidade)

    def remove_ingrediente(self, receita_ingrediente_id: int):
        return self.repo.remove_ingrediente(receita_ingrediente_id)

    # Adicionais
    def add_adicional(self, data: AdicionalIn):
        adicional = self.repo.add_adicional(data)
        # Busca o preço do cadastro para retornar
        adicional.preco = self.repo._buscar_preco_adicional(adicional.adicional_id)
        return adicional

    def list_adicionais(self, receita_id: int):
        adicionais = self.repo.list_adicionais(receita_id)
        # Busca o preço do cadastro para cada adicional
        for adicional in adicionais:
            adicional.preco = self.repo._buscar_preco_adicional(adicional.adicional_id)
        return adicionais

    def update_adicional(self, adicional_id: int):
        adicional = self.repo.update_adicional(adicional_id)
        # Busca o preço do cadastro para retornar
        adicional.preco = self.repo._buscar_preco_adicional(adicional.adicional_id)
        return adicional

    def remove_adicional(self, adicional_id: int):
        return self.repo.remove_adicional(adicional_id)

