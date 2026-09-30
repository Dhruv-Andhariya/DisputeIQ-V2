import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.errors import AppError, AuthenticationError
from app.database.db import init_db, count_disputes
from app.database.seed import seed_database
from app.api.routes import router
from app.auth.routes import router as auth_router
from app.organizations.routes import router as organizations_router
from app.users.routes import router as users_router
from app.domain.routes import router as domain_router
from app.evidence.routes import router as evidence_router
from app.document_intelligence.routes import router as document_intelligence_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logging.getLogger("alembic").setLevel(logging.WARNING)
logger = logging.getLogger("disputeiq")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.AUTO_MIGRATE:
        logger.info("Applying database migrations...")
        init_db()
    if settings.SEED_DEMO_DATA and count_disputes() == 0:
        logger.info("Empty database: seeding synthetic demo dataset into the demo organization...")
        seed_database()
    yield


app = FastAPI(
    title="DisputeIQ API",
    description=(
        "Multi-tenant dispute investigation and evidence intelligence platform.\n\n"
        "**Authentication:** call `POST /auth/login` (or `POST /auth/register`), then click "
        "**Authorize** and paste the `access_token`. All data is scoped to the organization of the "
        "authenticated user; resources belonging to other organizations return 404."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# Bearer tokens travel in the Authorization header, not cookies, so credentials mode is not needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthenticationError) else None
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    # Full traceback goes to server logs only; clients get a generic message.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(users_router)
app.include_router(domain_router)
app.include_router(evidence_router)
app.include_router(document_intelligence_router)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
