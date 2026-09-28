-- Voice AI Agent: Neon Serverless PostgreSQL Database Schema

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Optional: Enable pgvector for semantic memory embeddings if available on Neon
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'pgvector extension not installed or not supported in this environment; skipping.';
END $$;

-- 2. Users / User Profiles Table
CREATE TABLE IF NOT EXISTS public.users (
    id TEXT PRIMARY KEY,
    full_name TEXT,
    timezone TEXT DEFAULT 'UTC',
    preferred_persona TEXT DEFAULT 'executive',
    email TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Long-Term Semantic Memories Table
CREATE TABLE IF NOT EXISTS public.memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    confidence FLOAT DEFAULT 1.0,
    source TEXT DEFAULT 'conversation',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Conversation Messages / Transcript Store
CREATE TABLE IF NOT EXISTS public.messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Pending Actions Store (Deterministic confirmation ledger)
CREATE TABLE IF NOT EXISTS public.pending_actions (
    id TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    arguments JSONB NOT NULL DEFAULT '{}'::jsonb,
    arguments_hash TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    session_id TEXT,
    proposal_summary TEXT,
    consumed BOOLEAN DEFAULT FALSE,
    consumed_at TIMESTAMPTZ,
    state TEXT DEFAULT 'pending' CHECK (state IN ('pending', 'approved', 'rejected', 'expired')),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 6. Execution Receipts / Ledger (Idempotency and deduplication)
CREATE TABLE IF NOT EXISTS public.execution_receipts (
    id TEXT PRIMARY KEY,
    action_id TEXT,
    tool_name TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    session_id TEXT,
    arguments_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('success', 'failed')),
    result_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 7. Task Workflows & Checkpoints (Durable multi-step state)
CREATE TABLE IF NOT EXISTS public.tasks (
    task_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    session_id TEXT,
    goal TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('executing', 'awaiting_confirmation', 'awaiting_clarification', 'completed', 'failed')),
    current_step INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 0,
    steps JSONB DEFAULT '[]'::jsonb,
    results JSONB DEFAULT '{}'::jsonb,
    spoken_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 8. Performance Indexes
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON public.memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_category ON public.memories(category);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON public.messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON public.messages(user_id);
CREATE INDEX IF NOT EXISTS idx_pending_actions_user_id ON public.pending_actions(user_id);
CREATE INDEX IF NOT EXISTS idx_pending_actions_hash ON public.pending_actions(arguments_hash);
CREATE INDEX IF NOT EXISTS idx_execution_receipts_user_id ON public.execution_receipts(user_id);
CREATE INDEX IF NOT EXISTS idx_execution_receipts_hash ON public.execution_receipts(arguments_hash);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON public.tasks(user_id);
-- 9. Database Row-Level Security (RLS) & Multi-Tenant Isolation
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;
        GRANT USAGE ON SCHEMA public TO app_user;
        GRANT ALL ON ALL TABLES IN SCHEMA public TO app_user;
        GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO app_user;
        GRANT app_user TO CURRENT_USER;
    END IF;
END $$;

CREATE OR REPLACE FUNCTION public.current_app_user() RETURNS TEXT AS $$
BEGIN
    RETURN NULLIF(COALESCE(
        current_setting('app.current_user_id', true),
        current_setting('request.jwt.claim.sub', true)
    ), '');
END;
$$ LANGUAGE plpgsql STABLE;

ALTER TABLE public.memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memories FORCE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages FORCE ROW LEVEL SECURITY;
ALTER TABLE public.pending_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pending_actions FORCE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks FORCE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users FORCE ROW LEVEL SECURITY;
ALTER TABLE public.execution_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.execution_receipts FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_isolation_memories ON public.memories;
CREATE POLICY user_isolation_memories ON public.memories
    FOR ALL
    USING (user_id = public.current_app_user())
    WITH CHECK (user_id = public.current_app_user());

DROP POLICY IF EXISTS user_isolation_messages ON public.messages;
CREATE POLICY user_isolation_messages ON public.messages
    FOR ALL
    USING (user_id = public.current_app_user())
    WITH CHECK (user_id = public.current_app_user());

DROP POLICY IF EXISTS user_isolation_pending_actions ON public.pending_actions;
CREATE POLICY user_isolation_pending_actions ON public.pending_actions
    FOR ALL
    USING (user_id = public.current_app_user())
    WITH CHECK (user_id = public.current_app_user());

DROP POLICY IF EXISTS user_isolation_tasks ON public.tasks;
CREATE POLICY user_isolation_tasks ON public.tasks
    FOR ALL
    USING (user_id = public.current_app_user())
    WITH CHECK (user_id = public.current_app_user());

DROP POLICY IF EXISTS user_isolation_users ON public.users;
CREATE POLICY user_isolation_users ON public.users
    FOR ALL
    USING (id = public.current_app_user())
    WITH CHECK (id = public.current_app_user());

DROP POLICY IF EXISTS user_isolation_execution_receipts ON public.execution_receipts;
CREATE POLICY user_isolation_execution_receipts ON public.execution_receipts
    FOR ALL
    USING (user_id = public.current_app_user())
    WITH CHECK (user_id = public.current_app_user());
