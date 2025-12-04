/**
 * Utilitários de máscaras para formatação de campos de formulário
 */

/**
 * Formata telefone brasileiro
 * Aceita celular (11 dígitos) ou fixo (10 dígitos)
 * @param value - Valor do campo
 * @returns Telefone formatado: (00) 00000-0000 ou (00) 0000-0000
 */
export function formatarTelefone(value: string): string {
  // Remove tudo que não é número
  const numbers = value.replace(/\D/g, '')

  // Aplica a máscara
  if (numbers.length <= 10) {
    // Formato: (00) 0000-0000
    return numbers
      .replace(/^(\d{2})(\d)/, '($1) $2')
      .replace(/(\d{4})(\d)/, '$1-$2')
  } else {
    // Formato: (00) 00000-0000
    return numbers
      .replace(/^(\d{2})(\d)/, '($1) $2')
      .replace(/(\d{5})(\d)/, '$1-$2')
      .slice(0, 15) // Limita o tamanho
  }
}

/**
 * Formata CPF brasileiro
 * @param value - Valor do campo
 * @returns CPF formatado: 000.000.000-00
 */
export function formatarCPF(value: string): string {
  // Remove tudo que não é número
  const numbers = value.replace(/\D/g, '')

  // Aplica a máscara: 000.000.000-00
  return numbers
    .replace(/^(\d{3})(\d)/, '$1.$2')
    .replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d{2})$/, '.$1-$2')
    .slice(0, 14) // Limita o tamanho
}

/**
 * Formata CNPJ brasileiro
 * @param value - Valor do campo
 * @returns CNPJ formatado: 00.000.000/0000-00
 */
export function formatarCNPJ(value: string): string {
  // Remove tudo que não é número
  const numbers = value.replace(/\D/g, '')

  // Aplica a máscara: 00.000.000/0000-00
  return numbers
    .replace(/^(\d{2})(\d)/, '$1.$2')
    .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1/$2')
    .replace(/(\d{4})(\d)/, '$1-$2')
    .slice(0, 18) // Limita o tamanho
}

/**
 * Formata CEP brasileiro
 * @param value - Valor do campo
 * @returns CEP formatado: 00000-000
 */
export function formatarCEP(value: string): string {
  // Remove tudo que não é número
  const numbers = value.replace(/\D/g, '')

  // Aplica a máscara: 00000-000
  return numbers.replace(/^(\d{5})(\d)/, '$1-$2').slice(0, 9)
}

/**
 * Formata valor monetário (R$)
 * @param value - Valor do campo
 * @returns Valor formatado: R$ 0.000,00
 */
export function formatarMoeda(value: string): string {
  // Remove tudo que não é número
  const numbers = value.replace(/\D/g, '')

  // Se vazio, retorna vazio
  if (!numbers) return ''

  // Converte para número com centavos
  const amount = parseInt(numbers) / 100

  // Formata como moeda brasileira
  return amount.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  })
}

/**
 * Formata número para porcentagem
 * @param value - Valor do campo
 * @returns Valor formatado: 00,00%
 */
export function formatarPorcentagem(value: string): string {
  // Remove tudo que não é número
  const numbers = value.replace(/\D/g, '')

  // Se vazio, retorna vazio
  if (!numbers) return ''

  // Converte para número com decimais
  const amount = parseInt(numbers) / 100

  // Formata com 2 casas decimais
  return amount.toFixed(2).replace('.', ',') + '%'
}

/**
 * Formata placa de veículo (Mercosul ou antiga)
 * @param value - Valor do campo
 * @returns Placa formatada: ABC-1234 ou ABC-1D23
 */
export function formatarPlaca(value: string): string {
  // Remove caracteres especiais, mantém letras e números
  const clean = value.replace(/[^A-Za-z0-9]/g, '').toUpperCase()

  // Aplica a máscara: ABC-1234 ou ABC-1D23
  return clean.replace(/^([A-Z]{3})([A-Z0-9]{1,4})$/, '$1-$2').slice(0, 8)
}

/**
 * Remove toda formatação de um valor
 * @param value - Valor formatado
 * @returns Apenas números
 */
export function removerMascara(value: string): string {
  return value.replace(/\D/g, '')
}

/**
 * Converte valor monetário formatado para número
 * @param value - Valor formatado: R$ 1.234,56
 * @returns Número: 1234.56
 */
export function moedaParaNumero(value: string): number {
  // Remove tudo que não é número
  const numbers = value.replace(/\D/g, '')

  // Se vazio, retorna 0
  if (!numbers) return 0

  // Converte para número com centavos
  return parseInt(numbers) / 100
}
