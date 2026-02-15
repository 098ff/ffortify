import uvicorn
from app.main import app
from app.setup.config import Config

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=Config.PORT,
        reload=True
    )