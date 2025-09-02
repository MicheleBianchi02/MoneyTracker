import logging
import logging.config

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.endpoints import categories, settings, transactions, users
from src.core.exceptions import AppException
from src.core.services.shutdown_service import shutdown
from src.core.services.startup import bootstrap_app, startup

bootstrap_app()
logger = logging.getLogger(__name__)


# Define the FastAPI app
app = FastAPI()


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.message,
            "code": exc.code,
        },
    )


@app.on_event("startup")
async def startup_event():
    logger.info("Backend API starting up.")
    startup()


@app.on_event("shutdown")
def shutdown_event():
    logger.info("Application shutdown")
    shutdown()


app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(users.router)
app.include_router(settings.router)
