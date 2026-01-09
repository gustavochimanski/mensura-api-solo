"""
Assistente de Vendas via WhatsApp
Gerencia o fluxo completo de vendas do chatbot
"""
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import httpx
import json
from datetime import datetime

# Importar modelos do sistema (ajustar conforme sua estrutura)
try:
    from app.api.catalogo.models.model_produto import ProdutoModel
    from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
    from app.api.empresas.models.empresa_model import EmpresaModel
except Exception as e:
    print(f"⚠️ Erro ao importar modelos: {e}")
    # Fallback se a importação falhar
    ProdutoModel = None
    ProdutoEmpModel = None
    EmpresaModel = None


class SalesAssistant:
    """
    Assistente inteligente para vendas via WhatsApp
    """

    # Estados da conversa de vendas
    STATE_WELCOME = "welcome"
    STATE_PRODUCT_SEARCH = "product_search"
    STATE_PRODUCT_SELECTION = "product_selection"

    # Novos estados para fluxo de endereços
    STATE_CHECKING_ADDRESS = "checking_address"           # Verificando se cliente tem endereços
    STATE_LISTING_SAVED_ADDRESSES = "listing_saved_addresses"  # Listando endereços salvos
    STATE_SELECTING_SAVED_ADDRESS = "selecting_saved_address"  # Cliente escolhendo endereço salvo
    STATE_SEARCHING_NEW_ADDRESS = "searching_new_address"      # Buscando novo endereço no Google
    STATE_SELECTING_GOOGLE_ADDRESS = "selecting_google_address" # Cliente escolhendo endereço do Google
    STATE_COLLECTING_COMPLEMENT = "collecting_complement"       # Coletando complemento do endereço

    STATE_COLLECTING_ADDRESS = "collecting_address"       # Mantido para compatibilidade
    STATE_COLLECTING_PAYMENT = "collecting_payment"
    STATE_CONFIRM_ORDER = "confirm_order"
    STATE_ORDER_PLACED = "order_placed"

    def __init__(self, db: Session, empresa_id: int = 1):
        self.db = db
        self.empresa_id = empresa_id
        self.api_base_url = "http://localhost:8000"

    def get_welcome_message(self) -> str:
        """
        Mensagem de boas-vindas com link do cardápio e promoções
        """
        # Buscar produtos em promoção (você pode adicionar lógica real aqui)
        promocoes = self._buscar_produtos_promocao()

        mensagem = """🎉 Olá! Bem-vindo ao nosso atendimento via WhatsApp!

📱 *Formas de Pedido:*
• Acesse nosso cardápio completo: [LINK_CARDAPIO]
• Ou continue aqui e eu te ajudo a fazer o pedido! 😊

"""

        if promocoes:
            mensagem += "🔥 *PROMOÇÕES DO DIA:*\n"
            for idx, promo in enumerate(promocoes[:3], 1):  # Limitar a 3 promoções
                mensagem += f"{idx}. {promo['nome']} - R$ {promo['preco']:.2f}\n"
            mensagem += "\n"

        mensagem += """💬 *Para pedir por aqui, é só me dizer:*
• Qual produto você quer
• Ou peça sugestões!

Já sabe o que quer ou prefere uma sugestão? 😉"""

        return mensagem

    def _buscar_produtos_promocao(self) -> List[Dict[str, Any]]:
        """
        Busca produtos em promoção no banco de dados
        CORRIGIDO: Usa estrutura correta (Produto + ProdutoEmp)
        """
        if not ProdutoModel or not ProdutoEmpModel:
            return []

        try:
            # Query com JOIN entre produtos e produtos_empresa
            produtos = self.db.query(
                ProdutoModel.cod_barras,
                ProdutoModel.descricao,
                ProdutoEmpModel.preco_venda
            ).join(
                ProdutoEmpModel,
                ProdutoModel.cod_barras == ProdutoEmpModel.cod_barras
            ).filter(
                and_(
                    ProdutoEmpModel.empresa_id == self.empresa_id,
                    ProdutoModel.ativo == True,
                    ProdutoEmpModel.disponivel == True,
                    ProdutoEmpModel.exibir_delivery == True
                    # TODO: Adicionar campo promocao se existir
                )
            ).limit(5).all()

            return [
                {
                    "id": p.cod_barras,  # Usamos cod_barras como ID
                    "nome": p.descricao,  # descricao é o "nome" do produto
                    "preco": float(p.preco_venda),
                    "descricao": ""  # Pode adicionar descrição detalhada se tiver
                }
                for p in produtos
            ]
        except Exception as e:
            print(f"Erro ao buscar promoções: {e}")
            import traceback
            traceback.print_exc()
            return []

    def buscar_produtos(self, texto_busca: str) -> List[Dict[str, Any]]:
        """
        Busca produtos no banco de dados baseado no texto
        CORRIGIDO: Usa estrutura correta (Produto + ProdutoEmp)

        Args:
            texto_busca: Texto que o cliente digitou (ex: "pizza", "calabresa", "refri")

        Returns:
            Lista de produtos encontrados
        """
        if not ProdutoModel or not ProdutoEmpModel:
            return []

        try:
            # Normalizar busca
            termo_busca = f"%{texto_busca.lower()}%"

            # Buscar produtos por descrição
            produtos = self.db.query(
                ProdutoModel.cod_barras,
                ProdutoModel.descricao,
                ProdutoEmpModel.preco_venda
            ).join(
                ProdutoEmpModel,
                ProdutoModel.cod_barras == ProdutoEmpModel.cod_barras
            ).filter(
                and_(
                    ProdutoEmpModel.empresa_id == self.empresa_id,
                    ProdutoModel.ativo == True,
                    ProdutoEmpModel.disponivel == True,
                    ProdutoEmpModel.exibir_delivery == True,
                    ProdutoModel.descricao.ilike(termo_busca)
                )
            ).limit(10).all()

            resultados = []
            for p in produtos:
                produto_dict = {
                    "id": p.cod_barras,
                    "nome": p.descricao,
                    "preco": float(p.preco_venda),
                    "descricao": "",  # Pode adicionar descrição detalhada se existir
                    "categoria": "Geral"  # TODO: Buscar categoria se tiver
                }
                resultados.append(produto_dict)

            return resultados

        except Exception as e:
            print(f"Erro ao buscar produtos: {e}")
            import traceback
            traceback.print_exc()
            return []

    def formatar_lista_produtos(self, produtos: List[Dict[str, Any]]) -> str:
        """
        Formata lista de produtos para exibir ao cliente
        """
        if not produtos:
            return "😔 Não encontrei nenhum produto com esse nome. Pode tentar outro termo?"

        mensagem = f"🔍 Encontrei {len(produtos)} produto(s):\n\n"

        for idx, produto in enumerate(produtos, 1):
            mensagem += f"*{idx}. {produto['nome']}*\n"
            mensagem += f"   💰 R$ {produto['preco']:.2f}\n"
            if produto.get('descricao'):
                mensagem += f"   📝 {produto['descricao'][:100]}\n"
            mensagem += "\n"

        mensagem += "Digite o *número* do produto que deseja ou o nome completo! 😊"

        return mensagem

    def detectar_intencao(self, mensagem: str) -> Tuple[str, Optional[str]]:
        """
        Detecta a intenção do usuário baseado na mensagem

        Returns:
            (intencao, valor_extraido)

        Intenções possíveis:
        - 'buscar_produto': Cliente quer buscar um produto
        - 'sugestao': Cliente quer sugestão
        - 'cardapio': Cliente quer ver o cardápio/menu
        - 'confirmar': Cliente confirmou algo (ok, sim, confirmo)
        - 'cancelar': Cliente quer cancelar
        - 'numero': Cliente digitou um número (seleção de produto)
        """
        msg_lower = mensagem.lower().strip()

        # Detectar confirmação
        if msg_lower in ['ok', 'sim', 'confirmo', 'confirmar', 'yes', 'isso mesmo', 'correto', 'ta bom', 'tá bom']:
            return ('confirmar', None)

        # Detectar cancelamento
        if msg_lower in ['não', 'nao', 'cancelar', 'desistir', 'voltar']:
            return ('cancelar', None)

        # Detectar pedido de cardápio/menu
        palavras_cardapio = ['cardapio', 'cardápio', 'menu', 'o que tem', 'que tem', 'tem o que', 'opções', 'opcoes', 'produtos', 'qual produto']
        if any(palavra in msg_lower for palavra in palavras_cardapio):
            return ('sugestao', None)  # Mostra produtos em promoção/populares

        # Detectar pedido de sugestão
        if any(palavra in msg_lower for palavra in ['sugestão', 'sugestao', 'sugira', 'recomende', 'recomendação']):
            return ('sugestao', None)

        # Detectar número (seleção de produto)
        if msg_lower.isdigit():
            return ('numero', msg_lower)

        # Detectar palavras-chave de busca de produto
        palavras_produto = ['quero', 'gostaria', 'pode me', 'me vê', 'vê se tem', 'tem', 'vende', 'buscar', 'procurar']
        if any(palavra in msg_lower for palavra in palavras_produto):
            # Extrair o nome do produto
            for palavra in palavras_produto:
                if palavra in msg_lower:
                    produto = msg_lower.split(palavra, 1)[1].strip()
                    if produto and len(produto) > 2:  # Pelo menos 3 caracteres
                        return ('buscar_produto', produto)

        # Se não detectou nada específico, assume que é busca de produto
        return ('buscar_produto', mensagem)

    def calcular_frete(self, distancia_km: float = 5.0) -> Dict[str, Any]:
        """
        Calcula taxa de entrega baseado na distância
        Usa a tabela cadastros.regioes_entrega

        Args:
            distancia_km: Distância em km (default 5.0 para teste)

        Returns:
            {"taxa": float, "tempo_estimado_min": int}
        """
        try:
            from app.api.cadastros.models.model_regiao_entrega import RegiaoEntregaModel

            # Busca região que atende essa distância
            regiao = self.db.query(RegiaoEntregaModel).filter(
                and_(
                    RegiaoEntregaModel.empresa_id == self.empresa_id,
                    RegiaoEntregaModel.ativo == True,
                    RegiaoEntregaModel.distancia_min_km <= distancia_km,
                    RegiaoEntregaModel.distancia_max_km >= distancia_km
                )
            ).first()

            if regiao:
                return {
                    "taxa": float(regiao.taxa_entrega),
                    "tempo_estimado_min": regiao.tempo_estimado_min
                }
            else:
                # Fallback: Usa primeira região disponível
                regiao_default = self.db.query(RegiaoEntregaModel).filter(
                    and_(
                        RegiaoEntregaModel.empresa_id == self.empresa_id,
                        RegiaoEntregaModel.ativo == True
                    )
                ).first()

                if regiao_default:
                    return {
                        "taxa": float(regiao_default.taxa_entrega),
                        "tempo_estimado_min": regiao_default.tempo_estimado_min
                    }
                else:
                    # Fallback final
                    return {"taxa": 5.0, "tempo_estimado_min": 30}

        except Exception as e:
            print(f"Erro ao calcular frete: {e}")
            return {"taxa": 5.0, "tempo_estimado_min": 30}

    async def criar_preview_checkout(
        self,
        produtos_selecionados: List[Dict[str, Any]],
        cliente_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cria preview do pedido calculando totais, taxas, etc
        VERSÃO SIMPLIFICADA: Não usa endpoint externo, calcula diretamente

        Args:
            produtos_selecionados: Lista de produtos com quantidade
            cliente_data: Dados do cliente (telefone, nome, endereço)

        Returns:
            Resposta do preview com todos os cálculos
        """
        try:
            # Calcula subtotal
            subtotal = sum(
                p.get("preco", 0.0) * p.get("quantidade", 1)
                for p in produtos_selecionados
            )

            # Calcula frete
            frete_info = self.calcular_frete()
            taxa_entrega = frete_info["taxa"]
            tempo_estimado = frete_info["tempo_estimado_min"]

            # Total
            total = subtotal + taxa_entrega

            # Formata itens
            itens = [
                {
                    "nome": p["nome"],
                    "quantidade": p.get("quantidade", 1),
                    "preco_unitario": p["preco"],
                    "subtotal": p["preco"] * p.get("quantidade", 1)
                }
                for p in produtos_selecionados
            ]

            return {
                "erro": False,
                "itens": itens,
                "subtotal": subtotal,
                "taxa_entrega": taxa_entrega,
                "desconto": 0.0,
                "total": total,
                "previsao_entrega": f"{tempo_estimado} minutos",
                "metodo_pagamento": cliente_data.get("metodo_pagamento", "PIX"),
                "endereco": cliente_data.get("endereco_texto", ""),
                "payload_original": {
                    "produtos": produtos_selecionados,
                    "cliente_data": cliente_data,
                    "subtotal": subtotal,
                    "taxa_entrega": taxa_entrega,
                    "total": total
                }
            }

        except Exception as e:
            print(f"Erro ao criar preview: {e}")
            import traceback
            traceback.print_exc()
            return {
                "erro": True,
                "mensagem": f"Erro ao processar pedido: {str(e)}"
            }

    def formatar_preview_mensagem(self, preview_data: Dict[str, Any]) -> str:
        """
        Formata os dados do preview para uma mensagem bonita
        """
        if preview_data.get("erro"):
            return f"❌ {preview_data.get('mensagem', 'Erro ao processar pedido')}"

        mensagem = "📋 *RESUMO DO PEDIDO*\n\n"

        # Itens
        mensagem += "*Itens:*\n"
        for item in preview_data.get("itens", []):
            mensagem += f"• {item['quantidade']}x {item['nome']} - R$ {item['subtotal']:.2f}\n"

        mensagem += "\n"

        # Totais
        subtotal = preview_data.get("subtotal", 0)
        taxa_entrega = preview_data.get("taxa_entrega", 0)
        desconto = preview_data.get("desconto", 0)
        total = preview_data.get("total", 0)

        mensagem += f"Subtotal: R$ {subtotal:.2f}\n"
        if taxa_entrega > 0:
            mensagem += f"Taxa de entrega: R$ {taxa_entrega:.2f}\n"
        if desconto > 0:
            mensagem += f"Desconto: -R$ {desconto:.2f}\n"

        mensagem += f"\n*TOTAL: R$ {total:.2f}*\n\n"

        # Previsão de entrega
        if preview_data.get("previsao_entrega"):
            mensagem += f"🕒 Previsão de entrega: {preview_data['previsao_entrega']}\n\n"

        mensagem += "✅ Digite *OK* para confirmar o pedido\n"
        mensagem += "❌ Ou *CANCELAR* para desistir"

        return mensagem

    async def finalizar_pedido(
        self,
        preview_data: Dict[str, Any],
        cliente_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Chama o endpoint de checkout para finalizar o pedido
        """
        try:
            # Payload já foi montado no preview, agora é só confirmar
            payload = preview_data.get("payload_original", {})

            # Valida se o token existe e não está vazio
            token = cliente_data.get('token', '')
            if not token or token.strip() == "":
                return {
                    "erro": True,
                    "mensagem": "Token de autenticação do cliente não encontrado ou vazio"
                }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/cardapio/client/checkout/finalizar",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"}
                )

                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    return {
                        "erro": True,
                        "mensagem": f"Erro ao finalizar pedido: {response.text}"
                    }

        except Exception as e:
            return {
                "erro": True,
                "mensagem": f"Erro ao finalizar pedido: {str(e)}"
            }

    def formatar_confirmacao_pedido(self, pedido_data: Dict[str, Any]) -> str:
        """
        Formata mensagem de confirmação do pedido
        """
        if pedido_data.get("erro"):
            return f"❌ {pedido_data.get('mensagem', 'Erro ao finalizar pedido')}"

        pedido_id = pedido_data.get("id", "N/A")
        status = pedido_data.get("status", "PENDENTE")

        mensagem = "🎉 *PEDIDO CONFIRMADO!*\n\n"
        mensagem += f"📌 Número do pedido: *#{pedido_id}*\n"
        mensagem += f"📊 Status: {status}\n\n"

        # Se tiver pagamento PIX
        if pedido_data.get("pagamento"):
            pag = pedido_data["pagamento"]
            if pag.get("metodo") == "PIX" and pag.get("qr_code"):
                mensagem += "💳 *PAGAMENTO PIX:*\n"
                mensagem += f"QR Code: {pag['qr_code']}\n"
                mensagem += "Copie e cole no seu app de pagamento\n\n"

        mensagem += "✅ Você receberá atualizações sobre seu pedido!\n"
        mensagem += "\nObrigado pela preferência! 😊"

        return mensagem


# Função auxiliar para salvar estado da conversa
def salvar_estado_conversa(
    db: Session,
    user_id: str,
    estado: str,
    dados: Dict[str, Any]
) -> None:
    """
    Salva o estado atual da conversa de vendas
    Usa a tabela chatbot.conversations para salvar metadata
    """
    try:
        from sqlalchemy import text

        # Serializa os dados para JSON
        dados_json = json.dumps(dados, ensure_ascii=False)

        # Salva/atualiza no campo metadata da conversa
        query = text("""
            UPDATE chatbot.conversations
            SET
                metadata = jsonb_build_object(
                    'sales_state', CAST(:estado AS text),
                    'sales_data', CAST(:dados AS jsonb)
                ),
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
            AND id = (
                SELECT id FROM chatbot.conversations
                WHERE user_id = :user_id
                ORDER BY updated_at DESC
                LIMIT 1
            )
        """)

        db.execute(query, {
            "estado": estado,
            "dados": dados_json,
            "user_id": user_id
        })
        db.commit()

    except Exception as e:
        print(f"Erro ao salvar estado: {e}")
        db.rollback()


def obter_estado_conversa(
    db: Session,
    user_id: str
) -> Tuple[str, Dict[str, Any]]:
    """
    Obtém o estado atual da conversa de vendas

    Returns:
        (estado_atual, dados_salvos)
    """
    try:
        from sqlalchemy import text

        # Busca metadata da conversa mais recente
        query = text("""
            SELECT metadata
            FROM chatbot.conversations
            WHERE user_id = :user_id
            ORDER BY updated_at DESC
            LIMIT 1
        """)

        result = db.execute(query, {"user_id": user_id}).fetchone()

        if result and result[0]:
            metadata = result[0]
            estado = metadata.get('sales_state', SalesAssistant.STATE_WELCOME)
            dados = metadata.get('sales_data', {})
            return (estado, dados)
        else:
            # Primeira vez do usuário
            return (SalesAssistant.STATE_WELCOME, {})

    except Exception as e:
        print(f"Erro ao obter estado: {e}")
        import traceback
        traceback.print_exc()
        return (SalesAssistant.STATE_WELCOME, {})
