"""
Caching layer for analysis results.
Supports SQLite for local development, Cloud Storage/Postgres for production.
"""
import hashlib
import json
import sqlite3
import os
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from contextlib import contextmanager
from threading import Lock

from config import CACHE_DIR, CACHE_TTL_DAYS


@dataclass
class CacheEntry:
    key: str
    data: Dict[str, Any]
    created_at: float
    expires_at: float


class Cache:
    """Thread-safe cache with SQLite backend."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(CACHE_DIR, "cache.db")
        self._lock = Lock()
        self._init_db()

    def _init_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)
            """)
            conn.commit()

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _make_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """Create a deterministic cache key from parameters."""
        # Sort keys for consistent hashing
        param_str = json.dumps(params, sort_keys=True, default=str)
        hash_suffix = hashlib.sha256(param_str.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_suffix}"

    def get(self, prefix: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached result if not expired."""
        key = self._make_key(prefix, params)
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT data, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()

            if row and row["expires_at"] > time.time():
                return json.loads(row["data"])
            elif row:
                # Expired - delete
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
        return None

    def set(self, prefix: str, params: Dict[str, Any], data: Dict[str, Any], ttl_days: int = CACHE_TTL_DAYS) -> None:
        """Store result in cache."""
        key = self._make_key(prefix, params)
        now = time.time()
        expires_at = now + (ttl_days * 86400)

        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, data, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (key, json.dumps(data, default=str), now, expires_at)
            )
            conn.commit()

    def delete(self, prefix: str, params: Dict[str, Any]) -> None:
        """Delete a cache entry."""
        key = self._make_key(prefix, params)
        with self._get_conn() as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()

    def clear_expired(self) -> int:
        """Remove all expired entries. Returns count deleted."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM cache WHERE expires_at <= ?", (time.time(),)
            )
            conn.commit()
            return cursor.rowcount

    def clear_all(self) -> int:
        """Clear entire cache. Returns count deleted."""
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM cache")
            conn.commit()
            return cursor.rowcount

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM cache").fetchone()["c"]
            expired = conn.execute(
                "SELECT COUNT(*) as c FROM cache WHERE expires_at <= ?", (time.time(),)
            ).fetchone()["c"]
            size_bytes = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            return {
                "total_entries": total,
                "expired_entries": expired,
                "active_entries": total - expired,
                "size_mb": round(size_bytes / 1024 / 1024, 2),
            }


# Global cache instance
_cache: Optional[Cache] = None
_cache_lock = Lock()


def get_cache() -> Cache:
    """Get global cache instance (singleton)."""
    global _cache
    with _cache_lock:
        if _cache is None:
            _cache = Cache()
        return _cache


# =============================================================================
# CACHE KEY BUILDERS
# =============================================================================
def build_analysis_cache_key(request_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Build normalized cache key for analysis request."""
    # Remove fields that don't affect computation
    excluded = {"include_transitions", "include_landscape_metrics",
                "include_urban_growth", "include_environmental"}
    return {k: v for k, v in request_dict.items() if k not in excluded}


def build_tile_cache_key(layer: str, year: int, request_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Build cache key for tile request."""
    return {
        "layer": layer,
        "year": year,
        "district_id": request_dict.get("district_id"),
        "geojson": request_dict.get("geojson"),
        "classifier": request_dict.get("classifier"),
        "thresholds": request_dict.get("thresholds"),
        "baseline_year": request_dict.get("baseline_year"),
        "compare_year": request_dict.get("compare_year"),
        "season": request_dict.get("season"),
    }