import pandas as pd
import uuid
import logging
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.location import Country, State, District, City, Locality

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = 500  # tweak based on your DB and memory


async def insert_in_batches(session: AsyncSession, objects, batch_size=BATCH_SIZE):
    """Insert objects in batches to avoid memory/transaction overload."""
    for i in range(0, len(objects), batch_size):
        batch = objects[i:i + batch_size]
        session.add_all(batch)
        await session.flush()
        logger.info(f"Inserted batch {i // batch_size + 1} with {len(batch)} records.")


def parse_coord_series(series, coord_type):
    """Clean and convert coordinates in a pandas Series to Decimal with 6 decimals."""
    def fix(v):
        try:
            v = float(v)
            if abs(v) > 180:  # e.g. 81282380 -> 81.282380
                v /= 1_000_000
            if coord_type == "lat" and -90 <= v <= 90:
                return Decimal(f"{v:.6f}")
            if coord_type == "lng" and -180 <= v <= 180:
                return Decimal(f"{v:.6f}")
        except Exception:
            return None
        return None
    return series.apply(fix)


async def load_locations_from_csv(file_path: str, session: AsyncSession):
    logger.info("Checking if country 'India' exists...")
    india = await session.scalar(select(Country).where(Country.name == "India"))
    if india:
        return "Ok"

    if not india:
        logger.info("Country 'India' not found. Creating new entry...")
        india = Country(id=uuid.uuid4(), name="India", iso_code="IN")
        session.add(india)
        await session.flush()

    logger.info(f"Reading CSV file: {file_path}")
    df = pd.read_csv(file_path)
    logger.info(f"Loaded {len(df)} rows from CSV.")

    # Fix possible NaN in string columns before string operations
    for col in ["statename", "district", "divisionname", "officename"]:
        df[col] = df[col].fillna("").astype(str)

    # Clean coordinates
    df["lat"] = parse_coord_series(df["latitude"], "lat")
    df["lng"] = parse_coord_series(df["longitude"], "lng")

    # --- Process States ---
    logger.info("Processing unique states...")
    df["state_name"] = df["statename"].str.strip().str.upper()
    states_df = df[["state_name"]].drop_duplicates()
    logger.info(f"Found {len(states_df)} unique states.")

    state_map = {}
    new_states = []
    for _, row in states_df.iterrows():
        state_name = row.state_name
        if not state_name:
            continue  # skip empty names
        existing_state = await session.scalar(
            select(State).where(State.name == state_name, State.country_id == india.id)
        )
        if existing_state:
            state_map[state_name] = existing_state.id
        else:
            state_obj = State(id=uuid.uuid4(), country_id=india.id, name=state_name)
            new_states.append(state_obj)

    if new_states:
        await insert_in_batches(session, new_states)
        # After flush, populate state_map for new states
        for state_obj in new_states:
            state_map[state_obj.name] = state_obj.id

    logger.info("States processed.")

    # --- Process Districts ---
    logger.info("Processing unique districts...")
    df["district_name"] = df["district"].str.strip().str.upper()
    district_df = df[["district_name", "state_name"]].drop_duplicates()
    logger.info(f"Found {len(district_df)} unique districts.")

    district_map = {}
    new_districts = []
    for _, row in district_df.iterrows():
        district_name = row.district_name
        state_name = row.state_name
        if not district_name or not state_name:
            continue  # skip invalid
        existing_district = await session.scalar(
            select(District).where(
                District.name == district_name,
                District.state_id == state_map[state_name]
            )
        )
        if existing_district:
            district_map[(district_name, state_name)] = existing_district.id
        else:
            district_obj = District(
                id=uuid.uuid4(),
                state_id=state_map[state_name],
                name=district_name,
            )
            new_districts.append(district_obj)

    if new_districts:
        await insert_in_batches(session, new_districts)
        for district_obj in new_districts:
            state_name_for_district = next(
                (k for k, v in state_map.items() if v == district_obj.state_id), None)
            if state_name_for_district:
                district_map[(district_obj.name, state_name_for_district)] = district_obj.id

    logger.info("Districts processed.")

    # --- Process Cities ---
    logger.info("Processing unique cities with deduplication of lat/lng...")
    df["city_name"] = df["divisionname"].str.replace(" Division", "").str.strip()
    city_district_map = df.drop_duplicates(subset=["city_name", "state_name", "district_name"]).set_index(["city_name", "state_name"])["district_name"].to_dict()

    city_grouped = (
        df.groupby(["city_name", "state_name"])
        .agg(
            lat=pd.NamedAgg(column="lat", aggfunc=lambda x: x.dropna().mean()),
            lng=pd.NamedAgg(column="lng", aggfunc=lambda x: x.dropna().mean()),
        )
        .reset_index()
    )

    logger.info(f"Found {len(city_grouped)} unique cities.")

    city_map = {}
    new_cities = []
    
    for _, row in city_grouped.iterrows():
        city_name = row.city_name
        state_name = row.state_name
        district_name = city_district_map.get((city_name, state_name))  # get district_name from map
        if not city_name or not state_name or not district_name:
            continue
        existing_city = await session.scalar(
            select(City).where(
                City.name == city_name,
                City.state_id == state_map[state_name],
                City.district_id == district_map.get((district_name, state_name))
            )
        )
        district_id = district_map.get((district_name, state_name))
        if existing_city:
            city_map[(city_name, state_name, district_name)] = existing_city.id
        else:
            city_obj = City(
                id=uuid.uuid4(),
                state_id=state_map[state_name],
                district_id=district_id,  # assign district_id here
                name=city_name,
                lat=Decimal(f"{row.lat:.6f}") if row.lat is not None else None,
                lng=Decimal(f"{row.lng:.6f}") if row.lng is not None else None,
            )
            new_cities.append(city_obj)

    if new_cities:
        await insert_in_batches(session, new_cities)
        for city_obj in new_cities:
            state_name_for_city = next(
                (k for k, v in state_map.items() if v == city_obj.state_id), None)
            district_name_for_city = next(
                (k[0] for k, v in district_map.items() if v == city_obj.district_id), None)
            if state_name_for_city and district_name_for_city:
                city_map[(city_obj.name, state_name_for_city, district_name_for_city)] = city_obj.id

    # --- Process Localities ---
    logger.info("Processing localities...")
    df["locality_name"] = (
        df["officename"]
        .str.replace(" B.O", "", regex=False)
        .str.replace(" H.O", "", regex=False)
        .str.replace(" S.O", "", regex=False)
        .str.replace(" BO", "", regex=False)
        .str.replace(" HO", "", regex=False)
        .str.replace(" SO", "", regex=False)
        .str.strip()
        .str.upper()
    )

    localities_df = df[
        ["locality_name", "city_name", "state_name", "district_name", "pincode", "lat", "lng"]
    ].drop_duplicates()
    localities_df["pincode"] = localities_df["pincode"].astype(str)

    locality_objs = []
    for _, row in localities_df.iterrows():
        city_key = (row.city_name, row.state_name, row.district_name)
        city_id = city_map.get(city_key)
        if not city_id:
            logger.warning(f"City not found for locality {row.locality_name}, skipping.")
            continue

        locality_objs.append(
            Locality(
                id=uuid.uuid4(),
                city_id=city_id,
                name=row.locality_name,
                pincode=row.pincode,
                lat=Decimal(f"{row.lat:.6f}") if pd.notnull(row.lat) else None,
                lng=Decimal(f"{row.lng:.6f}") if pd.notnull(row.lng) else None,
            )
        )

    if locality_objs:
        await insert_in_batches(session, locality_objs)
    logger.info(f"Inserted {len(locality_objs)} localities.")

    await session.commit()
    logger.info("All data committed successfully.")
    return "Ok"
