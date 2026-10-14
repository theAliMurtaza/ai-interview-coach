BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TYPE subscription_plan AS ENUM ('free', 'pro');

CREATE TYPE interview_role AS ENUM ('frontend', 'backend', 'fullstack', 'mobile', 'data-ai', 'devops', 'qa');

CREATE TYPE interview_type AS ENUM ('technical', 'behavioral', 'system-design', 'mixed');

CREATE TYPE difficulty_level AS ENUM ('internship', 'junior', 'mid');

CREATE TYPE interview_status AS ENUM ('pending', 'in_progress', 'completed', 'abandoned');

CREATE TABLE users (
    id UUID NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    hashed_password VARCHAR(255), 
    full_name VARCHAR(255), 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    is_verified BOOLEAN DEFAULT false NOT NULL, 
    oauth_provider VARCHAR(50), 
    oauth_sub VARCHAR(255), 
    plan subscription_plan DEFAULT 'free' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    UNIQUE (email)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE refresh_tokens (
    id UUID NOT NULL, 
    user_id UUID, 
    token VARCHAR(512) NOT NULL, 
    revoked BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    UNIQUE (token)
);

CREATE UNIQUE INDEX ix_refresh_tokens_token ON refresh_tokens (token);

CREATE TABLE interviews (
    id UUID NOT NULL, 
    user_id UUID, 
    role interview_role NOT NULL, 
    interview_type interview_type NOT NULL, 
    difficulty difficulty_level NOT NULL, 
    question_count INTEGER DEFAULT '6' NOT NULL, 
    status interview_status DEFAULT 'pending' NOT NULL, 
    overall_score FLOAT, 
    communication_score FLOAT, 
    technical_score FLOAT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE questions (
    id UUID NOT NULL, 
    interview_id UUID, 
    order_index INTEGER NOT NULL, 
    text TEXT NOT NULL, 
    expected_concepts JSON DEFAULT '[]' NOT NULL, 
    follow_up_hint TEXT, 
    is_follow_up BOOLEAN DEFAULT false NOT NULL, 
    parent_question_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(interview_id) REFERENCES interviews (id) ON DELETE CASCADE, 
    FOREIGN KEY(parent_question_id) REFERENCES questions (id) ON DELETE SET NULL
);

CREATE TABLE answers (
    id UUID NOT NULL, 
    question_id UUID, 
    transcript TEXT NOT NULL, 
    duration_seconds FLOAT NOT NULL, 
    word_count INTEGER DEFAULT '0' NOT NULL, 
    audio_file_url VARCHAR(1024), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    UNIQUE (question_id), 
    FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE
);

CREATE TABLE evaluations (
    id UUID NOT NULL, 
    answer_id UUID, 
    overall_score FLOAT NOT NULL, 
    communication_score FLOAT NOT NULL, 
    technical_score FLOAT, 
    star_score FLOAT, 
    wpm INTEGER NOT NULL, 
    filler_count INTEGER NOT NULL, 
    filler_breakdown JSON DEFAULT '{}' NOT NULL, 
    concepts_hit JSON DEFAULT '[]' NOT NULL, 
    concepts_missed JSON DEFAULT '[]' NOT NULL, 
    feedback TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    UNIQUE (answer_id), 
    FOREIGN KEY(answer_id) REFERENCES answers (id) ON DELETE CASCADE
);

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

-- Running upgrade 0001 -> 0002

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE resumes (
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    user_id UUID NOT NULL, 
    filename VARCHAR(255) NOT NULL, 
    file_url VARCHAR(1024), 
    raw_text TEXT NOT NULL, 
    skills JSON NOT NULL, 
    projects JSON NOT NULL, 
    experience JSON NOT NULL, 
    education JSON NOT NULL, 
    certifications JSON NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE jobs (
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    user_id UUID NOT NULL, 
    title VARCHAR(255) NOT NULL, 
    company VARCHAR(255), 
    raw_text TEXT NOT NULL, 
    required_skills JSON NOT NULL, 
    preferred_skills JSON NOT NULL, 
    responsibilities JSON NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE learning_plans (
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    user_id UUID NOT NULL, 
    title VARCHAR(255) NOT NULL, 
    duration_days INTEGER NOT NULL, 
    focus_topics JSON NOT NULL, 
    daily_tasks JSON NOT NULL, 
    milestones JSON NOT NULL, 
    based_on_interview_ids JSON NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE user_topic_performances (
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    user_id UUID NOT NULL, 
    topic VARCHAR(100) NOT NULL, 
    attempts INTEGER NOT NULL, 
    avg_score FLOAT NOT NULL, 
    last_practiced_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    trend VARCHAR(50) NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_user_topic UNIQUE (user_id, topic), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE knowledge_chunks (
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    topic VARCHAR(100) NOT NULL, 
    source VARCHAR(255) NOT NULL, 
    content TEXT NOT NULL, 
    chunk_metadata JSON NOT NULL, 
    embedding VECTOR(1536), 
    embedding_model VARCHAR(100), 
    PRIMARY KEY (id)
);

CREATE TYPE subscription_status AS ENUM ('active', 'canceled', 'past_due', 'unpaid', 'trialing', 'incomplete', 'incomplete_expired', 'paused');

CREATE TABLE subscriptions (
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    user_id UUID NOT NULL, 
    stripe_customer_id VARCHAR(255) NOT NULL, 
    stripe_subscription_id VARCHAR(255) NOT NULL, 
    plan subscription_plan NOT NULL, 
    status subscription_status NOT NULL, 
    stripe_created_at INTEGER NOT NULL, 
    current_period_end TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE webhook_events (
    id VARCHAR(255) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_resumes_user_id ON resumes (user_id);

CREATE INDEX ix_jobs_user_id ON jobs (user_id);

CREATE INDEX ix_learning_plans_user_id ON learning_plans (user_id);

CREATE INDEX ix_user_topic_performances_user_id ON user_topic_performances (user_id);

CREATE UNIQUE INDEX ix_subscriptions_user_id ON subscriptions (user_id);

CREATE INDEX ix_knowledge_chunks_topic ON knowledge_chunks (topic);

CREATE INDEX ix_user_topic_performances_topic ON user_topic_performances (topic);

CREATE INDEX ix_subscriptions_stripe_customer_id ON subscriptions (stripe_customer_id);

CREATE UNIQUE INDEX ix_subscriptions_stripe_subscription_id ON subscriptions (stripe_subscription_id);

ALTER TABLE users ADD CONSTRAINT uq_oauth_identity UNIQUE (oauth_provider, oauth_sub);

UPDATE refresh_tokens SET revoked = true;

CREATE INDEX ix_interviews_user_id ON interviews (user_id);

CREATE INDEX ix_questions_interview_id ON questions (interview_id);

CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens (user_id);

ALTER TABLE questions ADD CONSTRAINT uq_question_parent UNIQUE (parent_question_id);

ALTER TABLE users ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE users ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE refresh_tokens ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE refresh_tokens ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE interviews ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE interviews ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE questions ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE questions ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE answers ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE answers ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE evaluations ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE evaluations ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE refresh_tokens ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE interviews ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE questions ALTER COLUMN interview_id SET NOT NULL;

ALTER TABLE answers ALTER COLUMN question_id SET NOT NULL;

ALTER TABLE evaluations ALTER COLUMN answer_id SET NOT NULL;

UPDATE alembic_version SET version_num='0002' WHERE alembic_version.version_num = '0001';

COMMIT;

