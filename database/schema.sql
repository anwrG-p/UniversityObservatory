-- ============================================================
-- schema.sql  –  University Observatory MAS
-- Compatible with both SQLite and PostgreSQL (minor tweaks needed
-- for PG: replace INTEGER PRIMARY KEY AUTOINCREMENT with SERIAL).
-- ============================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------
-- CLUSTERS  (created first – referenced by opportunities)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS clusters (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT,
    keywords    TEXT,           -- comma-separated top terms
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------
-- OPPORTUNITIES
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS opportunities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT    NOT NULL,   -- internship | scholarship | course | research_project | postdoc | fellowship
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL,
    source      TEXT,
    location    TEXT,
    eligibility TEXT,
    deadline    TEXT,
    url         TEXT,
    cluster_id  INTEGER REFERENCES clusters(id) ON DELETE SET NULL,
    category    TEXT,               -- output from ClassificationAgent
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------
-- USERS
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    email       TEXT    UNIQUE NOT NULL,
    profile     TEXT,               -- short bio / research area
    interests   TEXT,               -- comma-separated keywords
    skills      TEXT,               -- comma-separated skills
    level       TEXT DEFAULT 'bachelor',  -- bachelor | master | phd | postdoc | professor
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------
-- RECOMMENDATIONS
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS recommendations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id)          ON DELETE CASCADE,
    opportunity_id  INTEGER NOT NULL REFERENCES opportunities(id)  ON DELETE CASCADE,
    score           REAL    NOT NULL DEFAULT 0.0,
    reason          TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------
-- NOTIFICATIONS
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id)          ON DELETE CASCADE,
    opportunity_id  INTEGER NOT NULL REFERENCES opportunities(id)  ON DELETE CASCADE,
    status          TEXT    DEFAULT 'unread',   -- unread | read | dismissed
    message         TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------
-- INDEXES
-- ----------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_opp_type       ON opportunities(type);
CREATE INDEX IF NOT EXISTS idx_opp_cluster    ON opportunities(cluster_id);
CREATE INDEX IF NOT EXISTS idx_rec_user       ON recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_notif_user     ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notif_status   ON notifications(status);
