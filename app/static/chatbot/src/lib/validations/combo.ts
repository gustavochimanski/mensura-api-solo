import { z } from 'zod'

export const comboItemSchema = z.object({
  produto_cod_barras: z.string().min(1, 'Código de barras é obrigatório'),
  quantidade: z.number().int().min(1, 'Quantidade deve ser maior que zero'),
})

export const comboSchema = z.object({
  empresa_id: z.number().min(1, 'Empresa é obrigatória'),
  titulo: z.string().min(1, 'Título é obrigatório'),
  descricao: z.string().optional(),
  preco_total: z.number().min(0, 'Preço total deve ser maior ou igual a zero'),
  ativo: z.boolean().optional().default(true),
  itens: z
    .array(comboItemSchema)
    .min(1, 'Combo deve ter pelo menos um item'),
  tempo_local: z.number().optional(),
  tempo_delivery: z.number().optional(),
})

export type ComboFormData = z.infer<typeof comboSchema>

