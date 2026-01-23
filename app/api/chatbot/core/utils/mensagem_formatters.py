"""
Formatação de mensagens para o chatbot
"""
import json
import random
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

# Link do cardápio (configurável)
LINK_CARDAPIO = "https://chatbot.mensuraapi.com.br"


class MensagemFormatters:
    """
    Classe para formatação de mensagens do chatbot
    """

    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id

    def buscar_empresas_ativas(self) -> List[Dict]:
        """
        Busca todas as empresas ativas do banco de dados.
        Retorna lista de dicionários com informações das empresas.
        """
        try:
            result = self.db.execute(text("""
                SELECT id, nome, bairro, cidade, estado, logradouro, numero, 
                       complemento, horarios_funcionamento
                FROM cadastros.empresas
                ORDER BY nome
            """))
            empresas = []
            for row in result.fetchall():
                empresas.append({
                    'id': row[0],
                    'nome': row[1],
                    'bairro': row[2],
                    'cidade': row[3],
                    'estado': row[4],
                    'logradouro': row[5],
                    'numero': row[6],
                    'complemento': row[7],
                    'horarios_funcionamento': row[8]
                })
            return empresas
        except Exception as e:
            print(f"❌ Erro ao buscar empresas: {e}")
            return []

    def formatar_horarios_funcionamento(self, horarios_funcionamento) -> str:
        """
        Formata os horários de funcionamento em texto legível.
        horarios_funcionamento é um JSONB com estrutura:
        [{"dia_semana": 0..6, "intervalos": [{"inicio":"HH:MM","fim":"HH:MM"}]}]
        """
        if not horarios_funcionamento:
            return "Horários de funcionamento não informados."
        
        try:
            # Se já é uma lista, usa direto; se é string, faz parse
            if isinstance(horarios_funcionamento, str):
                horarios = json.loads(horarios_funcionamento)
            else:
                horarios = horarios_funcionamento
            
            if not horarios or not isinstance(horarios, list):
                return "Horários de funcionamento não informados."
            
            # Mapeia dias da semana
            dias_semana = {
                0: "Domingo",
                1: "Segunda-feira",
                2: "Terça-feira",
                3: "Quarta-feira",
                4: "Quinta-feira",
                5: "Sexta-feira",
                6: "Sábado"
            }
            
            # Agrupa por dia
            horarios_formatados = []
            for horario in horarios:
                dia_num = horario.get('dia_semana')
                intervalos = horario.get('intervalos', [])
                
                if dia_num is None or not intervalos:
                    continue
                
                dia_nome = dias_semana.get(dia_num, f"Dia {dia_num}")
                intervalos_str = []
                for intervalo in intervalos:
                    inicio = intervalo.get('inicio', '')
                    fim = intervalo.get('fim', '')
                    if inicio and fim:
                        intervalos_str.append(f"{inicio} às {fim}")
                
                if intervalos_str:
                    horarios_formatados.append(f"• {dia_nome}: {', '.join(intervalos_str)}")
            
            if horarios_formatados:
                return "🕐 *Horário de Funcionamento:*\n\n" + "\n".join(horarios_formatados)
            else:
                return "Horários de funcionamento não informados."
        except Exception as e:
            print(f"❌ Erro ao formatar horários: {e}")
            return "Horários de funcionamento não informados."

    def formatar_localizacao_empresas(self, empresas: List[Dict], empresa_atual_id: int) -> str:
        """
        Formata informações de localização das empresas.
        Se houver apenas 1 empresa, retorna informações dela.
        Se houver mais de 1, retorna informações da atual + lista das outras.
        """
        if not empresas:
            return "Informações de localização não disponíveis."
        
        # Filtra apenas empresas com endereço completo
        empresas_com_endereco = [
            emp for emp in empresas 
            if emp.get('bairro') and emp.get('cidade') and emp.get('estado')
        ]
        
        if not empresas_com_endereco:
            return "Informações de localização não disponíveis."
        
        # Encontra a empresa atual
        empresa_atual = None
        outras_empresas = []
        
        for emp in empresas_com_endereco:
            if emp['id'] == empresa_atual_id:
                empresa_atual = emp
            else:
                outras_empresas.append(emp)
        
        resposta = ""
        
        # Se há apenas 1 empresa ou não encontrou a atual, mostra só ela
        if len(empresas_com_endereco) == 1 or not empresa_atual:
            emp = empresas_com_endereco[0]
            resposta = "📍 *Nossa Localização:*\n\n"
            
            # Monta endereço completo
            endereco_parts = []
            if emp.get('logradouro'):
                endereco_parts.append(emp['logradouro'])
                if emp.get('numero'):
                    endereco_parts.append(f", {emp['numero']}")
            if emp.get('complemento'):
                endereco_parts.append(f" - {emp['complemento']}")
            
            if endereco_parts:
                resposta += "".join(endereco_parts) + "\n"
            
            resposta += f"{emp['bairro']} ({emp['cidade']}) / {emp['estado']}"
        else:
            # Há mais de 1 empresa - mostra a atual + lista das outras
            resposta = "📍 *Nossa Localização:*\n\n"
            
            # Informações da empresa atual
            resposta += f"*{empresa_atual['nome']}* (unidade atual):\n"
            endereco_parts = []
            if empresa_atual.get('logradouro'):
                endereco_parts.append(empresa_atual['logradouro'])
                if empresa_atual.get('numero'):
                    endereco_parts.append(f", {empresa_atual['numero']}")
            if empresa_atual.get('complemento'):
                endereco_parts.append(f" - {empresa_atual['complemento']}")
            
            if endereco_parts:
                resposta += "".join(endereco_parts) + "\n"
            
            resposta += f"{empresa_atual['bairro']} ({empresa_atual['cidade']}) / {empresa_atual['estado']}\n"
            
            # Lista outras unidades
            if outras_empresas:
                resposta += "\n*Outras unidades disponíveis:*\n"
                for emp in outras_empresas:
                    resposta += f"• {emp['nome']} - {emp['bairro']} ({emp['cidade']}) / {emp['estado']}\n"
        
        return resposta

    def gerar_lista_produtos(self, produtos: List[Dict], carrinho: List[Dict] = None) -> str:
        """Gera uma lista formatada de produtos para mostrar ao cliente"""
        if not produtos:
            return "Ops, não encontrei produtos disponíveis no momento 😅"

        # Agrupa produtos por categoria (baseado no nome)
        pizzas = []
        bebidas = []
        lanches = []
        outros = []

        for p in produtos:
            nome_lower = p['nome'].lower()
            if 'pizza' in nome_lower:
                pizzas.append(p)
            elif any(x in nome_lower for x in ['coca', 'refri', 'suco', 'água', 'agua', 'cerveja', 'guarana', 'guaraná']):
                bebidas.append(p)
            elif any(x in nome_lower for x in ['x-', 'x ', 'burger', 'lanche', 'hamburguer', 'hambúrguer']):
                lanches.append(p)
            else:
                outros.append(p)

        mensagem = "📋 *Nosso Cardápio:*\n\n"

        if pizzas:
            mensagem += "🍕 *Pizzas:*\n"
            for p in pizzas:
                mensagem += f"• {p['nome']} - R$ {p['preco']:.2f}\n"
            mensagem += "\n"

        if lanches:
            mensagem += "🍔 *Lanches:*\n"
            for p in lanches:
                mensagem += f"• {p['nome']} - R$ {p['preco']:.2f}\n"
            mensagem += "\n"

        if bebidas:
            mensagem += "🥤 *Bebidas:*\n"
            for p in bebidas:
                mensagem += f"• {p['nome']} - R$ {p['preco']:.2f}\n"
            mensagem += "\n"

        if outros:
            mensagem += "📦 *Outros:*\n"
            for p in outros:
                mensagem += f"• {p['nome']} - R$ {p['preco']:.2f}\n"
            mensagem += "\n"

        # Se tem carrinho, mostra o que já foi adicionado
        if carrinho:
            total = sum(item['preco'] * item.get('quantidade', 1) for item in carrinho)
            mensagem += f"🛒 *Seu carrinho:* R$ {total:.2f}\n\n"

        mensagem += "É só me dizer o que você quer! 😊"

        return mensagem

    def formatar_carrinho(self, carrinho: List[Dict]) -> str:
        """Formata o carrinho para exibição, incluindo personalizações.
        Complementos/adicionais são impressos indentados (à direita do item) com ➕
        para indicar que pertencem àquele item e que foram adicionados."""
        if not carrinho:
            return "🛒 *Seu carrinho está vazio!*\n\nO que você gostaria de pedir hoje? 😊"

        msg = "🛒 *SEU PEDIDO*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

        # Indentação: item usa 3 espaços; complementos usam 12 (mais à direita, pertencem ao item)
        _indent_complemento = "            "

        total = 0
        for idx, item in enumerate(carrinho, 1):
            qtd = item.get('quantidade', 1)
            preco_base = item['preco']
            pers = item.get('personalizacoes', {})
            preco_adicionais = pers.get('preco_adicionais', item.get('preco_adicionais', 0.0))
            subtotal = (preco_base + preco_adicionais) * qtd
            total += subtotal

            msg += f"*{idx}. {qtd}x {item['nome']}*\n"
            msg += f"   R$ {subtotal:.2f}\n"

            removidos = pers.get('removidos', item.get('removidos', []))
            adicionais = pers.get('adicionais', item.get('adicionais', []))

            if removidos:
                msg += f"   🚫 Sem: {', '.join(removidos)}\n"

            # Complementos/adicionais: cada um em linha, indentado, com ➕ (foi adicional)
            if adicionais:
                for add in adicionais:
                    if isinstance(add, dict):
                        nome = add.get('nome', add)
                        preco = add.get('preco', 0)
                        if preco and preco > 0:
                            msg += f"{_indent_complemento}➕ {nome} (+R$ {preco:.2f})\n"
                        else:
                            msg += f"{_indent_complemento}➕ {nome}\n"
                    else:
                        msg += f"{_indent_complemento}➕ {add}\n"

            msg += "\n"

        msg += "━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"💰 *TOTAL: R$ {total:.2f}*\n"
        return msg

    def gerar_mensagem_boas_vindas(self, buscar_promocoes_func) -> str:
        """
        Gera mensagem de boas-vindas CURTA e NATURAL
        Recebe uma função para buscar promoções (para evitar dependência circular)
        """
        # Busca alguns produtos para sugestão
        produtos = buscar_promocoes_func()

        # Mensagens variadas de boas-vindas
        saudacoes = [
            "E aí! 😊 Tudo bem?",
            "Opa! Beleza?",
            "Olá! Tudo certo?",
            "E aí, tudo bem? 👋",
        ]

        saudacao = random.choice(saudacoes)

        mensagem = f"{saudacao}\n\n"
        mensagem += "Aqui é o atendimento do delivery!\n\n"

        # Mostra apenas 2-3 sugestões rápidas
        if produtos:
            destaques = produtos[:3]
            mensagem += "🔥 *Hoje tá saindo muito:*\n"
            for p in destaques:
                mensagem += f"• {p['nome']} - R$ {p['preco']:.2f}\n"
            mensagem += "\n"

        mensagem += "O que vai ser hoje? 😋"

        return mensagem

    def gerar_mensagem_boas_vindas_conversacional(self, get_chatbot_config_func, obter_link_cardapio_func) -> str:
        """
        Gera mensagem de boas-vindas para modo conversacional com botões
        Recebe funções para evitar dependência circular
        """
        # Busca configuração do chatbot
        config = get_chatbot_config_func()
        
        # Busca nome da empresa e link do cardápio do banco
        try:
            empresa_query = text("""
                SELECT nome, cardapio_link
                FROM cadastros.empresas
                WHERE id = :empresa_id
            """)
            result = self.db.execute(empresa_query, {"empresa_id": self.empresa_id})
            empresa = result.fetchone()
            
            nome_empresa = empresa[0] if empresa and empresa[0] else "[Nome da Empresa]"
            link_cardapio = empresa[1] if empresa and empresa[1] else obter_link_cardapio_func()
        except Exception as e:
            print(f"⚠️ Erro ao buscar dados da empresa: {e}")
            nome_empresa = "[Nome da Empresa]"
            link_cardapio = obter_link_cardapio_func()

        # Usa mensagem personalizada se configurada, senão usa padrão
        if config and config.mensagem_boas_vindas:
            mensagem = config.mensagem_boas_vindas
            # Substitui placeholders se necessário
            mensagem = mensagem.replace("{nome_empresa}", nome_empresa)
            mensagem = mensagem.replace("{link_cardapio}", link_cardapio)
        else:
            mensagem = f"👋 Olá! Seja bem-vindo(a) à {nome_empresa}!\n"
            mensagem += "É um prazer te atender 😊\n\n"
            mensagem += f"📲 Para conferir nosso cardápio completo, é só acessar o link abaixo:\n"
            mensagem += f"👉 {link_cardapio}\n\n"
            
            # Só mostra opção de pedir pelo WhatsApp se aceita pedidos
            if config and config.aceita_pedidos_whatsapp:
                mensagem += "💬 Você também pode fazer seu pedido diretamente aqui pelo WhatsApp! É só me dizer o que você quer 😊\n"
        
        return mensagem
