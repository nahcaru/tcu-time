-- Stored PDF links for change detection
CREATE TABLE pdf_links (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url        TEXT UNIQUE NOT NULL,
  hash       TEXT NOT NULL,
  label      TEXT,
  updated_at TIMESTAMPTZ DEFAULT now()
);
