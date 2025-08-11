from fastapi import APIRouter, Depends, HTTPException, status,Body,Form,Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
import random
from app.app_service import rate_limiter

from app.db.session import get_async_session
from app.models.user import User, LoginMethod
from app.schemas.auth import LoginSchema, SignupSchema, OTPVerifySchema, PasswordOTPChangeSchema
from app.utils.security import verify_password, hash_password
from app.utils.email import send_otp_email
from app.utils.sms import send_otp_sms
from app.utils.response import api_response
from app.core.redis import get_redis
from app.core.config import settings
from app.utils.auth import create_access_token,refresh_access_token,create_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])

OTP_EXPIRY_SECONDS = settings.OTP_TOKEN_EXPIRE_MINUTES * 60  # Convert minutes to seconds





@router.post("/sendotp")
@rate_limiter.limit("10/hour")  # example: 10 requests per minute per IP
async def send_otp(
    request: Request, 
    method: LoginMethod = Body(...),
    contact: str = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    # Check uniqueness based on login_type
    if method == LoginMethod.EMAIL:
        q = await session.execute(select(User).filter(User.email == contact))
    else:  # PHONE
        q = await session.execute(select(User).filter(User.phone == contact))
    
    existing_user = q.scalars().first()
    if not existing_user:
        return api_response(
        success=False,
        status_code=400,
        message=f"{contact} not registered",
        data={}
    )
    otp = str(random.randint(100000, 999999))
    redis = await get_redis()
    await redis.set(f"otp:{contact}", otp, ex=OTP_EXPIRY_SECONDS)

    if method == LoginMethod.EMAIL:
        await send_otp_email(contact, otp)
    elif method == LoginMethod.PHONE:
        await send_otp_sms(contact, otp)
    else:
        return api_response(
            success=False,
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid method"
        )

    return api_response(message="OTP sent")

@rate_limiter.limit("10/minute")  # example: 10 requests per minute per IP
@router.post("/verifyotp")
async def verify_otp(request: Request,data: OTPVerifySchema, session: AsyncSession = Depends(get_async_session)):
    redis = await get_redis()
    otp_key = f"otp:{data.contact}"
    stored_otp = await redis.get(otp_key)

    if not stored_otp or stored_otp != data.otp:
        return api_response(
            success=False,
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid or expired OTP"
        )


    # Determine filter field based on login_method (optional: you could also pass login_method in schema)
    # user = None
    # if data.login_method == LoginMethod.EMAIL:
    #     q = await session.execute(select(User).filter(User.email == data.contact))
    #     user = q.scalars().first()
    # elif data.login_method == LoginMethod.PHONE:
    #     q = await session.execute(select(User).filter(User.phone == data.contact))
    #     user = q.scalars().first()

    # if user and not user.is_verified:
    #     user.is_verified = True
    #     await session.commit()
    #     return api_response(message="OTP verified, user is now verified")

    return api_response(message="OTP verified")

@rate_limiter.limit("10/minute")  # example: 10 requests per minute per IP
@router.post("/login")
async def login(request: Request,data: LoginSchema, session: AsyncSession = Depends(get_async_session)):
    user = None
    if data.login_method == LoginMethod.EMAIL:
        q = await session.execute(select(User).filter(User.email == data.contact))
        user = q.scalars().first()
    elif data.login_method == LoginMethod.PHONE:
        q = await session.execute(select(User).filter(User.phone == data.contact))
        user = q.scalars().first()

    if not user or not verify_password(data.password, user.hashed_password):
        return api_response(
            success=False,
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid credentials"
        )
    
    # TODO: replace with your real JWT generation logic
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return api_response(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        },
        message="Login successful"
    )


@rate_limiter.limit("10/hour")  # example: 10 requests per minute per IP
@router.post("/forget-password-change")
async def password_change(request: Request,data: PasswordOTPChangeSchema, session: AsyncSession = Depends(get_async_session)):
    redis = await get_redis()
    otp_key = f"otp:{data.contact}"
    stored_otp = await redis.get(otp_key)

    if not stored_otp or stored_otp != data.otp:
        return api_response(
            success=False,
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Session expired"
        )
    await redis.delete(otp_key)
    user = None
    if data.login_method == LoginMethod.EMAIL:
        q = await session.execute(select(User).filter(User.email == data.contact))
        user = q.scalars().first()
    elif data.login_method == LoginMethod.PHONE:
        q = await session.execute(select(User).filter(User.phone == data.contact))
        user = q.scalars().first()

    if not user:
        return api_response(
            success=False,
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found"
        )

    user.hashed_password = hash_password(data.new_password)
    await session.commit()
    return api_response(message="Password updated successfully")

@rate_limiter.limit("25/hour")  # example: 10 requests per minute per IP
@router.post("/refresh")
async def refresh_token_endpoint(request: Request,refresh_token: str = Body(...)):
    new_access_token = refresh_access_token(refresh_token)
    return api_response(
        data={"access_token": new_access_token, "token_type": "bearer"},
        message="Access token refreshed"
    )
