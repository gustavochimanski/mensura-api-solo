import { z } from 'zod'

/**
 * Schema de validação para criar/atualizar banner
 */
export const bannerSchema = z
  .object({
    nome: z.string().min(1, 'Nome é obrigatório').max(255, 'Nome muito longo'),
    ativo: z.boolean().default(true),
    tipo_banner: z.enum(['V', 'H'], {
      message: 'Tipo deve ser V (Vertical) ou H (Horizontal)',
    }),
    redireciona_categoria: z.boolean().default(true),
    categoria_id: z.number().optional().nullable(),
    href_destino: z.string().optional().or(z.literal('')),
  })
  .superRefine((data, ctx) => {
    if (data.redireciona_categoria) {
      if (!data.categoria_id || data.categoria_id <= 0) {
        ctx.addIssue({
          path: ['categoria_id'],
          code: z.ZodIssueCode.custom,
          message: 'Selecione uma categoria',
        })
      }
    }
  })

export type BannerFormData = z.infer<typeof bannerSchema>
