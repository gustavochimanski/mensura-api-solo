# app/api/chatbot/services/service_carrinho.py
from typing import Optional, List
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.chatbot.repositories.repo_carrinho import CarrinhoRepository
from app.api.chatbot.models.model_carrinho import CarrinhoTemporarioModel
from app.api.chatbot.models.model_carrinho_item import CarrinhoItemModel
from app.api.chatbot.models.model_carrinho_item_complemento import CarrinhoItemComplementoModel
from app.api.chatbot.models.model_carrinho_item_complemento_adicional import CarrinhoItemComplementoAdicionalModel
from app.api.chatbot.schemas.schema_carrinho import (
    CriarCarrinhoRequest,
    AdicionarItemCarrinhoRequest,
    AtualizarItemCarrinhoRequest,
    RemoverItemCarrinhoRequest,
    CarrinhoResponse,
    ItemCarrinhoRequest,
    ReceitaCarrinhoRequest,
    ComboCarrinhoRequest,
)
from app.api.catalogo.contracts.produto_contract import IProdutoContract
from app.api.catalogo.contracts.complemento_contract import IComplementoContract
from app.api.catalogo.contracts.receitas_contract import IReceitasContract
from app.api.catalogo.contracts.combo_contract import IComboContract
from app.api.pedidos.utils.complementos import (
    resolve_produto_complementos,
    resolve_complementos_diretos
)
from app.utils.logger import logger


class CarrinhoService:
    """Service para gerenciar carrinho temporário do chatbot"""
    
    def __init__(
        self,
        db: Session,
        produto_contract: Optional[IProdutoContract] = None,
        complemento_contract: Optional[IComplementoContract] = None,
        receitas_contract: Optional[IReceitasContract] = None,
        combo_contract: Optional[IComboContract] = None,
    ):
        self.db = db
        self.repo = CarrinhoRepository(db)
        self.produto_contract = produto_contract
        self.complemento_contract = complemento_contract
        self.receitas_contract = receitas_contract
        self.combo_contract = combo_contract

    def obter_ou_criar_carrinho(
        self,
        user_id: str,
        empresa_id: int,
        tipo_entrega: str
    ) -> CarrinhoTemporarioModel:
        """Obtém carrinho existente ou cria um novo"""
        carrinho = self.repo.get_by_user_id(user_id, empresa_id, load_items=True)
        
        if not carrinho:
            carrinho = self.repo.create(
                user_id=user_id,
                empresa_id=empresa_id,
                tipo_entrega=tipo_entrega
            )
            logger.info(f"[Carrinho] Carrinho criado carrinho_id={carrinho.id} user_id={user_id}")
        else:
            # Atualiza tipo_entrega se mudou
            if carrinho.tipo_entrega != tipo_entrega:
                carrinho = self.repo.update(carrinho, tipo_entrega=tipo_entrega)
        
        return carrinho

    def criar_ou_atualizar_carrinho(self, data: CriarCarrinhoRequest) -> CarrinhoResponse:
        """Cria ou atualiza carrinho com itens"""
        carrinho = self.obter_ou_criar_carrinho(
            user_id=data.user_id,
            empresa_id=data.empresa_id,
            tipo_entrega=data.tipo_entrega.value
        )
        
        # Atualiza informações do carrinho
        update_data = {}
        if data.endereco_id is not None:
            update_data['endereco_id'] = data.endereco_id
        if data.meio_pagamento_id is not None:
            update_data['meio_pagamento_id'] = data.meio_pagamento_id
        if data.cupom_id is not None:
            update_data['cupom_id'] = data.cupom_id
        if data.mesa_id is not None:
            update_data['mesa_id'] = data.mesa_id
        if data.observacoes is not None:
            update_data['observacoes'] = data.observacoes
        if data.observacao_geral is not None:
            update_data['observacao_geral'] = data.observacao_geral
        if data.num_pessoas is not None:
            update_data['num_pessoas'] = data.num_pessoas
        if data.troco_para is not None:
            update_data['troco_para'] = data.troco_para
        
        if update_data:
            carrinho = self.repo.update(carrinho, **update_data)
        
        # Adiciona/atualiza itens
        if data.itens:
            for item_req in data.itens:
                self._adicionar_item_produto(carrinho.id, item_req)
        
        if data.receitas:
            for receita_req in data.receitas:
                self._adicionar_item_receita(carrinho.id, receita_req)
        
        if data.combos:
            for combo_req in data.combos:
                self._adicionar_item_combo(carrinho.id, combo_req)
        
        # Recalcula totais
        self._recalcular_totais(carrinho)
        
        return self._carrinho_to_response(carrinho)

    def adicionar_item(self, data: AdicionarItemCarrinhoRequest) -> CarrinhoResponse:
        """Adiciona um item ao carrinho"""
        carrinho = self.repo.get_by_user_id(data.user_id, load_items=True)
        if not carrinho:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Carrinho não encontrado. Crie um carrinho primeiro."
            )
        
        if data.item:
            self._adicionar_item_produto(carrinho.id, data.item)
        elif data.receita:
            self._adicionar_item_receita(carrinho.id, data.receita)
        elif data.combo:
            self._adicionar_item_combo(carrinho.id, data.combo)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="É necessário informar item, receita ou combo"
            )
        
        # Recalcula totais
        self._recalcular_totais(carrinho)
        
        return self._carrinho_to_response(carrinho)

    def atualizar_item(self, user_id: str, data: AtualizarItemCarrinhoRequest) -> CarrinhoResponse:
        """Atualiza um item do carrinho"""
        item = self.repo.get_item_by_id(data.item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item não encontrado"
            )
        
        carrinho = self.repo.get_by_id(item.carrinho_id, load_items=True)
        if not carrinho or carrinho.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Item não pertence ao seu carrinho"
            )
        
        # Atualiza item
        update_data = {}
        if data.quantidade is not None:
            update_data['quantidade'] = data.quantidade
        if data.observacao is not None:
            update_data['observacao'] = data.observacao
        
        if update_data:
            self.repo.update_item(item, **update_data)
        
        # Atualiza complementos se fornecidos
        if data.complementos is not None:
            # Remove complementos existentes
            for complemento in item.complementos:
                self.db.delete(complemento)
            self.db.commit()
            
            # Adiciona novos complementos
            self._adicionar_complementos_item(item, data.complementos)
        
        # Recalcula totais
        self._recalcular_totais(carrinho)
        
        return self._carrinho_to_response(carrinho)

    def remover_item(self, user_id: str, data: RemoverItemCarrinhoRequest) -> CarrinhoResponse:
        """Remove um item do carrinho"""
        item = self.repo.get_item_by_id(data.item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item não encontrado"
            )
        
        carrinho = self.repo.get_by_id(item.carrinho_id, load_items=True)
        if not carrinho or carrinho.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Item não pertence ao seu carrinho"
            )
        
        self.repo.remove_item(item)
        
        # Recalcula totais
        self._recalcular_totais(carrinho)
        
        return self._carrinho_to_response(carrinho)

    def obter_carrinho(self, user_id: str, empresa_id: Optional[int] = None) -> Optional[CarrinhoResponse]:
        """Obtém carrinho do usuário"""
        carrinho = self.repo.get_by_user_id(user_id, empresa_id, load_items=True)
        if not carrinho:
            return None
        
        return self._carrinho_to_response(carrinho)

    def limpar_carrinho(self, user_id: str, empresa_id: Optional[int] = None) -> bool:
        """Limpa o carrinho do usuário"""
        return self.repo.delete_by_user_id(user_id, empresa_id)

    def _adicionar_item_produto(self, carrinho_id: int, item_req: ItemCarrinhoRequest):
        """Adiciona item de produto ao carrinho"""
        if not self.produto_contract:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Contrato de produto não disponível"
            )
        
        # Busca produto
        produto_emp = self.produto_contract.obter_produto_emp_por_cod(
            self.repo.get_by_id(carrinho_id).empresa_id,
            item_req.produto_cod_barras
        )
        if not produto_emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produto {item_req.produto_cod_barras} não encontrado"
            )
        
        if not produto_emp.disponivel or not (produto_emp.produto and produto_emp.produto.ativo):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Produto {item_req.produto_cod_barras} indisponível"
            )
        
        # Calcula preço e complementos
        preco_unitario = Decimal(str(produto_emp.preco_venda))
        preco_total = preco_unitario * item_req.quantidade
        
        # Calcula complementos
        total_complementos = Decimal("0")
        if item_req.complementos and self.complemento_contract:
            total_complementos, _ = resolve_produto_complementos(
                complemento_contract=self.complemento_contract,
                produto_cod_barras=item_req.produto_cod_barras,
                complementos_request=item_req.complementos,
                quantidade_item=item_req.quantidade
            )
            preco_total += total_complementos
        
        # Cria item
        item = self.repo.add_item(
            carrinho_id=carrinho_id,
            produto_cod_barras=item_req.produto_cod_barras,
            quantidade=item_req.quantidade,
            preco_unitario=preco_unitario,
            preco_total=preco_total,
            observacao=item_req.observacao,
            produto_descricao_snapshot=produto_emp.produto.descricao,
            produto_imagem_snapshot=produto_emp.produto.imagem
        )
        
        # Adiciona complementos
        if item_req.complementos:
            self._adicionar_complementos_item(item, item_req.complementos)
        
        return item

    def _adicionar_item_receita(self, carrinho_id: int, receita_req: ReceitaCarrinhoRequest):
        """Adiciona item de receita ao carrinho"""
        if not self.receitas_contract:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Contrato de receitas não disponível"
            )
        
        # Busca receita
        receita = self.receitas_contract.obter_receita_por_id(receita_req.receita_id)
        if not receita:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Receita {receita_req.receita_id} não encontrada"
            )
        
        empresa_id = self.repo.get_by_id(carrinho_id).empresa_id
        preco_unitario = Decimal(str(receita.preco_venda or 0))
        preco_total = preco_unitario * receita_req.quantidade
        
        # Calcula complementos
        total_complementos = Decimal("0")
        if receita_req.complementos and self.complemento_contract:
            total_complementos, _ = resolve_complementos_diretos(
                complemento_contract=self.complemento_contract,
                empresa_id=empresa_id,
                complementos_request=receita_req.complementos,
                quantidade_item=receita_req.quantidade,
                receita_id=receita_req.receita_id
            )
            preco_total += total_complementos
        
        # Cria item
        item = self.repo.add_item(
            carrinho_id=carrinho_id,
            receita_id=receita_req.receita_id,
            quantidade=receita_req.quantidade,
            preco_unitario=preco_unitario,
            preco_total=preco_total,
            observacao=receita_req.observacao,
            produto_descricao_snapshot=receita.nome
        )
        
        # Adiciona complementos
        if receita_req.complementos:
            self._adicionar_complementos_item(item, receita_req.complementos)
        
        return item

    def _adicionar_item_combo(self, carrinho_id: int, combo_req: ComboCarrinhoRequest):
        """Adiciona item de combo ao carrinho"""
        if not self.combo_contract:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Contrato de combo não disponível"
            )
        
        # Busca combo
        combo = self.combo_contract.obter_combo_por_id(combo_req.combo_id)
        if not combo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Combo {combo_req.combo_id} não encontrado"
            )
        
        empresa_id = self.repo.get_by_id(carrinho_id).empresa_id
        preco_unitario = Decimal(str(combo.preco or 0))
        preco_total = preco_unitario * combo_req.quantidade
        
        # Calcula complementos
        total_complementos = Decimal("0")
        if combo_req.complementos and self.complemento_contract:
            total_complementos, _ = resolve_complementos_diretos(
                complemento_contract=self.complemento_contract,
                empresa_id=empresa_id,
                complementos_request=combo_req.complementos,
                quantidade_item=combo_req.quantidade,
                combo_id=combo_req.combo_id
            )
            preco_total += total_complementos
        
        # Cria item
        item = self.repo.add_item(
            carrinho_id=carrinho_id,
            combo_id=combo_req.combo_id,
            quantidade=combo_req.quantidade,
            preco_unitario=preco_unitario,
            preco_total=preco_total,
            produto_descricao_snapshot=combo.titulo or combo.descricao
        )
        
        # Adiciona complementos
        if combo_req.complementos:
            self._adicionar_complementos_item(item, combo_req.complementos)
        
        return item

    def _adicionar_complementos_item(
        self,
        item: CarrinhoItemModel,
        complementos_request: List
    ):
        """Adiciona complementos a um item"""
        if not self.complemento_contract:
            return
        
        empresa_id = item.carrinho.empresa_id
        
        for comp_req in complementos_request:
            complemento_id = getattr(comp_req, "complemento_id", None)
            if not complemento_id:
                continue
            
            # Busca complemento
            if item.produto_cod_barras:
                complementos = self.complemento_contract.buscar_por_ids_para_produto(
                    item.produto_cod_barras,
                    [complemento_id]
                )
            elif item.combo_id:
                complementos = self.complemento_contract.listar_por_combo(
                    item.combo_id,
                    apenas_ativos=True
                )
                complementos = [c for c in complementos if c.id == complemento_id]
            elif item.receita_id:
                complementos = self.complemento_contract.listar_por_receita(
                    item.receita_id,
                    apenas_ativos=True
                )
                complementos = [c for c in complementos if c.id == complemento_id]
            else:
                continue
            
            if not complementos:
                continue
            
            complemento = complementos[0]
            adicionais_req = getattr(comp_req, "adicionais", []) or []
            
            # Calcula total do complemento
            total_complemento = Decimal("0")
            adicionais_por_id = {a.id: a for a in complemento.adicionais}
            
            for ad_req in adicionais_req:
                adicional_id = getattr(ad_req, "adicional_id", None)
                quantidade_adicional = getattr(ad_req, "quantidade", 1)
                
                if adicional_id not in adicionais_por_id:
                    continue
                
                adicional = adicionais_por_id[adicional_id]
                
                # Se não for quantitativo, força quantidade = 1
                if not complemento.quantitativo:
                    quantidade_adicional = 1
                
                preco_unitario = Decimal(str(adicional.preco or 0))
                subtotal = preco_unitario * quantidade_adicional * item.quantidade
                total_complemento += subtotal
            
            # Cria complemento
            item_complemento = self.repo.add_complemento(
                item_id=item.id,
                complemento_id=complemento_id,
                total=total_complemento
            )
            
            # Adiciona adicionais
            for ad_req in adicionais_req:
                adicional_id = getattr(ad_req, "adicional_id", None)
                quantidade_adicional = getattr(ad_req, "quantidade", 1)
                
                if adicional_id not in adicionais_por_id:
                    continue
                
                adicional = adicionais_por_id[adicional_id]
                
                if not complemento.quantitativo:
                    quantidade_adicional = 1
                
                preco_unitario = Decimal(str(adicional.preco or 0))
                total_adicional = preco_unitario * quantidade_adicional * item.quantidade
                
                self.repo.add_adicional(
                    complemento_id=item_complemento.id,
                    adicional_id=adicional_id,
                    quantidade=quantidade_adicional,
                    preco_unitario=preco_unitario,
                    total=total_adicional
                )

    def _recalcular_totais(self, carrinho: CarrinhoTemporarioModel):
        """Recalcula subtotal e total do carrinho"""
        subtotal = carrinho.calcular_subtotal()
        total = carrinho.calcular_total()
        
        self.repo.update(
            carrinho,
            subtotal=subtotal,
            valor_total=total
        )

    def _carrinho_to_response(self, carrinho: CarrinhoTemporarioModel) -> CarrinhoResponse:
        """Converte model para response"""
        return CarrinhoResponse(
            id=carrinho.id,
            user_id=carrinho.user_id,
            empresa_id=carrinho.empresa_id,
            tipo_entrega=carrinho.tipo_entrega,
            mesa_id=carrinho.mesa_id,
            cliente_id=carrinho.cliente_id,
            endereco_id=carrinho.endereco_id,
            meio_pagamento_id=carrinho.meio_pagamento_id,
            cupom_id=carrinho.cupom_id,
            observacoes=carrinho.observacoes,
            observacao_geral=carrinho.observacao_geral,
            num_pessoas=carrinho.num_pessoas,
            subtotal=carrinho.subtotal,
            desconto=carrinho.desconto,
            taxa_entrega=carrinho.taxa_entrega,
            taxa_servico=carrinho.taxa_servico,
            valor_total=carrinho.valor_total,
            troco_para=carrinho.troco_para,
            endereco_snapshot=carrinho.endereco_snapshot,
            created_at=carrinho.created_at,
            updated_at=carrinho.updated_at,
            itens=[
                self._item_to_response(item) for item in carrinho.itens
            ]
        )

    def _item_to_response(self, item: CarrinhoItemModel):
        """Converte item model para response"""
        from app.api.chatbot.schemas.schema_carrinho import ItemCarrinhoResponse, ItemComplementoCarrinhoResponse, ItemComplementoAdicionalCarrinhoResponse
        
        return ItemCarrinhoResponse(
            id=item.id,
            produto_cod_barras=item.produto_cod_barras,
            combo_id=item.combo_id,
            receita_id=item.receita_id,
            quantidade=item.quantidade,
            preco_unitario=item.preco_unitario,
            preco_total=item.preco_total,
            observacao=item.observacao,
            produto_descricao_snapshot=item.produto_descricao_snapshot,
            produto_imagem_snapshot=item.produto_imagem_snapshot,
            complementos=[
                ItemComplementoCarrinhoResponse(
                    id=comp.id,
                    complemento_id=comp.complemento_id,
                    total=comp.total,
                    adicionais=[
                        ItemComplementoAdicionalCarrinhoResponse(
                            id=adic.id,
                            adicional_id=adic.adicional_id,
                            quantidade=adic.quantidade,
                            preco_unitario=adic.preco_unitario,
                            total=adic.total
                        )
                        for adic in comp.adicionais
                    ]
                )
                for comp in item.complementos
            ]
        )

    def converter_para_checkout(self, carrinho: CarrinhoTemporarioModel, cliente_id: Optional[int] = None) -> dict:
        """
        Converte carrinho do banco para formato do checkout (FinalizarPedidoRequest).
        
        Args:
            carrinho: Carrinho temporário do banco
            cliente_id: ID do cliente (opcional, mas recomendado para garantir que sempre tenha)
        
        Returns:
            dict com estrutura compatível com FinalizarPedidoRequest
        """
        from app.api.pedidos.schemas.schema_pedido import (
            ItemPedidoRequest,
            ReceitaPedidoRequest,
            ComboPedidoRequest,
            ProdutosPedidoRequest,
            ItemComplementoRequest,
            ItemAdicionalComplementoRequest
        )
        
        itens = []
        receitas = []
        combos = []
        
        for item in carrinho.itens:
            # Converte complementos
            complementos = None
            if item.complementos:
                complementos = []
                for comp in item.complementos:
                    adicionais = [
                        ItemAdicionalComplementoRequest(
                            adicional_id=adic.adicional_id,
                            quantidade=adic.quantidade
                        )
                        for adic in comp.adicionais
                    ]
                    complementos.append(
                        ItemComplementoRequest(
                            complemento_id=comp.complemento_id,
                            adicionais=adicionais
                        )
                    )
            
            if item.produto_cod_barras:
                itens.append(
                    ItemPedidoRequest(
                        produto_cod_barras=item.produto_cod_barras,
                        quantidade=item.quantidade,
                        observacao=item.observacao,
                        complementos=complementos
                    )
                )
            elif item.receita_id:
                receitas.append(
                    ReceitaPedidoRequest(
                        receita_id=item.receita_id,
                        quantidade=item.quantidade,
                        observacao=item.observacao,
                        complementos=complementos
                    )
                )
            elif item.combo_id:
                combos.append(
                    ComboPedidoRequest(
                        combo_id=item.combo_id,
                        quantidade=item.quantidade,
                        complementos=complementos
                    )
                )
        
        produtos = ProdutosPedidoRequest(
            itens=itens,  # Sempre deve ser uma lista (mesmo que vazia)
            receitas=receitas if receitas else None,
            combos=combos if combos else None
        )
        
        # Mapeia tipo_entrega do carrinho para o formato do checkout
        tipo_entrega_map = {
            "DELIVERY": "DELIVERY",
            "RETIRADA": "RETIRADA",
            "BALCAO": "BALCAO",
            "MESA": "MESA"
        }
        
        tipo_entrega = tipo_entrega_map.get(carrinho.tipo_entrega, "DELIVERY")
        
        payload = {
            "empresa_id": carrinho.empresa_id,
            "tipo_entrega": tipo_entrega,
            "tipo_pedido": tipo_entrega,  # Para compatibilidade
            "origem": "APP",  # WhatsApp = APP
            "produtos": produtos.model_dump(exclude_none=True),
            "endereco_id": carrinho.endereco_id,
            "meio_pagamento_id": carrinho.meio_pagamento_id,
            "cupom_id": carrinho.cupom_id,
            "observacao_geral": carrinho.observacao_geral,
            "troco_para": float(carrinho.troco_para) if carrinho.troco_para else None,
        }
        
        # Adiciona cliente_id se fornecido (garante que sempre tenha para delivery e retirada)
        if cliente_id:
            payload["cliente_id"] = str(cliente_id)
        
        # Adiciona campos específicos de mesa
        if carrinho.mesa_id:
            payload["mesa_codigo"] = str(carrinho.mesa_id)
            payload["num_pessoas"] = carrinho.num_pessoas
        
        # Remove campos None
        return {k: v for k, v in payload.items() if v is not None}
