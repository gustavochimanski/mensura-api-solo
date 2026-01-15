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
        # Calcula o custo_total após criar a receita baseado no custo dos itens
        custo_total = self.repo.calcular_custo_receita(receita.id)
        receita.custo_total = custo_total
        return receita

    def get_receita(self, receita_id: int):
        receita = self.repo.get_receita_by_id(receita_id)
        if receita:
            # Calcula o custo_total da receita baseado no custo dos itens
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
        # Calcula o custo_total para cada receita baseado no custo dos itens
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
        """Lista receitas com seus itens incluídos, com suporte a busca textual."""
        receitas = self.repo.list_receitas_com_ingredientes(empresa_id=empresa_id, ativo=ativo, search=search)
        
        resultado = []
        for receita in receitas:
            # Monta lista de itens detalhados
            ingredientes_detalhados = []
            for ri in receita.ingredientes:
                # Determina o tipo de item e monta o objeto detalhado
                if ri.receita_ingrediente_id is not None:
                    # Sub-receita
                    ingrediente_detalhado = ReceitaIngredienteDetalhadoOut(
                        id=ri.id,
                        receita_id=ri.receita_id,
                        receita_ingrediente_id=ri.receita_ingrediente_id,
                        produto_cod_barras=None,
                        combo_id=None,
                        quantidade=float(ri.quantidade) if ri.quantidade else None,
                        receita_ingrediente_nome=ri.receita_ingrediente.nome if ri.receita_ingrediente else None,
                        receita_ingrediente_descricao=ri.receita_ingrediente.descricao if ri.receita_ingrediente else None,
                        receita_ingrediente_preco_venda=ri.receita_ingrediente.preco_venda if ri.receita_ingrediente else None,
                        produto_descricao=None,
                        produto_imagem=None,
                        combo_titulo=None,
                        combo_descricao=None,
                        combo_preco_total=None,
                    )
                elif ri.produto_cod_barras is not None:
                    # Produto normal
                    ingrediente_detalhado = ReceitaIngredienteDetalhadoOut(
                        id=ri.id,
                        receita_id=ri.receita_id,
                        receita_ingrediente_id=None,
                        produto_cod_barras=ri.produto_cod_barras,
                        combo_id=None,
                        quantidade=float(ri.quantidade) if ri.quantidade else None,
                        receita_ingrediente_nome=None,
                        receita_ingrediente_descricao=None,
                        receita_ingrediente_preco_venda=None,
                        produto_descricao=ri.produto.descricao if ri.produto else None,
                        produto_imagem=ri.produto.imagem if ri.produto else None,
                        combo_titulo=None,
                        combo_descricao=None,
                        combo_preco_total=None,
                    )
                elif ri.combo_id is not None:
                    # Combo
                    ingrediente_detalhado = ReceitaIngredienteDetalhadoOut(
                        id=ri.id,
                        receita_id=ri.receita_id,
                        receita_ingrediente_id=None,
                        produto_cod_barras=None,
                        combo_id=ri.combo_id,
                        quantidade=float(ri.quantidade) if ri.quantidade else None,
                        receita_ingrediente_nome=None,
                        receita_ingrediente_descricao=None,
                        receita_ingrediente_preco_venda=None,
                        produto_descricao=None,
                        produto_imagem=None,
                        combo_titulo=ri.combo.titulo if ri.combo else None,
                        combo_descricao=ri.combo.descricao if ri.combo else None,
                        combo_preco_total=ri.combo.preco_total if ri.combo else None,
                    )
                else:
                    # Item inválido (não deveria acontecer devido à constraint)
                    continue
                
                ingredientes_detalhados.append(ingrediente_detalhado)
            
            # Calcula o custo_total da receita baseado no custo dos itens
            custo_total = self.repo.calcular_custo_receita(receita.id)
            
            # Cria objeto de resposta com itens
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
        # Calcula o custo_total após atualizar a receita baseado no custo dos itens
        custo_total = self.repo.calcular_custo_receita(receita_id)
        receita.custo_total = custo_total
        return receita

    def delete_receita(self, receita_id: int):
        return self.repo.delete_receita(receita_id)

    # Ingredientes (vinculação a receitas)
    def add_ingrediente(self, data: ReceitaIngredienteIn):
        return self.repo.add_ingrediente(data)

    def list_ingredientes(self, receita_id: int, tipo: Optional[str] = None):
        """
        Lista itens de uma receita, opcionalmente filtrados por tipo.
        
        Args:
            receita_id: ID da receita
            tipo: Tipo de item ('sub-receita', 'produto' ou 'combo')
        """
        return self.repo.list_ingredientes(receita_id, tipo=tipo)

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

