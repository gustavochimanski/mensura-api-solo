"""
Domain Service de Carrinho.

Responsável por operações de carrinho/pedido temporário:
- obter/formatar carrinho em aberto
- sincronizar carrinho com 'dados' da conversa
- adicionar/remover itens via CarrinhoService
- personalizar itens no carrinho (ingredientes/adicionais) e no pedido_contexto
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.api.chatbot.schemas.schema_carrinho import (
    AdicionarItemCarrinhoRequest,
    AtualizarItemCarrinhoRequest,
    ComboCarrinhoRequest,
    ItemCarrinhoRequest,
    ReceitaCarrinhoRequest,
    RemoverItemCarrinhoRequest,
)
from app.api.chatbot.services.service_carrinho import CarrinhoService
from app.api.catalogo.adapters.combo_adapter import ComboAdapter
from app.api.catalogo.adapters.complemento_adapter import ComplementoAdapter
from app.api.catalogo.adapters.produto_adapter import ProdutoAdapter
from app.api.catalogo.adapters.receitas_adapter import ReceitasAdapter

from ..ingredientes_service import IngredientesService


class CarrinhoDomainService:
    def __init__(self, db: Session, empresa_id: int, ingredientes_service: IngredientesService):
        self.db = db
        self.empresa_id = empresa_id
        self.ingredientes_service = ingredientes_service
        self._carrinho_service: Optional[CarrinhoService] = None

    def get_carrinho_service(self) -> CarrinhoService:
        if not self._carrinho_service:
            self._carrinho_service = CarrinhoService(
                db=self.db,
                produto_contract=ProdutoAdapter(self.db),
                complemento_contract=ComplementoAdapter(self.db),
                receitas_contract=ReceitasAdapter(self.db),
                combo_contract=ComboAdapter(self.db),
            )
        return self._carrinho_service

    def obter_carrinho_db(self, user_id: str):
        service = self.get_carrinho_service()
        return service.obter_carrinho(user_id=user_id, empresa_id=self.empresa_id)

    def verificar_carrinho_aberto(self, user_id: str) -> Optional[Any]:
        """
        Verifica se existe um carrinho temporário em aberto para o usuário.
        Retorna o carrinho se existir, None caso contrário.
        """
        try:
            carrinho_resp = self.obter_carrinho_db(user_id)
            if carrinho_resp and carrinho_resp.itens and len(carrinho_resp.itens) > 0:
                return carrinho_resp
            return None
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao verificar carrinho aberto: {e}", exc_info=True)
            return None

    def formatar_mensagem_carrinho_aberto(self, carrinho_resp) -> str:
        if not carrinho_resp or not carrinho_resp.itens:
            return ""

        mensagem = "🛒 *Você tem um pedido em aberto:*\n\n"

        for item in carrinho_resp.itens:
            qtd = int(item.quantidade or 1)
            preco_item = float(item.preco_total or 0)
            nome_item = item.produto_descricao_snapshot or "Item"
            mensagem += f"• {qtd}x {nome_item} - R$ {preco_item:.2f}\n"

        total = float(carrinho_resp.valor_total or 0)
        mensagem += f"\n💰 *Total: R$ {total:.2f}*\n\n"
        mensagem += "💬 Quer continuar esse pedido ou cancelar para fazer um novo?\n"
        mensagem += "(Digite 'continuar' para seguir com esse pedido ou 'cancelar' para fazer um novo)"
        return mensagem

    def _resolve_adicional_nome(self, adicional_id: int) -> str:
        """Resolve adicional_id (vinculo) para nome no catálogo."""
        try:
            from sqlalchemy.orm import joinedload
            from app.api.catalogo.models.model_complemento_vinculo_item import ComplementoVinculoItemModel

            v = (
                self.db.query(ComplementoVinculoItemModel)
                .options(
                    joinedload(ComplementoVinculoItemModel.produto),
                    joinedload(ComplementoVinculoItemModel.receita),
                    joinedload(ComplementoVinculoItemModel.combo),
                )
                .filter(ComplementoVinculoItemModel.id == adicional_id)
                .first()
            )
            if v and getattr(v, "nome", None):
                return str(v.nome)
        except Exception:
            pass
        return "Adicional"

    def carrinho_response_para_lista(self, carrinho_resp) -> List[Dict]:
        if not carrinho_resp or not carrinho_resp.itens:
            return []

        lista: List[Dict] = []
        for item in carrinho_resp.itens:
            qtd = int(item.quantidade or 1)
            preco_total = float(item.preco_total or 0)
            preco_unit = preco_total / qtd if qtd else float(item.preco_unitario or 0)
            item_id = item.produto_cod_barras
            if not item_id and item.receita_id:
                item_id = f"receita_{item.receita_id}"
            if not item_id and item.combo_id:
                item_id = f"combo_{item.combo_id}"

            removidos: List[str] = []
            obs = (item.observacao or "").strip()
            if obs.upper().startswith("SEM:"):
                rest = obs[4:].strip()
                if rest:
                    removidos = [x.strip() for x in rest.split(",") if x.strip()]

            adicionais: List[Dict[str, Any]] = []
            preco_adicionais = 0.0
            if getattr(item, "complementos", None):
                for comp in item.complementos:
                    for adic in getattr(comp, "adicionais", []) or []:
                        total_adic = float(adic.total or 0)
                        preco_adicionais += total_adic
                        nome = self._resolve_adicional_nome(int(adic.adicional_id))
                        qtd_adic = int(adic.quantidade or 1)
                        if qtd_adic > 1:
                            nome = f"{qtd_adic}x {nome}"
                        adicionais.append({"nome": nome, "preco": total_adic})

            # preco_total do item já inclui adicionais; preco_base = só item, preco_adicionais = complementos
            preco_base = preco_unit
            if preco_adicionais > 0 and qtd:
                base_calc = (preco_total - preco_adicionais) / qtd
                preco_base = max(0.0, base_calc)

            lista.append(
                {
                    "id": item_id or item.id,
                    "nome": item.produto_descricao_snapshot or "Item",
                    "descricao": "",
                    "preco": preco_base,
                    "quantidade": qtd,
                    "observacao": item.observacao,
                    "personalizacoes": {
                        "removidos": removidos,
                        "adicionais": adicionais,
                        "preco_adicionais": preco_adicionais,
                    },
                }
            )

        return lista

    def sincronizar_carrinho_dados(self, user_id: str, dados: Dict) -> Tuple[Optional[Any], List[Dict]]:
        carrinho_resp = self.obter_carrinho_db(user_id)
        carrinho_lista = self.carrinho_response_para_lista(carrinho_resp)
        dados["carrinho"] = carrinho_lista
        return carrinho_resp, carrinho_lista

    def montar_item_carrinho_request(self, produto: Dict, quantidade: int) -> Dict[str, Any]:
        produto_id = str(produto.get("id", ""))
        tipo = produto.get("tipo")
        if tipo == "receita" or produto_id.startswith("receita_"):
            receita_id = int(produto_id.replace("receita_", ""))
            return {"receita": ReceitaCarrinhoRequest(receita_id=receita_id, quantidade=quantidade)}
        if tipo == "combo" or produto_id.startswith("combo_"):
            combo_id = int(produto_id.replace("combo_", ""))
            return {"combo": ComboCarrinhoRequest(combo_id=combo_id, quantidade=quantidade)}
        return {"item": ItemCarrinhoRequest(produto_cod_barras=produto_id, quantidade=quantidade)}

    def adicionar_ao_carrinho(self, user_id: str, dados: Dict, produto: Dict, quantidade: int = 1):
        service = self.get_carrinho_service()
        tipo_entrega = dados.get("tipo_entrega") or "DELIVERY"
        service.obter_ou_criar_carrinho(user_id=user_id, empresa_id=self.empresa_id, tipo_entrega=tipo_entrega)

        payload = self.montar_item_carrinho_request(produto, quantidade)
        request = AdicionarItemCarrinhoRequest(user_id=user_id, **payload)
        carrinho_resp = service.adicionar_item(request)

        dados["ultimo_produto_adicionado"] = produto.get("nome") or dados.get("ultimo_produto_adicionado")
        carrinho_resp, carrinho_lista = self.sincronizar_carrinho_dados(user_id, dados)
        print(f"🛒 Produto adicionado no banco: {produto.get('nome', 'item')}")
        return carrinho_resp, carrinho_lista

    def remover_do_carrinho(
        self, user_id: str, dados: Dict, produto: Dict, quantidade: int = None
    ) -> Tuple[bool, str, Optional[Any], List[Dict]]:
        service = self.get_carrinho_service()
        carrinho_resp = self.obter_carrinho_db(user_id)
        if not carrinho_resp or not carrinho_resp.itens:
            return False, "Seu carrinho está vazio.", None, []

        produto_id = str(produto.get("id", ""))
        tipo = produto.get("tipo")
        item_alvo = None

        if tipo == "receita" or produto_id.startswith("receita_"):
            receita_id = int(produto_id.replace("receita_", ""))
            item_alvo = next((i for i in carrinho_resp.itens if i.receita_id == receita_id), None)
        elif tipo == "combo" or produto_id.startswith("combo_"):
            combo_id = int(produto_id.replace("combo_", ""))
            item_alvo = next((i for i in carrinho_resp.itens if i.combo_id == combo_id), None)
        else:
            item_alvo = next((i for i in carrinho_resp.itens if i.produto_cod_barras == produto_id), None)

        if not item_alvo:
            carrinho_lista = self.carrinho_response_para_lista(carrinho_resp)
            return (
                False,
                f"Hmm, não encontrei *{produto.get('nome', produto_id)}* no seu carrinho 🤔",
                carrinho_resp,
                carrinho_lista,
            )

        if quantidade is None or quantidade >= item_alvo.quantidade:
            service.remover_item(user_id, RemoverItemCarrinhoRequest(item_id=item_alvo.id))
            nome_removido = item_alvo.produto_descricao_snapshot or produto.get("nome", "item")
            carrinho_resp, carrinho_lista = self.sincronizar_carrinho_dados(user_id, dados)
            print(f"🗑️ Produto removido no banco: {nome_removido}")
            return True, f"✅ *{nome_removido}* removido do carrinho!", carrinho_resp, carrinho_lista

        nova_qtd = max(int(item_alvo.quantidade or 1) - quantidade, 1)
        service.atualizar_item(user_id, AtualizarItemCarrinhoRequest(item_id=item_alvo.id, quantidade=nova_qtd))
        nome_item = item_alvo.produto_descricao_snapshot or produto.get("nome", "item")
        carrinho_resp, carrinho_lista = self.sincronizar_carrinho_dados(user_id, dados)
        print(f"🛒 Quantidade reduzida no banco: {nome_item} x{nova_qtd}")
        return True, f"✅ Reduzi para {nova_qtd}x *{nome_item}*", carrinho_resp, carrinho_lista

    def converter_contexto_para_carrinho(self, pedido_contexto: List[Dict]) -> List[Dict]:
        carrinho: List[Dict] = []
        for item in pedido_contexto:
            removidos = item.get("removidos", [])
            adicionais = item.get("adicionais", [])
            complementos_checkout = item.get("complementos_checkout", [])

            observacao = None
            if removidos:
                observacao = f"SEM: {', '.join(removidos)}"

            carrinho_item = {
                "id": item.get("id", ""),
                "nome": item["nome"],
                "preco": item["preco"],
                "quantidade": item.get("quantidade", 1),
                "observacoes": observacao,
                "complementos": complementos_checkout,
                "personalizacoes": {
                    "removidos": removidos,
                    "adicionais": adicionais,
                    "preco_adicionais": item.get("preco_adicionais", 0.0),
                    "complemento_obrigatorio": item.get("complemento_obrigatorio", False),
                },
            }
            carrinho.append(carrinho_item)
        return carrinho

    def personalizar_item_carrinho(
        self, dados: Dict, acao: str, item_nome: str, produto_busca: str = None
    ) -> Tuple[bool, str]:
        carrinho = dados.get("carrinho", [])
        pedido_contexto = dados.get("pedido_contexto", [])
        lista_itens = carrinho if carrinho else pedido_contexto
        usando_contexto = not carrinho and bool(pedido_contexto)

        if not lista_itens:
            return False, "Seu carrinho está vazio! Primeiro adicione um produto 😊"

        produto_alvo = None
        if produto_busca:
            for item in lista_itens:
                item_nome_check = item.get("nome", "")
                if produto_busca.lower() in item_nome_check.lower():
                    produto_alvo = item
                    break
        else:
            produto_alvo = lista_itens[-1]

        if not produto_alvo:
            return False, f"Não encontrei '{produto_busca}' no seu carrinho 🤔"

        if usando_contexto:
            produto_alvo.setdefault("removidos", [])
            produto_alvo.setdefault("adicionais", [])
            produto_alvo.setdefault("preco_adicionais", 0.0)

            if acao == "remover_ingrediente":
                ingrediente = self.ingredientes_service.verificar_ingrediente_na_receita_por_nome(
                    produto_alvo["nome"], item_nome
                )
                if ingrediente:
                    if ingrediente["nome"] not in produto_alvo["removidos"]:
                        produto_alvo["removidos"].append(ingrediente["nome"])
                        dados["pedido_contexto"] = pedido_contexto
                        return True, f"✅ Ok! *{produto_alvo['nome']}* SEM {ingrediente['nome']} 👍"
                    return True, f"Esse já tá sem {ingrediente['nome']}! 😊"
                return False, f"Hmm, {produto_alvo['nome']} não leva {item_nome} 🤔"

            if acao == "adicionar_extra":
                adicional = self.ingredientes_service.buscar_adicional_por_nome(item_nome)
                if adicional:
                    adicionais_nomes = [
                        add if isinstance(add, str) else add.get("nome", "") for add in produto_alvo["adicionais"]
                    ]
                    if adicional["nome"].lower() not in [a.lower() for a in adicionais_nomes]:
                        produto_alvo["adicionais"].append(adicional["nome"])
                        produto_alvo["preco_adicionais"] += adicional["preco"]
                        dados["pedido_contexto"] = pedido_contexto
                        return (
                            True,
                            f"✅ Adicionei *{adicional['nome']}* (+R$ {adicional['preco']:.2f}) no seu *{produto_alvo['nome']}* 👍",
                        )
                    return True, f"Já adicionei {adicional['nome']}! 😊"

                todos_adicionais = self.ingredientes_service.buscar_todos_adicionais()
                if todos_adicionais:
                    nomes = [a["nome"] for a in todos_adicionais[:5]]
                    return False, f"Não encontrei esse adicional 🤔\n\nTemos disponível: {', '.join(nomes)}"
                return False, "Não encontrei esse adicional 🤔"

            return False, "Não entendi a personalização 😅"

        # carrinho normal com personalizacoes
        if "personalizacoes" not in produto_alvo:
            produto_alvo["personalizacoes"] = {"removidos": [], "adicionais": [], "preco_adicionais": 0.0}
        personalizacoes = produto_alvo["personalizacoes"]

        if acao == "remover_ingrediente":
            ingrediente = self.ingredientes_service.verificar_ingrediente_na_receita_por_nome(
                produto_alvo["nome"], item_nome
            )
            if ingrediente:
                if ingrediente["nome"] not in personalizacoes["removidos"]:
                    personalizacoes["removidos"].append(ingrediente["nome"])
                    dados["carrinho"] = carrinho
                    return True, f"✅ Ok! *{produto_alvo['nome']}* SEM {ingrediente['nome']} 👍"
                return True, f"Esse já tá sem {ingrediente['nome']}! 😊"
            return False, f"Hmm, {produto_alvo['nome']} não leva {item_nome} 🤔"

        if acao == "adicionar_extra":
            adicional = self.ingredientes_service.buscar_adicional_por_nome(item_nome)
            if adicional:
                for add in personalizacoes["adicionais"]:
                    if add.get("nome", "").lower() == adicional["nome"].lower():
                        return True, f"Já adicionei {adicional['nome']}! 😊"
                personalizacoes["adicionais"].append(
                    {"id": adicional["id"], "nome": adicional["nome"], "preco": adicional["preco"]}
                )
                personalizacoes["preco_adicionais"] += adicional["preco"]
                dados["carrinho"] = carrinho
                return (
                    True,
                    f"✅ Adicionei *{adicional['nome']}* (+R$ {adicional['preco']:.2f}) no seu *{produto_alvo['nome']}* 👍",
                )

            todos_adicionais = self.ingredientes_service.buscar_todos_adicionais()
            if todos_adicionais:
                nomes = [a["nome"] for a in todos_adicionais[:5]]
                return False, f"Não encontrei esse adicional 🤔\n\nTemos disponível: {', '.join(nomes)}"
            return False, "Não encontrei esse adicional 🤔"

        return False, "Não entendi a personalização 😅"

