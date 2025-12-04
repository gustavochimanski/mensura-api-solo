import { z } from 'zod'

export const vitrineSchema = z.object({
  cod_categoria: z
    .union([z.number(), z.nan()])
    .optional()
    .transform((val) => (val === undefined || isNaN(val) ? undefined : val)),
  titulo: z.string().min(1, 'Título é obrigatório'),
  ordem: z
    .union([z.number(), z.nan()])
    .optional()
    .transform((val) => (val === undefined || isNaN(val) ? undefined : val)),
  is_home: z.boolean().optional(),
})

export type VitrineFormData = z.infer<typeof vitrineSchema>
