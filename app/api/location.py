from fastapi import APIRouter, Depends, HTTPException,Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from uuid import UUID
import uuid
from app.db.session import get_async_session
from app.models.location import Country, State, City, Locality
from app.utils.response import api_response
from app.utils.query_helper import apply_filters, apply_ordering, paginate,soft_delete

router = APIRouter(prefix="/locations", tags=["Locations"])

# ---------------------------------------
# Country Endpoints
# ---------------------------------------
@router.post("/countries")
async def create_country(
    payload: dict = Body(...),
    session: AsyncSession = Depends(get_async_session)
):
    name = payload.get("name")
    is_active = payload.get("is_active", True)

    exists = await session.scalar(select(Country).where(Country.name == name))
    if exists:
        raise HTTPException(status_code=400, detail="Country already exists")

    country = Country(name=name, is_active=is_active)
    session.add(country)
    await session.commit()
    await session.refresh(country)

    return api_response(message="Country created", data={"id": country.id, "name": country.name})


@router.put("/countries/{country_id}")
async def update_country(
    country_id: UUID,
    payload: dict = Body(...),
    session: AsyncSession = Depends(get_async_session)
):
    name = payload.get("name")
    is_active = payload.get("is_active")

    country = await session.get(Country, country_id)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    if name is not None:
        country.name = name
    if is_active is not None:
        country.is_active = is_active

    await session.commit()
    return api_response(message="Country updated")


@router.get("/countries")
async def list_countries(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    query: Optional[str] = Query(None),  # New param
    order_by: Optional[str] = None,
    name: Optional[str] = None,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_async_session)
):
    session_query = select(Country.id, Country.name, Country.is_active)
    filters = {}
    if name:
        filters["name"] = name
    if is_active is not None:
        filters["is_active"] = is_active

    session_query = apply_filters(session_query, Country, filters,search_query=query)
    session_query = apply_ordering(session_query, Country, order_by)
    session_query = paginate(session_query, page, limit)

    result = await session.execute(session_query)
    return api_response(data=result.mappings().all())

# ---------------------------------------
# State Endpoints
# ---------------------------------------
@router.post("/states")
async def create_state(
    payload: dict = Body(...),
    session: AsyncSession = Depends(get_async_session)
):
    country_id = payload.get("country_id")
    name = payload.get("name")
    is_active = payload.get("is_active", True)

    exists = await session.scalar(
        select(State).where(State.name == name, State.country_id == country_id)
    )
    if exists:
        raise HTTPException(status_code=400, detail="State already exists for this country")

    state = State(name=name, country_id=country_id, is_active=is_active)
    session.add(state)
    await session.commit()
    await session.refresh(state)

    return api_response(message="State created", data={"id": state.id, "name": state.name})


@router.get("/states")
async def list_states(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    query: Optional[str] = Query(None),  # New param
    order_by: Optional[str] = None,
    country_id: Optional[UUID] = None,
    name: Optional[str] = None,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_async_session)
):
    session_query = select(State.id, State.name, State.is_active)
    filters = {}
    if country_id:
        filters["country_id"] = country_id
    if name:
        filters["name"] = name
    if is_active is not None:
        filters["is_active"] = is_active

    session_query = apply_filters(session_query, State, filters,search_query=query)
    session_query = apply_ordering(session_query, State, order_by)
    session_query = paginate(session_query, page, limit)

    result = await session.execute(session_query)
    return api_response(data=result.mappings().all())

# ---------------------------------------
# City Endpoints
# ---------------------------------------
@router.post("/cities")
async def create_city(
    payload: dict = Body(...),
    session: AsyncSession = Depends(get_async_session)
):
    state_id = payload.get("state_id")
    name = payload.get("name")
    is_active = payload.get("is_active", True)

    exists = await session.scalar(
        select(City).where(City.name == name, City.state_id == state_id)
    )
    if exists:
        raise HTTPException(status_code=400, detail="City already exists for this state")

    city = City(name=name, state_id=state_id, is_active=is_active)
    session.add(city)
    await session.commit()
    await session.refresh(city)

    return api_response(message="City created", data={"id": city.id, "name": city.name})


@router.get("/cities")
async def list_cities(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    query: Optional[str] = Query(None),  # New param
    order_by: Optional[str] = None,
    state_id: Optional[UUID] = None,
    name: Optional[str] = None,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_async_session)
):
    session_query = (
        select(City.id, City.name, City.is_active, City.state_id, State.name.label("state_name"))
        .join(State, City.state_id == State.id)
    )
    filters = {}
    if state_id:
        filters["state_id"] = state_id
    if name:
        filters["name"] = name
    if is_active is not None:
        filters["is_active"] = is_active

    session_query = apply_filters(session_query, City, filters,search_query=query)
    session_query = apply_ordering(session_query, City, order_by)
    session_query = paginate(session_query, page, limit)

    result = await session.execute(session_query)
    return api_response(data=result.mappings().all())

# ---------------------------------------
# Locality Endpoints
# ---------------------------------------
@router.post("/localities")
async def create_locality(
    payload: dict = Body(...),
    session: AsyncSession = Depends(get_async_session)
):
    city_id = payload.get("city_id")
    name = payload.get("name")
    pincode = payload.get("pincode")
    is_active = payload.get("is_active", True)

    exists = await session.scalar(
        select(Locality).where(Locality.name == name, Locality.city_id == city_id)
    )
    if exists:
        raise HTTPException(status_code=400, detail="Locality already exists for this city")

    locality = Locality(name=name, city_id=city_id, pincode=pincode, is_active=is_active)
    session.add(locality)
    await session.commit()
    await session.refresh(locality)

    return api_response(message="Locality created", data={"id": locality.id, "name": locality.name})


@router.get("/localities")
async def list_localities(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    query: Optional[str] = Query(None),  # New param
    order_by: Optional[str] = None,
    city_id: Optional[UUID] = None,
    name: Optional[str] = None,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_async_session)
):
    session_query = select(Locality.id, Locality.name, Locality.pincode, Locality.is_active)
    filters = {}
    if city_id:
        filters["city_id"] = city_id
    if name:
        filters["name"] = name
    if is_active is not None:
        filters["is_active"] = is_active

    session_query = apply_filters(session_query, Locality, filters,search_query=query)
    session_query = apply_ordering(session_query, Locality, order_by)
    session_query = paginate(session_query, page, limit)

    result = await session.execute(session_query)
    return api_response(data=result.mappings().all())

@router.delete("/countries/{country_id}")
async def delete_country(country_id: uuid.UUID,     session: AsyncSession = Depends(get_async_session)
):
    return await soft_delete(session, Country, country_id)

@router.delete("/states/{state_id}")
async def delete_state(state_id: uuid.UUID,     session: AsyncSession = Depends(get_async_session)
):
    return await soft_delete(session, State, state_id)

@router.delete("/cities/{city_id}")
async def delete_city(city_id: uuid.UUID,     session: AsyncSession = Depends(get_async_session)
):
    return await soft_delete(session, City, city_id)

@router.delete("/localities/{locality_id}")
async def delete_locality(locality_id: uuid.UUID,     session: AsyncSession = Depends(get_async_session)
):
    return await soft_delete(session, Locality, locality_id)