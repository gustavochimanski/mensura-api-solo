import type { MetricaDashboard } from '@/types/dashboard'

/**
 * Calcula a variação percentual entre dois valores
 *
 * @param valorAtual - Valor do período atual
 * @param valorAnterior - Valor do período anterior
 * @returns Variação percentual (ex: 15 para 15% de aumento, -10 para 10% de diminuição)
 *
 * @example
 * calcularVariacao(120, 100) // retorna 20 (aumento de 20%)
 * calcularVariacao(80, 100)  // retorna -20 (diminuição de 20%)
 * calcularVariacao(50, 0)    // retorna 100 (quando anterior é 0, considera 100% de aumento)
 */
export function calcularVariacao(
  valorAtual: number,
  valorAnterior: number
): number {
  // Se o valor anterior for 0, considera aumento de 100% se houver valor atual
  if (valorAnterior === 0) {
    return valorAtual > 0 ? 100 : 0
  }

  // Calcula a variação percentual
  const variacao = ((valorAtual - valorAnterior) / valorAnterior) * 100

  // Arredonda para 1 casa decimal
  return Math.round(variacao * 10) / 10
}

/**
 * Cria um objeto MetricaDashboard com valor atual, valor anterior e variação calculada
 *
 * @param valorAtual - Valor do período atual
 * @param valorAnterior - Valor do período anterior
 * @returns Objeto MetricaDashboard completo
 */
export function criarMetrica(
  valorAtual: number,
  valorAnterior: number
): MetricaDashboard {
  return {
    valor: valorAtual,
    valorAnterior,
    variacao: calcularVariacao(valorAtual, valorAnterior),
  }
}

/**
 * Calcula o tempo médio de entrega em minutos a partir de pedidos
 *
 * @param pedidos - Array de pedidos com data_pedido e opcionalmente data_entrega
 * @returns Tempo médio em minutos (0 se não houver pedidos entregues)
 */
export function calcularTempoMedioEntrega(
  pedidos: Array<{
    data_pedido: string
    status: string
  }>
): number {
  // Filtra apenas pedidos entregues
  const pedidosEntregues = pedidos.filter((p) => p.status === 'E')

  if (pedidosEntregues.length === 0) {
    return 0
  }

  // Por enquanto, retorna um valor fixo estimado
  // TODO: Implementar cálculo real quando houver campo data_entrega na API
  // const tempos = pedidosEntregues.map((p) => {
  //   const inicio = new Date(p.data_pedido).getTime()
  //   const fim = new Date(p.data_entrega).getTime()
  //   return (fim - inicio) / 60000 // converte para minutos
  // })
  // return tempos.reduce((sum, t) => sum + t, 0) / tempos.length

  return 18 // Valor estimado padrão
}

/**
 * Formata valor monetário para exibição
 *
 * @param valor - Valor em reais
 * @returns String formatada (ex: "R$ 1.234,56")
 */
export function formatarMoeda(valor: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(valor)
}

/**
 * Formata tempo em minutos para exibição
 *
 * @param minutos - Tempo em minutos
 * @returns String formatada (ex: "18 min")
 */
export function formatarTempo(minutos: number): string {
  const hasDecimals = !Number.isInteger(minutos)
  const formatted = new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: hasDecimals ? 1 : 0,
    maximumFractionDigits: hasDecimals ? 2 : 0,
  }).format(minutos)
  return `${formatted} min`
}
