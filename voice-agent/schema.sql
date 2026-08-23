-- ==============================================================================
-- Voice AI Agent: Supabase PostgreSQL Database Schema with Row Level Security
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

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
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT unique_user_memory_key UNIQUE (user_id, key)
);

-- 4. Conversation Messages / Transcript Store
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Performance Indexes
CREATE INDEX IF NOT EXISTS idx_memories_user_key ON public.memories(user_id, key);
CREATE INDEX IF NOT EXISTS idx_memories_category ON public.memories(category);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON public.messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON public.messages(user_id);

-- 6. Enable Row Level Security (RLS)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- 7. RLS Policies (Allow Full Access for Backend Service Role and Users)
CREATE POLICY "Allow all access to users for service role" ON public.users
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all access to memories for service role" ON public.memories
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all access to messages for service role" ON public.messages
    FOR ALL USING (true) WITH CHECK (true);

-- 8. Seed Default Web Playground User
INSERT INTO public.users (id, full_name, email, timezone, preferred_persona)
VALUES ('web_user', 'Web Playground User', 'user@example.com', 'UTC', 'executive')
ON CONFLICT (id) DO NOTHING;
