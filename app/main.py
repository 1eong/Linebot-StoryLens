import torch
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routes.line_webhook import line_router
from app.config import get_config
from app.resource_monitor import system_monitoring_middleware
from app.utils.logger import system_logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時執行
    system_logger.info("Application is starting up")
    
    # 釋放資源時執行
    yield
    
    system_logger.info("Application is shutting down")

app = FastAPI(
    title="LineBot AI Service",
    description="LineBot with AI-powered services",
    lifespan=lifespan
)
app.middleware("http")(system_monitoring_middleware)
app.include_router(line_router)

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


@app.get("/info")
def get_environment():
    config = get_config()
    return {
        "app_name": config.app_info.app_name,
        "author_name": config.app_info.author,
        "app_mode": config.env_config.app_mode,
        "host": config.env_config.host,
        "reload": config.env_config.reload,
    }
