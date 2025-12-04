import { z } from 'zod'

/**
 * Schema de validação para criar/atualizar cupom
 */
export const cupomSchema = z
  .object({
    codigo: z
      .string()
      .min(1, 'Código é obrigatório')
      .max(50, 'Código muito longo')
      .regex(/^[A-Z0-9]+$/, 'Use apenas letras maiúsculas e números'),
    descricao: z.string().max(500, 'Descrição muito longa').optional(),
    desconto_valor: z.number().min(0, 'Valor deve ser positivo').optional().nullable(),
    desconto_percentual: z
      .number()
      .min(0, 'Percentual deve ser entre 0 e 100')
      .max(100, 'Percentual deve ser entre 0 e 100')
      .optional()
      .nullable(),
    ativo: z.boolean().default(true),
    validade_inicio: z.string().optional(),
    validade_fim: z.string().optional(),
    monetizado: z.boolean().default(false),
    valor_por_lead: z.number().min(0, 'Valor deve ser positivo').optional().nullable(),
    link_redirecionamento: z.string().url('Link inválido').optional().or(z.literal('')),
    parceiro_id: z.number().optional().nullable(),
    empresa_ids: z.array(z.number()).default([]),
  })
  .refine(
    (data) => {
      // Se monetizado, empresa_ids deve ter pelo menos 1 empresa
      if (data.monetizado && data.empresa_ids.length === 0) {
        return false
      }
      return true
    },
    {
      message: 'Cupom monetizado deve ter pelo menos 1 empresa selecionada',
      path: ['empresa_ids'],
    }
  )
  .refine(
    (data) => {
      // Deve ter pelo menos um tipo de desconto
      if (!data.desconto_valor && !data.desconto_percentual) {
        return false
      }
      return true
    },
    {
      message: 'Informe desconto em valor ou percentual',
      path: ['desconto_valor'],
    }
  )

export type CupomFormData = z.infer<typeof cupomSchema>
