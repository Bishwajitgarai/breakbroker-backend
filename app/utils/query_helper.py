
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Type
from sqlalchemy.future import select
import uuid
# --------------------------
# Utility: Safe Filters & Ordering
# --------------------------
from typing import Optional
from sqlalchemy import or_

def apply_filters(query, model, filters: dict, search_query: Optional[str] = None):
    """Apply validated filters from query params, plus optional partial name search."""
    for field, value in filters.items():
        if not hasattr(model, field):
            continue  # skip invalid field
        col = getattr(model, field)
        query = query.where(col == value)

    # Add partial search on 'name' column if search_query provided
    if search_query:
        if hasattr(model, "name"):
            name_col = getattr(model, "name")
            query = query.where(name_col.ilike(f"%{search_query}%"))

    return query


def apply_ordering(query, model, order_by: str):
    """Apply safe ordering."""
    if not order_by:
        return query
    direction = "asc"
    if order_by.startswith("-"):
        direction = "desc"
        order_by = order_by[1:]
    if hasattr(model, order_by):
        col = getattr(model, order_by)
        query = query.order_by(col.desc() if direction == "desc" else col.asc())
    return query

def paginate(query, page: int, limit: int):
    """Apply pagination."""
    offset = (page - 1) * limit
    return query.offset(offset).limit(limit)

async def soft_delete(
    session: AsyncSession, model: Type, obj_id: uuid.UUID
):
    result = await session.execute(select(model).where(model.id == obj_id))
    obj = result.scalar_one_or_none()

    if not obj:
        raise HTTPException(status_code=404, detail="Not found")

    obj.is_active = False
    await session.commit()
    return {"success": True, "message": f"{model.__name__} deactivated"}
