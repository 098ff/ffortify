from fastapi import FastAPI
from app.routes import router
from app.modules.scheduler import start_scheduler, shutdown_scheduler

app = FastAPI(title="Spotify Bot API")

app.include_router(router)


@app.on_event("startup")
async def startup_event():
    start_scheduler()
    # Initialize Rich Menus (version-aware: recreates if layout changed)
    try:
        from app.modules.rich_menu import initialize_rich_menus
        initialize_rich_menus()
    except Exception as e:
        print(f"⚠️ Rich Menu init error (non-critical): {e}")


@app.on_event("shutdown")
async def shutdown_event():
    shutdown_scheduler()