"""
Serviço de integração com Printer API
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.api.delivery.models.model_pedido_dv import PedidoDeliveryModel
from app.api.delivery.schemas.schema_shared_enums import PedidoStatusEnum
from app.utils.printer_client import PrinterClient
from app.utils.logger import logger
from app.config.printer_config import PrinterConfig


class PrinterIntegrationService:
    def __init__(self, db: Session, printer_api_url: Optional[str] = None):
        self.db = db
        self.printer_client = PrinterClient(
            printer_api_url or PrinterConfig.get_printer_url()
        )
    
    def _converter_pedido_para_printer_format(self, pedido: PedidoDeliveryModel) -> Dict[str, Any]:
        """
        Converte pedido do banco para formato da Printer API
        
        Args:
            pedido: Pedido do banco de dados
            
        Returns:
            Dict no formato esperado pela Printer API
        """
        # Converte itens do pedido
        itens = []
        for item in pedido.itens:
            itens.append({
                "descricao": item.produto_descricao_snapshot or f"Produto {item.produto_cod_barras}",
                "quantidade": item.quantidade,
                "preco": float(item.preco_unitario)
            })
        
        # Determina tipo de pagamento
        tipo_pagamento = "DINHEIRO"  # Padrão
        if pedido.meio_pagamento:
            tipo_pagamento = pedido.meio_pagamento.metodo or "DINHEIRO"
        
        # Calcula troco se necessário
        troco = None
        if tipo_pagamento.upper() == "DINHEIRO" and pedido.troco_para:
            troco = float(pedido.troco_para)
        
        return {
            "numero": pedido.id,
            "cliente": pedido.cliente.nome if pedido.cliente else "Cliente não informado",
            "itens": itens,
            "total": float(pedido.valor_total or 0),
            "tipo_pagamento": tipo_pagamento,
            "troco": troco
        }
    
    async def imprimir_pedido(self, pedido_id: int) -> Dict[str, Any]:
        """
        Imprime um pedido específico
        
        Args:
            pedido_id: ID do pedido a ser impresso
            
        Returns:
            Dict com resultado da impressão
        """
        try:
            # Busca o pedido
            pedido = self.db.query(PedidoDeliveryModel).filter(
                PedidoDeliveryModel.id == pedido_id,
                PedidoDeliveryModel.status == PedidoStatusEnum.I.value
            ).first()
            
            if not pedido:
                return {
                    "sucesso": False,
                    "mensagem": f"Pedido {pedido_id} não encontrado ou não está pendente de impressão"
                }
            
            # Converte para formato da printer API
            pedido_data = self._converter_pedido_para_printer_format(pedido)
            
            # Envia para impressão
            resultado = await self.printer_client.imprimir_pedido(pedido_data)
            
            if resultado.get("sucesso"):
                # Marca como impresso (muda status para R)
                pedido.status = PedidoStatusEnum.R.value
                self.db.commit()
                
                logger.info(f"[PrinterIntegration] Pedido {pedido_id} impresso com sucesso")
                return {
                    "sucesso": True,
                    "mensagem": f"Pedido {pedido_id} impresso com sucesso",
                    "numero_pedido": pedido_id
                }
            else:
                logger.error(f"[PrinterIntegration] Falha ao imprimir pedido {pedido_id}: {resultado.get('mensagem')}")
                return resultado
                
        except Exception as e:
            logger.error(f"[PrinterIntegration] Erro ao imprimir pedido {pedido_id}: {str(e)}")
            return {
                "sucesso": False,
                "mensagem": f"Erro interno: {str(e)}"
            }
    
    async def imprimir_pedidos_pendentes(self, empresa_id: int, limite: Optional[int] = None) -> Dict[str, Any]:
        """
        Imprime todos os pedidos pendentes de impressão de uma empresa
        
        Args:
            empresa_id: ID da empresa
            limite: Número máximo de pedidos para imprimir por vez (usa config se None)
            
        Returns:
            Dict com resultado da operação
        """
        try:
            # Usa limite da configuração se não especificado
            limite_final = limite or PrinterConfig.get_max_pedidos()
            
            # Busca pedidos pendentes de impressão
            pedidos = self.db.query(PedidoDeliveryModel).filter(
                PedidoDeliveryModel.empresa_id == empresa_id,
                PedidoDeliveryModel.status == PedidoStatusEnum.I.value
            ).limit(limite_final).all()
            
            if not pedidos:
                return {
                    "sucesso": True,
                    "mensagem": "Nenhum pedido pendente de impressão encontrado",
                    "pedidos_impressos": 0
                }
            
            resultados = []
            sucessos = 0
            falhas = 0
            
            for pedido in pedidos:
                resultado = await self.imprimir_pedido(pedido.id)
                resultados.append({
                    "pedido_id": pedido.id,
                    "sucesso": resultado.get("sucesso", False),
                    "mensagem": resultado.get("mensagem", "Erro desconhecido")
                })
                
                if resultado.get("sucesso"):
                    sucessos += 1
                else:
                    falhas += 1
            
            return {
                "sucesso": falhas == 0,  # Sucesso total apenas se todos foram impressos
                "mensagem": f"Processados {len(pedidos)} pedidos: {sucessos} sucessos, {falhas} falhas",
                "pedidos_impressos": sucessos,
                "pedidos_falharam": falhas,
                "detalhes": resultados
            }
            
        except Exception as e:
            logger.error(f"[PrinterIntegration] Erro ao imprimir pedidos pendentes da empresa {empresa_id}: {str(e)}")
            return {
                "sucesso": False,
                "mensagem": f"Erro interno: {str(e)}",
                "pedidos_impressos": 0
            }
    
    async def verificar_conectividade(self) -> bool:
        """
        Verifica se a Printer API está acessível
        
        Returns:
            True se a API está funcionando, False caso contrário
        """
        return await self.printer_client.verificar_saude()
