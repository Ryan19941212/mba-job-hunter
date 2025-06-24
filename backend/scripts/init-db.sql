-- MBA Job Hunter Database Initialization Script
-- This script sets up the initial database schema and configuration

-- Create database if it doesn't exist (handled by docker-compose)
-- CREATE DATABASE IF NOT EXISTS mba_job_hunter;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create custom types
DO $$ BEGIN
    CREATE TYPE job_status AS ENUM ('active', 'inactive', 'expired', 'filled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE application_status AS ENUM ('pending', 'applied', 'interview', 'offer', 'rejected', 'withdrawn');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE scrape_status AS ENUM ('pending', 'in_progress', 'completed', 'failed', 'skipped');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create function for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create function for generating short IDs
CREATE OR REPLACE FUNCTION generate_short_id()
RETURNS TEXT AS $$
BEGIN
    RETURN LOWER(SUBSTRING(ENCODE(GEN_RANDOM_BYTES(6), 'base64'), 1, 8));
END;
$$ LANGUAGE 'plpgsql';

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
END $$;