import { z } from 'zod'

export const categoriaSchema = z.object({
  descricao: z.string().min(1, 'Descrição é obrigatória'),
  slug: z.string().optional(),
  parent_id: z
    .union([z.number(), z.nan()])
    .optional()
    .transform((val) => (val === undefined || isNaN(val) ? undefined : val)),
  posicao: z
    .union([z.number(), z.nan()])
    .optional()
    .transform((val) => (val === undefined || isNaN(val) ? undefined : val)),
  imagem: z.any().optional(),
})

export type CategoriaFormData = z.infer<typeof categoriaSchema>
