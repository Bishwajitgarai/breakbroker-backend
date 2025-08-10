from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.api import health,user,auth,location
from app.core.config import settings
from app.utils.response import api_response  # your custom response helper
from app.app_service import rate_limiter
from slowapi.errors import RateLimitExceeded
from app.utils.location_saver import load_locations_from_csv
from app.db.session import get_async_session,async_session
import os

app = FastAPI(title=settings.PROJECT_NAME)
app.state.limiter = rate_limiter

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost/"],  # restrict in production to your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(location.router)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return api_response(
        success=False,
        status_code=429,
        message="Too Many Requests",
        data={}
    )


@app.get("/")
@rate_limiter.limit("10/minute")  # example: 10 requests per minute per IP
async def root(request: Request):
    return api_response(
        success=True,
        status_code=200,
        message="Welcome to BreakBroker!",
        data={}
    )

@app.on_event("startup")
async def startup_event():
    async with async_session() as session:
        get_full_path=os.path.join(os.path.curdir,"app/utils/location_mapper.csv")
        await load_locations_from_csv(session=session, file_path=get_full_path)