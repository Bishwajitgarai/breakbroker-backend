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
        batch = objects[i : i + batch_size]
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


async def load_locations_from_csv(
    cities_file_path: str, mapper_file_path: str, session: AsyncSession
):
    logger.info("Checking if country 'India' exists...")
    india = await session.scalar(select(Country).where(Country.name == "INDIA"))
    if not india:
        logger.info("Country 'India' not found. Creating new entry...")
        india = Country(id=uuid.uuid4(), name="INDIA", iso_code="IN")
        session.add(india)
        await session.flush()
    else:
        logger.info("Country 'India' found.")

    # --- LOAD cities.csv and filter only India rows ---
    logger.info(f"Reading cities CSV file: {cities_file_path}")
    cities_df = pd.read_csv(cities_file_path)

    # Filter only India rows by country_name (case insensitive)
    cities_df = cities_df[cities_df["country_name"].str.upper() == "INDIA"].copy()
    logger.info(f"Filtered {len(cities_df)} rows for country 'India' from cities.csv")

    # Uppercase relevant columns for uniformity
    cities_df["name"] = cities_df["name"].str.upper()
    cities_df["state_name"] = cities_df["state_name"].str.upper()

    # Parse lat/lng with your helper
    cities_df["lat"] = parse_coord_series(cities_df["latitude"], "lat")
    cities_df["lng"] = parse_coord_series(cities_df["longitude"], "lng")

    # --- LOAD location mapper CSV ---
    logger.info(f"Reading location mapper CSV file: {mapper_file_path}")
    mapper_df = pd.read_csv(mapper_file_path)

    # Rename statename to state_name before uppercasing
    mapper_df.rename(columns={"statename": "state_name"}, inplace=True)

    # Uppercase all relevant string columns for consistency
    for col in ["state_name", "district", "divisionname", "officename"]:
        mapper_df[col] = mapper_df[col].fillna("").astype(str).str.upper()

    # Clean coordinates
    mapper_df["lat"] = parse_coord_series(mapper_df["latitude"], "lat")
    mapper_df["lng"] = parse_coord_series(mapper_df["longitude"], "lng")

    # --- Prepare city name in mapper_df from divisionname ---
    mapper_df["city_name"] = (
        mapper_df["divisionname"].str.replace(" DIVISION", "", regex=False).str.strip()
    )

    # --- Create city dataframe from mapper_df unique city/state/district with lat/lng mean ---
    mapper_city_grouped = (
        mapper_df.groupby(["city_name", "state_name"])
        .agg(
            district_name=pd.NamedAgg(
                column="district", aggfunc=lambda x: x.mode().iat[0] if not x.mode().empty else None
            ),
            lat=pd.NamedAgg(column="lat", aggfunc=lambda x: x.dropna().mean()),
            lng=pd.NamedAgg(column="lng", aggfunc=lambda x: x.dropna().mean()),
        )
        .reset_index()
    )

    # --- Prepare city dataframe from cities.csv (no district) ---
    cities_for_db = cities_df.rename(
        columns={"name": "city_name", "state_name": "state_name"}
    )[["city_name", "state_name", "lat", "lng"]].copy()
    # No district info in cities.csv, so fill with None for district_name
    cities_for_db["district_name"] = None

    # --- Combine city dataframes ---
    combined_cities_df = pd.concat(
        [
            cities_for_db,
            mapper_city_grouped[["city_name", "state_name", "district_name", "lat", "lng"]],
        ],
        ignore_index=True,
    )

    # Drop duplicates based on city_name + state_name + district_name
    combined_cities_df = combined_cities_df.drop_duplicates(
        subset=["city_name", "state_name", "district_name"]
    ).reset_index(drop=True)

    # --- Process States ---
    logger.info("Processing unique states...")
    combined_cities_df["state_name"] = combined_cities_df["state_name"].fillna("").str.strip().str.upper()
    states_df = combined_cities_df[["state_name"]].drop_duplicates()
    logger.info(f"Found {len(states_df)} unique states.")

    state_map = {}
    new_states = []
    for _, row in states_df.iterrows():
        state_name = row.state_name
        if not state_name:
            continue  # skip empty
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
        for state_obj in new_states:
            state_map[state_obj.name] = state_obj.id

    logger.info("States processed.")

    # --- Process Districts ---
    logger.info("Processing unique districts...")
    combined_cities_df["district_name"] = combined_cities_df["district_name"].fillna("").str.strip().str.upper()
    district_df = combined_cities_df[["district_name", "state_name"]].drop_duplicates()
    logger.info(f"Found {len(district_df)} unique districts.")

    district_map = {}
    new_districts = []
    for _, row in district_df.iterrows():
        district_name = row.district_name
        state_name = row.state_name
        if not district_name or not state_name:
            continue
        existing_district = await session.scalar(
            select(District).where(
                District.name == district_name,
                District.state_id == state_map[state_name],
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
                (k for k, v in state_map.items() if v == district_obj.state_id), None
            )
            if state_name_for_district:
                district_map[(district_obj.name, state_name_for_district)] = district_obj.id

    logger.info("Districts processed.")

    # --- Process Cities with lat/lng cache ---
    logger.info("Processing cities...")
    city_map = {}
    new_cities = []
    existing_city_coords_cache = {}

    for _, row in combined_cities_df.iterrows():
        city_name = row.city_name
        state_name = row.state_name
        district_name = row.district_name if pd.notnull(row.district_name) and row.district_name != "" else None

        if not city_name or not state_name:
            continue

        district_id = None
        if district_name:
            district_id = district_map.get((district_name, state_name))

        lat = row.lat
        lng = row.lng

        existing_city = await session.scalar(
            select(City).where(
                City.name == city_name,
                City.state_id == state_map[state_name],
                City.district_id == district_id,
            )
        )
        if existing_city:
            city_map[(city_name, state_name, district_name)] = existing_city.id
            existing_city_coords_cache[(city_name, state_name, district_name)] = (existing_city.lat, existing_city.lng)
        else:
            # Fallback lat/lng from cache if missing
            if (lat is None or lng is None) and (city_name, state_name, district_name) in existing_city_coords_cache:
                lat, lng = existing_city_coords_cache[(city_name, state_name, district_name)]

            city_obj = City(
                id=uuid.uuid4(),
                state_id=state_map[state_name],
                district_id=district_id,
                name=city_name,
                lat=Decimal(f"{lat:.6f}") if lat is not None else None,
                lng=Decimal(f"{lng:.6f}") if lng is not None else None,
            )
            new_cities.append(city_obj)

    if new_cities:
        await insert_in_batches(session, new_cities)
        for city_obj in new_cities:
            state_name_for_city = next(
                (k for k, v in state_map.items() if v == city_obj.state_id), None
            )
            district_name_for_city = next(
                (k[0] for k, v in district_map.items() if v == city_obj.district_id), None
            )
            if state_name_for_city:
                city_map[(city_obj.name, state_name_for_city, district_name_for_city)] = city_obj.id
                existing_city_coords_cache[(city_obj.name, state_name_for_city, district_name_for_city)] = (city_obj.lat, city_obj.lng)

    logger.info("Cities processed.")

    # --- Process Localities from mapper_df ---
    logger.info("Processing localities...")
    mapper_df["locality_name"] = (
        mapper_df["officename"]
        .str.replace(" B.O", "", regex=False)
        .str.replace(" H.O", "", regex=False)
        .str.replace(" S.O", "", regex=False)
        .str.replace(" BO", "", regex=False)
        .str.replace(" HO", "", regex=False)
        .str.replace(" SO", "", regex=False)
        .str.strip()
        .str.upper()
    )

    localities_df = mapper_df[
        ["locality_name", "city_name", "state_name", "district", "pincode", "lat", "lng"]
    ].copy()

    localities_df.rename(
        columns={"district": "district_name"}, inplace=True
    )
    localities_df["pincode"] = localities_df["pincode"].astype(str).str.strip()

    locality_objs = []
    for _, row in localities_df.drop_duplicates().iterrows():
        city_key = (row.city_name, row.state_name, row.district_name)
        city_id = city_map.get(city_key)
        if not city_id:
            logger.warning(f"City not found for locality {row.locality_name}, skipping.")
            continue

        lat = row.lat
        lng = row.lng
        # Fallback lat/lng from cached city coords if missing in locality
        if (lat is None or lng is None) and city_key in existing_city_coords_cache:
            lat, lng = existing_city_coords_cache[city_key]

        locality_objs.append(
            Locality(
                id=uuid.uuid4(),
                city_id=city_id,
                name=row.locality_name,
                pincode=row.pincode,
                lat=Decimal(f"{lat:.6f}") if lat is not None else None,
                lng=Decimal(f"{lng:.6f}") if lng is not None else None,
            )
        )

    if locality_objs:
        await insert_in_batches(session, locality_objs)
    logger.info(f"Inserted {len(locality_objs)} localities.")

    await session.commit()
    logger.info("All data committed successfully.")
    return "Ok"
