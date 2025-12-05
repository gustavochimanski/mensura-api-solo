import { z } from 'zod'

export const clienteSchema = z.object({
  nome: z.string().min(1, 'Nome é obrigatório'),
  cpf: z.string().optional(),
  telefone: z.string().min(1, 'Telefone é obrigatório'),
  email: z
    .string()
    .optional()
    .refine(
      (val) => !val || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val),
      'Email inválido'
    ),
  data_nascimento: z.string().optional().or(z.literal('')),
  ativo: z.boolean().optional().default(true),
})

export type ClienteFormData = z.infer<typeof clienteSchema>
