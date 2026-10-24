"""
reaper_service.py - Phase 5: Automated TTL Reaper Service
Automatically purges guest data older than 2 hours to maintain data privacy
and control storage usage.

Optimized with:
- Set-based batch SQL deletions (zero loops)
- Asynchronous background execution (zero API latency impact)
- Safe namespaced filesystem cleanup for guest directories
"""

import os
import time
import shutil
import logging
import asyncio
from typing import Dict, Any
import psycopg

from config import DATABASE_URL

logger = logging.getLogger("travel_reaper")

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_STORAGE_DIR = os.path.join(BACKEND_DIR, "tenant_storage")

# Background task reference to prevent garbage collection
_reaper_task: asyncio.Task = None
_reaper_stats: Dict[str, Any] = {
    "last_run": None,
    "last_duration_ms": 0,
    "total_purged_memories": 0,
    "total_purged_documents": 0,
    "total_purged_users": 0,
    "total_purged_dirs": 0,
    "status": "idle"
}


def purge_expired_guest_data(max_age_hours: float = 2.0) -> Dict[str, Any]:
    """
    Executes set-based batch purging of guest data exceeding the TTL threshold (default 2 hours).
    Uses high-speed relational queries to eliminate iteration latency.
    """
    t0 = time.time()
    cutoff_seconds = max_age_hours * 3600
    now_epoch = time.time()

    purged_memories = 0
    purged_documents = 0
    purged_users = 0
    purged_dirs = 0

    # 1. Database Batch Deletions (Set-based, single roundtrip)
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    # A. Purge expired episodic memory
                    cur.execute(
                        """
                        DELETE FROM episodic_memory
                        WHERE (owner_id LIKE 'guest_%%' OR (metadata->>'is_guest')::boolean = true)
                          AND created_at < NOW() - (%s * INTERVAL '1 hour');
                        """,
                        (max_age_hours,)
                    )
                    purged_memories = cur.rowcount

                    # B. Purge expired guest tenant documents & vector embeddings
                    cur.execute(
                        """
                        DELETE FROM tenant_documents
                        WHERE owner_id LIKE 'guest_%%'
                          AND created_at < NOW() - (%s * INTERVAL '1 hour');
                        """,
                        (max_age_hours,)
                    )
                    purged_documents = cur.rowcount

                    # C. Purge expired guest users if persisted
                    cur.execute(
                        """
                        DELETE FROM users
                        WHERE (is_guest = TRUE OR id LIKE 'guest_%%')
                          AND created_at < NOW() - (%s * INTERVAL '1 hour');
                        """,
                        (max_age_hours,)
                    )
                    purged_users = cur.rowcount

                    conn.commit()
        except Exception as e:
            logger.error(f"[TTL Reaper DB Error]: {e}")

    # 2. Filesystem Namespaced Directory Cleanup (Only guest_* directories older than cutoff)
    if os.path.exists(BASE_STORAGE_DIR):
        try:
            for entry in os.scandir(BASE_STORAGE_DIR):
                if entry.is_dir() and entry.name.startswith("guest_"):
                    # Check directory age
                    try:
                        dir_mtime = entry.stat().st_mtime
                        if (now_epoch - dir_mtime) >= cutoff_seconds:
                            shutil.rmtree(entry.path, ignore_errors=True)
                            purged_dirs += 1
                    except OSError:
                        pass
        except Exception as fs_err:
            logger.warning(f"[TTL Reaper FS Error]: {fs_err}")

    elapsed_ms = round((time.time() - t0) * 1000, 2)

    # Update global observability stats
    _reaper_stats["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    _reaper_stats["last_duration_ms"] = elapsed_ms
    _reaper_stats["total_purged_memories"] += purged_memories
    _reaper_stats["total_purged_documents"] += purged_documents
    _reaper_stats["total_purged_users"] += purged_users
    _reaper_stats["total_purged_dirs"] += purged_dirs
    _reaper_stats["status"] = "active"

    if purged_memories or purged_documents or purged_dirs:
        logger.info(
            f"[TTL Reaper] Purged {purged_memories} memories, {purged_documents} documents, "
            f"{purged_users} guest users, {purged_dirs} storage folders in {elapsed_ms}ms"
        )

    return {
        "purged_memories": purged_memories,
        "purged_documents": purged_documents,
        "purged_users": purged_users,
        "purged_storage_dirs": purged_dirs,
        "duration_ms": elapsed_ms,
        "cutoff_hours": max_age_hours,
    }


def get_reaper_stats() -> Dict[str, Any]:
    """Returns telemetry of the TTL reaper."""
    return _reaper_stats.copy()


async def ttl_reaper_loop(interval_seconds: int = 1800, max_age_hours: float = 2.0):
    """
    Non-blocking periodic background task to purge expired guest data.
    Runs every 30 minutes by default.
    """
    logger.info(f"[TTL Reaper] Background loop initialized (interval: {interval_seconds}s, TTL: {max_age_hours}h)")
    # Initial light run upon server startup
    try:
        purge_expired_guest_data(max_age_hours=max_age_hours)
    except Exception as e:
        logger.warning(f"[TTL Reaper Initial Run Warning]: {e}")

    while True:
        try:
            await asyncio.sleep(interval_seconds)
            purge_expired_guest_data(max_age_hours=max_age_hours)
        except asyncio.CancelledError:
            logger.info("[TTL Reaper] Background task received cancellation signal.")
            break
        except Exception as e:
            logger.error(f"[TTL Reaper Loop Exception]: {e}")
            await asyncio.sleep(60)  # Brief pause before retrying


def start_reaper_background_task(interval_seconds: int = 1800, max_age_hours: float = 2.0) -> asyncio.Task:
    """Spawns the TTL reaper background worker."""
    global _reaper_task
    if _reaper_task is None or _reaper_task.done():
        loop = asyncio.get_event_loop()
        _reaper_task = loop.create_task(
            ttl_reaper_loop(interval_seconds=interval_seconds, max_age_hours=max_age_hours)
        )
    return _reaper_task


def stop_reaper_background_task():
    """Cancels the TTL reaper background worker."""
    global _reaper_task
    if _reaper_task and not _reaper_task.done():
        _reaper_task.cancel()
        _reaper_task = None
