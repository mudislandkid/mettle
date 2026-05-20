"""Cross-project digest API. Single GET endpoint, read-only."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from mettle.digest import compute_digest, render_json

from ..database.connection import get_session
from ..schemas.digest import DigestReportResponse

router = APIRouter()


def _parse_window(spec: str) -> int:
    """Parse '7d' / '2w' / '1m' / bare digits into days."""
    spec = spec.strip().lower()
    if spec.isdigit():
        return int(spec)
    if spec.endswith("d") and spec[:-1].isdigit():
        return int(spec[:-1])
    if spec.endswith("w") and spec[:-1].isdigit():
        return int(spec[:-1]) * 7
    if spec.endswith("m") and spec[:-1].isdigit():
        return int(spec[:-1]) * 30
    raise ValueError(f"Cannot parse since={spec!r}. Use e.g. '7d', '2w', '1m', or bare days.")


@router.get("/", response_model=DigestReportResponse)
async def get_digest(
    since: str = Query("7d", description="Time window (e.g. 1d, 7d, 30d, 2w, 1m)."),
    top: int = Query(5, ge=1, le=50, description="Max entries per delta section."),
    stale_days: int = Query(30, ge=1, le=365, description="Days-no-commit threshold."),
    session: Session = Depends(get_session),
) -> dict:
    """Cross-project digest. Reads completed analyses from the DB; computes
    delta + coverage stats; returns a 7-section report. Same data shape as
    `mettle digest --format json`."""
    try:
        window_days = _parse_window(since)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    report = compute_digest(
        session,
        window_days=window_days,
        top_n=top,
        stale_days=stale_days,
    )
    return render_json(report)
