// Number, date, and duration formatters shared across all hero pages.
// Ported from docs/design/phase-d/mettle/project/src/analyze-shared.jsx + digest-components.jsx.

export function fmtNum(n: number | null | undefined): string {
  if (n == null) return '—'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(n >= 10_000_000 ? 1 : 2) + 'M'
  if (n >= 10_000) return (n / 1000).toFixed(0) + 'k'
  return n.toLocaleString()
}

export function fmtNumExact(n: number | null | undefined): string {
  if (n == null) return '—'
  return n.toLocaleString()
}

export function fmtDuration(seconds: number | null | undefined): string {
  if (seconds == null) return '—'
  if (seconds < 60) return `${seconds}s`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}m ${s}s`
}

export function fmtRelative(iso: string | null | undefined): string {
  if (!iso) return 'never'
  const ms = Date.now() - new Date(iso).getTime()
  if (Number.isNaN(ms)) return '—'
  const days = Math.floor(ms / 86_400_000)
  if (days < 1) {
    const hrs = Math.floor(ms / 3_600_000)
    if (hrs < 1) return 'just now'
    return `${hrs}h ago`
  }
  if (days < 30) return `${days}d ago`
  if (days < 365) return `${Math.floor(days / 30)}mo ago`
  return `${Math.floor(days / 365)}y ago`
}

export function fmtCalendar(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

export function fmtCalendarShort(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export function fmtCalendarLong(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

export function fmtWindow(days: number): string {
  if (days <= 1) return 'last day'
  if (days === 7) return 'last 7 days'
  if (days === 14) return 'last 2 weeks'
  if (days === 30) return 'last month'
  if (days === 90) return 'last quarter'
  if (days % 7 === 0) return `last ${days / 7} weeks`
  if (days % 30 === 0) return `last ${days / 30} months`
  return `last ${days} days`
}

export function fmtRelativeDays(days: number): string {
  if (days < 1) return 'today'
  if (days < 30) return `${days}d ago`
  if (days < 365) return `${Math.round(days / 30)}mo ago`
  return `${Math.round(days / 365)}y ago`
}
