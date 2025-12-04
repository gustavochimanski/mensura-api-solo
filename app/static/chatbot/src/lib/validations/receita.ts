import { z } from 'zod'

export const ingredienteSchema = z.object({
  produto_cod_barras: z.string().min(1, 'Código de barras do produto é obrigatório'),
  ingrediente_cod_barras: z.string().min(1, 'Código de barras do ingrediente é obrigatório'),
  quantidade: z.number().nonnegative('Quantidade deve ser maior ou igual a zero').nullable().optional(),
  unidade: z.string().max(10, 'Unidade deve ter no máximo 10 caracteres').nullable().optional(),
})

export const adicionalSchema = z.object({
  adicional_id: z
    .number({
      required_error: 'Adicional é obrigatório',
      invalid_type_error: 'Adicional é obrigatório',
    })
    .int('Adicional inválido')
    .positive('Adicional inválido'),
})

export const atualizarIngredienteSchema = z.object({
  quantidade: z.number().nonnegative('Quantidade deve ser maior ou igual a zero').nullable().optional(),
  unidade: z.string().max(10, 'Unidade deve ter no máximo 10 caracteres').nullable().optional(),
})

export type IngredienteFormData = z.infer<typeof ingredienteSchema>
export type AdicionalFormData = z.infer<typeof adicionalSchema>
export type AtualizarIngredienteFormData = z.infer<typeof atualizarIngredienteSchema>
