import { z } from 'zod'

/**
 * Schema de validação para criar/atualizar parceiro
 */
export const parceiroSchema = z.object({
  nome: z.string().min(1, 'Nome é obrigatório').max(255, 'Nome muito longo'),
  ativo: z.boolean().default(true),
})

export type ParceiroFormData = z.infer<typeof parceiroSchema>
