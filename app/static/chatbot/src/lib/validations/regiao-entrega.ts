import { z } from 'zod'
import { moedaParaNumero } from '@/lib/masks'

export const regiaoEntregaSchema = z
  .object({
    distanciaMaxKm: z.coerce
      .number()
      .refine((valor) => Number.isFinite(valor), {
        message: 'Quilometragem inválida',
      })
      .positive('Quilometragem máxima deve ser maior que zero'),
    taxaEntrega: z
      .string()
      .min(1, 'Taxa de entrega é obrigatória')
      .refine(
        (valor) => moedaParaNumero(valor) >= 0,
        'Taxa de entrega deve ser maior ou igual a zero'
      ),
    tempoEstimadoMin: z.coerce
      .number()
      .refine((valor) => typeof valor === 'number', {
        message: 'Tempo estimado é obrigatório',
      })
      .int('Informe um número inteiro de minutos')
      .positive('Tempo estimado deve ser maior que zero'),
  })

export type RegiaoEntregaFormData = z.infer<typeof regiaoEntregaSchema>
