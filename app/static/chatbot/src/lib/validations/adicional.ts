import { z } from 'zod'

export const adicionalSchema = z.object({
  empresa_id: z.number().min(1, 'Empresa é obrigatória'),
  nome: z.string().min(1, 'Nome é obrigatório'),
  descricao: z.string().optional().nullable(),
  preco: z.number().min(0, 'Preço deve ser maior ou igual a zero'),
  ativo: z.boolean().optional().default(true),
  obrigatorio: z.boolean().optional().default(false),
  permite_multipla_escolha: z.boolean().optional().default(false),
  ordem: z.number().int().min(0, 'Ordem deve ser maior ou igual a zero').optional().default(0),
})

export type AdicionalFormData = z.infer<typeof adicionalSchema>

