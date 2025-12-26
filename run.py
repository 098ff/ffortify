from app import create_app
from app.setup.config import Config

app = create_app()

if __name__ == "__main__":
    app.run(port=Config.PORT)