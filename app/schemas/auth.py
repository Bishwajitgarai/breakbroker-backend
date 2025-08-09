from pydantic import BaseModel, EmailStr, constr
from enum import Enum
from typing import Optional, Union
from datetime import date


class UserType(str, Enum):
    ADMIN = "admin"
    OWNER = "owner"
    TENANT = "tenant"
    BROKER = "broker"


class LoginMethod(str, Enum):
    EMAIL = "email"
    PHONE = "phone"


class SignupSchema(BaseModel):
    first_name: constr(strip_whitespace=True, min_length=1)
    last_name: constr(strip_whitespace=True, min_length=1)
    gender: constr(strip_whitespace=True, min_length=1)
    dob: date  # Use date type for better validation
    login_method: LoginMethod
    email: Optional[EmailStr] = None
    phone: Optional[str] = None  # Add phone field
    password: constr(min_length=6)
    last_otp: Optional[str]  # Usually this isn't needed in signup, but keeping as per your input

    # Validation to ensure contact info matches login_method
    def validate_contact(self):
        if self.login_method == LoginMethod.EMAIL and not self.email:
            raise ValueError("Email must be provided when login_method is email")
        if self.login_method == LoginMethod.PHONE and not self.phone:
            raise ValueError("Phone must be provided when login_method is phone")

    def dict(self, *args, **kwargs):
        self.validate_contact()
        return super().dict(*args, **kwargs)


class LoginSchema(BaseModel):
    login_method: LoginMethod
    contact: str  # can be email or phone depending on login_method
    password: constr(min_length=6)


class OTPVerifySchema(BaseModel):
    contact: str  # email or phone
    otp: constr(min_length=4, max_length=6)
    login_method:str


class PasswordOTPChangeSchema(BaseModel):
    login_method: LoginMethod
    contact: str  # email or phone
    new_password: constr(min_length=6)
    otp:str
