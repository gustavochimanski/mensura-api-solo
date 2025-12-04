import { z } from 'zod'

export const meioPagamentoSchema = z.object({
  nome: z.string().min(1, 'Nome é obrigatório'),
  tipo: z.enum([
    'CARTAO_ENTREGA',
    'PIX_ENTREGA',
    'DINHEIRO',
    'CARTAO_ONLINE',
    'PIX_ONLINE',
  ]),
  ativo: z.boolean(),
})

export type MeioPagamentoFormData = z.infer<typeof meioPagamentoSchema>
