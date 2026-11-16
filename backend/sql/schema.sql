-- =====================================================
-- AI CREATIVE STUDIO
-- PostgreSQL schema: users, studios, access control
-- =====================================================

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    mobile VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'user'
        CHECK (role IN ('systemadministrator', 'user')),
    can_access_image BOOLEAN NOT NULL DEFAULT FALSE,
    can_access_audio BOOLEAN NOT NULL DEFAULT FALSE,
    can_access_video BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- TEXT-TO-IMAGE RESULTS
-- =====================================================

CREATE TABLE IF NOT EXISTS generated_images (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NULL REFERENCES users(id) ON DELETE SET NULL,
    visitor_id VARCHAR(64),
    prompt TEXT NOT NULL,
    negative_prompt TEXT,
    model_name VARCHAR(150),
    image_path TEXT,
    thumbnail_path TEXT,
    image_width INTEGER,
    image_height INTEGER,
    image_format VARCHAR(20),
    status VARCHAR(30) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    generation_time_seconds NUMERIC(10, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_generated_images_user_id
    ON generated_images(user_id);
CREATE INDEX IF NOT EXISTS idx_generated_images_visitor_id
    ON generated_images(visitor_id);
CREATE INDEX IF NOT EXISTS idx_generated_images_status
    ON generated_images(status);
CREATE INDEX IF NOT EXISTS idx_generated_images_created_at
    ON generated_images(created_at DESC);

DROP TRIGGER IF EXISTS trg_generated_images_updated_at ON generated_images;
CREATE TRIGGER trg_generated_images_updated_at
BEFORE UPDATE ON generated_images
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- TEXT-TO-AUDIO RESULTS
-- =====================================================

CREATE TABLE IF NOT EXISTS generated_audios (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NULL REFERENCES users(id) ON DELETE SET NULL,
    visitor_id VARCHAR(64),
    prompt TEXT NOT NULL,
    model_name VARCHAR(150),
    audio_path TEXT,
    audio_format VARCHAR(20),
    duration_seconds NUMERIC(10, 2),
    sample_rate INTEGER,
    status VARCHAR(30) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    generation_time_seconds NUMERIC(10, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_generated_audios_user_id
    ON generated_audios(user_id);
CREATE INDEX IF NOT EXISTS idx_generated_audios_visitor_id
    ON generated_audios(visitor_id);
CREATE INDEX IF NOT EXISTS idx_generated_audios_status
    ON generated_audios(status);
CREATE INDEX IF NOT EXISTS idx_generated_audios_created_at
    ON generated_audios(created_at DESC);

DROP TRIGGER IF EXISTS trg_generated_audios_updated_at ON generated_audios;
CREATE TRIGGER trg_generated_audios_updated_at
BEFORE UPDATE ON generated_audios
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- TEXT-TO-VIDEO RESULTS
-- =====================================================

CREATE TABLE IF NOT EXISTS generated_videos (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NULL REFERENCES users(id) ON DELETE SET NULL,
    visitor_id VARCHAR(64),
    prompt TEXT NOT NULL,
    negative_prompt TEXT,
    model_name VARCHAR(150),
    video_path TEXT,
    thumbnail_path TEXT,
    video_width INTEGER,
    video_height INTEGER,
    video_format VARCHAR(20),
    duration_seconds NUMERIC(10, 2),
    status VARCHAR(30) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    generation_time_seconds NUMERIC(10, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_generated_videos_user_id
    ON generated_videos(user_id);
CREATE INDEX IF NOT EXISTS idx_generated_videos_visitor_id
    ON generated_videos(visitor_id);
CREATE INDEX IF NOT EXISTS idx_generated_videos_status
    ON generated_videos(status);
CREATE INDEX IF NOT EXISTS idx_generated_videos_created_at
    ON generated_videos(created_at DESC);

DROP TRIGGER IF EXISTS trg_generated_videos_updated_at ON generated_videos;
CREATE TRIGGER trg_generated_videos_updated_at
BEFORE UPDATE ON generated_videos
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- AI STUDIO ACCESS SETTINGS (image / audio / video)
-- =====================================================

CREATE TABLE IF NOT EXISTS ai_studio_access_settings (
    id BIGSERIAL PRIMARY KEY,
    studio VARCHAR(20) NOT NULL UNIQUE
        CHECK (studio IN ('image', 'audio', 'video')),
    guest_access_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    guest_generation_limit INTEGER NOT NULL DEFAULT 3,
    guest_limit_period VARCHAR(20) NOT NULL DEFAULT 'day'
        CHECK (guest_limit_period IN ('day', 'week', 'month', 'lifetime')),
    authenticated_limit_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    authenticated_generation_limit INTEGER,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (guest_generation_limit >= 0),
    CHECK (
        authenticated_generation_limit IS NULL
        OR authenticated_generation_limit >= 0
    )
);

INSERT INTO ai_studio_access_settings (studio, guest_generation_limit)
VALUES
    ('image', 3),
    ('audio', 5),
    ('video', 3)
ON CONFLICT (studio) DO NOTHING;

-- =====================================================
-- GENERATION ATTEMPT TRACKING
-- =====================================================

CREATE TABLE IF NOT EXISTS ai_generation_attempts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NULL REFERENCES users(id) ON DELETE SET NULL,
    visitor_id VARCHAR(64),
    studio VARCHAR(20) NOT NULL
        CHECK (studio IN ('image', 'audio', 'video')),
    ip_address INET,
    user_agent TEXT,
    prompt TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'started'
        CHECK (status IN ('started', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ai_attempts_user_studio
    ON ai_generation_attempts(user_id, studio, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_attempts_visitor_studio
    ON ai_generation_attempts(visitor_id, studio, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_attempts_ip_studio
    ON ai_generation_attempts(ip_address, studio, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_attempts_created
    ON ai_generation_attempts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_attempts_status
    ON ai_generation_attempts(status);

-- =====================================================
-- EXISTING DATABASE FIX (safe to run again)
-- =====================================================

ALTER TABLE generated_images
    ADD COLUMN IF NOT EXISTS visitor_id VARCHAR(64);

ALTER TABLE generated_images
    ALTER COLUMN user_id DROP NOT NULL;

CREATE INDEX IF NOT EXISTS idx_generated_images_visitor_id
    ON generated_images(visitor_id);
