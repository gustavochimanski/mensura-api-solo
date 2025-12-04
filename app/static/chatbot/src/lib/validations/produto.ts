import { z } from 'zod'

export const produtoSchema = z.object({
  cod_barras: z.string().optional(),
  descricao: z.string().min(1, 'Descrição é obrigatória'),
  preco_venda: z
    .union([z.number(), z.nan()])
    .transform((val) => (Number.isNaN(val) ? undefined : val))
    .pipe(z.number().min(0, 'Preço de venda deve ser maior ou igual a 0'))
    .optional(),
  custo: z
    .union([z.number(), z.nan()])
    .transform((val) => (Number.isNaN(val) ? undefined : val))
    .pipe(z.number().min(0, 'Custo deve ser maior ou igual a 0'))
    .optional(),
  cod_categoria: z
    .union([z.number(), z.nan()])
    .transform((val) => (Number.isNaN(val) ? undefined : val))
    .pipe(z.number().min(1, 'Categoria é obrigatória'))
    .optional(),
  disponivel: z.boolean().optional(),
  exibir_delivery: z.boolean().optional(),
  imagem: z.instanceof(File).optional(),
  diretivas: z.array(z.string()).optional().nullable(),
})

export type ProdutoFormData = z.infer<typeof produtoSchema>
