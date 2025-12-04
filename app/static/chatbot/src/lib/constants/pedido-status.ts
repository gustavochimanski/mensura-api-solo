import type { PedidoStatus } from '@/types/pedido'

type PedidoStatusConfig = {
  label: string
  color: string
  textColor: string
  badgeColor: string
}

// Configuração visual e de texto para cada status de pedido
export const PEDIDO_STATUS: Record<PedidoStatus, PedidoStatusConfig> = {
  P: {
    label: 'Pendente',
    color: 'bg-yellow-500',
    textColor: 'text-white',
    badgeColor: 'text-yellow-500',
  },
  I: {
    label: 'Pendente Impressão',
    color: 'bg-blue-500',
    textColor: 'text-white',
    badgeColor: 'text-blue-500',
  },
  R: {
    label: 'Em Preparo',
    color: 'bg-purple-600',
    textColor: 'text-white',
    badgeColor: 'text-purple-600',
  },
  S: {
    label: 'Em Rota de Entrega',
    color: 'bg-orange-500',
    textColor: 'text-white',
    badgeColor: 'text-orange-500',
  },
  E: {
    label: 'Entregue',
    color: 'bg-green-500',
    textColor: 'text-white',
    badgeColor: 'text-green-500',
  },
  C: {
    label: 'Cancelados',
    color: 'bg-red-600',
    textColor: 'text-white',
    badgeColor: 'text-red-600',
  },
  D: {
    label: 'Editado',
    color: 'bg-orange-500',
    textColor: 'text-white',
    badgeColor: 'text-orange-500',
  },
  X: {
    label: 'Em Edição',
    color: 'bg-slate-700',
    textColor: 'text-white',
    badgeColor: 'text-slate-700',
  },
  A: {
    label: 'Aguardando Pagamento',
    color: 'bg-gray-500',
    textColor: 'text-white',
    badgeColor: 'text-gray-500',
  },
  T: {
    label: 'Pronto',
    color: 'bg-emerald-500',
    textColor: 'text-white',
    badgeColor: 'text-emerald-500',
  },
}

// Ordem de exibição das colunas no Kanban
export const STATUS_ORDER: PedidoStatus[] = ['P', 'R', 'S', 'E', 'C']
