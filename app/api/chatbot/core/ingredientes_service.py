"""
Serviço para gerenciar ingredientes, adicionais e combos no chatbot
Permite consultar composição de produtos, adicionar extras, remover ingredientes e listar combos
"""
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text


class IngredientesService:
    """
    Serviço para consultar e manipular ingredientes e adicionais de receitas
    """

    def __init__(self, db: Session, empresa_id: int = 1):
        self.db = db
        self.empresa_id = empresa_id

    def buscar_ingredientes_receita(self, receita_id: int) -> List[Dict[str, Any]]:
        """
        Busca todos os ingredientes de uma receita

        Returns:
            Lista de ingredientes com id, nome, quantidade
        """
        try:
            query = text("""
                SELECT
                    i.id,
                    i.nome,
                    i.descricao,
                    ri.quantidade,
                    i.unidade_medida
                FROM catalogo.receita_ingrediente ri
                JOIN catalogo.ingredientes i ON i.id = ri.ingrediente_id
                WHERE ri.receita_id = :receita_id
                ORDER BY i.nome
            """)

            result = self.db.execute(query, {"receita_id": receita_id})

            ingredientes = []
            for row in result.fetchall():
                ingredientes.append({
                    "id": row[0],
                    "nome": row[1],
                    "descricao": row[2],
                    "quantidade": float(row[3]) if row[3] else 0,
                    "unidade": row[4]
                })

            return ingredientes

        except Exception as e:
            print(f"Erro ao buscar ingredientes: {e}")
            return []

    def buscar_ingredientes_por_nome_receita(self, nome_receita: str) -> List[Dict[str, Any]]:
        """
        Busca ingredientes pelo nome da receita
        """
        try:
            # Primeiro busca o ID da receita
            query = text("""
                SELECT id FROM catalogo.receitas
                WHERE nome ILIKE :nome AND empresa_id = :empresa_id
                LIMIT 1
            """)

            result = self.db.execute(query, {
                "nome": f"%{nome_receita}%",
                "empresa_id": self.empresa_id
            }).fetchone()

            if result:
                return self.buscar_ingredientes_receita(result[0])

            return []

        except Exception as e:
            print(f"Erro ao buscar ingredientes por nome: {e}")
            return []

    def buscar_adicionais_receita(self, receita_id: int) -> List[Dict[str, Any]]:
        """
        Busca todos os adicionais disponíveis para uma receita

        Returns:
            Lista de adicionais com id, nome, preco
        """
        try:
            query = text("""
                SELECT
                    a.id,
                    a.nome,
                    a.descricao,
                    a.preco
                FROM catalogo.receita_adicional ra
                JOIN catalogo.adicionais a ON a.id = ra.adicional_id
                WHERE ra.receita_id = :receita_id
                AND a.ativo = true
                ORDER BY a.preco
            """)

            result = self.db.execute(query, {"receita_id": receita_id})

            adicionais = []
            for row in result.fetchall():
                adicionais.append({
                    "id": row[0],
                    "nome": row[1],
                    "descricao": row[2],
                    "preco": float(row[3]) if row[3] else 0
                })

            return adicionais

        except Exception as e:
            print(f"Erro ao buscar adicionais: {e}")
            return []

    def buscar_adicionais_por_nome_receita(self, nome_receita: str) -> List[Dict[str, Any]]:
        """
        Busca adicionais pelo nome da receita
        """
        try:
            query = text("""
                SELECT id FROM catalogo.receitas
                WHERE nome ILIKE :nome AND empresa_id = :empresa_id
                LIMIT 1
            """)

            result = self.db.execute(query, {
                "nome": f"%{nome_receita}%",
                "empresa_id": self.empresa_id
            }).fetchone()

            if result:
                return self.buscar_adicionais_receita(result[0])

            return []

        except Exception as e:
            print(f"Erro ao buscar adicionais por nome: {e}")
            return []

    def buscar_todos_adicionais(self) -> List[Dict[str, Any]]:
        """
        Busca todos os adicionais disponíveis da empresa
        """
        try:
            query = text("""
                SELECT id, nome, descricao, preco
                FROM catalogo.adicionais
                WHERE empresa_id = :empresa_id AND ativo = true
                ORDER BY preco
            """)

            result = self.db.execute(query, {"empresa_id": self.empresa_id})

            return [
                {
                    "id": row[0],
                    "nome": row[1],
                    "descricao": row[2],
                    "preco": float(row[3]) if row[3] else 0
                }
                for row in result.fetchall()
            ]

        except Exception as e:
            print(f"Erro ao buscar todos adicionais: {e}")
            return []

    def verificar_ingrediente_na_receita(self, receita_id: int, nome_ingrediente: str) -> Optional[Dict[str, Any]]:
        """
        Verifica se um ingrediente específico está na receita

        Returns:
            Dict com dados do ingrediente se encontrado, None se não
        """
        ingredientes = self.buscar_ingredientes_receita(receita_id)

        nome_lower = nome_ingrediente.lower().strip()

        # Remove acentos para comparação
        def remover_acentos(texto):
            acentos = {'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'é': 'e', 'ê': 'e',
                       'í': 'i', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ú': 'u', 'ç': 'c'}
            for acentuado, sem_acento in acentos.items():
                texto = texto.replace(acentuado, sem_acento)
            return texto

        nome_sem_acento = remover_acentos(nome_lower)

        for ing in ingredientes:
            ing_nome_lower = ing['nome'].lower()
            ing_nome_sem_acento = remover_acentos(ing_nome_lower)

            # Match exato ou parcial
            if (nome_lower in ing_nome_lower or
                nome_sem_acento in ing_nome_sem_acento or
                ing_nome_lower in nome_lower or
                ing_nome_sem_acento in nome_sem_acento):
                return ing

        return None

    def verificar_ingrediente_na_receita_por_nome(
        self,
        nome_receita: str,
        nome_ingrediente: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verifica se um ingrediente está na receita buscando pelo nome da receita

        Returns:
            Dict com dados do ingrediente se encontrado, None se não
        """
        try:
            # Primeiro busca o ID da receita
            query = text("""
                SELECT id FROM catalogo.receitas
                WHERE nome ILIKE :nome AND empresa_id = :empresa_id
                LIMIT 1
            """)

            result = self.db.execute(query, {
                "nome": f"%{nome_receita}%",
                "empresa_id": self.empresa_id
            }).fetchone()

            if result:
                return self.verificar_ingrediente_na_receita(result[0], nome_ingrediente)

            return None

        except Exception as e:
            print(f"Erro ao verificar ingrediente por nome da receita: {e}")
            return None

    def buscar_adicional_por_nome(self, nome_adicional: str) -> Optional[Dict[str, Any]]:
        """
        Busca um adicional pelo nome
        """
        try:
            # Remove acentos para comparação
            def remover_acentos(texto):
                acentos = {'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'é': 'e', 'ê': 'e',
                           'í': 'i', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ú': 'u', 'ç': 'c'}
                for acentuado, sem_acento in acentos.items():
                    texto = texto.replace(acentuado, sem_acento)
                return texto

            nome_lower = nome_adicional.lower().strip()
            nome_sem_acento = remover_acentos(nome_lower)

            # Busca todos os adicionais
            adicionais = self.buscar_todos_adicionais()

            # Mapeamento de termos comuns
            mapeamento = {
                'queijo extra': ['queijo extra', 'mais queijo', 'queijo a mais'],
                'bacon extra': ['bacon extra', 'mais bacon', 'bacon a mais'],
                'borda recheada': ['borda recheada', 'borda catupiry', 'borda cheddar'],
                'ovo extra': ['ovo extra', 'mais ovo', 'ovo a mais'],
            }

            for adicional in adicionais:
                add_nome_lower = adicional['nome'].lower()
                add_nome_sem_acento = remover_acentos(add_nome_lower)

                # Match direto
                if (nome_sem_acento in add_nome_sem_acento or
                    add_nome_sem_acento in nome_sem_acento):
                    return adicional

                # Match por mapeamento
                for chave, variantes in mapeamento.items():
                    if any(v in nome_sem_acento for v in variantes):
                        if chave in add_nome_sem_acento:
                            return adicional

            return None

        except Exception as e:
            print(f"Erro ao buscar adicional: {e}")
            return None

    def formatar_composicao_produto(self, nome_receita: str) -> str:
        """
        Formata a composição de um produto para exibir ao cliente

        Returns:
            Mensagem formatada com ingredientes e adicionais disponíveis
        """
        ingredientes = self.buscar_ingredientes_por_nome_receita(nome_receita)
        adicionais = self.buscar_adicionais_por_nome_receita(nome_receita)

        if not ingredientes:
            return f"Não encontrei informações sobre a composição de {nome_receita}"

        mensagem = f"*{nome_receita}*\n\n"
        mensagem += "📋 *Ingredientes:*\n"

        for ing in ingredientes:
            mensagem += f"• {ing['nome']}\n"

        if adicionais:
            mensagem += "\n➕ *Adicionais disponíveis:*\n"
            for add in adicionais:
                mensagem += f"• {add['nome']} (+R$ {add['preco']:.2f})\n"

        mensagem += "\nQuer tirar ou adicionar algo? 😊"

        return mensagem

    # ========== MÉTODOS PARA COMBOS ==========

    def buscar_todos_combos(self) -> List[Dict[str, Any]]:
        """
        Busca todos os combos ativos da empresa

        Returns:
            Lista de combos com id, titulo, descricao, preco_total
        """
        try:
            query = text("""
                SELECT
                    c.id,
                    c.titulo,
                    c.descricao,
                    c.preco_total,
                    c.imagem
                FROM catalogo.combos c
                WHERE c.empresa_id = :empresa_id
                AND c.ativo = true
                ORDER BY c.titulo
            """)

            result = self.db.execute(query, {"empresa_id": self.empresa_id})

            combos = []
            for row in result.fetchall():
                combos.append({
                    "id": row[0],
                    "titulo": row[1],
                    "descricao": row[2],
                    "preco": float(row[3]) if row[3] else 0,
                    "imagem": row[4]
                })

            return combos

        except Exception as e:
            print(f"Erro ao buscar combos: {e}")
            return []

    def buscar_combo_por_nome(self, nome_combo: str) -> Optional[Dict[str, Any]]:
        """
        Busca um combo pelo nome/título

        Returns:
            Dict com dados do combo ou None se não encontrar
        """
        try:
            query = text("""
                SELECT
                    c.id,
                    c.titulo,
                    c.descricao,
                    c.preco_total,
                    c.imagem
                FROM catalogo.combos c
                WHERE c.empresa_id = :empresa_id
                AND c.ativo = true
                AND c.titulo ILIKE :nome
                LIMIT 1
            """)

            result = self.db.execute(query, {
                "empresa_id": self.empresa_id,
                "nome": f"%{nome_combo}%"
            }).fetchone()

            if result:
                return {
                    "id": result[0],
                    "titulo": result[1],
                    "descricao": result[2],
                    "preco": float(result[3]) if result[3] else 0,
                    "imagem": result[4]
                }

            return None

        except Exception as e:
            print(f"Erro ao buscar combo por nome: {e}")
            return None

    def buscar_itens_combo(self, combo_id: int) -> List[Dict[str, Any]]:
        """
        Busca os itens (produtos) de um combo

        Returns:
            Lista de itens com produto e quantidade
        """
        try:
            query = text("""
                SELECT
                    ci.id,
                    ci.produto_cod_barras,
                    ci.quantidade,
                    p.descricao as produto_nome,
                    pe.preco_venda
                FROM catalogo.combos_itens ci
                LEFT JOIN catalogo.produtos p ON p.cod_barras = ci.produto_cod_barras
                LEFT JOIN catalogo.produtos_empresa pe ON pe.cod_barras = ci.produto_cod_barras
                    AND pe.empresa_id = :empresa_id
                WHERE ci.combo_id = :combo_id
                ORDER BY p.descricao
            """)

            result = self.db.execute(query, {
                "combo_id": combo_id,
                "empresa_id": self.empresa_id
            })

            itens = []
            for row in result.fetchall():
                itens.append({
                    "id": row[0],
                    "cod_barras": row[1],
                    "quantidade": row[2],
                    "produto_nome": row[3] or "Produto",
                    "preco_unitario": float(row[4]) if row[4] else 0
                })

            return itens

        except Exception as e:
            print(f"Erro ao buscar itens do combo: {e}")
            return []

    def formatar_combos_para_chat(self) -> str:
        """
        Formata a lista de combos para exibir ao cliente no WhatsApp

        Returns:
            Mensagem formatada com todos os combos
        """
        combos = self.buscar_todos_combos()

        if not combos:
            return "😕 No momento não temos combos disponíveis.\n\nMas temos várias opções no cardápio! Quer ver?"

        mensagem = "🎁 *COMBOS ESPECIAIS*\n"
        mensagem += "━━━━━━━━━━━━━━━━━\n\n"

        for combo in combos:
            mensagem += f"🍔 *{combo['titulo']}*\n"
            if combo['descricao']:
                mensagem += f"   {combo['descricao']}\n"
            mensagem += f"   💰 *R$ {combo['preco']:.2f}*\n"

            # Buscar itens do combo
            itens = self.buscar_itens_combo(combo['id'])
            if itens:
                mensagem += "   📦 Inclui:\n"
                for item in itens:
                    qtd = f"{item['quantidade']}x " if item['quantidade'] > 1 else ""
                    mensagem += f"      • {qtd}{item['produto_nome']}\n"

            mensagem += "\n"

        mensagem += "━━━━━━━━━━━━━━━━━\n"
        mensagem += "Quer pedir algum combo? 😋"

        return mensagem

    def formatar_combo_detalhado(self, nome_combo: str) -> str:
        """
        Formata detalhes de um combo específico

        Returns:
            Mensagem formatada com detalhes do combo
        """
        combo = self.buscar_combo_por_nome(nome_combo)

        if not combo:
            return f"Não encontrei o combo '{nome_combo}' 😕\n\nDigite *COMBOS* para ver os disponíveis!"

        mensagem = f"🎁 *{combo['titulo']}*\n\n"

        if combo['descricao']:
            mensagem += f"📝 {combo['descricao']}\n\n"

        itens = self.buscar_itens_combo(combo['id'])
        if itens:
            mensagem += "📦 *O que vem no combo:*\n"
            for item in itens:
                qtd = f"{item['quantidade']}x " if item['quantidade'] > 1 else ""
                mensagem += f"   • {qtd}{item['produto_nome']}\n"
            mensagem += "\n"

        mensagem += f"💰 *Preço: R$ {combo['preco']:.2f}*\n\n"
        mensagem += "Quer adicionar ao pedido? 😊"

        return mensagem


    # ========== MÉTODOS PARA COMPLEMENTOS ==========

    def buscar_complementos_receita(self, receita_id: int) -> List[Dict[str, Any]]:
        """
        Busca complementos disponíveis para uma receita direto do banco (mais rápido)

        Returns:
            Lista de complementos com seus adicionais, min/max, obrigatório
        """
        try:
            # Busca direto do banco para evitar timeout de HTTP
            query = text("""
                SELECT
                    c.id, c.nome, c.descricao, c.obrigatorio, c.quantitativo,
                    c.minimo_itens, c.maximo_itens, c.ordem, c.ativo
                FROM catalogo.complemento_produto c
                JOIN catalogo.receita_complemento_link rcl ON rcl.complemento_id = c.id
                WHERE rcl.receita_id = :receita_id AND c.ativo = true
                ORDER BY c.ordem
            """)
            result = self.db.execute(query, {"receita_id": receita_id})

            complementos = []
            for row in result.fetchall():
                comp_id = row[0]
                # Busca adicionais do complemento
                query_add = text("""
                    SELECT a.id, a.nome, a.descricao, a.preco, a.ativo, cil.ordem
                    FROM catalogo.adicionais a
                    JOIN catalogo.complemento_item_link cil ON cil.item_id = a.id
                    WHERE cil.complemento_id = :comp_id AND a.ativo = true
                    ORDER BY cil.ordem
                """)
                result_add = self.db.execute(query_add, {"comp_id": comp_id})

                adicionais = []
                for add_row in result_add.fetchall():
                    adicionais.append({
                        "id": add_row[0],
                        "nome": add_row[1],
                        "descricao": add_row[2],
                        "preco": float(add_row[3]) if add_row[3] else 0.0,
                        "ativo": add_row[4],
                        "ordem": add_row[5] or 0
                    })

                complementos.append({
                    "id": row[0],
                    "nome": row[1],
                    "descricao": row[2],
                    "obrigatorio": row[3],
                    "quantitativo": row[4],
                    "minimo_itens": row[5] or 0,
                    "maximo_itens": row[6] or 0,
                    "ordem": row[7],
                    "ativo": row[8],
                    "adicionais": adicionais
                })

            return complementos
        except Exception as e:
            print(f"Erro ao buscar complementos da receita: {e}")
            return []

    def buscar_complementos_produto(self, cod_barras: str) -> List[Dict[str, Any]]:
        """
        Busca complementos disponíveis para um produto via API interna
        """
        import httpx
        try:
            url = f"http://localhost:8000/api/catalogo/public/complementos/produto/{cod_barras}?apenas_ativos=true"
            response = httpx.get(url, timeout=10.0)

            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Erro ao buscar complementos do produto: {e}")
            return []

    def buscar_complementos_combo(self, combo_id: int) -> List[Dict[str, Any]]:
        """
        Busca complementos disponíveis para um combo via API interna
        """
        import httpx
        try:
            url = f"http://localhost:8000/api/catalogo/public/complementos/combo/{combo_id}?apenas_ativos=true"
            response = httpx.get(url, timeout=10.0)

            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Erro ao buscar complementos do combo: {e}")
            return []

    def buscar_complementos_por_nome_receita(self, nome_receita: str) -> List[Dict[str, Any]]:
        """
        Busca complementos pelo nome da receita
        """
        try:
            query = text("""
                SELECT id FROM catalogo.receitas
                WHERE nome ILIKE :nome AND empresa_id = :empresa_id
                LIMIT 1
            """)

            result = self.db.execute(query, {
                "nome": f"%{nome_receita}%",
                "empresa_id": self.empresa_id
            }).fetchone()

            if result:
                return self.buscar_complementos_receita(result[0])

            return []
        except Exception as e:
            print(f"Erro ao buscar complementos por nome: {e}")
            return []

    def formatar_complementos_para_chat(self, complementos: List[Dict[str, Any]], nome_produto: str) -> str:
        """
        Formata complementos disponíveis para exibir no WhatsApp

        Returns:
            Mensagem formatada com grupos de complementos e itens
        """
        if not complementos:
            return ""

        mensagem = f"\n\n🍽️ *Escolha os adicionais:*\n"

        for comp in complementos:
            nome = comp.get('nome', 'Complemento')
            obrigatorio = comp.get('obrigatorio', False)
            minimo = comp.get('minimo_itens', 0)
            maximo = comp.get('maximo_itens', 0)
            adicionais = comp.get('adicionais', [])

            # Limite de seleção - formato mais limpo
            if obrigatorio:
                if minimo == maximo:
                    limite_txt = f"escolha {minimo}"
                else:
                    limite_txt = f"escolha de {minimo} a {maximo}"
                mensagem += f"\n*{nome}* ⚠️ *OBRIGATÓRIO* _{limite_txt}_\n"
            else:
                if maximo > 0:
                    mensagem += f"\n*{nome}* _(opcional, máx {maximo})_\n"
                else:
                    mensagem += f"\n*{nome}* _(opcional)_\n"

            for add in adicionais[:8]:  # Limita a 8 itens
                preco = add.get('preco', 0)
                add_nome = add.get('nome', '')
                if preco > 0:
                    mensagem += f"  ▸ {add_nome} *+R$ {preco:.2f}*\n"
                else:
                    mensagem += f"  ▸ {add_nome} _grátis_\n"

            if len(adicionais) > 8:
                mensagem += f"  _...e mais {len(adicionais) - 8} opções_\n"

        return mensagem

    def tem_complementos_obrigatorios(self, complementos: List[Dict[str, Any]]) -> bool:
        """
        Verifica se há complementos obrigatórios na lista
        """
        return any(comp.get('obrigatorio', False) for comp in complementos)

    def buscar_receita_id_por_nome(self, nome_receita: str) -> Optional[int]:
        """
        Busca o ID da receita pelo nome
        """
        try:
            query = text("""
                SELECT id FROM catalogo.receitas
                WHERE nome ILIKE :nome AND empresa_id = :empresa_id
                LIMIT 1
            """)

            result = self.db.execute(query, {
                "nome": f"%{nome_receita}%",
                "empresa_id": self.empresa_id
            }).fetchone()

            return result[0] if result else None
        except:
            return None


def detectar_remocao_ingrediente(mensagem: str) -> Tuple[bool, Optional[str]]:
    """
    Detecta se o cliente quer remover um ingrediente

    Returns:
        (quer_remover: bool, nome_ingrediente: str ou None)
    """
    msg_lower = mensagem.lower().strip()

    # Padrões de remoção
    padroes_remocao = [
        r'sem\s+(\w+)',
        r'tira[r]?\s+(?:o|a)?\s*(\w+)',
        r'remove[r]?\s+(?:o|a)?\s*(\w+)',
        r'n[aã]o\s+(?:quero|coloca|bota|põe)\s+(\w+)',
        r'(?:sem|tira|remove)\s+(?:a|o)?\s*(\w+)',
    ]

    import re
    for padrao in padroes_remocao:
        match = re.search(padrao, msg_lower)
        if match:
            ingrediente = match.group(1)
            # Ignora palavras genéricas
            genericas = ['nada', 'isso', 'mais', 'esse', 'essa', 'aquele', 'aquela']
            if ingrediente not in genericas:
                return (True, ingrediente)

    return (False, None)


def detectar_adicao_extra(mensagem: str) -> Tuple[bool, Optional[str]]:
    """
    Detecta se o cliente quer adicionar um extra

    Returns:
        (quer_adicionar: bool, nome_adicional: str ou None)
    """
    msg_lower = mensagem.lower().strip()

    # Padrões de adição
    padroes_adicao = [
        r'(?:adiciona|coloca|bota|põe|quero)\s+(?:mais\s+)?(\w+(?:\s+\w+)?)\s*(?:extra)?',
        r'com\s+(\w+)\s+extra',
        r'(?:mais|extra)\s+(\w+)',
        r'borda\s+(?:recheada|de)?\s*(\w+)?',
    ]

    import re

    # Verifica padrão de borda primeiro
    if 'borda' in msg_lower:
        if 'catupiry' in msg_lower:
            return (True, 'borda recheada catupiry')
        elif 'cheddar' in msg_lower:
            return (True, 'borda recheada cheddar')
        elif 'recheada' in msg_lower:
            return (True, 'borda recheada')

    for padrao in padroes_adicao:
        match = re.search(padrao, msg_lower)
        if match:
            adicional = match.group(1) if match.group(1) else None
            if adicional:
                # Ignora palavras genéricas
                genericas = ['mais', 'isso', 'esse', 'essa', 'um', 'uma']
                if adicional not in genericas:
                    return (True, adicional)

    return (False, None)


def detectar_pergunta_ingredientes(mensagem: str) -> Tuple[bool, Optional[str]]:
    """
    Detecta se o cliente quer saber os ingredientes de um produto

    Returns:
        (quer_saber: bool, nome_produto: str ou None)
    """
    msg_lower = mensagem.lower().strip()

    # Padrões de pergunta sobre ingredientes
    padroes = [
        r'(?:o\s+)?que\s+(?:vem|tem)\s+(?:no|na|n[oa])\s+(.+?)(?:\?|$)',
        r'(?:quais?\s+)?ingredientes?\s+(?:do|da|tem)\s+(.+?)(?:\?|$)',
        r'(?:do|da)\s+que\s+[eé]\s+(?:feito|feita)\s+(?:o|a)?\s*(.+?)(?:\?|$)',
        r'(?:o|a)\s+(.+?)\s+(?:vem|tem)\s+(?:o\s+)?que(?:\?|$)',
        r'composi[cç][aã]o\s+(?:do|da)\s+(.+?)(?:\?|$)',
    ]

    import re
    for padrao in padroes:
        match = re.search(padrao, msg_lower)
        if match:
            produto = match.group(1).strip()
            if produto and len(produto) > 2:
                return (True, produto)

    return (False, None)
