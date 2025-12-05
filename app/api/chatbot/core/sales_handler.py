"""
Handler principal para processar mensagens de vendas via WhatsApp
Integra o SalesAssistant com o webhook do chatbot
Inclui fluxo completo de endereços com Google Maps e endereços salvos
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import json

from .sales_assistant import SalesAssistant, obter_estado_conversa, salvar_estado_conversa
from .sales_prompts import SALES_SYSTEM_PROMPT, ERROR_MESSAGES, SUCCESS_MESSAGES
from .address_service import ChatbotAddressService


class SalesConversationHandler:
    """
    Gerencia o estado e fluxo da conversa de vendas
    """

    def __init__(self, db: Session, user_id: str, empresa_id: int = 1):
        self.db = db
        self.user_id = user_id
        self.empresa_id = empresa_id
        self.assistant = SalesAssistant(db, empresa_id)
        self.address_service = ChatbotAddressService(db, empresa_id)

        # Carregar estado da conversa
        self.estado, self.dados = obter_estado_conversa(db, user_id)

        # Inicializar carrinho se não existir
        if 'carrinho' not in self.dados:
            self.dados['carrinho'] = []

    async def processar_mensagem(self, mensagem: str) -> str:
        """
        Processa uma mensagem do cliente e retorna a resposta adequada

        Args:
            mensagem: Texto enviado pelo cliente

        Returns:
            Resposta para enviar ao cliente
        """

        # Se é a primeira mensagem ou cliente disse "oi"/"olá"
        if self.estado == SalesAssistant.STATE_WELCOME or mensagem.lower() in ['oi', 'olá', 'ola', 'hey', 'menu', 'cardapio']:
            return self._processar_boas_vindas()

        # Detectar intenção da mensagem
        intencao, valor = self.assistant.detectar_intencao(mensagem)

        # Processar baseado no estado atual e intenção
        if intencao == 'sugestao':
            return await self._processar_sugestao()

        elif intencao == 'buscar_produto':
            return await self._processar_busca_produto(valor or mensagem)

        elif intencao == 'numero' and self.estado == SalesAssistant.STATE_PRODUCT_SELECTION:
            return await self._processar_selecao_produto(int(valor))

        elif intencao == 'confirmar':
            return await self._processar_confirmacao()

        elif intencao == 'cancelar':
            return self._processar_cancelamento()

        else:
            # ========== FLUXO DE ENDEREÇOS ==========

            # Estado: Verificando se quer usar endereço salvo ou novo
            if self.estado == SalesAssistant.STATE_LISTING_SAVED_ADDRESSES:
                return await self._processar_escolha_endereco_salvo_ou_novo(mensagem)

            # Estado: Cliente selecionando endereço salvo
            elif self.estado == SalesAssistant.STATE_SELECTING_SAVED_ADDRESS:
                return await self._processar_selecao_endereco_salvo(mensagem)

            # Estado: Cliente digitou endereço para buscar no Google
            elif self.estado == SalesAssistant.STATE_SEARCHING_NEW_ADDRESS:
                return await self._processar_busca_endereco_google(mensagem)

            # Estado: Cliente escolhendo endereço do Google
            elif self.estado == SalesAssistant.STATE_SELECTING_GOOGLE_ADDRESS:
                return await self._processar_selecao_endereco_google(mensagem)

            # Estado: Coletando complemento
            elif self.estado == SalesAssistant.STATE_COLLECTING_COMPLEMENT:
                return await self._processar_complemento(mensagem)

            # Estado antigo de coleta de endereço (compatibilidade)
            elif self.estado == SalesAssistant.STATE_COLLECTING_ADDRESS:
                return await self._iniciar_fluxo_endereco()

            # ========== FLUXO DE PAGAMENTO ==========

            elif self.estado == SalesAssistant.STATE_COLLECTING_PAYMENT:
                return await self._processar_pagamento(mensagem)

            else:
                # Mensagem genérica - trata como busca de produto
                return await self._processar_busca_produto(mensagem)

    def _processar_boas_vindas(self) -> str:
        """Envia mensagem de boas-vindas"""
        self.estado = SalesAssistant.STATE_PRODUCT_SEARCH
        salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

        return self.assistant.get_welcome_message()

    async def _processar_sugestao(self) -> str:
        """Cliente pediu sugestão de produtos"""
        # Buscar produtos populares/em promoção
        produtos = self.assistant._buscar_produtos_promocao()

        if not produtos:
            return "No momento não tenho sugestões específicas, mas posso te mostrar nosso cardápio! O que você gosta de comer?"

        # Salvar produtos encontrados para seleção
        self.dados['produtos_encontrados'] = produtos
        self.estado = SalesAssistant.STATE_PRODUCT_SELECTION
        salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

        mensagem = "🔥 *Olha só o que tá fazendo sucesso:*\n\n"
        for idx, p in enumerate(produtos[:5], 1):
            mensagem += f"*{idx}. {p['nome']}*\n"
            mensagem += f"   💰 R$ {p['preco']:.2f}\n"
            if p.get('descricao'):
                mensagem += f"   📝 {p['descricao'][:80]}\n"
            mensagem += "\n"

        mensagem += "Digite o *número* do que você quer! 😊"

        return mensagem

    async def _processar_busca_produto(self, termo_busca: str) -> str:
        """Busca produtos no banco de dados"""
        produtos = self.assistant.buscar_produtos(termo_busca)

        if not produtos:
            return ERROR_MESSAGES["produto_nao_encontrado"]

        # Salvar produtos encontrados
        self.dados['produtos_encontrados'] = produtos
        self.estado = SalesAssistant.STATE_PRODUCT_SELECTION
        salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

        return self.assistant.formatar_lista_produtos(produtos)

    async def _processar_selecao_produto(self, numero: int) -> str:
        """Cliente selecionou um produto pelo número"""
        produtos = self.dados.get('produtos_encontrados', [])

        if not produtos or numero < 1 or numero > len(produtos):
            return "Ops! Esse número não tá na lista 😅\nEscolhe um número da lista que te mostrei!"

        produto_selecionado = produtos[numero - 1]

        # Perguntar quantidade
        self.dados['produto_atual'] = produto_selecionado
        self.dados['aguardando'] = 'quantidade'

        mensagem = f"Show! Você escolheu:\n\n"
        mensagem += f"*{produto_selecionado['nome']}*\n"
        mensagem += f"💰 R$ {produto_selecionado['preco']:.2f}\n\n"
        mensagem += "Quantos você quer?"

        salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

        return mensagem

    async def _processar_quantidade(self, quantidade_str: str) -> str:
        """Processa a quantidade informada"""
        try:
            quantidade = int(quantidade_str)
            if quantidade < 1:
                return "Opa! Precisa ser pelo menos 1 😊"

            produto = self.dados.get('produto_atual')
            produto['quantidade'] = quantidade

            # Adicionar ao carrinho
            self.dados['carrinho'].append(produto)

            mensagem = f"✅ Adicionei {quantidade}x {produto['nome']} no seu pedido!\n\n"
            mensagem += "Quer mais alguma coisa ou já podemos fechar?"

            self.dados['aguardando'] = 'mais_produtos_ou_fechar'
            salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

            return mensagem

        except ValueError:
            return "Não entendi a quantidade 😅\nMe manda só o número, tipo: 2"

    # ========== NOVO FLUXO DE ENDEREÇOS ==========

    async def _iniciar_fluxo_endereco(self) -> str:
        """
        Inicia o fluxo de endereço verificando se cliente tem endereços salvos
        """
        # Buscar endereços existentes do cliente
        enderecos = self.address_service.get_enderecos_cliente(self.user_id)

        if enderecos:
            # Cliente tem endereços salvos - mostrar opções
            self.dados['enderecos_salvos'] = enderecos
            self.estado = SalesAssistant.STATE_LISTING_SAVED_ADDRESSES
            salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

            mensagem = self.address_service.formatar_lista_enderecos_para_chat(enderecos)
            mensagem += "\n*Quer usar um desses endereços?*\n\n"
            mensagem += "Digite o *número* do endereço\n"
            mensagem += "Ou digite *NOVO* para cadastrar outro endereço"

            return mensagem
        else:
            # Cliente não tem endereços - pedir para digitar
            self.estado = SalesAssistant.STATE_SEARCHING_NEW_ADDRESS
            salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

            mensagem = "📍 Agora preciso do endereço de entrega!\n\n"
            mensagem += "Digite seu endereço completo:\n"
            mensagem += "_Exemplo: Rua das Flores, 123, Centro, São Paulo_"

            return mensagem

    async def _processar_escolha_endereco_salvo_ou_novo(self, mensagem: str) -> str:
        """
        Processa a escolha do cliente: usar endereço salvo ou cadastrar novo
        """
        msg_lower = mensagem.lower().strip()

        # Cliente quer cadastrar novo endereço
        if msg_lower in ['novo', 'new', 'outro', 'cadastrar', 'adicionar']:
            self.estado = SalesAssistant.STATE_SEARCHING_NEW_ADDRESS
            salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

            mensagem = "📍 Ok! Vamos cadastrar um novo endereço.\n\n"
            mensagem += "Digite seu endereço completo:\n"
            mensagem += "_Exemplo: Rua das Flores, 123, Centro, São Paulo_"

            return mensagem

        # Cliente escolheu um número (endereço salvo)
        if msg_lower.isdigit():
            numero = int(msg_lower)
            enderecos = self.dados.get('enderecos_salvos', [])

            if numero < 1 or numero > len(enderecos):
                return f"Ops! Digite um número de 1 a {len(enderecos)}, ou *NOVO* para cadastrar outro 😊"

            # Selecionar endereço
            endereco_selecionado = enderecos[numero - 1]
            self.dados['endereco_selecionado'] = endereco_selecionado
            self.dados['endereco_texto'] = endereco_selecionado['endereco_completo']
            self.dados['endereco_id'] = endereco_selecionado['id']

            # Ir para pagamento
            self.estado = SalesAssistant.STATE_COLLECTING_PAYMENT
            salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

            mensagem = f"✅ Endereço selecionado:\n📍 {endereco_selecionado['endereco_completo']}\n\n"
            mensagem += self._mensagem_formas_pagamento()

            return mensagem

        # Não entendeu a resposta
        return "Não entendi 😅\nDigite o *número* do endereço ou *NOVO* para cadastrar outro"

    async def _processar_busca_endereco_google(self, texto_endereco: str) -> str:
        """
        Busca endereço no Google Maps e mostra opções
        """
        # Validação básica
        if len(texto_endereco) < 5:
            return "Hmm, esse endereço tá muito curto 🤔\nTenta colocar mais detalhes, tipo rua, número e bairro"

        # Buscar no Google Maps
        enderecos_google = self.address_service.buscar_enderecos_google(texto_endereco, max_results=3)

        if not enderecos_google:
            mensagem = "😅 Não encontrei esse endereço no mapa.\n\n"
            mensagem += "Tenta de novo com mais detalhes:\n"
            mensagem += "_Exemplo: Rua das Flores, 123, Centro, São Paulo_"
            return mensagem

        # Salvar opções do Google
        self.dados['enderecos_google'] = enderecos_google
        self.estado = SalesAssistant.STATE_SELECTING_GOOGLE_ADDRESS
        salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

        mensagem = self.address_service.formatar_opcoes_google_para_chat(enderecos_google)

        return mensagem

    async def _processar_selecao_endereco_google(self, mensagem: str) -> str:
        """
        Processa a seleção do endereço do Google Maps
        """
        msg_lower = mensagem.lower().strip()

        # Cliente quer tentar de novo
        if msg_lower in ['outro', 'nenhum', 'tentar', 'nova busca']:
            self.estado = SalesAssistant.STATE_SEARCHING_NEW_ADDRESS
            salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

            return "Ok! Digite o endereço novamente:\n_Exemplo: Rua das Flores, 123, Centro, São Paulo_"

        # Cliente escolheu um número
        if msg_lower.isdigit():
            numero = int(msg_lower)
            enderecos_google = self.dados.get('enderecos_google', [])

            if numero < 1 or numero > len(enderecos_google):
                return f"Digite um número de 1 a {len(enderecos_google)} 😊"

            # Selecionar endereço do Google
            endereco_selecionado = enderecos_google[numero - 1]
            self.dados['endereco_google_selecionado'] = endereco_selecionado

            # Perguntar complemento
            self.estado = SalesAssistant.STATE_COLLECTING_COMPLEMENT
            salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

            mensagem = f"✅ Endereço: *{endereco_selecionado['endereco_completo']}*\n\n"
            mensagem += "Tem algum *complemento*?\n"
            mensagem += "_Ex: Apartamento 101, Bloco B, Casa dos fundos_\n\n"
            mensagem += "Se não tiver, digite *NAO*"

            return mensagem

        # Não entendeu
        return "Digite o *número* do endereço correto ou *OUTRO* para tentar novamente"

    async def _processar_complemento(self, mensagem: str) -> str:
        """
        Processa o complemento do endereço e salva
        """
        msg_lower = mensagem.lower().strip()
        endereco_google = self.dados.get('endereco_google_selecionado', {})

        # Definir complemento
        complemento = None
        if msg_lower not in ['nao', 'não', 'n', 'nenhum', 'sem complemento', '-']:
            complemento = mensagem.strip()

        # Montar dados do endereço para salvar
        dados_endereco = {
            "logradouro": endereco_google.get("logradouro"),
            "numero": endereco_google.get("numero"),
            "complemento": complemento,
            "bairro": endereco_google.get("bairro"),
            "cidade": endereco_google.get("cidade"),
            "estado": endereco_google.get("estado"),
            "cep": endereco_google.get("cep"),
            "latitude": endereco_google.get("latitude"),
            "longitude": endereco_google.get("longitude")
        }

        # Criar cliente se não existir e salvar endereço
        cliente = self.address_service.criar_cliente_se_nao_existe(self.user_id)

        if cliente:
            # Salvar endereço no banco
            endereco_salvo = self.address_service.criar_endereco_cliente(
                self.user_id,
                dados_endereco,
                is_principal=True  # Primeiro endereço é principal
            )

            if endereco_salvo:
                self.dados['endereco_selecionado'] = endereco_salvo
                self.dados['endereco_id'] = endereco_salvo['id']

        # Montar endereço completo para exibição
        endereco_completo = endereco_google.get('endereco_completo', '')
        if complemento:
            endereco_completo += f" - {complemento}"

        self.dados['endereco_texto'] = endereco_completo

        # Ir para pagamento
        self.estado = SalesAssistant.STATE_COLLECTING_PAYMENT
        salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

        mensagem = f"✅ Endereço salvo!\n📍 {endereco_completo}\n\n"
        mensagem += self._mensagem_formas_pagamento()

        return mensagem

    def _mensagem_formas_pagamento(self) -> str:
        """Retorna a mensagem padrão de formas de pagamento"""
        return """Agora me fala, como vai ser o pagamento?

💳 *Formas disponíveis:*
1️⃣ PIX (paga agora)
2️⃣ Dinheiro na entrega
3️⃣ Cartão na entrega

Digite o número da opção!"""

    # ========== FIM DO FLUXO DE ENDEREÇOS ==========

    async def _processar_endereco(self, endereco: str) -> str:
        """
        Processa o endereço informado pelo cliente
        AGORA REDIRECIONA PARA O NOVO FLUXO
        """
        return await self._iniciar_fluxo_endereco()

    async def _processar_pagamento(self, opcao: str) -> str:
        """Processa a forma de pagamento escolhida"""
        formas = {
            '1': 'PIX',
            '2': 'DINHEIRO',
            '3': 'CARTAO'
        }

        forma_pagamento = formas.get(opcao)

        if not forma_pagamento:
            return "Ops! Escolhe uma das opções: 1, 2 ou 3 😊"

        self.dados['forma_pagamento'] = forma_pagamento

        # Agora gerar o preview
        return await self._gerar_preview()

    async def _gerar_preview(self) -> str:
        """Gera o preview do pedido antes de finalizar"""
        try:
            # Preparar dados do cliente
            cliente_data = {
                "telefone": self.user_id,
                "endereco_texto": self.dados.get('endereco_texto'),
                "endereco_id": self.dados.get('endereco_id'),
                "metodo_pagamento": self.dados.get('forma_pagamento', 'PIX')
            }

            # Chamar preview
            preview = await self.assistant.criar_preview_checkout(
                self.dados['carrinho'],
                cliente_data
            )

            if preview.get("erro"):
                return ERROR_MESSAGES["erro_sistema"]

            # Salvar preview para confirmação
            self.dados['preview'] = preview
            self.estado = SalesAssistant.STATE_CONFIRM_ORDER
            salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

            return self.assistant.formatar_preview_mensagem(preview)

        except Exception as e:
            print(f"Erro ao gerar preview: {e}")
            return ERROR_MESSAGES["erro_sistema"]

    async def _processar_confirmacao(self) -> str:
        """Cliente confirmou o pedido"""
        if self.estado != SalesAssistant.STATE_CONFIRM_ORDER:
            # Se não está no estado de confirmação, talvez queira fechar o pedido
            if self.dados.get('carrinho') and len(self.dados['carrinho']) > 0:
                # Tem itens no carrinho, iniciar fluxo de endereço
                return await self._iniciar_fluxo_endereco()
            return "Ainda não temos nada para confirmar 😊\nMe diz o que você quer!"

        try:
            preview = self.dados.get('preview')

            if not preview:
                return ERROR_MESSAGES["pedido_invalido"]

            # Finalizar pedido
            cliente_data = {
                "telefone": self.user_id,
                "endereco_id": self.dados.get('endereco_id')
            }

            resultado = await self.assistant.finalizar_pedido(preview, cliente_data)

            if resultado.get("erro"):
                return ERROR_MESSAGES["erro_sistema"]

            # Limpar carrinho e resetar estado
            self.dados = {'carrinho': []}
            self.estado = SalesAssistant.STATE_ORDER_PLACED
            salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

            return self.assistant.formatar_confirmacao_pedido(resultado)

        except Exception as e:
            print(f"Erro ao finalizar pedido: {e}")
            return ERROR_MESSAGES["erro_sistema"]

    def _processar_cancelamento(self) -> str:
        """Cliente cancelou o pedido"""
        self.dados = {'carrinho': []}
        self.estado = SalesAssistant.STATE_WELCOME

        salvar_estado_conversa(self.db, self.user_id, self.estado, self.dados)

        return "Tudo bem! Pedido cancelado 😊\n\nQuando quiser fazer um pedido, é só me chamar!"


# Função auxiliar para usar no webhook
async def processar_mensagem_venda(
    db: Session,
    user_id: str,
    mensagem: str,
    empresa_id: int = 1
) -> str:
    """
    Função principal para processar mensagens de vendas

    Args:
        db: Sessão do banco de dados
        user_id: ID do usuário (telefone WhatsApp)
        mensagem: Texto da mensagem
        empresa_id: ID da empresa

    Returns:
        Resposta para enviar ao cliente
    """
    handler = SalesConversationHandler(db, user_id, empresa_id)
    resposta = await handler.processar_mensagem(mensagem)
    return resposta
