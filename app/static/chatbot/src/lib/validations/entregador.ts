import { z } from 'zod'

export const entregadorSchema = z.object({
  nome: z.string().min(1, 'Nome é obrigatório'),
  telefone: z.string().min(1, 'Telefone é obrigatório'),
  documento: z.string().min(1, 'Documento é obrigatório'),
  veiculo_tipo: z.string().min(1, 'Tipo de Veículo é obrigatório'),
  placa: z.string().min(1, 'Placa é obrigatória'),
  acrescimo_taxa: z.any(),
  valor_diaria: z.any(),
})

export type EntregadorFormData = z.infer<typeof entregadorSchema>
