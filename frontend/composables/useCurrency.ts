export function useCurrency() {
  const formatter = new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  })

  function format(value: number | string): string {
    const num = typeof value === 'string' ? parseFloat(value) : value
    return formatter.format(num)
  }

  return { format }
}
