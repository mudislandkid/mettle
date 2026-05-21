import type { Project } from '@/types'

type LicenseInput = Pick<Project, 'license_spdx' | 'flags'>

export function isProprietary(p: Pick<Project, 'flags'>): boolean {
  return p.flags?.includes('proprietary') ?? false
}

// A project counts as "missing license" when no SPDX id is detected AND the
// project isn't explicitly marked proprietary. Proprietary projects opt out of
// the missing-license signal because default copyright is what they want.
export function isMissingLicense(p: LicenseInput): boolean {
  if (p.license_spdx) return false
  if (isProprietary(p)) return false
  return true
}
