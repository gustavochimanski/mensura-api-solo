"""
Handler de vendas integrado com LLM (Ollama/TinyLlama)
Usa o modelo de linguagem para gerar respostas naturais baseadas em dados do banco
"""
import httpx
import json
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .sales_prompts import SALES_SYSTEM_PROMPT

# Configuração do Ollama
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "tinyllama"  # Modelo leve para servidor com pouca RAM


class LLMSalesHandler:
    """
    Handler de vendas que usa LLM para gerar respostas naturais
    Busca dados do banco e passa como contexto para o modelo
    """

    def __init__(self, db: Session, empresa_id: int = 1):
        self.db = db
        self.empresa_id = empresa_id

    def _buscar_produtos(self, termo_busca: str = "") -> List[Dict[str, Any]]:
        """Busca produtos no banco de dados"""
        try:
            from app.api.catalogo.models.model_produto import ProdutoModel
            from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel

            query = self.db.query(
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
                    ProdutoEmpModel.disponivel == True
                )
            )

            if termo_busca:
                query = query.filter(
                    ProdutoModel.descricao.ilike(f"%{termo_busca}%")
                )

            produtos = query.limit(10).all()

            return [
                {
                    "id": p.cod_barras,
                    "nome": p.descricao,
                    "preco": float(p.preco_venda)
                }
                for p in produtos
            ]
        except Exception as e:
            print(f"Erro ao buscar produtos: {e}")
            return []

    def _buscar_promocoes(self) -> List[Dict[str, Any]]:
        """Busca produtos em promoção/destaque"""
        try:
            from app.api.catalogo.models.model_produto import ProdutoModel
            from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel

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
                )
            ).limit(5).all()

            return [
                {
                    "id": p.cod_barras,
                    "nome": p.descricao,
                    "preco": float(p.preco_venda)
                }
                for p in produtos
            ]
        except Exception as e:
            print(f"Erro ao buscar promoções: {e}")
            return []

    def _obter_estado_conversa(self, user_id: str) -> Tuple[str, Dict[str, Any]]:
        """Obtém estado salvo da conversa"""
        try:
            from sqlalchemy import text

            query = text("""
                SELECT metadata
                FROM chatbot.conversations
                WHERE user_id = :user_id
                ORDER BY updated_at DESC
                LIMIT 1
            """)

            result = self.db.execute(query, {"user_id": user_id}).fetchone()

            if result and result[0]:
                metadata = result[0]
                estado = metadata.get('sales_state', 'welcome')
                dados = metadata.get('sales_data', {})
                return (estado, dados)

            return ('welcome', {'carrinho': []})
        except Exception as e:
            print(f"Erro ao obter estado: {e}")
            return ('welcome', {'carrinho': []})

    def _salvar_estado_conversa(self, user_id: str, estado: str, dados: Dict[str, Any]):
        """Salva estado da conversa"""
        try:
            from sqlalchemy import text

            dados_json = json.dumps(dados, ensure_ascii=False)

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

            self.db.execute(query, {
                "estado": estado,
                "dados": dados_json,
                "user_id": user_id
            })
            self.db.commit()
        except Exception as e:
            print(f"Erro ao salvar estado: {e}")
            self.db.rollback()

    def _montar_contexto(self, user_id: str, mensagem: str) -> str:
        """
        Monta o contexto com dados do banco para o LLM
        """
        estado, dados = self._obter_estado_conversa(user_id)
        carrinho = dados.get('carrinho', [])

        # Busca produtos relevantes baseado na mensagem
        produtos_encontrados = []

        # Detecta se é busca de produto
        msg_lower = mensagem.lower()
        palavras_ignorar = ['oi', 'ola', 'olá', 'hey', 'bom dia', 'boa tarde', 'boa noite', 'opa']

        if not any(p in msg_lower for p in palavras_ignorar):
            # Tenta buscar produto
            produtos_encontrados = self._buscar_produtos(mensagem)

        # Se não encontrou nada, busca promoções
        if not produtos_encontrados:
            produtos_encontrados = self._buscar_promocoes()

        # Monta contexto
        contexto = f"""
=== DADOS DO SISTEMA ===

ESTADO DA CONVERSA: {estado}

PRODUTOS DISPONÍVEIS NO CARDÁPIO:
"""

        if produtos_encontrados:
            for i, p in enumerate(produtos_encontrados, 1):
                contexto += f"{i}. {p['nome']} - R$ {p['preco']:.2f}\n"
        else:
            contexto += "Nenhum produto encontrado para essa busca.\n"

        contexto += f"""
CARRINHO ATUAL DO CLIENTE:
"""
        if carrinho:
            total = 0
            for item in carrinho:
                subtotal = item['preco'] * item.get('quantidade', 1)
                total += subtotal
                contexto += f"- {item.get('quantidade', 1)}x {item['nome']} = R$ {subtotal:.2f}\n"
            contexto += f"TOTAL: R$ {total:.2f}\n"
        else:
            contexto += "Carrinho vazio\n"

        contexto += f"""
=== MENSAGEM DO CLIENTE ===
"{mensagem}"

=== INSTRUÇÕES ===
Responda de forma natural e humana baseado nos dados acima.
- Se o cliente mandou "oi" ou similar, cumprimente e pergunte o que ele deseja
- Se buscou um produto, mostre os resultados numerados
- Se digitou um número, confirme o produto e pergunte quantidade
- Seja breve e direto, como uma conversa real de WhatsApp
- Use no máximo 1-2 emojis por mensagem
"""

        # Salva produtos encontrados para referência
        dados['produtos_encontrados'] = produtos_encontrados
        self._salvar_estado_conversa(user_id, estado, dados)

        return contexto

    async def processar_mensagem(self, user_id: str, mensagem: str) -> str:
        """
        Processa mensagem usando LLM com contexto do banco
        """
        try:
            # Monta contexto com dados do banco
            contexto = self._montar_contexto(user_id, mensagem)

            # Prepara mensagens para o Ollama
            messages = [
                {"role": "system", "content": SALES_SYSTEM_PROMPT},
                {"role": "user", "content": contexto}
            ]

            # Chama o Ollama
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {
                    "model": MODEL_NAME,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 300,  # Limita resposta para ser mais rápido
                    }
                }

                print(f"🤖 Chamando Ollama ({MODEL_NAME})...")
                response = await client.post(OLLAMA_URL, json=payload)

                if response.status_code == 200:
                    result = response.json()
                    resposta = result["message"]["content"]
                    print(f"✅ Resposta do LLM: {resposta[:100]}...")
                    return resposta.strip()
                else:
                    print(f"❌ Erro no Ollama: {response.text}")
                    return "Opa, deu um probleminha aqui! Pode mandar de novo?"

        except httpx.TimeoutException:
            print("⏰ Timeout no Ollama")
            return "Xiii, demorou demais pra responder... Pode mandar de novo?"

        except Exception as e:
            print(f"❌ Erro ao processar: {e}")
            import traceback
            traceback.print_exc()
            return "Ops, tive um probleminha técnico. Tenta de novo!"

    def processar_selecao_numero(self, user_id: str, numero: int) -> Optional[Dict[str, Any]]:
        """
        Quando usuário digita um número, retorna o produto correspondente
        """
        estado, dados = self._obter_estado_conversa(user_id)
        produtos = dados.get('produtos_encontrados', [])

        if produtos and 1 <= numero <= len(produtos):
            produto = produtos[numero - 1]

            # Adiciona ao carrinho
            carrinho = dados.get('carrinho', [])
            produto['quantidade'] = 1
            carrinho.append(produto)
            dados['carrinho'] = carrinho

            self._salvar_estado_conversa(user_id, 'aguardando_quantidade', dados)

            return produto

        return None


# Função principal para usar no webhook
async def processar_mensagem_llm(
    db: Session,
    user_id: str,
    mensagem: str,
    empresa_id: int = 1
) -> str:
    """
    Processa mensagem usando LLM integrado com banco de dados
    """
    handler = LLMSalesHandler(db, empresa_id)
    return await handler.processar_mensagem(user_id, mensagem)
