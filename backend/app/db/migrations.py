"""
Database migrations for adding new columns
"""
from sqlalchemy import text
from sqlalchemy.orm import Session


def run_migrations(db: Session):
    """Run all pending migrations"""
    try:
        # Add visitor_id columns to audio tables if they don't exist
        migrations = [
            "ALTER TABLE voice_profiles ADD COLUMN IF NOT EXISTS visitor_id VARCHAR(255)",
            "CREATE INDEX IF NOT EXISTS ix_voice_profiles_visitor_id ON voice_profiles(visitor_id)",
            
            "ALTER TABLE tts_generations ADD COLUMN IF NOT EXISTS visitor_id VARCHAR(255)",
            "ALTER TABLE tts_generations ALTER COLUMN user_id DROP NOT NULL",
            "CREATE INDEX IF NOT EXISTS ix_tts_generations_visitor_id ON tts_generations(visitor_id)",
            
            "ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS visitor_id VARCHAR(255)",
            "ALTER TABLE transcriptions ALTER COLUMN user_id DROP NOT NULL",
            "CREATE INDEX IF NOT EXISTS ix_transcriptions_visitor_id ON transcriptions(visitor_id)",
        ]
        
        for migration in migrations:
            db.execute(text(migration))
        
        db.commit()
        print("✓ Database migrations completed")
        
    except Exception as e:
        db.rollback()
        print(f"Migration error (may be safe to ignore if already applied): {str(e)}")
