from fastapi import APIRouter, Depends, HTTPException,Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_,func
from typing import Optional
from uuid import UUID
import uuid
from app.db.session import get_async_session
from app.models.location import Country, State, City, Locality,District
from app.utils.response import api_response
from app.utils.query_helper import apply_filters, apply_ordering, paginate,soft_delete
import math

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


@router.get("/reverse-geocode")
async def reverse_geocode(
    lat: float = Query(..., description="Latitude"),
    long: float = Query(..., description="Longitude"),
    session: AsyncSession = Depends(get_async_session)
):
    # Calculate squared Euclidean distance to simplify
    # (For better accuracy, you can use Haversine or PostGIS if installed)
    distance_expr = (
        (City.lat - lat) * (City.lat - lat) + (City.lng - long) * (City.lng - long)
    )

    query = (
        select(City.id, City.name.label("city_name"), State.name.label("state_name"),State.id.label("state_id"),District.id.label("district_id"))
        .join(State, City.state_id == State.id)
        .join(District, City.district_id == District.id)
        .where(City.is_active == True)
        .order_by(distance_expr.asc())
        .limit(1)
    )

    result = await session.execute(query)
    city_row = result.first()

    if not city_row:
        raise HTTPException(status_code=404, detail="No city found")

    return api_response(
        message="Nearest city found for given coordinates",
        data={
            "city_id": city_row.id,
            "city_name": city_row.city_name,
            "state_name": city_row.state_name,
            "state_id": city_row.state_id,
            "district_id": city_row.district_id,
        },
    )

def haversine(lat1, lon1, lat2, lon2):
    # Returns distance in meters between two lat/lon points
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c



from sqlalchemy import func

@router.get("/suggestions")
async def location_suggestions(
    query: Optional[str] = Query(None, description="Search term for city, state, district or locality"),
    page: int = Query(1, ge=1, description="Page number, starts from 1"),
    limit: int = Query(10, ge=1, le=50, description="Number of results per page"),
    lat: Optional[float] = Query(None, description="Latitude for distance sorting"),
    long: Optional[float] = Query(None, description="Longitude for distance sorting"),
    session: AsyncSession = Depends(get_async_session)
):
    # Base query with Locality join added
    base_query = (
        select(
            Locality.id.label("locality_id"),
            Locality.name.label("locality_name"),
            City.id.label("city_id"),
            City.name.label("city_name"),
            State.id.label("state_id"),
            State.name.label("state_name"),
            District.id.label("district_id"),
            District.name.label("district_name"),
            City.lat,
            City.lng,
        )
        .join(City, Locality.city_id == City.id)
        .join(State, City.state_id == State.id)
        .outerjoin(District, City.district_id == District.id)
        .where(City.is_active == True,State.is_active==True,Locality.is_active==True,District.is_active==True)
    )

    if query:
        ilike_query = f"%{query}%"
        # Case insensitive matching using upper()
        base_query = base_query.where(
            or_(
                func.upper(City.name).like(func.upper(ilike_query)),
                func.upper(State.name).like(func.upper(ilike_query)),
                func.upper(District.name).like(func.upper(ilike_query)),
                func.upper(Locality.name).like(func.upper(ilike_query)),
            )
        )

    # Count total results
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await session.execute(count_query)
    total_count = total_result.scalar_one()

    offset_val = (page - 1) * limit
    paginated_query = base_query.limit(limit).offset(offset_val)

    result = await session.execute(paginated_query)
    rows = result.all()
    suggestions = []

    if not rows:
        return api_response(
            message="Location suggestions fetched",
            data={
                "total": total_count,
                "page": page,
                "limit": limit,
                "suggestions": suggestions,
            },
        )

    if lat is not None and long is not None:
        rows_with_distance = []
        for r in rows:
            locality_id, locality_name, city_id, city_name, state_id, state_name, district_id, district_name, city_lat, city_lng = r
            if city_lat is not None and city_lng is not None:
                dist = haversine(lat, long, float(city_lat), float(city_lng))
            else:
                dist = None
            rows_with_distance.append((r, dist))

        rows_with_distance.sort(key=lambda x: x[1] if x[1] is not None else float('inf'))

        for row, dist in rows_with_distance:
            locality_id, locality_name, city_id, city_name, state_id, state_name, district_id, district_name, *_ = row
            entry = {
                "locality_id": locality_id,
                "locality_name": locality_name,
                "city_id": city_id,
                "city_name": city_name,
                "state_id": state_id,
                "state_name": state_name,
                "district_id": district_id,
                "district_name": district_name,
            }
            if dist is not None:
                entry["distance_meters"] = dist
            suggestions.append(entry)
    else:
        suggestions = [
            {
                "locality_id": r.locality_id,
                "locality_name": r.locality_name,
                "city_id": r.city_id,
                "city_name": r.city_name,
                "state_id": r.state_id,
                "state_name": r.state_name,
                "district_id": r.district_id,
                "district_name": r.district_name,
            }
            for r in rows
        ]

    return api_response(
        message="Location suggestions fetched",
        data={
            "total": total_count,
            "page": page,
            "limit": limit,
            "suggestions": suggestions,
        },
    )
