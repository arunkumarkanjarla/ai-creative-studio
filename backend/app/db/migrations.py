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
            "ALTER TABLE voice_profiles ADD COLUMN IF NOT EXISTS region VARCHAR(50)",
            "ALTER TABLE voice_profiles ADD COLUMN IF NOT EXISTS country VARCHAR(100)",
            "ALTER TABLE voice_profiles ADD COLUMN IF NOT EXISTS accent VARCHAR(100)",
            "ALTER TABLE voice_profiles ADD COLUMN IF NOT EXISTS voice_type VARCHAR(50)",
            "CREATE INDEX IF NOT EXISTS ix_voice_profiles_region ON voice_profiles(region)",
            
            "ALTER TABLE tts_generations ADD COLUMN IF NOT EXISTS visitor_id VARCHAR(255)",
            "ALTER TABLE tts_generations ALTER COLUMN user_id DROP NOT NULL",
            "CREATE INDEX IF NOT EXISTS ix_tts_generations_visitor_id ON tts_generations(visitor_id)",
            
            "ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS visitor_id VARCHAR(255)",
            "ALTER TABLE transcriptions ALTER COLUMN user_id DROP NOT NULL",
            "CREATE INDEX IF NOT EXISTS ix_transcriptions_visitor_id ON transcriptions(visitor_id)",
        ]
        
        for migration in migrations:
            db.execute(text(migration))
        
        # Create audio_events table if it doesn't exist
        create_audio_events = """
        CREATE TABLE IF NOT EXISTS audio_events (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            visitor_id VARCHAR(255),
            ip_address INET,
            user_agent TEXT,
            browser VARCHAR(100),
            os VARCHAR(100),
            device VARCHAR(100),
            action VARCHAR(50) NOT NULL,
            studio VARCHAR(20) NOT NULL DEFAULT 'audio',
            voice_id VARCHAR(100),
            voice_name VARCHAR(255),
            language VARCHAR(10),
            text_length INTEGER,
            input_text TEXT,
            audio_duration FLOAT,
            file_size INTEGER,
            processing_time_ms INTEGER,
            status VARCHAR(20) NOT NULL,
            error_message TEXT,
            generation_id INTEGER,
            transcription_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        db.execute(text(create_audio_events))
        
        # Create indexes for audio_events
        audio_events_indexes = [
            "CREATE INDEX IF NOT EXISTS ix_audio_events_user_id ON audio_events(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_audio_events_visitor_id ON audio_events(visitor_id)",
            "CREATE INDEX IF NOT EXISTS ix_audio_events_action ON audio_events(action)",
            "CREATE INDEX IF NOT EXISTS ix_audio_events_status ON audio_events(status)",
            "CREATE INDEX IF NOT EXISTS ix_audio_events_created_at ON audio_events(created_at)",
        ]
        
        for index_sql in audio_events_indexes:
            db.execute(text(index_sql))

        # Video Studio indexes / safety alters (tables created via SQLAlchemy create_all)
        video_migrations = [
            "CREATE INDEX IF NOT EXISTS ix_video_projects_user_created ON video_projects (user_id, created_at)",
            "CREATE INDEX IF NOT EXISTS ix_video_projects_status_created ON video_projects (status, created_at)",
            "CREATE INDEX IF NOT EXISTS ix_video_events_action ON video_events (action)",
            "CREATE INDEX IF NOT EXISTS ix_video_events_status ON video_events (status)",
            "CREATE INDEX IF NOT EXISTS ix_video_events_created_at ON video_events (created_at)",
            "CREATE INDEX IF NOT EXISTS ix_video_events_project_id ON video_events (project_id)",
        ]
        for migration in video_migrations:
            try:
                db.execute(text(migration))
            except Exception as video_err:
                print(f"Video migration note: {video_err}")

        # Refresh tokens for persistent login (hashed opaque tokens)
        create_refresh_tokens = """
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            family_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ NOT NULL,
            user_agent TEXT,
            ip_address VARCHAR(64),
            revoked BOOLEAN NOT NULL DEFAULT FALSE,
            revoked_at TIMESTAMPTZ,
            revoked_reason VARCHAR(64),
            replaced_by_id INTEGER
        )
        """
        db.execute(text(create_refresh_tokens))
        refresh_indexes = [
            "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash ON refresh_tokens(token_hash)",
            "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_family_id ON refresh_tokens(family_id)",
            "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_expires_at ON refresh_tokens(expires_at)",
            "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_revoked ON refresh_tokens(revoked)",
            "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_active ON refresh_tokens(user_id, revoked, expires_at)",
            "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_family ON refresh_tokens(family_id, revoked)",
        ]
        for index_sql in refresh_indexes:
            db.execute(text(index_sql))

        # Optional per-scene background image for Video Studio
        try:
            db.execute(
                text(
                    "ALTER TABLE video_scenes ADD COLUMN IF NOT EXISTS image_path VARCHAR(500)"
                )
            )
        except Exception as scene_err:
            print(f"Video scene image_path migration note: {scene_err}")
        
        db.commit()
        print("✓ Database migrations completed")
        
    except Exception as e:
        db.rollback()
        print(f"Migration error (may be safe to ignore if already applied): {str(e)}")
