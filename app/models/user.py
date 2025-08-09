import uuid
from enum import Enum as PyEnum
from datetime import date
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Enum,
    Date,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserType(str, PyEnum):
    ADMIN = "admin"
    OWNER = "owner"
    TENANT = "tenant"
    BROKER = "broker"


class Gender(str, PyEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class LoginMethod(str, PyEnum):
    EMAIL = "email"
    PHONE = "phone"


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role = Column(Enum(UserType, name="user_type_enum"), primary_key=True)

    user = relationship("User", back_populates="roles")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    gender = Column(Enum(Gender, name="gender_enum"), nullable=False)
    dob = Column(Date, nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)  # phone can be nullable if login_method=email
    login_method = Column(Enum(LoginMethod, name="login_method_enum"), nullable=False, default=LoginMethod.EMAIL)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Many-to-many user roles
    roles = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
