import logging
import logging.config
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.endpoints import categories, settings, transactions, users
from src.core.exceptions import AppException
from src.core.services.startup import startup

# Create a logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(lineno)d - %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",  # z is the the offset to the UTC time in hours
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO",
            # "level": "WARNING",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/app.log",
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "formatter": "detailed",
            "level": "INFO",
        },
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["console", "file"],
            "level": "INFO",
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)

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


# Get a logger for this module
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    """Log app startup"""

    logger.info("Backend API starting up.")
    startup()


app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(users.router)
app.include_router(settings.router)
