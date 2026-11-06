-- Esquema inicial de ocr-mcp. Significado de cada tabla: docs/modelo-datos.md.
-- Las claves, los tokens y los enlaces se guardan solo como hash (decisión 0006).

CREATE TABLE access_keys (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    is_public INTEGER NOT NULL DEFAULT 0 CHECK (is_public IN (0, 1)),
    pages_per_day INTEGER CHECK (pages_per_day > 0),
    pages_per_month INTEGER CHECK (pages_per_month > 0),
    max_active_jobs INTEGER CHECK (max_active_jobs > 0),
    created_at REAL NOT NULL,
    last_used_at REAL
);

CREATE TABLE oauth_clients (
    client_id TEXT PRIMARY KEY,
    info TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE oauth_pending (
    request_hash TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES oauth_clients (client_id) ON DELETE CASCADE,
    params TEXT NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE oauth_codes (
    code_hash TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES oauth_clients (client_id) ON DELETE CASCADE,
    key_id TEXT NOT NULL REFERENCES access_keys (id) ON DELETE CASCADE,
    params TEXT NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE oauth_tokens (
    token_hash TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('access', 'refresh')),
    client_id TEXT NOT NULL REFERENCES oauth_clients (client_id) ON DELETE CASCADE,
    key_id TEXT NOT NULL REFERENCES access_keys (id) ON DELETE CASCADE,
    scopes TEXT NOT NULL,
    resource TEXT NOT NULL,
    expires_at REAL NOT NULL,
    created_at REAL NOT NULL
);

CREATE INDEX oauth_tokens_by_key ON oauth_tokens (key_id);

-- Trabajos del core creados por este servidor. Al borrar una clave, sus
-- trabajos quedan sin dueño (nadie los ve) pero se conservan los conteos.
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    key_id TEXT REFERENCES access_keys (id) ON DELETE SET NULL,
    -- Huella del pedido (clave, contenido, artefactos y título): un reenvío
    -- idéntico devuelve el mismo trabajo sin consumir cuota otra vez.
    request_hash TEXT NOT NULL UNIQUE,
    is_public INTEGER NOT NULL CHECK (is_public IN (0, 1)),
    pages INTEGER NOT NULL CHECK (pages > 0),
    bytes INTEGER NOT NULL CHECK (bytes > 0),
    artifacts TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'processing', 'done', 'failed', 'blocked')),
    refunded INTEGER NOT NULL DEFAULT 0 CHECK (refunded IN (0, 1)),
    created_at REAL NOT NULL,
    finished_at REAL
);

CREATE INDEX jobs_by_key ON jobs (key_id, created_at);
CREATE INDEX jobs_public_by_day ON jobs (is_public, created_at);

CREATE TABLE uploads (
    id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    key_id TEXT NOT NULL REFERENCES access_keys (id) ON DELETE CASCADE,
    state TEXT NOT NULL CHECK (state IN ('waiting', 'ready', 'used')),
    bytes INTEGER,
    pages INTEGER,
    sha256 TEXT,
    expires_at REAL NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE downloads (
    token_hash TEXT PRIMARY KEY,
    key_id TEXT NOT NULL REFERENCES access_keys (id) ON DELETE CASCADE,
    job_id TEXT NOT NULL,
    artifact TEXT NOT NULL CHECK (artifact IN ('pdf', 'text', 'md')),
    expires_at REAL NOT NULL
);

CREATE TABLE admin_sessions (
    token_hash TEXT PRIMARY KEY,
    csrf TEXT NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE rate_limits (
    bucket TEXT NOT NULL,
    subject TEXT NOT NULL,
    at REAL NOT NULL
);

CREATE INDEX rate_limits_lookup ON rate_limits (bucket, subject, at);

CREATE TABLE settings (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
