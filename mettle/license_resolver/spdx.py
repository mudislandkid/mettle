"""SPDX identifier normalisation + the copyleft sets used by risk scoring.

Resolvers return raw license strings from registries (which are inconsistent —
PyPI classifiers, npm `{type, url}` objects, etc.). `normalize()` maps the
common variants onto canonical SPDX ids. Anything we can't recognise returns
None, which the caller stores as "unresolved" rather than guessing.
"""

from __future__ import annotations

from typing import Literal

# Canonical SPDX expressions we explicitly understand. Lower-cased lookup so
# input variants like "MIT License", "BSD 3-Clause" hit the right id.
_ALIASES: dict[str, str] = {
    # MIT family
    "mit": "MIT",
    "mit license": "MIT",
    "the mit license": "MIT",
    "mit/x11": "MIT",
    # Apache
    "apache 2.0": "Apache-2.0",
    "apache-2.0": "Apache-2.0",
    "apache 2": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache license, version 2.0": "Apache-2.0",
    # BSD
    "bsd": "BSD-3-Clause",  # bare "BSD" historically means 3-clause
    "bsd license": "BSD-3-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd 3-clause": "BSD-3-Clause",
    "new bsd license": "BSD-3-Clause",
    "modified bsd license": "BSD-3-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd 2-clause": "BSD-2-Clause",
    "simplified bsd license": "BSD-2-Clause",
    "freebsd": "BSD-2-Clause",
    "bsd-2-clause-freebsd": "BSD-2-Clause-FreeBSD",
    # ISC
    "isc": "ISC",
    "isc license (iscl)": "ISC",
    "isc license": "ISC",
    # GPL family
    "gpl": "GPL-3.0-or-later",
    "gpl-2.0": "GPL-2.0-only",
    "gpl-2.0-only": "GPL-2.0-only",
    "gpl-2.0+": "GPL-2.0-or-later",
    "gpl-2.0-or-later": "GPL-2.0-or-later",
    "gnu general public license v2 (gplv2)": "GPL-2.0-only",
    "gpl-3.0": "GPL-3.0-only",
    "gpl-3.0-only": "GPL-3.0-only",
    "gpl-3.0+": "GPL-3.0-or-later",
    "gpl-3.0-or-later": "GPL-3.0-or-later",
    "gnu general public license v3 (gplv3)": "GPL-3.0-only",
    "gnu general public license v3 or later (gplv3+)": "GPL-3.0-or-later",
    # LGPL
    "lgpl": "LGPL-3.0-or-later",
    "lgpl-2.1": "LGPL-2.1-only",
    "lgpl-2.1-only": "LGPL-2.1-only",
    "lgpl-2.1+": "LGPL-2.1-or-later",
    "lgpl-2.1-or-later": "LGPL-2.1-or-later",
    "lgpl-3.0": "LGPL-3.0-only",
    "lgpl-3.0-only": "LGPL-3.0-only",
    "lgpl-3.0+": "LGPL-3.0-or-later",
    "lgpl-3.0-or-later": "LGPL-3.0-or-later",
    "gnu lesser general public license v3 (lgplv3)": "LGPL-3.0-only",
    # AGPL
    "agpl": "AGPL-3.0-or-later",
    "agpl-3.0": "AGPL-3.0-only",
    "agpl-3.0-only": "AGPL-3.0-only",
    "agpl-3.0+": "AGPL-3.0-or-later",
    "agpl-3.0-or-later": "AGPL-3.0-or-later",
    "gnu affero general public license v3": "AGPL-3.0-only",
    "gnu affero general public license v3 or later (agplv3+)": "AGPL-3.0-or-later",
    # Mozilla / Eclipse / CDDL
    "mpl-2.0": "MPL-2.0",
    "mpl 2.0": "MPL-2.0",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    "epl-2.0": "EPL-2.0",
    "eclipse public license v2.0": "EPL-2.0",
    "cddl-1.0": "CDDL-1.0",
    "cddl-1.1": "CDDL-1.1",
    # Public-domain-ish
    "unlicense": "Unlicense",
    "the unlicense": "Unlicense",
    "public domain": "CC0-1.0",
    "cc0": "CC0-1.0",
    "cc0-1.0": "CC0-1.0",
    # Misc common
    "wtfpl": "WTFPL",
    "zlib": "Zlib",
    "boost software license 1.0": "BSL-1.0",
    "boost-1.0": "BSL-1.0",
    "0bsd": "0BSD",
}


# Strong copyleft: linking imposes copyleft on the entire combined work.
# Mixing one of these into a proprietary product is the canonical risk.
COPYLEFT_STRONG = frozenset(
    {
        "GPL-2.0-only",
        "GPL-2.0-or-later",
        "GPL-3.0-only",
        "GPL-3.0-or-later",
        "AGPL-3.0-only",
        "AGPL-3.0-or-later",
    }
)

# Weak / file-scoped copyleft. Lower risk in most use cases (you can link
# proprietary code as long as you don't modify the copyleft files). Flag it
# but don't sound the same alarm.
COPYLEFT_WEAK = frozenset(
    {
        "LGPL-2.1-only",
        "LGPL-2.1-or-later",
        "LGPL-3.0-only",
        "LGPL-3.0-or-later",
        "MPL-2.0",
        "EPL-2.0",
        "CDDL-1.0",
        "CDDL-1.1",
    }
)


def normalize(raw: str | None) -> str | None:
    """Best-effort SPDX normaliser. Returns the canonical id on hit, None on miss."""
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    # Crude SPDX-expression handling: "MIT OR Apache-2.0" → take the first
    # operand. Compound licenses are rare in practice for direct deps and
    # we don't model the full expression grammar here.
    for sep in (" OR ", " AND ", "/", " or ", " and "):
        if sep in text:
            text = text.split(sep, 1)[0].strip()
            break
    lowered = text.lower().strip().rstrip(".")
    # Strip surrounding parentheses common in npm: "(MIT)"
    if lowered.startswith("(") and lowered.endswith(")"):
        lowered = lowered[1:-1].strip()
    if not lowered or lowered in {
        "see license",
        "see license in file",
        "noassertion",
        "unknown",
        "other/proprietary license",
    }:
        return None
    if lowered in _ALIASES:
        return _ALIASES[lowered]
    # If the raw form is already a recognised SPDX id (case-preserved), accept it.
    canonical_values = set(_ALIASES.values())
    if text in canonical_values:
        return text
    # As a last attempt, treat the raw form as canonical when it looks SPDX-ish
    # (no spaces, contains a dash or starts with a known prefix). This lets
    # niche but legitimate ids ("Zlib", "0BSD") pass through even if missing
    # from the alias table.
    if " " not in text and any(c in text for c in "-."):
        return text
    return None


def is_copyleft(spdx: str | None) -> Literal["strong", "weak"] | None:
    if not spdx:
        return None
    if spdx in COPYLEFT_STRONG:
        return "strong"
    if spdx in COPYLEFT_WEAK:
        return "weak"
    return None
