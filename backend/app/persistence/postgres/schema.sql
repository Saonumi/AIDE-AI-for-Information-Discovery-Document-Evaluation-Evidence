-- Reference DDL (PostgreSQL). The app creates these via SQLAlchemy `init_db()`;
-- this file documents the schema for docs/project.md and manual inspection.

CREATE TABLE IF NOT EXISTS users (
    id            VARCHAR(64) PRIMARY KEY,
    username      VARCHAR(128) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role          VARCHAR(16)  NOT NULL          -- USER | EMPLOYEE
);

CREATE TABLE IF NOT EXISTS documents (
    document_id        VARCHAR(64) PRIMARY KEY,
    filename           VARCHAR(512) NOT NULL,
    type               VARCHAR(32)  NOT NULL,     -- REGULATION | AMENDMENT | INTERNAL_POLICY
    document_number    VARCHAR(128),
    file_hash          VARCHAR(80)  NOT NULL,
    file_path          VARCHAR(1024),
    processing_status  VARCHAR(32)  DEFAULT 'QUARANTINED',
    approval_status    VARCHAR(32)  DEFAULT 'PENDING',
    injection_suspected BOOLEAN     DEFAULT FALSE,
    uploaded_by        VARCHAR(64),
    doc_metadata       JSONB,
    created_at         TIMESTAMP    DEFAULT now()
);

CREATE TABLE IF NOT EXISTS provisions (
    provision_id VARCHAR(64) PRIMARY KEY,
    document_id  VARCHAR(64) REFERENCES documents(document_id),
    lookup_key   VARCHAR(256),                    -- doc_number|Darticle|Kclause|Ppoint (resolution only)
    heading_path JSONB,
    article      VARCHAR(32),
    clause       VARCHAR(32),
    point        VARCHAR(32)
);

CREATE TABLE IF NOT EXISTS provision_versions (
    version_id         VARCHAR(64) PRIMARY KEY,
    provision_id       VARCHAR(64),
    document_id        VARCHAR(64),
    content            TEXT NOT NULL,
    valid_from         DATE NOT NULL,             -- half-open interval start
    valid_to_exclusive DATE,                      -- NULL == open-ended (infinity)
    approval_status    VARCHAR(32) DEFAULT 'PENDING',
    page               INTEGER,
    obligation         JSONB,
    scope              JSONB,
    created_at         TIMESTAMP DEFAULT now(),
    approved_at        TIMESTAMP
);

CREATE TABLE IF NOT EXISTS change_events (
    change_event_id     VARCHAR(64) PRIMARY KEY,
    amending_document_id VARCHAR(64),
    target_provision_id VARCHAR(64),
    operation           VARCHAR(32),              -- REPLACE_TEXT | INSERT_TEXT | DELETE_TEXT | REPEAL_PROVISION
    old_text            TEXT,
    new_text            TEXT,
    before_version_id   VARCHAR(64),
    after_version_id    VARCHAR(64),
    valid_from          DATE,
    source_page         INTEGER,
    review_status       VARCHAR(32) DEFAULT 'PENDING'
);

CREATE TABLE IF NOT EXISTS internal_artifacts (
    artifact_id           VARCHAR(64) PRIMARY KEY,
    document_id           VARCHAR(64),
    title                 VARCHAR(512),
    aligned_to_version_id VARCHAR(64),
    obligation            JSONB,
    page                  INTEGER
);

CREATE TABLE IF NOT EXISTS review_tasks (
    task_id     VARCHAR(64) PRIMARY KEY,
    task_type   VARCHAR(32),                      -- PARSING_REVIEW | CHANGE_EVENT_REVIEW | ...
    document_id VARCHAR(64),
    source_ref  VARCHAR(256),
    extracted   JSONB,
    diff_before TEXT,
    diff_after  TEXT,
    confidence  REAL DEFAULT 1.0,
    valid_from  DATE,
    status      VARCHAR(32) DEFAULT 'PENDING',
    decision    VARCHAR(32),
    decided_by  VARCHAR(64),
    created_at  TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id      VARCHAR(64) PRIMARY KEY,
    user_id       VARCHAR(64),
    role          VARCHAR(16),
    query         TEXT,
    query_date    DATE,
    payload       JSONB,                          -- retrieved_chunks, used/excluded versions, graph_paths
    status        VARCHAR(32),
    latency_ms    INTEGER,
    prompt_version VARCHAR(32),
    model_version VARCHAR(64),
    created_at    TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS feedback (
    id         VARCHAR(64) PRIMARY KEY,
    user_id    VARCHAR(64),
    query      TEXT,
    verdict    VARCHAR(32),
    created_at TIMESTAMP DEFAULT now()
);
