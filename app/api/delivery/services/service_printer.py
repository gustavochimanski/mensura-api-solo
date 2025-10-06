"""
Service para lógica de negócio relacionada à Printer API
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.api.delivery.repositories.repo_printer import PrinterRepository
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.delivery.schemas.schema_printer import (
    PedidoPrinterRequest, 
    RespostaImpressaoPrinter, 
    PedidoPendenteImpressaoResponse,
    DadosEmpresaPrinter
)
from app.api.delivery.schemas.schema_shared_enums import PedidoStatusEnum
from app.utils.printer_client import PrinterClient
# Configuração da impressora removida - será gerenciada pelo gestor
from app.utils.logger import logger


class PrinterService:
    """Service para operações de impressão"""
    
    def __init__(self, db: Session, printer_api_url: Optional[str] = None):
        self.db = db
        self.repo = PrinterRepository(db)
        self.empresa_repo = EmpresaRepository(db)
        self.printer_client = PrinterClient(
            printer_api_url or "http://localhost:3001"
        )
    
    def _buscar_dados_empresa(self, empresa_id: int) -> DadosEmpresaPrinter:
        """
        Busca dados da empresa para impressão
        
        Args:
            empresa_id: ID da empresa
            
        Returns:
            Dados da empresa formatados para impressão
        """
        try:
            empresa = self.empresa_repo.get_empresa_by_id(empresa_id)
            
            if not empresa:
                logger.warning(f"[PrinterService] Empresa {empresa_id} não encontrada")
                return DadosEmpresaPrinter()
            
            # Monta endereço completo
            endereco_completo = None
            if empresa.endereco:
                endereco_parts = []
                if empresa.endereco.logradouro:
                    endereco_parts.append(empresa.endereco.logradouro)
                if empresa.endereco.numero:
                    endereco_parts.append(empresa.endereco.numero)
                if empresa.endereco.complemento:
                    endereco_parts.append(empresa.endereco.complemento)
                if empresa.endereco.bairro:
                    endereco_parts.append(empresa.endereco.bairro)
                if empresa.endereco.cidade:
                    endereco_parts.append(empresa.endereco.cidade)
                if empresa.endereco.estado:
                    endereco_parts.append(empresa.endereco.estado)
                if empresa.endereco.cep:
                    endereco_parts.append(f"CEP: {empresa.endereco.cep}")
                
                endereco_completo = ", ".join(endereco_parts) if endereco_parts else None
            
            dados_empresa = DadosEmpresaPrinter(
                cnpj=empresa.cnpj,
                endereco=endereco_completo,
                telefone=empresa.telefone
            )
            
            return dados_empresa
            
        except Exception as e:
            logger.error(f"[PrinterService] Erro ao buscar dados da empresa {empresa_id}: {str(e)}")
            return DadosEmpresaPrinter()
    
    def _formatar_dados_empresa_do_pedido(self, empresa) -> DadosEmpresaPrinter:
        """
        Formata dados da empresa a partir do objeto empresa do pedido
        
        Args:
            empresa: Objeto empresa do pedido
            
        Returns:
            Dados da empresa formatados para impressão
        """
        try:
            # Monta endereço completo
            endereco_completo = None
            if empresa.endereco:
                endereco_parts = []
                if empresa.endereco.logradouro:
                    endereco_parts.append(empresa.endereco.logradouro)
                if empresa.endereco.numero:
                    endereco_parts.append(empresa.endereco.numero)
                if empresa.endereco.complemento:
                    endereco_parts.append(empresa.endereco.complemento)
                if empresa.endereco.bairro:
                    endereco_parts.append(empresa.endereco.bairro)
                if empresa.endereco.cidade:
                    endereco_parts.append(empresa.endereco.cidade)
                if empresa.endereco.estado:
                    endereco_parts.append(empresa.endereco.estado)
                if empresa.endereco.cep:
                    endereco_parts.append(f"CEP: {empresa.endereco.cep}")
                
                endereco_completo = ", ".join(endereco_parts) if endereco_parts else None
            
            dados_empresa = DadosEmpresaPrinter(
                cnpj=empresa.cnpj,
                endereco=endereco_completo,
                telefone=empresa.telefone
            )
            
            return dados_empresa
            
        except Exception as e:
            logger.error(f"[PrinterService] Erro ao formatar dados da empresa: {str(e)}")
            return DadosEmpresaPrinter()
    
    
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
            status=pedido_impressao.status,
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
            endereco=pedido_impressao.endereco,
            data_criacao=pedido_impressao.data_criacao
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
    
    def get_pedidos_pendentes_para_impressao(self, empresa_id: int, limite: Optional[int] = None) -> List[PedidoPendenteImpressaoResponse]:
        """
        Busca pedidos pendentes de impressão formatados para o endpoint GET
        Inclui pedidos com status 'I' (PENDENTE_IMPRESSAO) e 'D' (EM_EDICAO)
        
        Args:
            empresa_id: ID da empresa
            limite: Número máximo de pedidos
            
        Returns:
            Lista de pedidos formatados para impressão com status incluído
        """
        try:
            # Busca pedidos pendentes (já com relacionamento empresa carregado)
            pedidos = self.repo.get_pedidos_pendentes_impressao(empresa_id, limite)
            
            # Busca dados da empresa uma única vez (usando o primeiro pedido se disponível)
            dados_empresa = None
            if pedidos:
                primeiro_pedido = pedidos[0]
                if hasattr(primeiro_pedido, 'empresa') and primeiro_pedido.empresa:
                    dados_empresa = self._formatar_dados_empresa_do_pedido(primeiro_pedido.empresa)
                else:
                    logger.warning(f"[PrinterService] Pedido {primeiro_pedido.id} não tem empresa carregada, buscando separadamente")
                    dados_empresa = self._buscar_dados_empresa(empresa_id)
            else:
                dados_empresa = self._buscar_dados_empresa(empresa_id)
            
            resultados = []
            for pedido in pedidos:
                # Converte pedido para formato de impressão
                pedido_impressao = self.repo.converter_pedido_para_impressao(pedido)
                
                # Determina tipo de pagamento
                tipo_pagamento = "DINHEIRO"  # Padrão
                if pedido_impressao.meio_pagamento_descricao:
                    tipo_pagamento = pedido_impressao.meio_pagamento_descricao.upper()
                
                # Calcula troco se necessário (simplificado)
                troco = None
                if tipo_pagamento == "DINHEIRO":
                    # Aqui você pode implementar lógica para calcular troco baseado no valor pago
                    # Por enquanto, vamos usar o valor do pedido como referência
                    troco = pedido_impressao.valor_total
                
                # Cria resposta formatada usando os dados do pedido original
                resultado = PedidoPendenteImpressaoResponse(
                    numero=pedido_impressao.id,
                    status=pedido_impressao.status,
                    cliente=pedido_impressao.cliente_nome,
                    telefone_cliente=pedido_impressao.cliente_telefone,
                    itens=pedido_impressao.itens,
                    subtotal=float(pedido.subtotal or 0),
                    desconto=float(pedido.desconto or 0),
                    taxa_entrega=float(pedido.taxa_entrega or 0),
                    taxa_servico=float(pedido.taxa_servico or 0),
                    total=pedido_impressao.valor_total,
                    tipo_pagamento=tipo_pagamento,
                    troco=troco,
                    observacao_geral=pedido_impressao.observacao_geral,
                    endereco=pedido_impressao.endereco,
                    data_criacao=pedido_impressao.data_criacao,
                    empresa=dados_empresa or DadosEmpresaPrinter()
                )
                
                resultados.append(resultado)
            
            return resultados
            
        except Exception as e:
            logger.error(f"[PrinterService] Erro ao buscar pedidos pendentes da empresa {empresa_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao buscar pedidos pendentes: {str(e)}"
            )
