CREATE TABLE IF NOT EXISTS conversations (
    uuid        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    summary     TEXT DEFAULT '',
    created_at  TEXT NOT NULL,
    full_text   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS messages (
    uuid        TEXT PRIMARY KEY,
    conv_uuid   TEXT NOT NULL REFERENCES conversations(uuid),
    sender      TEXT NOT NULL,
    text        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(
    name,
    summary,
    full_text,
    content='conversations',
    content_rowid='rowid'
);
