import { z } from "zod"

export const loginSchema = z.object({
  username: z.string().min(1, "Usuário obrigatório"),
  password: z.string().min(1, "Senha obrigatória"),
  remember: z.boolean().optional().default(false),
})

export type LoginFormData = z.infer<typeof loginSchema>
