"""
database/db_manager.py
======================
Centralised database access layer using the Repository pattern.
Supports both SQLite and PostgreSQL (Supabase).
"""

import sqlite3
import logging
import os
import re
from typing import Any, Dict, List, Optional

import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Thread-safe connection manager and CRUD repository."""

    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = str(db_path)
        self.is_postgres = self.db_path.startswith(("postgres", "http"))
        
        if not self.is_postgres:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _connect(self):
        if self.is_postgres:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(self.db_path, cursor_factory=RealDictCursor)
            return conn
        else:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            return conn

    def _convert_sql(self, sql: str) -> str:
        """Convert SQLite syntax to PostgreSQL syntax if needed."""
        if not self.is_postgres:
            return sql
            
        # Replace ? with %s
        sql = sql.replace("?", "%s")
        # Replace INSERT OR IGNORE with ON CONFLICT DO NOTHING
        if "INSERT OR IGNORE INTO opportunities" in sql:
            sql = sql.replace("INSERT OR IGNORE INTO", "INSERT INTO")
            sql += " ON CONFLICT (id) DO NOTHING" # This requires id constraint, but url or title is better.
            # Actually, standardizing:
            sql = sql.replace("ON CONFLICT (id) DO NOTHING", "ON CONFLICT DO NOTHING")
            # If no unique constraint exists, PG doesn't support DO NOTHING without target.
            # Let's just remove OR IGNORE if postgres.
            sql = sql.replace("INSERT OR IGNORE INTO", "INSERT INTO")
            
        return sql

    def _ensure_schema(self):
        """Create tables from schema.sql if they don't exist."""
        if not os.path.exists(config.SCHEMA_PATH):
            logger.warning("schema.sql not found – skipping schema init")
            return
        with open(config.SCHEMA_PATH, "r", encoding="utf-8") as f:
            ddl = f.read()
            
        if self.is_postgres:
            ddl = ddl.replace("PRAGMA foreign_keys = ON;", "")
            ddl = ddl.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
            
        conn = self._connect()
        try:
            if self.is_postgres:
                with conn.cursor() as cur:
                    cur.execute(ddl)
            else:
                conn.executescript(ddl)
            conn.commit()
            logger.info("Database schema ready at %s", "PostgreSQL (Cloud)" if self.is_postgres else self.db_path)
        finally:
            conn.close()

    def execute(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute a single SQL statement and return all rows as dicts."""
        sql = self._convert_sql(sql)
        conn = self._connect()
        try:
            cur = conn.cursor() if self.is_postgres else conn.execute(sql, params)
            if self.is_postgres:
                cur.execute(sql, params)
            conn.commit()
            if cur.description:
                return [dict(row) for row in cur.fetchall()]
            return []
        finally:
            conn.close()

    def executemany(self, sql: str, params_list: List[tuple]) -> None:
        sql = self._convert_sql(sql)
        conn = self._connect()
        try:
            cur = conn.cursor() if self.is_postgres else conn
            if self.is_postgres:
                from psycopg2.extras import execute_batch
                execute_batch(cur, sql, params_list)
            else:
                cur.executemany(sql, params_list)
            conn.commit()
        finally:
            conn.close()

    def execute_script(self, script: str) -> None:
        if self.is_postgres:
            script = script.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
            script = script.replace("INSERT OR IGNORE INTO", "INSERT INTO")
        conn = self._connect()
        try:
            if self.is_postgres:
                with conn.cursor() as cur:
                    cur.execute(script)
            else:
                conn.executescript(script)
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Seed helpers
    # ------------------------------------------------------------------

    def seed_from_file(self, path: str) -> None:
        count = self.execute("SELECT COUNT(*) AS n FROM opportunities")[0]["n"]
        if count > 0:
            logger.info("Database already seeded (%d opportunities).", count)
            return
        if not os.path.exists(path):
            logger.warning("Seed file not found: %s", path)
            return
        with open(path, "r", encoding="utf-8") as f:
            self.execute_script(f.read())
        logger.info("Seeded database from %s", path)

    # ------------------------------------------------------------------
    # Opportunities CRUD
    # ------------------------------------------------------------------

    def get_opportunities(
        self,
        opp_type: Optional[str] = None,
        location: Optional[str] = None,
        cluster_id: Optional[int] = None,
        limit: int = 200,
    ) -> List[Dict]:
        where, params = [], []
        if opp_type:
            where.append("type = ?"); params.append(opp_type)
        if location:
            where.append("location LIKE ?"); params.append(f"%{location}%")
        if cluster_id is not None:
            where.append("cluster_id = ?"); params.append(cluster_id)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        sql = f"SELECT * FROM opportunities {clause} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return self.execute(sql, tuple(params))

    def get_opportunity(self, opp_id: int) -> Optional[Dict]:
        rows = self.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,))
        return rows[0] if rows else None

    def insert_opportunity(self, data: Dict) -> int:
        sql = """INSERT INTO opportunities
                 (type, title, description, source, location, eligibility,
                  deadline, url, cluster_id, category)
                 VALUES (?,?,?,?,?,?,?,?,?,?)"""
        if self.is_postgres:
            sql += " RETURNING id;"
            sql = self._convert_sql(sql)
            conn = self._connect()
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, (
                        data.get("type", ""), data.get("title", ""),
                        data.get("description", ""), data.get("source", ""),
                        data.get("location", ""), data.get("eligibility", ""),
                        data.get("deadline", ""), data.get("url", ""),
                        data.get("cluster_id"), data.get("category", ""),
                    ))
                    conn.commit()
                    return cur.fetchone()["id"]
            finally:
                conn.close()
        else:
            conn = self._connect()
            try:
                cur = conn.execute(sql, (
                    data.get("type", ""), data.get("title", ""),
                    data.get("description", ""), data.get("source", ""),
                    data.get("location", ""), data.get("eligibility", ""),
                    data.get("deadline", ""), data.get("url", ""),
                    data.get("cluster_id"), data.get("category", ""),
                ))
                conn.commit()
                return cur.lastrowid
            finally:
                conn.close()

    def update_opportunity_category(self, opp_id: int, category: str) -> None:
        self.execute("UPDATE opportunities SET category = ? WHERE id = ?", (category, opp_id))

    def update_opportunity_cluster(self, opp_id: int, cluster_id: int) -> None:
        self.execute("UPDATE opportunities SET cluster_id = ? WHERE id = ?", (cluster_id, opp_id))

    # ------------------------------------------------------------------
    # Users CRUD
    # ------------------------------------------------------------------

    def get_users(self) -> List[Dict]:
        return self.execute("SELECT * FROM users ORDER BY name")

    def get_user(self, user_id: int) -> Optional[Dict]:
        rows = self.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return rows[0] if rows else None

    def insert_user(self, data: Dict) -> int:
        sql = """INSERT INTO users (name, email, profile, interests, skills, level)
                 VALUES (?,?,?,?,?,?)"""
        if self.is_postgres:
            sql += " RETURNING id;"
            sql = self._convert_sql(sql)
            conn = self._connect()
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, (
                        data["name"], data["email"],
                        data.get("profile", ""), data.get("interests", ""),
                        data.get("skills", ""), data.get("level", "bachelor"),
                    ))
                    conn.commit()
                    return cur.fetchone()["id"]
            finally:
                conn.close()
        else:
            conn = self._connect()
            try:
                cur = conn.execute(sql, (
                    data["name"], data["email"],
                    data.get("profile", ""), data.get("interests", ""),
                    data.get("skills", ""), data.get("level", "bachelor"),
                ))
                conn.commit()
                return cur.lastrowid
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Clusters CRUD
    # ------------------------------------------------------------------

    def get_clusters(self) -> List[Dict]:
        return self.execute("SELECT * FROM clusters ORDER BY id")

    def get_cluster(self, cluster_id: int) -> Optional[Dict]:
        rows = self.execute("SELECT * FROM clusters WHERE id = ?", (cluster_id,))
        return rows[0] if rows else None

    def upsert_cluster(self, cluster_id: int, name: str, keywords: str) -> None:
        existing = self.get_cluster(cluster_id)
        if existing:
            self.execute("UPDATE clusters SET name=?, keywords=? WHERE id=?", (name, keywords, cluster_id))
        else:
            self.execute("INSERT INTO clusters (id, name, keywords) VALUES (?,?,?)", (cluster_id, name, keywords))

    # ------------------------------------------------------------------
    # Recommendations CRUD
    # ------------------------------------------------------------------

    def get_recommendations(self, user_id: int) -> List[Dict]:
        sql = """
            SELECT r.*, o.title, o.type, o.location, o.deadline, o.url
            FROM recommendations r
            JOIN opportunities o ON r.opportunity_id = o.id
            WHERE r.user_id = ?
            ORDER BY r.score DESC
        """
        return self.execute(sql, (user_id,))

    def insert_recommendation(self, user_id: int, opp_id: int, score: float, reason: str = "") -> None:
        self.execute("DELETE FROM recommendations WHERE user_id=? AND opportunity_id=?", (user_id, opp_id))
        self.execute("INSERT INTO recommendations (user_id, opportunity_id, score, reason) VALUES (?,?,?,?)", (user_id, opp_id, score, reason))

    def clear_recommendations(self, user_id: int) -> None:
        self.execute("DELETE FROM recommendations WHERE user_id=?", (user_id,))

    # ------------------------------------------------------------------
    # Notifications CRUD
    # ------------------------------------------------------------------

    def get_notifications(self, user_id: int, status: Optional[str] = None) -> List[Dict]:
        sql = """
            SELECT n.*, o.title AS opp_title, o.type AS opp_type
            FROM notifications n
            JOIN opportunities o ON n.opportunity_id = o.id
            WHERE n.user_id = ?
        """
        params: list = [user_id]
        if status:
            sql += " AND n.status = ?"
            params.append(status)
        sql += " ORDER BY n.created_at DESC"
        return self.execute(sql, tuple(params))

    def insert_notification(self, user_id: int, opp_id: int, message: str) -> None:
        self.execute("INSERT INTO notifications (user_id, opportunity_id, message) VALUES (?,?,?)", (user_id, opp_id, message))

    def mark_notification_read(self, notif_id: int) -> None:
        self.execute("UPDATE notifications SET status='read' WHERE id=?", (notif_id,))

    # ------------------------------------------------------------------
    # Stats helpers
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        opp_count     = self.execute("SELECT COUNT(*) AS n FROM opportunities")[0]["n"]
        user_count    = self.execute("SELECT COUNT(*) AS n FROM users")[0]["n"]
        cluster_count = self.execute("SELECT COUNT(*) AS n FROM clusters")[0]["n"]
        rec_count     = self.execute("SELECT COUNT(*) AS n FROM recommendations")[0]["n"]
        notif_unread  = self.execute("SELECT COUNT(*) AS n FROM notifications WHERE status='unread'")[0]["n"]
        by_type = self.execute("SELECT type, COUNT(*) AS cnt FROM opportunities GROUP BY type")
        return {
            "opportunities": opp_count,
            "users": user_count,
            "clusters": cluster_count,
            "recommendations": rec_count,
            "unread_notifications": notif_unread,
            "by_type": {row["type"]: row["cnt"] for row in by_type},
        }

