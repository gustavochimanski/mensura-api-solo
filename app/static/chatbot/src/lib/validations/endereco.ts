import { z } from 'zod'

/**
 * Schema de validação para endereço completo
 */
export const enderecoSchema = z.object({
  logradouro: z.string().min(1, 'Logradouro é obrigatório'),
  numero: z.string().optional(),
  complemento: z.string().optional(),
  bairro: z.string().min(1, 'Bairro é obrigatório'),
  cidade: z.string().min(1, 'Cidade é obrigatória'),
  estado: z.string().min(2, 'Estado é obrigatório').max(2, 'Use a sigla do estado'),
  cep: z
    .string()
    .min(1, 'CEP é obrigatório')
    .regex(/^\d{5}-?\d{3}$/, 'CEP inválido (formato: 12345-678)'),
  ponto_referencia: z.string().optional(),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
})

export type EnderecoFormData = z.infer<typeof enderecoSchema>
