from fastapi import APIRouter, Depends, HTTPException, status,Body,Form,Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from app.core.redis import get_redis

from app.db.session import get_async_session
from app.models.user import User,UserRole
from app.schemas.user import UserCreate, UserUpdate, UserOut,UserType
from app.utils.security import hash_password
from app.utils.response import api_response  # <-- import here
from app.models.user import LoginMethod
from app.app_service import rate_limiter
from app.utils.email import send_otp_email
from app.utils.sms import send_otp_sms
import random
from app.core.config import settings


router = APIRouter(prefix="/users", tags=["users"])



@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_async_session)):
    redis = await get_redis()
    otp_key = f"rotp:{user_in.email}" if user_in.login_method=="email" else f"otp:{user_in.phone}"
    stored_otp = await redis.get(otp_key)

    if not stored_otp or stored_otp != user_in.otp:
        return api_response(
            success=False,
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid or expired OTP"
        )
    # Check uniqueness based on login_type
    if user_in.login_method == LoginMethod.EMAIL:
        q = await db.execute(select(User).filter(User.email == user_in.email))
    else:  # PHONE
        q = await db.execute(select(User).filter(User.phone == user_in.phone))
    
    existing_user = q.scalars().first()
    if existing_user:
        return api_response(
        success=False,
        status_code=400,
        message=f"{user_in.login_method.value.capitalize()} already registered",
        data={}
    )
    # Create roles list (assuming you want to assign the primary user_type as role)
    roles = [UserRole(role=role) for role in {UserType.TENANT, UserType.BROKER}]
    user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        gender=user_in.gender,
        roles=roles,
        dob=user_in.dob,
        email=user_in.email if user_in.login_method == LoginMethod.EMAIL else None,
        phone=user_in.phone if user_in.login_method == LoginMethod.PHONE else None,
        hashed_password=hash_password(user_in.password),
        login_method=user_in.login_method,
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)
    await redis.delete(otp_key)

    return api_response(
        data=UserOut.from_orm(user).dict(),
        message="User created successfully",
        status_code=status.HTTP_201_CREATED,
    )

@router.get("/{user_id}")
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_async_session)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return api_response(
        data=UserOut.from_orm(user).dict(),
        message="User fetched successfully",
    )


@router.put("/{user_id}")
async def update_user(user_id: uuid.UUID, user_in: UserUpdate, db: AsyncSession = Depends(get_async_session)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_in.dict(exclude_unset=True)

    if "password" in update_data:
        user.hashed_password = hash_password(update_data.pop("password"))

    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)

    return api_response(
        data=UserOut.from_orm(user).dict(),
        message="User updated successfully",
    )



@router.delete("/{user_id}")
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_async_session)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Soft delete by setting is_active to False
    user.is_active = False
    await db.commit()
    await db.refresh(user)

    return api_response(message="User deactivated successfully")





@router.post("/register-otp")
@rate_limiter.limit("10/minute")  # example: 10 requests per minute per IP
async def send_otp(
    request: Request, 
    db: AsyncSession = Depends(get_async_session),
    method: LoginMethod = Body(...),
    contact: str = Body(...)
):
    # Check uniqueness based on login_type
    if method == LoginMethod.EMAIL:
        q = await db.execute(select(User).filter(User.email == contact))
    else:  # PHONE
        q = await db.execute(select(User).filter(User.phone == contact))
    
    existing_user = q.scalars().first()
    if existing_user:
        return api_response(
        success=False,
        status_code=400,
        message=f"{contact} already registered",
        data={}
    )
    otp = str(random.randint(100000, 999999))
    redis = await get_redis()
    response=await redis.set(f"rotp:{contact}", otp, ex=settings.OTP_TOKEN_EXPIRE_MINUTES*60)
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

