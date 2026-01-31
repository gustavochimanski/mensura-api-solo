"""
Serviço de Endereços para o Chatbot de Vendas
Gerencia busca no Google Maps, listagem e cadastro de endereços do cliente
Usa SQL direto para evitar problemas de mapper do SQLAlchemy
"""
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam

from app.api.localizacao.adapters.google_maps_adapter import GoogleMapsAdapter
from app.utils.logger import logger
from app.utils.telefone import normalizar_telefone_para_armazenar, variantes_telefone_para_busca


class ChatbotAddressService:
    """
    Serviço para gerenciar endereços no contexto do chatbot
    Usa SQL direto para evitar problemas de mapper
    """

    def __init__(self, db: Session, empresa_id: int = 1):
        self.db = db
        self.empresa_id = empresa_id
        self.google_maps = GoogleMapsAdapter()

    def get_cliente_by_telefone(self, telefone: str) -> Optional[Dict[str, Any]]:
        """
        Busca cliente pelo número de telefone (WhatsApp) usando SQL direto

        Args:
            telefone: Número do telefone (ex: 5561999999999)

        Returns:
            Dict com dados do cliente ou None se não encontrar
        """
        telefone_limpo = self._normalizar_telefone(telefone)
        candidatos = variantes_telefone_para_busca(telefone_limpo) or [telefone_limpo]

        query = text("""
            SELECT id, nome, telefone, email, ativo, super_token
            FROM cadastros.clientes
            WHERE telefone IN :telefones
            LIMIT 1
        """).bindparams(bindparam("telefones", expanding=True))
        result = self.db.execute(query, {"telefones": candidatos}).fetchone()

        if result:
            return {
                "id": result[0],
                "nome": result[1],
                "telefone": result[2],
                "email": result[3],
                "ativo": result[4],
                "super_token": result[5]
            }
        return None

    def get_enderecos_cliente(self, telefone: str) -> List[Dict[str, Any]]:
        """
        Busca todos os endereços cadastrados de um cliente usando SQL direto

        Args:
            telefone: Número do telefone do cliente

        Returns:
            Lista de endereços formatados para exibição no chat
        """
        cliente = self.get_cliente_by_telefone(telefone)

        if not cliente:
            logger.info(f"[ChatbotAddress] Cliente não encontrado para telefone: {telefone}")
            return []

        query = text("""
            SELECT id, logradouro, numero, complemento, bairro, cidade, estado,
                   cep, ponto_referencia, latitude, longitude, is_principal
            FROM cadastros.enderecos
            WHERE cliente_id = :cliente_id
            ORDER BY is_principal DESC, id DESC
        """)
        result = self.db.execute(query, {"cliente_id": cliente["id"]}).fetchall()

        enderecos = []
        for row in result:
            enderecos.append(self._row_to_endereco_dict(row))

        return enderecos

    def _row_to_endereco_dict(self, row) -> Dict[str, Any]:
        """Converte uma row SQL em dict de endereço formatado"""
        # Monta endereço formatado
        partes = []
        logradouro = row[1]
        numero = row[2]
        complemento = row[3]
        bairro = row[4]
        cidade = row[5]
        estado = row[6]
        cep = row[7]

        if logradouro:
            parte = logradouro
            if numero:
                parte += f", {numero}"
            partes.append(parte)

        if bairro:
            partes.append(bairro)

        cidade_estado = []
        if cidade:
            cidade_estado.append(cidade)
        if estado:
            cidade_estado.append(estado)
        if cidade_estado:
            partes.append(" - ".join(cidade_estado))

        endereco_formatado = ", ".join(partes)
        if cep:
            endereco_formatado += f" - CEP: {cep}"

        return {
            "id": row[0],
            "endereco_completo": endereco_formatado,
            "logradouro": logradouro,
            "numero": numero,
            "complemento": complemento,
            "bairro": bairro,
            "cidade": cidade,
            "estado": estado,
            "cep": cep,
            "ponto_referencia": row[8],
            "latitude": float(row[9]) if row[9] else None,
            "longitude": float(row[10]) if row[10] else None,
            "is_principal": row[11]
        }

    def buscar_enderecos_google(self, texto: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Busca endereços diretamente no Google Maps (sem passar pela API HTTP interna)
        Sempre tenta retornar pelo menos 3 resultados para o usuário escolher

        Args:
            texto: Texto do endereço digitado pelo cliente
            max_results: Número máximo de resultados (padrão 3)

        Returns:
            Lista de endereços encontrados no Google Maps
        """
        import re

        try:
            logger.info(f"[ChatbotAddress] Buscando endereço no Google Maps: {texto}")

            # Busca direta no Google Maps (sem HTTP interno)
            resultados = self.google_maps.buscar_enderecos(texto, max_results=max_results)

            # Se retornou menos de 3 resultados, busca endereços similares
            if len(resultados) < 3:
                logger.info(f"[ChatbotAddress] Apenas {len(resultados)} resultado(s), buscando similares...")
                enderecos_existentes = {r.get("endereco_formatado") for r in resultados}

                # Estratégia 1: Remove o número para buscar a rua inteira
                texto_sem_numero = re.sub(r'\b\d+\b', '', texto).strip()
                texto_sem_numero = re.sub(r'\s+', ' ', texto_sem_numero)

                # Estratégia 2: Pega só as primeiras palavras (nome da rua)
                palavras = texto.split()
                texto_rua_apenas = ' '.join(palavras[:3]) if len(palavras) > 3 else texto_sem_numero

                # Faz buscas adicionais
                buscas_extras = [texto_sem_numero, texto_rua_apenas]
                buscas_extras = [b for b in buscas_extras if b and b != texto and len(b) > 3]

                for busca in buscas_extras:
                    if len(resultados) >= 3:
                        break

                    resultados_similares = self.google_maps.buscar_enderecos(busca, max_results=5)

                    for r in resultados_similares:
                        if r.get("endereco_formatado") not in enderecos_existentes:
                            resultados.append(r)
                            enderecos_existentes.add(r.get("endereco_formatado"))
                        if len(resultados) >= 3:
                            break

            if not resultados:
                logger.info(f"[ChatbotAddress] Nenhum endereço encontrado para: {texto}")
                return []

            # Formata para exibição no chat
            enderecos_formatados = []
            for idx, resultado in enumerate(resultados[:max_results], 1):
                endereco_formatado = {
                    "index": idx,
                    "endereco_completo": resultado.get("endereco_formatado", ""),
                    "logradouro": resultado.get("logradouro"),
                    "numero": resultado.get("numero"),
                    "bairro": resultado.get("bairro"),
                    "cidade": resultado.get("cidade"),
                    "estado": resultado.get("codigo_estado") or resultado.get("estado"),
                    "cep": resultado.get("cep"),
                    "latitude": resultado.get("latitude"),
                    "longitude": resultado.get("longitude")
                }
                enderecos_formatados.append(endereco_formatado)

            logger.info(f"[ChatbotAddress] Retornando {len(enderecos_formatados)} endereços")
            return enderecos_formatados

        except Exception as e:
            logger.error(f"[ChatbotAddress] Erro ao buscar endereços: {e}")
            return []

    def _gerar_token_interno(self) -> str:
        """
        Gera um token JWT interno para autenticação na API de localização
        """
        import jwt
        from datetime import datetime, timedelta
        from app.config.settings import SECRET_KEY

        payload = {
            "sub": "1",  # ID do usuário interno
            "exp": datetime.utcnow() + timedelta(minutes=5)
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        return token

    def criar_endereco_cliente(
        self,
        telefone: str,
        dados_endereco: Dict[str, Any],
        is_principal: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Cria um novo endereço para o cliente usando SQL direto

        Args:
            telefone: Telefone do cliente
            dados_endereco: Dados do endereço (logradouro, numero, bairro, etc)
            is_principal: Se deve ser marcado como endereço principal

        Returns:
            Endereço criado formatado ou None se falhar
        """
        cliente = self.get_cliente_by_telefone(telefone)

        if not cliente:
            logger.warning(f"[ChatbotAddress] Tentativa de criar endereço para cliente não cadastrado: {telefone}")
            return None

        try:
            query = text("""
                INSERT INTO cadastros.enderecos
                (cliente_id, logradouro, numero, complemento, bairro, cidade, estado,
                 cep, ponto_referencia, latitude, longitude, is_principal, created_at, updated_at)
                VALUES (:cliente_id, :logradouro, :numero, :complemento, :bairro, :cidade, :estado,
                        :cep, :ponto_referencia, :latitude, :longitude, :is_principal, NOW(), NOW())
                RETURNING id, logradouro, numero, complemento, bairro, cidade, estado,
                          cep, ponto_referencia, latitude, longitude, is_principal
            """)
            result = self.db.execute(query, {
                "cliente_id": cliente["id"],
                "logradouro": dados_endereco.get("logradouro"),
                "numero": dados_endereco.get("numero"),
                "complemento": dados_endereco.get("complemento"),
                "bairro": dados_endereco.get("bairro"),
                "cidade": dados_endereco.get("cidade"),
                "estado": dados_endereco.get("estado"),
                "cep": dados_endereco.get("cep"),
                "ponto_referencia": dados_endereco.get("ponto_referencia"),
                "latitude": dados_endereco.get("latitude"),
                "longitude": dados_endereco.get("longitude"),
                "is_principal": is_principal
            })
            self.db.commit()

            row = result.fetchone()
            if row:
                logger.info(f"[ChatbotAddress] Endereço criado com sucesso para cliente {cliente['id']}: {row[0]}")
                return self._row_to_endereco_dict(row)

            return None

        except Exception as e:
            logger.error(f"[ChatbotAddress] Erro ao criar endereço: {e}")
            self.db.rollback()
            return None

    def criar_cliente_se_nao_existe(
        self,
        telefone: str,
        nome: str = "Cliente WhatsApp"
    ) -> Optional[Dict[str, Any]]:
        """
        Cria um cliente se ele ainda não existir usando SQL direto

        Args:
            telefone: Número do telefone
            nome: Nome do cliente (opcional)

        Returns:
            Dict do cliente existente ou recém-criado (inclui super_token)
        """
        telefone_limpo = self._normalizar_telefone(telefone)

        # Verifica se já existe
        cliente = self.get_cliente_by_telefone(telefone_limpo)
        if cliente:
            # Se o cliente já existe, mas tem nome genérico (ou vazio),
            # atualiza com o nome informado no cadastro rápido.
            try:
                nome_atual = (cliente.get("nome") or "").strip()
                nome_informado = (nome or "").strip()

                nomes_genericos = {"cliente whatsapp", "cliente", ""}
                deve_atualizar = (
                    bool(nome_informado)
                    and nome_informado.lower() not in nomes_genericos
                    and nome_atual.lower() in nomes_genericos
                )

                if deve_atualizar:
                    query_update = text("""
                        UPDATE cadastros.clientes
                        SET nome = :nome, updated_at = NOW()
                        WHERE id = :id
                        RETURNING id, nome, telefone, email, ativo, super_token
                    """)
                    row = self.db.execute(query_update, {"id": cliente["id"], "nome": nome_informado}).fetchone()
                    self.db.commit()
                    if row:
                        return {
                            "id": row[0],
                            "nome": row[1],
                            "telefone": row[2],
                            "email": row[3],
                            "ativo": row[4],
                            "super_token": row[5],
                        }
            except Exception as e:
                logger.error(f"[ChatbotAddress] Erro ao atualizar nome do cliente existente: {e}")
                self.db.rollback()

            return cliente

        try:
            import uuid
            super_token = str(uuid.uuid4())

            query = text("""
                INSERT INTO cadastros.clientes (telefone, nome, ativo, super_token, created_at, updated_at)
                VALUES (:telefone, :nome, true, :super_token, NOW(), NOW())
                RETURNING id, nome, telefone, email, ativo, super_token
            """)
            result = self.db.execute(query, {
                "telefone": telefone_limpo,
                "nome": nome,
                "super_token": super_token
            })
            self.db.commit()

            row = result.fetchone()
            if row:
                logger.info(f"[ChatbotAddress] Cliente criado automaticamente: {telefone_limpo}")
                return {
                    "id": row[0],
                    "nome": row[1],
                    "telefone": row[2],
                    "email": row[3],
                    "ativo": row[4],
                    "super_token": row[5]
                }
            return None

        except Exception as e:
            logger.error(f"[ChatbotAddress] Erro ao criar cliente: {e}")
            self.db.rollback()
            return None

    def get_endereco_by_id(self, telefone: str, endereco_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca um endereço específico do cliente por ID usando SQL direto

        Args:
            telefone: Telefone do cliente
            endereco_id: ID do endereço

        Returns:
            Endereço formatado ou None
        """
        cliente = self.get_cliente_by_telefone(telefone)

        if not cliente:
            return None

        try:
            query = text("""
                SELECT id, logradouro, numero, complemento, bairro, cidade, estado,
                       cep, ponto_referencia, latitude, longitude, is_principal
                FROM cadastros.enderecos
                WHERE cliente_id = :cliente_id AND id = :endereco_id
            """)
            result = self.db.execute(query, {
                "cliente_id": cliente["id"],
                "endereco_id": endereco_id
            }).fetchone()

            if result:
                return self._row_to_endereco_dict(result)
            return None
        except:
            return None

    def _formatar_endereco_para_chat_legacy(self, endereco) -> Dict[str, Any]:
        """
        Formata um endereço do banco para exibição no chat (legacy - mantido para compatibilidade)
        """
        # Monta endereço formatado
        partes = []
        if endereco.logradouro:
            parte = endereco.logradouro
            if endereco.numero:
                parte += f", {endereco.numero}"
            partes.append(parte)

        if endereco.bairro:
            partes.append(endereco.bairro)

        cidade_estado = []
        if endereco.cidade:
            cidade_estado.append(endereco.cidade)
        if endereco.estado:
            cidade_estado.append(endereco.estado)
        if cidade_estado:
            partes.append(" - ".join(cidade_estado))

        endereco_formatado = ", ".join(partes)
        if endereco.cep:
            endereco_formatado += f" - CEP: {endereco.cep}"

        return {
            "id": endereco.id,
            "endereco_completo": endereco_formatado,
            "logradouro": endereco.logradouro,
            "numero": endereco.numero,
            "complemento": endereco.complemento,
            "bairro": endereco.bairro,
            "cidade": endereco.cidade,
            "estado": endereco.estado,
            "cep": endereco.cep,
            "ponto_referencia": endereco.ponto_referencia,
            "latitude": float(endereco.latitude) if endereco.latitude else None,
            "longitude": float(endereco.longitude) if endereco.longitude else None,
            "is_principal": endereco.is_principal
        }

    def _normalizar_telefone(self, telefone: str) -> str:
        """
        Normaliza o número de telefone removendo caracteres especiais
        e garantindo que tenha o prefixo do país (55) quando necessário.

        IMPORTANTE:
        - Não inventa dígitos (ex.: NÃO adiciona "9" para "completar" o número).
        - Mantém consistência entre cadastro, conversa e envio de mensagem.
        - Usa o número EXATAMENTE como recebido, sem adicionar dígitos.
        """
        # Unificação:
        # - salva e trabalha com 55+DDD+9 dígitos quando for celular (WhatsApp)
        # - ainda assim, as consultas aceitam variações via variantes_telefone_para_busca()
        return normalizar_telefone_para_armazenar(telefone) or ""

    def formatar_lista_enderecos_para_chat(self, enderecos: List[Dict[str, Any]]) -> str:
        """
        Formata a lista de endereços para exibição bonita no WhatsApp

        Args:
            enderecos: Lista de endereços formatados

        Returns:
            Mensagem formatada para o WhatsApp
        """
        if not enderecos:
            return ""

        mensagem = "📍 *Seus endereços cadastrados:*\n\n"

        for idx, end in enumerate(enderecos, 1):
            emoji_principal = "⭐ " if end.get("is_principal") else ""
            mensagem += f"*{idx}.* {emoji_principal}{end['endereco_completo']}\n"
            if end.get("complemento"):
                mensagem += f"   📝 {end['complemento']}\n"
            if end.get("ponto_referencia"):
                mensagem += f"   🔍 Ref: {end['ponto_referencia']}\n"
            mensagem += "\n"

        return mensagem

    def formatar_opcoes_google_para_chat(self, enderecos: List[Dict[str, Any]]) -> str:
        """
        Formata as opções de endereço do Google Maps para exibição no WhatsApp

        Args:
            enderecos: Lista de endereços do Google Maps

        Returns:
            Mensagem formatada
        """
        if not enderecos:
            return "Não encontrei endereços com esse texto. Pode tentar de novo com mais detalhes?"

        mensagem = "🔍 *Encontrei esses endereços:*\n\n"

        for end in enderecos:
            mensagem += f"*{end['index']}.* {end['endereco_completo']}\n\n"

        mensagem += "Digite o *número* do endereço correto!"

        return mensagem
