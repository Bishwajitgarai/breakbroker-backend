# app/models/location.py
import uuid
from decimal import Decimal
from sqlalchemy import Column, String, ForeignKey, DECIMAL, CHAR, VARCHAR, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Country(Base):
    __tablename__ = "country"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    iso_code = Column(CHAR(2), nullable=False, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)

    states = relationship("State", back_populates="country", cascade="all, delete-orphan")


class State(Base):
    __tablename__ = "state"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_id = Column(UUID(as_uuid=True), ForeignKey("country.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(VARCHAR(10), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    country = relationship("Country", back_populates="states")
    districts = relationship("District", back_populates="state", cascade="all, delete-orphan")
    cities = relationship("City", back_populates="state", cascade="all, delete-orphan")  # <-- ADD THIS


class District(Base):
    __tablename__ = "district"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state_id = Column(UUID(as_uuid=True), ForeignKey("state.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    state = relationship("State", back_populates="districts")
    cities = relationship("City", back_populates="district", cascade="all, delete-orphan")


class City(Base):
    __tablename__ = "city"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state_id = Column(UUID(as_uuid=True), ForeignKey("state.id", ondelete="CASCADE"), nullable=False)
    # district relationship (nullable so migration/backfill is easier)
    district_id = Column(UUID(as_uuid=True), ForeignKey("district.id", ondelete="SET NULL"), nullable=True)

    name = Column(String, nullable=False)
    lat = Column(DECIMAL(9, 6), nullable=True)
    lng = Column(DECIMAL(9, 6), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    state = relationship("State", back_populates="cities")
    district = relationship("District", back_populates="cities")
    localities = relationship("Locality", back_populates="city", cascade="all, delete-orphan")


class Locality(Base):
    __tablename__ = "locality"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city_id = Column(UUID(as_uuid=True), ForeignKey("city.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    pincode = Column(VARCHAR(10), nullable=True)
    lat = Column(DECIMAL(9, 6), nullable=True)
    lng = Column(DECIMAL(9, 6), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    city = relationship("City", back_populates="localities")
