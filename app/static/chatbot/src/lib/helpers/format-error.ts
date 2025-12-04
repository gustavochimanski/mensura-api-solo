/**
 * Formata mensagens de erro da API para exibição
 * Garante que sempre retorna uma string, mesmo quando a API retorna objetos
 *
 * @param error - Erro da API (pode ser string, array de erros Pydantic, etc)
 * @param defaultMessage - Mensagem padrão caso não consiga extrair o erro
 * @returns Mensagem de erro formatada como string
 */
export function formatErrorMessage(
  error: unknown,
  defaultMessage = 'Ocorreu um erro'
): string {
  // Se já é uma string, retorna direto
  if (typeof error === 'string') {
    return error
  }

  // Se é um objeto com propriedade detail
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail

    // detail é string
    if (typeof detail === 'string') {
      return detail
    }

    // detail é array de erros de validação (FastAPI/Pydantic)
    if (Array.isArray(detail)) {
      return detail
        .map((err: { msg?: string; loc?: string[] }) => {
          const campo = err.loc ? err.loc.join('.') : ''
          const msg = err.msg || 'Erro de validação'
          return campo ? `${campo}: ${msg}` : msg
        })
        .join(', ')
    }
  }

  if (
    error &&
    typeof error === 'object' &&
    'message' in error &&
    typeof (error as { message?: unknown }).message === 'string'
  ) {
    const errorObj = error as { message: string; field?: unknown }
    const { message } = errorObj
    const field = typeof errorObj.field === 'string' ? `${errorObj.field}: ` : ''
    return `${field}${message}`.trim()
  }

  // Se é um objeto Error padrão
  if (error instanceof Error) {
    return error.message
  }

  // Fallback: retorna mensagem padrão
  return defaultMessage
}
