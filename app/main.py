from fastapi import FastAPI
from app.routes import router
from app.modules.scheduler import start_scheduler, shutdown_scheduler

app = FastAPI(title="Spotify Bot API")

app.include_router(router)


@app.on_event("startup")
async def startup_event():
    start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    shutdown_scheduler()