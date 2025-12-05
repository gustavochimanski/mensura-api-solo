import type { PedidoStatus } from '@/types/pedido'

/**
 * Status que REQUEREM entregador vinculado
 * Obs.: 'A' (Aguardando Pagamento) só é utilizado no fluxo de delivery,
 * onde o Kanban exige validação de entregador ao mover para esta coluna.
 */
export const STATUS_COM_ENTREGADOR: PedidoStatus[] = ['S', 'A', 'E']

/**
 * Status que NÃO requerem entregador vinculado
 */
export const STATUS_SEM_ENTREGADOR: PedidoStatus[] = ['P', 'R']

/**
 * Verifica se um status requer entregador vinculado
 */
export function statusRequerEntregador(status: PedidoStatus): boolean {
  return STATUS_COM_ENTREGADOR.includes(status)
}

/**
 * Verifica se uma mudança de status requer vincular entregador
 * @param statusAtual - Status atual do pedido
 * @param novoStatus - Novo status para o qual o pedido será movido
 * @returns true se precisa vincular entregador
 */
export function precisaVincularEntregador(
  statusAtual: PedidoStatus,
  novoStatus: PedidoStatus
): boolean {
  // Se está indo de um status SEM entregador para um status COM entregador
  return (
    !statusRequerEntregador(statusAtual) && statusRequerEntregador(novoStatus)
  )
}

/**
 * Verifica se uma mudança de status permite desvincular entregador
 * @param statusAtual - Status atual do pedido
 * @param novoStatus - Novo status para o qual o pedido será movido
 * @returns true se pode desvincular entregador
 */
export function podeDesvincularEntregador(
  statusAtual: PedidoStatus,
  novoStatus: PedidoStatus
): boolean {
  // Se está voltando de um status COM entregador para um status SEM entregador
  return (
    statusRequerEntregador(statusAtual) && !statusRequerEntregador(novoStatus)
  )
}
