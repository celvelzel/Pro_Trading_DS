export function chartTheme() {
  const style = getComputedStyle(document.documentElement)
  const color = (name: string, fallback: string) => style.getPropertyValue(name).trim() || fallback
  return {
    background: color('--card', '#FFFFFF'),
    text: color('--muted-foreground', '#5F6B7E'),
    grid: color('--border', '#E4E7EC'),
    primary: color('--primary', '#3E7BFA'),
    bullish: color('--color-success', '#16A34A'),
    bearish: color('--color-error', '#DC2626'),
    neutral: color('--color-neutral', '#64748B'),
  }
}
