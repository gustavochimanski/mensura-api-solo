"""
LLM Tools - Funções que o modelo de linguagem pode chamar
Permite que o chatbot busque produtos reais, calcule frete e crie pedidos
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Definição das ferramentas disponíveis para o LLM
TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "buscar_produtos",
            "description": "Busca produtos disponíveis no cardápio do restaurante. Use quando o cliente perguntar 'o que tem', 'cardápio', ou buscar um produto específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "termo_busca": {
                        "type": "string",
                        "description": "Termo para buscar (ex: 'pizza', 'teste', 'hamburguer'). Deixe vazio para listar todos os produtos."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_total",
            "description": "Calcula o total do pedido incluindo frete",
            "parameters": {
                "type": "object",
                "properties": {
                    "produtos": {
                        "type": "array",
                        "description": "Lista de produtos com ID e quantidade",
                        "items": {
                            "type": "object",
                            "properties": {
                                "produto_id": {"type": "string"},
                                "quantidade": {"type": "integer"}
                            }
                        }
                    }
                },
                "required": ["produtos"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_taxa_entrega",
            "description": "Calcula a taxa de entrega com base na distância do cliente",
            "parameters": {
                "type": "object",
                "properties": {
                    "distancia_km": {
                        "type": "number",
                        "description": "Distância em quilômetros até o endereço de entrega"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "criar_pedido",
            "description": "Cria um pedido no sistema após coletar todos os dados (produtos, endereço, pagamento)",
            "parameters": {
                "type": "object",
                "properties": {
                    "telefone": {"type": "string", "description": "Telefone do cliente (WhatsApp)"},
                    "endereco": {"type": "string", "description": "Endereço completo de entrega"},
                    "produtos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "produto_id": {"type": "string"},
                                "quantidade": {"type": "integer"}
                            }
                        }
                    },
                    "forma_pagamento": {
                        "type": "string",
                        "enum": ["PIX", "DINHEIRO", "CARTAO", "ONLINE"],
                        "description": "Forma de pagamento escolhida"
                    }
                },
                "required": ["telefone", "endereco", "produtos", "forma_pagamento"]
            }
        }
    }
]


def buscar_produtos(db: Session, termo_busca: str = "") -> Dict[str, Any]:
    """Busca produtos no banco de dados"""
    try:
        from app.api.catalogo.models.model_produto import ProdutoModel
        from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel

        query = db.query(
            ProdutoModel.cod_barras,
            ProdutoModel.descricao,
            ProdutoEmpModel.preco_venda
        ).join(
            ProdutoEmpModel,
            ProdutoModel.cod_barras == ProdutoEmpModel.cod_barras
        ).filter(
            and_(
                ProdutoEmpModel.empresa_id == 1,
                ProdutoModel.ativo == True,
                ProdutoEmpModel.disponivel == True
            )
        )

        # Se tiver termo de busca, filtra
        if termo_busca:
            query = query.filter(
                ProdutoModel.descricao.ilike(f"%{termo_busca}%")
            )

        produtos = query.limit(20).all()

        return {
            "success": True,
            "produtos": [
                {
                    "id": p.cod_barras,
                    "nome": p.descricao,
                    "preco": float(p.preco_venda)
                }
                for p in produtos
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def calcular_total(db: Session, produtos: List[Dict]) -> Dict[str, Any]:
    """Calcula total do pedido com frete"""
    try:
        from app.api.catalogo.models.model_produto_emp import ProdutoEmpModel
        from app.api.cadastros.models.model_regiao_entrega import RegiaoEntregaModel

        subtotal = 0.0

        # Busca preços dos produtos
        for item in produtos:
            produto = db.query(ProdutoEmpModel).filter(
                and_(
                    ProdutoEmpModel.cod_barras == item["produto_id"],
                    ProdutoEmpModel.empresa_id == 1
                )
            ).first()

            if produto:
                subtotal += float(produto.preco_venda) * item["quantidade"]

        # Busca frete
        regiao = db.query(RegiaoEntregaModel).filter(
            and_(
                RegiaoEntregaModel.empresa_id == 1,
                RegiaoEntregaModel.ativo == True
            )
        ).first()

        taxa_entrega = float(regiao.taxa_entrega) if regiao else 5.0
        total = subtotal + taxa_entrega

        return {
            "success": True,
            "subtotal": subtotal,
            "taxa_entrega": taxa_entrega,
            "total": total
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def calcular_taxa_entrega(db: Session, distancia_km: float | None = None) -> Dict[str, Any]:
    """Calcula taxa de entrega com base na distância"""
    try:
        from sqlalchemy import or_
        from app.api.cadastros.models.model_regiao_entrega import RegiaoEntregaModel

        query = db.query(RegiaoEntregaModel).filter(
            and_(
                RegiaoEntregaModel.empresa_id == 1,
                RegiaoEntregaModel.ativo == True
            )
        )

        if distancia_km is not None:
            query = query.filter(
                RegiaoEntregaModel.distancia_min_km <= distancia_km,
                or_(
                    RegiaoEntregaModel.distancia_max_km.is_(None),
                    RegiaoEntregaModel.distancia_max_km >= distancia_km
                )
            )

        regiao = query.order_by(RegiaoEntregaModel.distancia_max_km.asc()).first()

        if not regiao:
            return {
                "success": True,
                "taxa_entrega": 5.0,
                "tempo_estimado_min": 30
            }

        return {
            "success": True,
            "taxa_entrega": float(regiao.taxa_entrega),
            "tempo_estimado_min": regiao.tempo_estimado_min
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def criar_pedido(
    db: Session,
    telefone: str,
    endereco: str,
    produtos: List[Dict],
    forma_pagamento: str
) -> Dict[str, Any]:
    """Cria pedido no sistema"""
    try:
        from app.api.pedidos.models.model_pedido import PedidoModel
        from app.api.pedidos.models.model_pedido_item import PedidoItemModel
        from sqlalchemy import text

        # Calcula total
        calc = calcular_total(db, produtos)
        if not calc["success"]:
            return calc

        # Cria pedido
        pedido = PedidoModel(
            cliente_id=None,  # Cliente via WhatsApp não tem ID
            telefone=telefone,
            endereco_entrega=endereco,
            tipo_pedido="DELIVERY",
            status="PENDENTE",
            valor_subtotal=calc["subtotal"],
            valor_taxa_entrega=calc["taxa_entrega"],
            valor_total=calc["total"],
            forma_pagamento=forma_pagamento,
            observacoes=f"Pedido via WhatsApp"
        )

        db.add(pedido)
        db.flush()  # Pega o ID do pedido

        # Adiciona itens
        for item in produtos:
            pedido_item = PedidoItemModel(
                pedido_id=pedido.id,
                produto_cod_barras=item["produto_id"],
                quantidade=item["quantidade"]
            )
            db.add(pedido_item)

        db.commit()

        return {
            "success": True,
            "pedido_id": pedido.id,
            "total": calc["total"],
            "mensagem": f"Pedido #{pedido.id} criado com sucesso!"
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}


# Executa as funções baseado no nome
def executar_funcao(db: Session, nome_funcao: str, argumentos: Dict) -> Dict:
    """Executa a função solicitada pelo LLM"""

    if nome_funcao == "buscar_produtos":
        return buscar_produtos(db, argumentos.get("termo_busca", ""))

    elif nome_funcao == "calcular_total":
        return calcular_total(db, argumentos.get("produtos", []))

    elif nome_funcao == "calcular_taxa_entrega":
        return calcular_taxa_entrega(db, argumentos.get("distancia_km"))

    elif nome_funcao == "criar_pedido":
        return criar_pedido(
            db,
            argumentos.get("telefone"),
            argumentos.get("endereco"),
            argumentos.get("produtos"),
            argumentos.get("forma_pagamento")
        )

    else:
        return {"success": False, "error": f"Função {nome_funcao} não encontrada"}
