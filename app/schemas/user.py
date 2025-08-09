from datetime import date, datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, EmailStr, constr,model_validator,ConfigDict
from uuid import UUID


class UserType(str, Enum):
    ADMIN = "admin"
    OWNER = "owner"
    TENANT = "tenant"
    BROKER = "broker"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class LoginMethod(str, Enum):
    EMAIL = "email"
    PHONE = "phone"


class UserBase(BaseModel):
    first_name: constr(strip_whitespace=True, min_length=1)
    last_name: constr(strip_whitespace=True, min_length=1)
    gender: Gender
    dob: Optional[date]
    email: EmailStr
    phone: Optional[constr(strip_whitespace=True, min_length=5, max_length=20)]
    login_method: LoginMethod = LoginMethod.EMAIL


class UserCreate(UserBase):
    password: constr(min_length=6)
    otp: constr(min_length=4, max_length=6)
    @model_validator(mode='before')
    def check_contact(cls, values):
        login_method = values.get('login_method')
        email = values.get('email')
        phone = values.get('phone')
        if login_method == LoginMethod.EMAIL and not email:
            raise ValueError("Email must be provided if login_method is email")
        if login_method == LoginMethod.PHONE and not phone:
            raise ValueError("Phone must be provided if login_method is phone")
        return values


class UserUpdate(BaseModel):
    first_name: Optional[constr(strip_whitespace=True, min_length=1)]
    last_name: Optional[constr(strip_whitespace=True, min_length=1)]
    gender: Optional[Gender]
    dob: Optional[date]
    email: Optional[EmailStr]
    phone: Optional[constr(strip_whitespace=True, min_length=5, max_length=20)]
    login_method: Optional[LoginMethod]
    password: Optional[constr(min_length=6)]


class UserOut(UserBase):
    id: UUID  
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


