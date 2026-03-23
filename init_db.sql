-- ==========================================================
-- EXTENSIONS
-- ==========================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==========================================================
-- JOBS TABLE (matches models.py)
-- ==========================================================
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(50) UNIQUE NOT NULL,
    title TEXT,
    company TEXT,
    location TEXT,
    description TEXT,
    requirements TEXT,
    skills TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs(job_id);

-- ==========================================================
-- SUBMISSIONS TABLE (matches models.py)
-- ==========================================================
CREATE TABLE IF NOT EXISTS submissions (
    id SERIAL PRIMARY KEY,
    submission_id VARCHAR(50) UNIQUE NOT NULL,
    resume_id INTEGER,
    candidate_name TEXT,
    full_name TEXT,
    resume_text TEXT,
    job_id TEXT,
    job_title TEXT,
    job_description TEXT,

    match_score FLOAT,
    semantic_similarity FLOAT,
    score_breakdown TEXT,
    fit_summary TEXT,
    confidence_band VARCHAR(20),
    final_recommendation TEXT,
    skill_matrix TEXT,
    fabrication_observations TEXT,

    scoring_status VARCHAR(50),
    report_path TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_submissions_submission_id ON submissions(submission_id);
CREATE INDEX IF NOT EXISTS idx_submissions_resume_id ON submissions(resume_id);

-- ==========================================================
-- CANDIDATE RESUMES (from resume_parsing_worker)
-- ==========================================================
CREATE TABLE IF NOT EXISTS candidate_resumes (
    id SERIAL PRIMARY KEY,

    file_path TEXT NOT NULL,

    resume_text TEXT,

    embedding JSONB,
    embedding_model TEXT,

    parse_hash TEXT,

    parsed_successfully BOOLEAN DEFAULT FALSE,
    parse_error TEXT,

    last_parsed_at TIMESTAMP,
    indexed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resumes_parsed ON candidate_resumes(parsed_successfully);
CREATE INDEX IF NOT EXISTS idx_resumes_updated ON candidate_resumes(updated_at);

-- ==========================================================
-- SCORING QUEUE (from queue_runner.py)
-- ==========================================================
CREATE TABLE IF NOT EXISTS scoring_queue (
    id SERIAL PRIMARY KEY,

    submission_id VARCHAR(50) UNIQUE NOT NULL,

    status VARCHAR(20) DEFAULT 'PENDING',
    attempts INTEGER DEFAULT 0,

    last_error TEXT,
    next_attempt_at TIMESTAMP,

    locked_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scoring_status ON scoring_queue(status);
CREATE INDEX IF NOT EXISTS idx_scoring_next_attempt ON scoring_queue(next_attempt_at);

-- ==========================================================
-- JOB MATCHING QUEUE (from job_matching_worker.py)
-- ==========================================================
CREATE TABLE IF NOT EXISTS job_matching_queue (
    id SERIAL PRIMARY KEY,

    jobid TEXT,
    job_title TEXT,
    job_description TEXT,
    poster_email TEXT,

    status VARCHAR(20) DEFAULT 'PENDING',
    attempts INTEGER DEFAULT 0,

    last_error TEXT,
    next_attempt_at TIMESTAMP,

    locked_at TIMESTAMP,
    locked_by TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matching_status ON job_matching_queue(status);
CREATE INDEX IF NOT EXISTS idx_matching_next_attempt ON job_matching_queue(next_attempt_at);

-- ==========================================================
-- OPTIONAL: FUTURE SAFETY (FOREIGN KEYS)
-- ==========================================================

-- Uncomment after stability:
-- ALTER TABLE submissions
-- ADD CONSTRAINT fk_resume
-- FOREIGN KEY (resume_id) REFERENCES candidate_resumes(id);

-- ==========================================================
-- DONE
-- ==========================================================