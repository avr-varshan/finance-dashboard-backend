import uuid
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

from app.config import settings
from app.utils.errors import APIException
from app.utils.response import error_response
from app.routers import auth, users, records, dashboard, audit, health

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

app = FastAPI(
    title="Finance Dashboard Backend",
    version=settings.app_version,
    openapi_tags=[
        {"name": "Auth", "description": "Authentication endpoints"},
        {"name": "Users", "description": "User management"},
        {"name": "Records", "description": "Financial records"},
        {"name": "Dashboard", "description": "Aggregation endpoints"},
        {"name": "Audit", "description": "Audit logs"},
        {"name": "System", "description": "Health checks"},
    ],
)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    reqid = str(uuid.uuid4())
    details = {e["loc"][-1]: e["msg"] for e in exc.errors()}
    return JSONResponse(status_code=422, content=error_response("VALIDATION_ERROR", "Validation failed", reqid, details).dict())


@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    reqid = str(uuid.uuid4())
    body = error_response(exc.detail["code"], exc.detail["message"], reqid, exc.detail.get("details")).dict()
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    reqid = str(uuid.uuid4())
    return JSONResponse(status_code=500, content=error_response("INTERNAL_ERROR", "Internal server error", reqid).dict())


app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(records.router, prefix="/records", tags=["Records"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(audit.router, prefix="/audit", tags=["Audit"])
app.include_router(health.router, prefix="/health", tags=["System"])
