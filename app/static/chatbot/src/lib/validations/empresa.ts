import { z } from 'zod'

const enderecoSchema = z.object({
  cep: z.string().optional().or(z.literal('')),
  logradouro: z.string().optional().or(z.literal('')),
  numero: z.string().optional().or(z.literal('')),
  complemento: z.string().optional(),
  bairro: z.string().optional().or(z.literal('')),
  cidade: z.string().optional().or(z.literal('')),
  estado: z
    .string()
    .optional()
    .or(z.literal(''))
    .refine((value) => !value || value.length === 2, {
      message: 'Estado deve ter 2 caracteres',
    }),
  latitude: z
    .union([z.number(), z.nan()])
    .optional()
    .transform((val) => (val === undefined || isNaN(val) ? undefined : val)),
  longitude: z
    .union([z.number(), z.nan()])
    .optional()
    .transform((val) => (val === undefined || isNaN(val) ? undefined : val)),
})

export const empresaSchema = z.object({
  nome: z.string().min(1, 'Nome é obrigatório'),
  cnpj: z.string().optional(),
  cardapio_link: z.string().url('Link inválido').optional().or(z.literal('')),
  cardapio_tema: z.string().optional(), // Agora aceita qualquer string (formato oklch)
  aceita_pedido_automatico: z.boolean().optional(),
  tempo_entrega_maximo: z
    .union([z.number(), z.nan()])
    .optional()
    .transform((val) => (val === undefined || isNaN(val) ? undefined : val)),
  endereco: enderecoSchema.optional(),
})

export type EmpresaFormData = z.infer<typeof empresaSchema>
