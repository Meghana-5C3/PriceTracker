from app import create_app, start_scheduler
from app.models.models import db
import logging

# Configure standard Python logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Launch Factory
app = create_app()

with app.app_context():
    # Initialize SQLite database file if it doesn't exist
    db.create_all()
    # Safely kick off APScheduler in the background
    start_scheduler(app)

if __name__ == "__main__":
    # Start the Flask development server on :5000
    app.run(debug=True, use_reloader=False)
