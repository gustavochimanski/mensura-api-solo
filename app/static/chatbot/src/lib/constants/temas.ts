export const TEMAS_CARDAPIO = [
  { value: 'tema1', label: 'Vermelho', color: 'oklch(0.55 0.22 25)' },
  { value: 'tema2', label: 'Laranja', color: 'oklch(0.70 0.19 50)' },
  { value: 'tema3', label: 'Amarelo', color: 'oklch(0.85 0.18 95)' },
  { value: 'tema4', label: 'Verde Limão', color: 'oklch(0.75 0.20 130)' },
  { value: 'tema5', label: 'Verde Esmeralda', color: 'oklch(0.55 0.15 160)' },
  { value: 'tema6', label: 'Azul Céu', color: 'oklch(0.70 0.14 230)' },
  { value: 'tema7', label: 'Azul Marinho', color: 'oklch(0.35 0.12 250)' },
  { value: 'tema8', label: 'Roxo', color: 'oklch(0.50 0.18 290)' },
  { value: 'tema9', label: 'Rosa Pink', color: 'oklch(0.70 0.20 350)' },
  { value: 'tema10', label: 'Marrom', color: 'oklch(0.40 0.08 40)' },
  { value: 'tema11', label: 'Cinza Grafite', color: 'oklch(0.35 0.02 270)' },
  { value: 'tema12', label: 'Turquesa', color: 'oklch(0.65 0.16 195)' },
  { value: 'tema13', label: 'Coral', color: 'oklch(0.68 0.18 35)' },
  { value: 'tema14', label: 'Vinho', color: 'oklch(0.38 0.14 15)' },
  { value: 'tema15', label: 'Dourado', color: 'oklch(0.75 0.12 75)' },
  { value: 'tema16', label: 'Prata', color: 'oklch(0.65 0.01 270)' },
  { value: 'tema17', label: 'Bege', color: 'oklch(0.80 0.05 70)' },
  { value: 'tema18', label: 'Terracota', color: 'oklch(0.58 0.13 45)' },
  { value: 'tema19', label: 'Menta', color: 'oklch(0.78 0.12 165)' },
  { value: 'tema20', label: 'Lavanda', color: 'oklch(0.72 0.13 300)' },
  { value: 'tema21', label: 'Pêssego', color: 'oklch(0.80 0.10 55)' },
  { value: 'tema22', label: 'Verde Oliva', color: 'oklch(0.50 0.10 120)' },
  { value: 'tema23', label: 'Azul Petróleo', color: 'oklch(0.45 0.10 210)' },
  { value: 'tema24', label: 'Salmão', color: 'oklch(0.72 0.14 30)' },
  { value: 'tema25', label: 'Magenta', color: 'oklch(0.60 0.24 330)' },
  { value: 'tema26', label: 'Ciano', color: 'oklch(0.75 0.15 200)' },
] as const

// Array com apenas os valores para validação
export const TEMAS_VALUES = TEMAS_CARDAPIO.map((tema) => tema.value)

// Tipo derivado dos valores
export type TemaCardapio = (typeof TEMAS_VALUES)[number]
