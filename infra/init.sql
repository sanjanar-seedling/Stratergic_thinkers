-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS seedlings;

-- Users / Founders table
CREATE TABLE IF NOT EXISTS seedlings.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    encryption_salt VARCHAR(255),
    public_key TEXT,
    privacy_settings JSONB DEFAULT '{}',
    intervention_preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- Founder Events (normalized from all ingestion sources)
CREATE TABLE IF NOT EXISTS seedlings.founder_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES seedlings.users(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,  -- 'voice', 'slack', 'journal', 'calendar', 'upload'
    event_type VARCHAR(50) NOT NULL,  -- 'reflection', 'decision', 'observation', 'review'
    scrubbed_text TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Decision Tracking (Judgment Quality Scorecard)
CREATE TABLE IF NOT EXISTS seedlings.decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES seedlings.users(id) ON DELETE CASCADE,
    event_id UUID REFERENCES seedlings.founder_events(id),
    title VARCHAR(500) NOT NULL,
    rationale TEXT,
    alternatives JSONB DEFAULT '[]',
    expected_outcome TEXT,
    expected_outcome_date DATE,
    actual_outcome TEXT,
    confidence_score DECIMAL(3,2),  -- 0.00 to 1.00
    outcome_score DECIMAL(3,2),
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'resolved', 'revised'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- Cognitive Bias Detections
CREATE TABLE IF NOT EXISTS seedlings.bias_detections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES seedlings.users(id) ON DELETE CASCADE,
    event_id UUID REFERENCES seedlings.founder_events(id),
    bias_type VARCHAR(100) NOT NULL,
    description TEXT,
    severity VARCHAR(20) DEFAULT 'medium',
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Knowledge Base chunks (RAG)
CREATE TABLE IF NOT EXISTS seedlings.knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_title VARCHAR(500),
    source_author VARCHAR(255),
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- OAuth Integration Tokens
CREATE TABLE IF NOT EXISTS seedlings.integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES seedlings.users(id) ON DELETE CASCADE,
    service VARCHAR(50) NOT NULL,  -- 'slack', 'google', 'gmail'
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    scopes TEXT,
    external_user_id VARCHAR(255),
    connected_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    UNIQUE(user_id, service)
);

-- Slack Installations (encrypted tokens per workspace)
CREATE TABLE IF NOT EXISTS seedlings.slack_installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES seedlings.users(id) ON DELETE CASCADE,
    slack_user_id VARCHAR(255) NOT NULL,
    slack_workspace_id VARCHAR(255) NOT NULL,
    slack_workspace_name VARCHAR(511),
    encrypted_user_token TEXT NOT NULL,
    user_token_nonce VARCHAR(255) NOT NULL,
    user_token_tag VARCHAR(255) NOT NULL,
    encrypted_bot_token TEXT,
    bot_token_nonce VARCHAR(255),
    bot_token_tag VARCHAR(255),
    refresh_token TEXT,
    refresh_token_expires_at TIMESTAMPTZ,
    user_scopes VARCHAR(1024),
    bot_scopes VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    installed_at TIMESTAMPTZ DEFAULT NOW(),
    token_expires_at TIMESTAMPTZ,
    last_accessed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, slack_workspace_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_events_user ON seedlings.founder_events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_created ON seedlings.founder_events(created_at);
CREATE INDEX IF NOT EXISTS idx_decisions_user ON seedlings.decisions(user_id);
CREATE INDEX IF NOT EXISTS idx_decisions_status ON seedlings.decisions(status);
CREATE INDEX IF NOT EXISTS idx_bias_user ON seedlings.bias_detections(user_id);
CREATE INDEX IF NOT EXISTS idx_integrations_user ON seedlings.integrations(user_id);
CREATE INDEX IF NOT EXISTS idx_slack_installations_user ON seedlings.slack_installations(user_id);
CREATE INDEX IF NOT EXISTS idx_slack_installations_workspace ON seedlings.slack_installations(slack_workspace_id);

-- Vector similarity indexes (IVFFlat for performance)
CREATE INDEX IF NOT EXISTS idx_events_embedding ON seedlings.founder_events
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding ON seedlings.knowledge_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
