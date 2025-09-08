import logging
import logging.config

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from src.api.endpoints import categories, settings, transactions, users
from src.api.security import Token, create_access_token
from src.core.exceptions import (
    AppException,
    InternalServerErrorException,
    ServiceError,
    UnauthorizedException,
)
from src.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from src.core.services.shutdown_service import shutdown
from src.core.services.startup import bootstrap_app, startup
from src.core.services.user_service import UserService
from src.infrastructure.dependencies import get_uow

app = FastAPI()

bootstrap_app()
logger = logging.getLogger(__name__)

user_service = UserService()


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.message,
            "code": exc.code,
        },
    )


@app.exception_handler(UnauthorizedException)
async def unauthorized_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        headers={"WWW-Authenticate": "Bearer"},
        content={
            "message": exc.message,
            "code": exc.code,
        },
    )


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    # Rewrite only the 401 code to add the custom message and code
    if exc.status_code == 401:
        return JSONResponse(
            status_code=401,
            content={
                "message": UnauthorizedException().message,
                "code": UnauthorizedException().code,
            },
            headers={"WWW-Authenticate": "Bearer"},  # keep auth header
        )
    # fallback to default for all other HTTPException
    return await request.app.default_exception_handler(request, exc)


@app.on_event("startup")
async def startup_event():
    logger.info("Backend API starting up.")
    startup()


@app.on_event("shutdown")
async def shutdown_event():
    shutdown()
    logger.info("Application shutdown")


app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(users.router)
app.include_router(settings.router)


@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> Token:
    try:
        user = user_service.authenticate(uow, form_data.username, form_data.password)
        if not user:
            raise UnauthorizedException()

    except ServiceError:
        raise InternalServerErrorException()

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")
