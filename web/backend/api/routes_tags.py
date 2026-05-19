"""Tag API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database.connection import get_session
from ..database.models import Tag, FLAG_TYPES, FLAG_LABELS, FLAG_COLORS
from ..schemas.tags import TagCreate, TagUpdate, TagResponse

router = APIRouter()


@router.get("/", response_model=list[TagResponse])
async def list_tags(session: Session = Depends(get_session)):
    """List all tags."""
    tags = session.exec(select(Tag).order_by(Tag.name)).all()
    return tags


@router.post("/", response_model=TagResponse)
async def create_tag(request: TagCreate, session: Session = Depends(get_session)):
    """Create a new tag."""
    # Check if tag with same name exists
    existing = session.exec(select(Tag).where(Tag.name == request.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tag with this name already exists")

    tag = Tag(name=request.name, color=request.color)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    return tag


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: int, session: Session = Depends(get_session)):
    """Get a single tag."""
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    return tag


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int,
    request: TagUpdate,
    session: Session = Depends(get_session),
):
    """Update a tag."""
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    if request.name is not None:
        # Check for duplicate name
        existing = session.exec(
            select(Tag).where(Tag.name == request.name).where(Tag.id != tag_id)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Tag with this name already exists")
        tag.name = request.name

    if request.color is not None:
        tag.color = request.color

    session.commit()
    session.refresh(tag)

    return tag


@router.delete("/{tag_id}")
async def delete_tag(tag_id: int, session: Session = Depends(get_session)):
    """Delete a tag."""
    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    session.delete(tag)
    session.commit()

    return {"message": "Tag deleted", "success": True}


@router.get("/flags/types")
async def get_flag_types():
    """Get available flag types with labels and colors."""
    return [
        {
            "type": flag_type,
            "label": FLAG_LABELS.get(flag_type, flag_type),
            "color": FLAG_COLORS.get(flag_type, "#6b7280"),
        }
        for flag_type in FLAG_TYPES
    ]
