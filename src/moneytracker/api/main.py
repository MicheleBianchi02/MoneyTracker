import argparse
import json
import logging
import logging.config
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from moneytracker.api.endpoints import categories, settings, transactions, users
from moneytracker.api.security import Token, create_access_token
from moneytracker.core.exceptions import (
    AppException,
    InternalServerErrorException,
    ServiceError,
    UnauthorizedException,
)
from moneytracker.core.repositories.abstract_unit_of_work import AbstractUnitOfWork
from moneytracker.core.services.shutdown_service import shutdown
from moneytracker.core.services.startup import (
    HOST_KEY,
    LOG_LEVEL_KEY,
    PORT_KEY,
    bootstrap_app,
    startup,
)
from moneytracker.core.services.user_service import UserService
from moneytracker.infrastructure.dependencies import get_uow
from moneytracker.tui.main import ALTERNATE_SCREEN_MODE, DELETE_SCREEN_MODE, run_tui

# WARNING: this backend works only on one processor, so it is not allowed to use
# --worker >1 inside uvicorn settings. This beacuse we are using threading.Lock and not
# multiprocessing.Lock inside the job_manager.

# This script is run two times. The first when initializing the server, and the
# second one by uvicorn. So don't put anything here since it will be run two times


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger(__name__)
    # Startup tasks
    logger.info("Backend API starting up...")
    startup()

    yield

    # shutdown task
    shutdown()
    logger.info("Application shutdown")


app = FastAPI(lifespan=lifespan)


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


app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(users.router)
app.include_router(settings.router)


@app.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> Token:
    try:
        user_service = UserService()
        user = user_service.authenticate(uow, form_data.username, form_data.password)
        if user is None:
            raise UnauthorizedException()

    except ServiceError:
        raise InternalServerErrorException()

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")


if __name__ == "__main__":
    server_config = bootstrap_app()

    # ---
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--terminal",
        action="store_true",
        help="Run the application in terminal mode (TUI) instead of launching the GUI.",
    )

    args = parser.parse_args()
    if args.terminal:
        print("Do you want to open an alternate screen (without scrolling)")
        print("or use this terminal window (all history will be deleted)?")

        # TODO: Save those settings in the database
        while True:
            choice = input("Choice (a for alternate, c for current window):")

            if choice == "a":
                mode = ALTERNATE_SCREEN_MODE
                break
            elif choice == "c":
                mode = DELETE_SCREEN_MODE
                break
            else:
                print("Wrong input, try again")
                continue

        startup()
        run_tui(mode)
        shutdown()

    else:
        # Don't need to start the server since the tui uses only the services

        # TODO: add description and app name
        host = server_config[HOST_KEY]
        port = server_config[PORT_KEY]
        log_level = server_config[LOG_LEVEL_KEY]

        log_level = log_level.lower()
        available_log = ["critical", "error", "warning", "info", "debug", "trace"]
        if log_level not in available_log:
            raise ValueError(
                f"{LOG_LEVEL_KEY} is not a valid parameter. Choose between {available_log}. "
                "Note: The required value is case insensitive."
            )

        # TODO: Return also api version and other required stuff
        data = {
            HOST_KEY: host,
            PORT_KEY: port,
        }
        json.dump(data, sys.stdout)
        print()  # just to have a space between logging and the json

        uvicorn.run(
            "moneytracker.api.main:app",
            host=host,
            port=int(port),
            log_level=log_level,
        )
