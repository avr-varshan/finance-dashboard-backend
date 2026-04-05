-- Initial Schema SQL for Supabase
-- Copy and paste this into Supabase SQL Editor

-- Create custom types (enums)
CREATE TYPE role AS ENUM ('viewer', 'analyst', 'admin');
CREATE TYPE recordtype AS ENUM ('income', 'expense');
CREATE TYPE auditaction AS ENUM ('created', 'updated', 'deleted');

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(256) NOT NULL UNIQUE,
    hashed_password VARCHAR(256) NOT NULL,
    full_name VARCHAR(256) NOT NULL,
    role role NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Financial records table
CREATE TABLE financial_records (
    id UUID PRIMARY KEY,
    amount NUMERIC(12,2) NOT NULL,
    type recordtype NOT NULL,
    category VARCHAR(128) NOT NULL,
    date DATE NOT NULL,
    notes TEXT,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Record audit logs table
CREATE TABLE record_audit_logs (
    id UUID PRIMARY KEY,
    record_id UUID NOT NULL REFERENCES financial_records(id),
    action auditaction NOT NULL,
    changed_by UUID NOT NULL REFERENCES users(id),
    before_snapshot JSONB,
    after_snapshot JSONB,
    changed_at TIMESTAMPTZ NOT NULL
);

-- Revoked tokens table
CREATE TABLE revoked_tokens (
    id UUID PRIMARY KEY,
    jti VARCHAR(256) NOT NULL UNIQUE,
    revoked_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);