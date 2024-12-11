from fastapi import FastAPI
from app.routes.line_webhook import line_router
from app.config import get_config

app = FastAPI()
app.include_router(line_router)

print("main")


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
