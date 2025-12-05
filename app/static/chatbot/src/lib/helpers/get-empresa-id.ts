import { getCurrentUser } from '@/actions/auth/get-current-user'
import { redirect } from 'next/navigation'

/**
 * Obtém o empresa_id do usuário autenticado
 *
 * Se o usuário não estiver autenticado, redireciona para a página de login
 * Se o usuário não tiver empresa vinculada válida, retorna 1 como fallback
 *
 * @returns O ID da primeira empresa vinculada ao usuário ou 1 como fallback
 */
export async function getEmpresaId(): Promise<number> {
  const user = await getCurrentUser()

  if (!user) {
    redirect('/login')
  }

  // Verifica se o usuário tem empresas vinculadas e válidas (> 0)
  if (
    !user.empresa_ids ||
    user.empresa_ids.length === 0 ||
    !user.empresa_ids[0] ||
    user.empresa_ids[0] === 0
  ) {
    // Fallback para empresa_id 1 (padrão para usuários sem empresa específica)
    return 1
  }

  // Retorna a primeira empresa do array
  return user.empresa_ids[0]
}

/**
 * Obtém o empresa_id do usuário autenticado (versão segura)
 *
 * Retorna null se o usuário não estiver autenticado ou não tiver empresa
 *
 * @returns O ID da primeira empresa vinculada ou null
 */
export async function getEmpresaIdSafe(): Promise<number | null> {
  const user = await getCurrentUser()

  if (!user || !user.empresa_ids || user.empresa_ids.length === 0) {
    return null
  }

  return user.empresa_ids[0]
}

/**
 * Obtém todos os IDs de empresas do usuário autenticado
 *
 * @returns Array com IDs de todas as empresas vinculadas
 */
export async function getAllEmpresaIds(): Promise<number[]> {
  const user = await getCurrentUser()

  if (!user) {
    redirect('/login')
  }

  return user.empresa_ids || []
}
