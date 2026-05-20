// Tone palettes, language colours, kind-keyed digest accents, manager pills,
// and the health bucket function. Ported from analyze-shared.jsx + digest-components.jsx.
//
// All class names are pre-built so Tailwind's JIT picks them up at build time —
// don't construct class strings via interpolation.

export type Tone = 'emerald' | 'lime' | 'amber' | 'orange' | 'rose' | 'slate' | 'indigo' | 'sky' | 'red'

export const TONE: Record<Tone, { text: string; bg: string; ring: string; bar: string }> = {
  emerald: { text: 'text-emerald-300', bg: 'bg-emerald-500/15', ring: 'ring-emerald-500/30', bar: 'bg-emerald-400' },
  lime:    { text: 'text-lime-300',    bg: 'bg-lime-500/15',    ring: 'ring-lime-500/30',    bar: 'bg-lime-400'    },
  amber:   { text: 'text-amber-300',   bg: 'bg-amber-500/15',   ring: 'ring-amber-500/30',   bar: 'bg-amber-400'   },
  orange:  { text: 'text-orange-300',  bg: 'bg-orange-500/15',  ring: 'ring-orange-500/30',  bar: 'bg-orange-400'  },
  rose:    { text: 'text-rose-300',    bg: 'bg-rose-500/15',    ring: 'ring-rose-500/30',    bar: 'bg-rose-400'    },
  slate:   { text: 'text-slate-300',   bg: 'bg-slate-500/15',   ring: 'ring-slate-500/30',   bar: 'bg-slate-500'   },
  indigo:  { text: 'text-indigo-300',  bg: 'bg-indigo-500/15',  ring: 'ring-indigo-500/30',  bar: 'bg-indigo-400'  },
  sky:     { text: 'text-sky-300',     bg: 'bg-sky-500/15',     ring: 'ring-sky-500/30',     bar: 'bg-sky-400'     },
  red:     { text: 'text-red-300',     bg: 'bg-red-500/15',     ring: 'ring-red-500/30',     bar: 'bg-red-400'     },
}

export const LANG_TONE: Record<string, Tone> = {
  TypeScript: 'sky',
  JavaScript: 'amber',
  Python:     'emerald',
  Rust:       'orange',
  Vue:        'emerald',
  Go:         'sky',
  Ruby:       'rose',
  PHP:        'indigo',
  Shell:      'slate',
  Markdown:   'slate',
  Swift:      'orange',
  HTML:       'rose',
  GLSL:       'sky',
  Dockerfile: 'indigo',
}

export interface HealthBucket {
  label: string
  tone: Tone
}

export function healthBucket(score: number | null | undefined): HealthBucket {
  if (score == null) return { label: '—', tone: 'slate' }
  if (score >= 80) return { label: 'Healthy', tone: 'emerald' }
  if (score >= 60) return { label: 'OK', tone: 'lime' }
  if (score >= 40) return { label: 'At risk', tone: 'amber' }
  if (score >= 20) return { label: 'Poor', tone: 'orange' }
  return { label: 'Critical', tone: 'rose' }
}

// Digest section kind → accent + tone.
export type DigestKindAccent = {
  tone: 'narrative' | 'coverage'
  accent: 'emerald' | 'indigo' | 'amber' | 'orange' | 'rose' | 'sky' | 'slate'
}

export const KIND_STYLE: Record<string, DigestKindAccent> = {
  grown_most:         { tone: 'narrative', accent: 'emerald' },
  biggest_swing:      { tone: 'narrative', accent: 'indigo' },
  dependency_drift:   { tone: 'narrative', accent: 'amber' },
  stalled_with_todos: { tone: 'narrative', accent: 'orange' },
  newly_stale:        { tone: 'narrative', accent: 'rose' },
  new_since:          { tone: 'coverage', accent: 'sky' },
  no_recent_activity: { tone: 'coverage', accent: 'slate' },
}

export const ACCENT_CLASSES: Record<string, { ring: string; text: string; bg: string; dot: string }> = {
  emerald:  { ring: 'ring-emerald-500/30', text: 'text-emerald-300', bg: 'bg-emerald-500/10', dot: 'bg-emerald-400' },
  indigo:   { ring: 'ring-indigo-500/30',  text: 'text-indigo-300',  bg: 'bg-indigo-500/10',  dot: 'bg-indigo-400'  },
  amber:    { ring: 'ring-amber-500/30',   text: 'text-amber-300',   bg: 'bg-amber-500/10',   dot: 'bg-amber-400'   },
  orange:   { ring: 'ring-orange-500/30',  text: 'text-orange-300',  bg: 'bg-orange-500/10',  dot: 'bg-orange-400'  },
  rose:     { ring: 'ring-rose-500/30',    text: 'text-rose-300',    bg: 'bg-rose-500/10',    dot: 'bg-rose-400'    },
  sky:      { ring: 'ring-sky-500/30',     text: 'text-sky-300',     bg: 'bg-sky-500/10',     dot: 'bg-sky-400'     },
  slate:    { ring: 'ring-slate-500/30',   text: 'text-slate-300',   bg: 'bg-slate-500/10',   dot: 'bg-slate-400'   },
}

// Package-manager pill colours match the existing DependencyPanel.vue scheme.
export const MANAGER_PILL: Record<string, string> = {
  npm:      'bg-red-500/15 text-red-300 ring-red-500/20',
  pypi:     'bg-blue-500/15 text-blue-300 ring-blue-500/20',
  cargo:    'bg-orange-500/15 text-orange-300 ring-orange-500/20',
  go:       'bg-cyan-500/15 text-cyan-300 ring-cyan-500/20',
  composer: 'bg-purple-500/15 text-purple-300 ring-purple-500/20',
  rubygems: 'bg-rose-500/15 text-rose-300 ring-rose-500/20',
}

export function managerPill(manager: string): string {
  return MANAGER_PILL[manager] || 'bg-slate-500/15 text-slate-300 ring-slate-500/20'
}
