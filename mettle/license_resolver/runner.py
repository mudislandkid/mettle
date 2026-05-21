"""Per-project orchestration: resolve all detected deps, build the summary
JSON the database stores, and decide whether the project trips the
license-risk flag."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict

from . import ResolvedLicense, resolve_all
from .cache import LicenseCache
from .http import RegistryClient
from .spdx import is_copyleft


def resolve_project(
    deps: list[dict],
    *,
    project_license_spdx: str | None,
    project_flags: list[str] | None,
    cache: LicenseCache | None = None,
    client: RegistryClient | None = None,
    on_progress=None,
) -> tuple[list[dict], dict, bool]:
    """Resolve every dep, return `(license_list, summary, has_risk)`.

    Args:
        deps: dep dicts as produced by `detect_dependencies`.
        project_license_spdx: the project's own SPDX id (`Project.license_spdx`).
        project_flags: the project's flag list (used to detect `proprietary`).

    Returns:
        license_list: serialisable list of dicts mirroring `ResolvedLicense`.
        summary: aggregate stats used by the UI.
        has_risk: True iff any copyleft-strong dep is shipped under a
            proprietary status (proprietary flag, or no SPDX license at all).
    """
    resolved: list[ResolvedLicense] = resolve_all(
        deps, cache=cache, client=client, on_progress=on_progress
    )

    license_list = [asdict(r) for r in resolved]

    by_spdx: Counter[str] = Counter()
    unresolved = 0
    copyleft_strong = 0
    copyleft_weak = 0
    for r in resolved:
        if r.spdx is None:
            unresolved += 1
            continue
        by_spdx[r.spdx] += 1
        tier = is_copyleft(r.spdx)
        if tier == "strong":
            copyleft_strong += 1
        elif tier == "weak":
            copyleft_weak += 1

    summary = {
        "resolved": sum(by_spdx.values()),
        "unresolved": unresolved,
        "by_spdx": dict(by_spdx),
        "copyleft_strong": copyleft_strong,
        "copyleft_weak": copyleft_weak,
    }

    is_proprietary_status = (project_flags or []).__contains__("proprietary") or (
        project_license_spdx is None
    )
    has_risk = copyleft_strong > 0 and is_proprietary_status

    return license_list, summary, has_risk
