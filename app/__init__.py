from flask import Flask
from app.modules.scheduler import start_scheduler

def create_app():
    app = Flask(__name__)
    
    # Register Blueprint (Routes)
    from app.routes import bp
    app.register_blueprint(bp)
    
    # Start Scheduler
    start_scheduler()
    
    return app

app = create_app()