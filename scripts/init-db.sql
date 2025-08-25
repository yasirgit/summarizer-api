-- Initialize database for Summarizer API

-- Create database if it doesn't exist (this won't run in the init script but shows intent)
-- CREATE DATABASE IF NOT EXISTS summarizer;

-- Grant privileges to user
GRANT ALL PRIVILEGES ON DATABASE summarizer TO "user";

-- Create extensions if needed
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The tables will be created by Alembic migrations
-- This script is mainly for any initial setup or seed data

-- Insert any seed data here if needed
-- For example, default configuration values, admin users, etc.

-- Log the initialization
\echo 'Database initialization completed successfully'
