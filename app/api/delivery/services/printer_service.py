"""
Service para lógica de negócio relacionada à Printer API
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.api.delivery.repositories.repo_printer import PrinterRepository
from app.api.delivery.schemas.schema_printer import (
    PedidoPrinterRequest, 
    RespostaImpressaoPrinter, 
    RespostaImpressaoMultipla,
    StatusPrinterResponse,
    ConfigImpressaoPrinter,
    ImpressaoMultiplaRequest
)
from app.api.delivery.schemas.schema_shared_enums import PedidoStatusEnum
from app.utils.printer_client import PrinterClient
from app.config.printer_config import PrinterConfig
from app.utils.logger import logger


class PrinterService:
    """Service para operações de impressão"""
    
    def __init__(self, db: Session, printer_api_url: Optional[str] = None):
        self.db = db
        self.repo = PrinterRepository(db)
        self.printer_client = PrinterClient(
            printer_api_url or PrinterConfig.get_printer_url()
        )
    
    def _converter_pedido_para_printer_request(self, pedido_impressao) -> PedidoPrinterRequest:
        """
        Converte pedido formatado para impressão em request da Printer API
        
        Args:
            pedido_impressao: Pedido formatado para impressão
            
        Returns:
            Request formatado para Printer API
        """
        # Determina tipo de pagamento
        tipo_pagamento = "DINHEIRO"  # Padrão
        if pedido_impressao.meio_pagamento_descricao:
            tipo_pagamento = pedido_impressao.meio_pagamento_descricao.upper()
        
        # Calcula troco se necessário
        troco = None
        if tipo_pagamento == "DINHEIRO":
            # Aqui você pode implementar lógica para calcular troco baseado no valor pago
            # Por enquanto, vamos usar o valor do pedido como referência
            troco = pedido_impressao.valor_total
        
        return PedidoPrinterRequest(
            numero=pedido_impressao.id,
            cliente=pedido_impressao.cliente_nome,
            telefone_cliente=pedido_impressao.cliente_telefone,
            itens=pedido_impressao.itens,
            subtotal=pedido_impressao.valor_total,  # Simplificado - pode ser calculado dos itens
            desconto=0.0,  # Pode ser implementado posteriormente
            taxa_entrega=0.0,  # Pode ser implementado posteriormente
            taxa_servico=0.0,  # Pode ser implementado posteriormente
            total=pedido_impressao.valor_total,
            tipo_pagamento=tipo_pagamento,
            troco=troco,
            observacao_geral=pedido_impressao.observacao_geral,
            endereco=pedido_impressao.endereco_cliente,
            data_criacao=pedido_impressao.data_criacao
        )
    
    
    async def imprimir_pedidos_pendentes(
        self, 
        empresa_id: int, 
        limite: Optional[int] = None,
        config: Optional[ConfigImpressaoPrinter] = None
    ) -> RespostaImpressaoMultipla:
        """
        Imprime todos os pedidos pendentes de impressão de uma empresa
        
        Args:
            empresa_id: ID da empresa
            limite: Número máximo de pedidos para imprimir
            config: Configurações de impressão opcionais
            
        Returns:
            Resposta da operação de impressão múltipla
        """
        try:
            # Usa limite da configuração se não especificado
            limite_final = limite or PrinterConfig.get_max_pedidos()
            
            # Busca pedidos pendentes
            pedidos = self.repo.get_pedidos_pendentes_impressao(empresa_id, limite_final)
            
            if not pedidos:
                return RespostaImpressaoMultipla(
                    sucesso=True,
                    mensagem="Nenhum pedido pendente de impressão encontrado",
                    pedidos_impressos=0,
                    pedidos_falharam=0
                )
            
            resultados = []
            sucessos = 0
            falhas = 0
            
            for pedido in pedidos:
                resultado = await self.imprimir_pedido(pedido.id, config)
                resultados.append(resultado)
                
                if resultado.sucesso:
                    sucessos += 1
                else:
                    falhas += 1
            
            return RespostaImpressaoMultipla(
                sucesso=falhas == 0,  # Sucesso total apenas se todos foram impressos
                mensagem=f"Processados {len(pedidos)} pedidos: {sucessos} sucessos, {falhas} falhas",
                pedidos_impressos=sucessos,
                pedidos_falharam=falhas,
                detalhes=resultados
            )
            
        except Exception as e:
            logger.error(f"[PrinterService] Erro ao imprimir pedidos pendentes da empresa {empresa_id}: {str(e)}")
            return RespostaImpressaoMultipla(
                sucesso=False,
                mensagem=f"Erro interno: {str(e)}",
                pedidos_impressos=0,
                pedidos_falharam=0
            )
    
    async def verificar_status_printer(self) -> StatusPrinterResponse:
        """
        Verifica se a Printer API está funcionando
        
        Returns:
            Status da Printer API
        """
        try:
            conectado = await self.printer_client.verificar_saude()
            
            return StatusPrinterResponse(
                conectado=conectado,
                mensagem="Printer API funcionando" if conectado else "Printer API não acessível"
            )
            
        except Exception as e:
            logger.error(f"[PrinterService] Erro ao verificar status da Printer API: {str(e)}")
            return StatusPrinterResponse(
                conectado=False,
                mensagem=f"Erro ao verificar status: {str(e)}"
            )
    
    def listar_pedidos_pendentes_impressao(self, empresa_id: int, limite: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Lista pedidos pendentes de impressão formatados para o admin
        
        Args:
            empresa_id: ID da empresa
            limite: Número máximo de pedidos
            
        Returns:
            Lista de pedidos formatados com itens incluídos
        """
        try:
            pedidos = self.repo.get_pedidos_pendentes_impressao(empresa_id, limite)
            
            resultados = []
            for pedido in pedidos:
                pedido_impressao = self.repo.converter_pedido_para_impressao(pedido)
                
                # Converte itens para formato de dicionário
                itens_formatados = []
                for item in pedido_impressao.itens:
                    itens_formatados.append({
                        "descricao": item.descricao,
                        "quantidade": item.quantidade,
                        "preco": item.preco,
                        "observacao": item.observacao
                    })
                
                resultados.append({
                    "id": pedido_impressao.id,
                    "status": pedido_impressao.status,
                    "cliente_nome": pedido_impressao.cliente_nome,
                    "cliente_telefone": pedido_impressao.cliente_telefone,
                    "valor_total": pedido_impressao.valor_total,
                    "data_criacao": pedido_impressao.data_criacao,
                    "endereco_cliente": pedido_impressao.endereco_cliente,
                    "meio_pagamento_descricao": pedido_impressao.meio_pagamento_descricao,
                    "observacao_geral": pedido_impressao.observacao_geral,
                    "quantidade_itens": len(pedido_impressao.itens),
                    "itens": itens_formatados
                })
            
            return resultados
            
        except Exception as e:
            logger.error(f"[PrinterService] Erro ao listar pedidos pendentes da empresa {empresa_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao listar pedidos pendentes: {str(e)}"
            )
    
    def get_estatisticas_impressao(self, empresa_id: int) -> Dict[str, Any]:
        """
        Retorna estatísticas de impressão para uma empresa
        
        Args:
            empresa_id: ID da empresa
            
        Returns:
            Dicionário com estatísticas
        """
        try:
            return self.repo.get_estatisticas_impressao(empresa_id)
            
        except Exception as e:
            logger.error(f"[PrinterService] Erro ao obter estatísticas da empresa {empresa_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao obter estatísticas: {str(e)}"
            )
    
    def marcar_pedido_impresso_manual(self, pedido_id: int) -> RespostaImpressaoPrinter:
        """
        Marca um pedido como impresso manualmente (sem usar Printer API)
        
        Args:
            pedido_id: ID do pedido
            
        Returns:
            Resposta da operação
        """
        try:
            if self.repo.marcar_pedido_impresso(pedido_id):
                return RespostaImpressaoPrinter(
                    sucesso=True,
                    mensagem=f"Pedido {pedido_id} marcado como impresso manualmente",
                    numero_pedido=pedido_id
                )
            else:
                return RespostaImpressaoPrinter(
                    sucesso=False,
                    mensagem=f"Falha ao marcar pedido {pedido_id} como impresso",
                    numero_pedido=pedido_id
                )
                
        except Exception as e:
            logger.error(f"[PrinterService] Erro ao marcar pedido {pedido_id} como impresso manualmente: {str(e)}")
            return RespostaImpressaoPrinter(
                sucesso=False,
                mensagem=f"Erro interno: {str(e)}",
                numero_pedido=pedido_id
            )
