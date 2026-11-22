"""
Initialize analytics tables in the database.
Run this after adding the analytics models.
"""

from app.db.database import engine, Base
from app.models.analytics import VisitorSession, LoginSession, UsageEvent
from app.models.user import User
from app.models.generated_image import GeneratedImage
from app.models.ai_access import AIGenerationAttempt

def init_analytics_tables():
    """Create all analytics tables if they don't exist."""
    print("Initializing analytics tables...")
    
    try:
        # Import all models to ensure they're registered with Base
        Base.metadata.create_all(bind=engine, checkfirst=True)
        print("✓ Analytics tables created successfully!")
        print("  - visitor_sessions")
        print("  - login_sessions")
        print("  - usage_events")
    except Exception as e:
        print(f"✗ Failed to create analytics tables: {e}")
        raise

if __name__ == "__main__":
    init_analytics_tables()
